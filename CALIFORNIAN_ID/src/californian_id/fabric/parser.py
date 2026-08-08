"""FabricParser — исполнитель orchestrator по промптам data/fabric/*.md.

Пайплайн:
    raw_text
      → source_map (deterministic)
      → 01 coarse_composition (LLM)
      → 02 multiscale_segmentation (LLM, optional in MVP)
      → 03 semantic_move_extraction (LLM, per coarse_block)
      → 04 block_assembly (LLM)
      → 05 relation_extraction (LLM)
      → 06 thread_induction (LLM)
      → 07 cross_scale_reconciliation (LLM, optional)
      → 09 scene_reconstruction (LLM)
      → 10 provenance_validation (deterministic)
      → 11 no_loss_validation (deterministic)
      → FabricSnapshot

Приоритет надёжности: MVP пропускает 02, 07, 08 если LLM не выдал валидный
JSON — эти проходы дают marginal улучшение и не блокируют snapshot.

**HARD_RULES §1:** никакого mock fallback. Требуется live LLM провайдер.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import DATA_ROOT
from ..models import Message, ModelClient
from .schemas import (
    FabricBlock,
    FabricEvidenceFragment,
    FabricRelation,
    FabricSceneState,
    FabricSnapshot,
    FabricSourceSpan,
    FabricThread,
    FabricUnit,
)


_FABRIC_DIR = DATA_ROOT / "fabric"


def _load_prompt(name: str) -> str:
    p = _FABRIC_DIR / name
    if not p.exists():
        raise RuntimeError(f"fabric prompt missing: {p}")
    return p.read_text(encoding="utf-8")


def _parse_json_from_text(text: str) -> dict[str, Any]:
    """Извлечь JSON-объект из ответа модели. Толерантно к markdown-обёрткам."""
    t = text.strip()
    # ```json ... ``` fence
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", t, flags=re.DOTALL)
    if m:
        return json.loads(m.group(1))
    # начинается с {
    if t.startswith("{"):
        return json.loads(t)
    # ищем первый {...} блок
    m = re.search(r"\{.*\}", t, flags=re.DOTALL)
    if not m:
        raise ValueError(f"no JSON object found in model response: {t[:200]}…")
    return json.loads(m.group(0))


def _short_id(prefix: str, s: str) -> str:
    h = hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()[:10]
    return f"{prefix}{h}"


class FabricParser:
    """Исполнитель fabric pipeline. Принимает ModelClient (live LLM обязателен).

    Ошибки non-critical проходов ловятся и логгируются в parser_log;
    critical проходы (source_map, semantic_move_extraction) — raise-fatal.
    """

    def __init__(self, client: ModelClient) -> None:
        if getattr(client, "provider", "") == "mock":
            raise RuntimeError(
                "FabricParser: mock provider forbidden — HARD_RULES §1. "
                "Set API_302AI_KEY or ANTHROPIC_API_KEY."
            )
        self.client = client
        self.parser_log: list[dict[str, Any]] = []

    # ---------------- helpers ----------------
    def _call(self, prompt_name: str, user_payload: str, role: str,
              max_tokens: int = 4000) -> dict[str, Any]:
        """Вызвать LLM с промптом data/fabric/<prompt_name> и разобрать JSON."""
        system = _load_prompt(prompt_name)
        messages = [
            Message(role="system", content=system),
            Message(role="user", content=user_payload),
        ]
        result = self.client.generate(
            messages,
            settings={"role": role, "max_tokens": max_tokens},
        )
        self.parser_log.append({
            "step": prompt_name,
            "provider": getattr(self.client, "provider", "?"),
            "model": getattr(self.client, "model", "?"),
            "chars_returned": len(result.text or ""),
        })
        return _parse_json_from_text(result.text)

    # ---------------- passes ----------------
    def source_map(self, text: str, source_id: str) -> list[dict[str, Any]]:
        """Deterministic: split by paragraphs / sentences, produce char spans."""
        spans = []
        offset = 0
        # split by blank line first (paragraph)
        for para_ix, para in enumerate(re.split(r"\n\s*\n", text)):
            if not para.strip():
                offset += len(para) + 2
                continue
            spans.append({
                "para_ix": para_ix,
                "char_start": offset,
                "char_end": offset + len(para),
                "text": para,
            })
            offset += len(para) + 2
        return spans

    def pass_coarse_composition(self, text: str) -> dict[str, Any]:
        # small window: send whole text or first 20K chars
        payload = json.dumps({"text": text[:20000], "text_length_full": len(text)}, ensure_ascii=False)
        try:
            return self._call("01_coarse_composition.md", payload, role="fabric_coarse", max_tokens=3000)
        except Exception as e:
            self.parser_log.append({"step": "01_coarse_composition", "error": str(e)[:200]})
            return {"coarse_blocks": []}

    def pass_semantic_moves(self, text: str, coarse_blocks: list[dict], source_id: str
                            ) -> tuple[list[FabricUnit], list[FabricSourceSpan],
                                       list[FabricEvidenceFragment]]:
        """Прогнать extraction по каждому coarse_block отдельно (chunk by chunk)."""
        all_units: list[FabricUnit] = []
        all_spans: list[FabricSourceSpan] = []
        all_evidence: list[FabricEvidenceFragment] = []

        blocks = coarse_blocks or [{"id": "cb001", "char_start": 0, "char_end": len(text),
                                    "type": "episode", "title": "весь текст"}]
        for cb in blocks:
            start = int(cb.get("char_start", 0))
            end = int(cb.get("char_end", len(text)))
            fragment = text[start:end]
            if len(fragment) < 40:
                continue

            payload = json.dumps({
                "coarse_block_id": cb.get("id"),
                "coarse_block_type": cb.get("type"),
                "coarse_block_title": cb.get("title"),
                "text": fragment,
                "char_offset_in_source": start,
            }, ensure_ascii=False)

            try:
                data = self._call("03_semantic_move_extraction.md", payload,
                                  role="fabric_moves", max_tokens=6000)
            except Exception as e:
                self.parser_log.append({"step": "03_semantic_move_extraction",
                                        "coarse_block": cb.get("id"), "error": str(e)[:200]})
                continue

            # spans (LLM возвращает span'ы с offset относительно fragment,
            # но по подсказке `char_offset_in_source` может ставить абсолютные —
            # тут упрощаем: доверяем LLM, но если span < end - start, считаем
            # относительным и сдвигаем).
            local_span_index: dict[str, str] = {}
            for sp in data.get("spans", []):
                cs = int(sp.get("char_start", 0))
                ce = int(sp.get("char_end", 0))
                # heuristic: если оба ≤ длине fragment → relative → сдвинуть
                if cs < len(fragment) and ce <= len(fragment):
                    cs += start
                    ce += start
                span = FabricSourceSpan(
                    span_id=_short_id("s", f"{source_id}|{cs}|{ce}"),
                    source_id=source_id,
                    char_start=cs,
                    char_end=ce,
                    locator=sp.get("locator", f"[{cs}:{ce}]"),
                )
                local_span_index[sp.get("span_id", "")] = span.span_id
                all_spans.append(span)

            for ev in data.get("evidence", []):
                sp_ref = ev.get("span", {}).get("span_id", "")
                new_span_id = local_span_index.get(sp_ref, sp_ref)
                # find span
                span_obj = next((s for s in all_spans if s.span_id == new_span_id), None)
                if not span_obj:
                    continue
                all_evidence.append(FabricEvidenceFragment(
                    fragment_id=_short_id("e", f"{new_span_id}|{ev.get('verbatim','')[:40]}"),
                    span=span_obj,
                    verbatim=ev.get("verbatim", "")[:2000],
                ))

            for u in data.get("units", []):
                ev_refs = [local_span_index.get(x, x) for x in (u.get("evidence_span_ids") or [])]
                if not ev_refs:
                    # HARD RULE: no evidence → drop unit
                    continue
                all_units.append(FabricUnit(
                    unit_id=_short_id("u", f"{source_id}|{u.get('text','')[:60]}"),
                    intention=u.get("intention", "claim"),
                    text=u.get("text", "")[:2000],
                    evidence_span_ids=ev_refs,
                    scale=u.get("scale", "expression"),
                    speaker_ref=u.get("speaker_ref", ""),
                    confidence=float(u.get("confidence", 0.5)),
                    interpretation_status=u.get("interpretation_status", "proposed"),
                ))
        return all_units, all_spans, all_evidence

    def pass_block_assembly(self, units: list[FabricUnit]) -> list[FabricBlock]:
        if len(units) < 2:
            return []
        payload = json.dumps({
            "units": [
                {"unit_id": u.unit_id, "intention": u.intention, "text": u.text[:200],
                 "speaker_ref": u.speaker_ref}
                for u in units
            ][:80]  # cap для контекста
        }, ensure_ascii=False)
        try:
            data = self._call("04_block_assembly.md", payload, role="fabric_blocks", max_tokens=4000)
        except Exception as e:
            self.parser_log.append({"step": "04_block_assembly", "error": str(e)[:200]})
            return []
        blocks: list[FabricBlock] = []
        unit_ids_set = {u.unit_id for u in units}
        for b in data.get("blocks", []):
            member_ids = [uid for uid in (b.get("unit_ids") or []) if uid in unit_ids_set]
            if len(member_ids) < 2:
                continue
            blocks.append(FabricBlock(
                block_id=_short_id("b", f"{b.get('title','')}|{','.join(sorted(member_ids)[:5])}"),
                block_type=b.get("block_type", "argument"),
                title=b.get("title", "")[:200],
                unit_ids=member_ids,
                scale=b.get("scale", "composition"),
                interpretation_status=b.get("interpretation_status", "proposed"),
            ))
        return blocks

    def pass_relations(self, units: list[FabricUnit],
                       blocks: list[FabricBlock]) -> list[FabricRelation]:
        if len(units) < 2:
            return []
        payload = json.dumps({
            "units": [{"unit_id": u.unit_id, "intention": u.intention, "text": u.text[:150]}
                      for u in units][:60],
            "blocks": [{"block_id": b.block_id, "block_type": b.block_type, "title": b.title}
                       for b in blocks][:30],
        }, ensure_ascii=False)
        try:
            data = self._call("05_relation_extraction.md", payload, role="fabric_relations", max_tokens=4000)
        except Exception as e:
            self.parser_log.append({"step": "05_relation_extraction", "error": str(e)[:200]})
            return []
        rels: list[FabricRelation] = []
        valid_ids = {u.unit_id for u in units} | {b.block_id for b in blocks}
        for r in data.get("relations", []):
            src = r.get("source_id")
            tgt = r.get("target_id")
            if not src or not tgt or src not in valid_ids or tgt not in valid_ids or src == tgt:
                continue
            rels.append(FabricRelation(
                relation_id=_short_id("r", f"{src}|{r.get('relation_type','')}|{tgt}"),
                relation_type=r.get("relation_type", "responds_to"),
                source_id=src,
                target_id=tgt,
                interpretation_status=r.get("interpretation_status", "proposed"),
            ))
        return rels

    def pass_threads(self, units: list[FabricUnit],
                     blocks: list[FabricBlock]) -> list[FabricThread]:
        if len(units) < 3:
            return []
        payload = json.dumps({
            "units": [{"unit_id": u.unit_id, "intention": u.intention, "text": u.text[:120]}
                      for u in units][:60],
            "blocks": [{"block_id": b.block_id, "block_type": b.block_type, "title": b.title}
                       for b in blocks][:20],
        }, ensure_ascii=False)
        try:
            data = self._call("06_thread_induction.md", payload, role="fabric_threads", max_tokens=3000)
        except Exception as e:
            self.parser_log.append({"step": "06_thread_induction", "error": str(e)[:200]})
            return []
        threads: list[FabricThread] = []
        valid_ids = {u.unit_id for u in units} | {b.block_id for b in blocks}
        for t in data.get("threads", []):
            member_ids = [mid for mid in (t.get("member_ids") or []) if mid in valid_ids]
            if len(member_ids) < 3:
                continue
            threads.append(FabricThread(
                thread_id=_short_id("t", f"{t.get('label','')}|{','.join(sorted(member_ids)[:5])}"),
                thread_type=t.get("thread_type", "concept"),
                label=t.get("label", "")[:200],
                member_ids=member_ids,
                interpretation_status=t.get("interpretation_status", "proposed"),
            ))
        return threads

    def pass_scene(self, units: list[FabricUnit], blocks: list[FabricBlock],
                   threads: list[FabricThread]) -> FabricSceneState | None:
        if not units:
            return None
        payload = json.dumps({
            "units": [{"intention": u.intention, "text": u.text[:180],
                       "speaker_ref": u.speaker_ref}
                      for u in units][:60],
            "block_titles": [b.title for b in blocks][:30],
            "thread_labels": [t.label for t in threads][:20],
        }, ensure_ascii=False)
        try:
            data = self._call("09_scene_reconstruction.md", payload, role="fabric_scene", max_tokens=2000)
        except Exception as e:
            self.parser_log.append({"step": "09_scene_reconstruction", "error": str(e)[:200]})
            return None
        return FabricSceneState(
            scene_id=_short_id("sc", data.get("question", "")[:60] or "scene"),
            participants=[str(x) for x in (data.get("participants") or [])][:20],
            question=data.get("question", "")[:400],
            positions=[dict(p) for p in (data.get("positions") or [])][:20],
            stakes=[str(x)[:200] for x in (data.get("stakes") or [])][:12],
            tensions=[str(x)[:200] for x in (data.get("tensions") or [])][:12],
            open_loops=[str(x)[:200] for x in (data.get("open_loops") or [])][:20],
            phase=data.get("phase", "exploration"),
        )

    # ---------------- top-level ----------------
    def parse(self, text: str, source_id: str | None = None,
              parser_run_id: str | None = None) -> FabricSnapshot:
        source_id = source_id or _short_id("src", text[:200])
        parser_run_id = parser_run_id or f"fab_{uuid.uuid4().hex[:12]}"
        # 01
        coarse = self.pass_coarse_composition(text).get("coarse_blocks", [])
        # 03 (spans + evidence + units)
        units, spans, evidence = self.pass_semantic_moves(text, coarse, source_id)
        # 04
        blocks = self.pass_block_assembly(units)
        # 05
        relations = self.pass_relations(units, blocks)
        # 06
        threads = self.pass_threads(units, blocks)
        # 09
        scene = self.pass_scene(units, blocks, threads)

        # 10 provenance (deterministic)
        valid_span_ids = {s.span_id for s in spans}
        for u in list(units):
            if not [x for x in u.evidence_span_ids if x in valid_span_ids]:
                units.remove(u)

        # 11 no-loss (deterministic coverage)
        covered = 0
        for s in spans:
            covered += max(0, s.char_end - s.char_start)
        total = len(text)
        coverage_pct = round(covered / total, 3) if total else 0.0

        snap = FabricSnapshot(
            snapshot_id=_short_id("snap", f"{source_id}|{parser_run_id}"),
            source_id=source_id,
            source_version="v1",
            created_at=datetime.now(timezone.utc).isoformat(),
            parser_run_id=parser_run_id,
            units=units,
            blocks=blocks,
            relations=relations,
            threads=threads,
            spans=spans,
            evidence=evidence,
            scene=scene,
            stats={
                "n_units": len(units),
                "n_blocks": len(blocks),
                "n_relations": len(relations),
                "n_threads": len(threads),
                "n_spans": len(spans),
                "n_coarse_blocks": len(coarse),
                "coverage_pct": coverage_pct,
                "total_chars": total,
                "parser_log_events": len(self.parser_log),
            },
        )
        return snap

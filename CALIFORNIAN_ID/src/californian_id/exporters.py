"""Пик 8.1 — ExportService.

Форматы:
  - json   — сырой payload из <workspace>/results/<run_id>.json.
  - md     — читаемая markdown-версия (закрытие + список ходов).
  - bundle — tar.gz со всем: result.json, closing.md, trace_dir/*, fabric snapshot.
"""
from __future__ import annotations

import io
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .async_jobs import result_path
from .workspaces import RunStore, validate_workspace_id, workspace_dir


def export_json(workspace_id: str, run_id: str) -> bytes | None:
    p = result_path(validate_workspace_id(workspace_id), run_id)
    if not p.exists():
        return None
    return p.read_bytes()


def _md_from_payload(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# Run `{payload.get('run_id', '?')}`")
    lines.append("")
    lines.append(f"- **workspace**: `{payload.get('workspace_id') or 'default'}`")
    lines.append(f"- **mode**: {payload.get('mode', '?')}")
    lines.append(f"- **status**: {payload.get('status', '?')}")
    lines.append(f"- **stopping_reason**: {payload.get('stopping_reason', '')}")
    lines.append(f"- **input_mode**: {payload.get('input_mode', '')}")
    lines.append(f"- **turns**: {payload.get('turn_count', 0)}")
    lines.append(f"- **voices_used**: {', '.join(payload.get('voices_used') or [])}")
    lines.append("")

    completion = payload.get("completion") or {}
    form = completion.get("form") or ""
    if form:
        lines.append(f"## Форма завершения: `{form}`")
        lines.append("")
        rationale = completion.get("rationale") or ""
        if rationale:
            lines.append(f"**Почему эта форма:** {rationale}")
            lines.append("")

    closing = payload.get("closing_speech") or completion.get("closing_speech") or ""
    if closing:
        lines.append("## Заключительная речь Заратустры")
        lines.append("")
        lines.append(closing)
        lines.append("")

    turns = payload.get("turns") or []
    if turns:
        lines.append(f"## Ходы совета ({len(turns)})")
        lines.append("")
        for t in turns:
            idx = t.get("turn_index", "?")
            pid = t.get("persona_id", "?")
            op = t.get("operation", "?")
            utt = (t.get("utterance") or "").strip()
            lines.append(f"### T{idx} · `{pid}` · `{op}`")
            lines.append("")
            lines.append(utt)
            lines.append("")

    conflict_map = completion.get("conflict_map") or []
    if conflict_map:
        lines.append("## Карта конфликтов")
        lines.append("")
        for c in conflict_map:
            lines.append(f"- **{c.get('tension','')}** [{c.get('status','')}]")
            lines.append(f"  - {c.get('side_a','')}  ↔  {c.get('side_b','')}")
        lines.append("")

    minority = completion.get("minority_positions") or []
    if minority:
        lines.append("## Меньшинственные позиции")
        lines.append("")
        for m in minority:
            lines.append(f"- **[{m.get('persona_id','?')}]** {m.get('text','')}")
        lines.append("")

    unresolved = completion.get("unresolved_questions") or []
    if unresolved:
        lines.append("## Нерешённые вопросы")
        lines.append("")
        for q in unresolved:
            lines.append(f"- {q}")
        lines.append("")

    lines.append("---")
    lines.append(
        f"_exported at {datetime.now(timezone.utc).isoformat()} · "
        f"trace_dir: `{payload.get('trace_dir','')}`_"
    )
    return "\n".join(lines)


def export_markdown(workspace_id: str, run_id: str) -> bytes | None:
    raw = export_json(workspace_id, run_id)
    if raw is None:
        return None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        return None
    return _md_from_payload(payload).encode("utf-8")


def export_bundle(workspace_id: str, run_id: str) -> bytes | None:
    """tar.gz с result.json + closing.md + trace_dir (если существует)."""
    ws = validate_workspace_id(workspace_id)
    raw = export_json(ws, run_id)
    if raw is None:
        return None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        payload = {}

    md = _md_from_payload(payload).encode("utf-8") if payload else b""
    trace_dir_str = payload.get("trace_dir") or ""

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        # result.json
        info = tarfile.TarInfo(name=f"{run_id}/result.json")
        info.size = len(raw)
        info.mtime = int(datetime.now(timezone.utc).timestamp())
        tar.addfile(info, io.BytesIO(raw))
        # closing.md
        if md:
            info = tarfile.TarInfo(name=f"{run_id}/closing.md")
            info.size = len(md)
            info.mtime = int(datetime.now(timezone.utc).timestamp())
            tar.addfile(info, io.BytesIO(md))
        # RunMetadata snapshot from RunStore
        store = RunStore.for_workspace(ws)
        try:
            m = store.get(run_id)
        finally:
            store.close()
        if m is not None:
            meta_json = json.dumps(m.__dict__, ensure_ascii=False,
                                   indent=2, default=str).encode("utf-8")
            info = tarfile.TarInfo(name=f"{run_id}/metadata.json")
            info.size = len(meta_json)
            info.mtime = int(datetime.now(timezone.utc).timestamp())
            tar.addfile(info, io.BytesIO(meta_json))
        # B-5.5 Веха 5 — interventions audit (pause/resume/cancel/steer/…)
        try:
            from . import runtime_control
            iv_store = runtime_control.InterventionStore.for_workspace(ws)
            try:
                interventions = iv_store.list_for_run(run_id)
            finally:
                iv_store.close()
            if interventions:
                lines = []
                for iv in interventions:
                    lines.append(json.dumps({
                        "intervention_id": iv.intervention_id,
                        "kind": iv.kind, "author": iv.author,
                        "payload": iv.payload,
                        "at_turn_index": iv.at_turn_index,
                        "applied": iv.applied,
                        "applied_at": iv.applied_at,
                        "created_at": iv.created_at,
                    }, ensure_ascii=False, default=str))
                iv_body = ("\n".join(lines) + "\n").encode("utf-8")
                info = tarfile.TarInfo(name=f"{run_id}/interventions.jsonl")
                info.size = len(iv_body)
                info.mtime = int(datetime.now(timezone.utc).timestamp())
                tar.addfile(info, io.BytesIO(iv_body))
        except Exception:
            pass
        # trace_dir (если существует и в пределах workspace)
        if trace_dir_str:
            trace_dir = Path(trace_dir_str)
            if trace_dir.exists() and trace_dir.is_dir():
                for f in sorted(trace_dir.rglob("*")):
                    if not f.is_file():
                        continue
                    try:
                        data = f.read_bytes()
                    except Exception:
                        continue
                    rel = f.relative_to(trace_dir)
                    info = tarfile.TarInfo(name=f"{run_id}/trace/{rel.as_posix()}")
                    info.size = len(data)
                    info.mtime = int(datetime.now(timezone.utc).timestamp())
                    tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def content_type_for(fmt: str) -> str:
    return {
        "json": "application/json; charset=utf-8",
        "md": "text/markdown; charset=utf-8",
        "bundle": "application/gzip",
    }.get(fmt, "application/octet-stream")


def filename_for(run_id: str, fmt: str) -> str:
    ext = {"json": ".json", "md": ".md", "bundle": ".tar.gz"}.get(fmt, ".bin")
    return f"tinkuy-{run_id}{ext}"

from __future__ import annotations

import json
import math
import sqlite3
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .config import PERSONA_LAYER_ROOT


BASE_FALLBACK_ORDER = ["C", "EA", "Ex", "L", "R", "S", "T"]

# NOTE: since v0.4.3 the routing lexicon lives in data, not in this module.
#   - per-persona topics: runtime_assets/personas/v0.2/personas/<ID>/manifest.yaml::routing.topics.{en,ru}
#   - cross-cutting triggers: runtime_assets/personas/v0.2/registry/routing_policy.yaml
# The three deleted constants used to be ROUTING_KEYWORDS / FULL_COUNCIL_KEYWORDS /
# NEMO8_TRIGGER_KEYWORDS, all English-only. Loading is now bilingual and swappable
# per persona pack — see load_routing_policy() below.


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _dump_yaml(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in "".join(ch if ch.isalnum() else " " for ch in text).split() if len(t) > 1]


@dataclass
class PersonaLayerIssue:
    scope: str
    detail: str
    severity: str = "error"


@dataclass
class PersonaCard:
    raw: dict[str, Any]

    @property
    def card_id(self) -> str:
        return str(self.raw["card_id"])

    @property
    def persona_id(self) -> str:
        return str(self.raw["persona_id"])

    @property
    def operation_id_exact(self) -> str:
        if self.raw.get("operation_id_exact"):
            return str(self.raw["operation_id_exact"])
        ops = self.raw.get("operation_ids") or []
        return str(ops[0]) if ops else ""

    @property
    def retrieval_namespace(self) -> str:
        return str(self.raw.get("retrieval_namespace") or self.raw.get("namespace") or "")

    @property
    def retrieval_text(self) -> str:
        return str(self.raw.get("retrieval_text") or self.raw.get("statement") or "")

    @property
    def secondary_operation_ids(self) -> list[str]:
        if self.raw.get("secondary_operation_ids"):
            return [str(x) for x in self.raw.get("secondary_operation_ids") or []]
        ops = [str(x) for x in self.raw.get("operation_ids") or []]
        return ops[1:]


@dataclass
class PersonaPackage:
    persona_id: str
    manifest: dict[str, Any]
    cards: list[PersonaCard]
    operations: list[dict[str, Any]]
    package_dir: Path

    @property
    def display_name(self) -> str:
        return str(self.manifest.get("display_name") or self.persona_id)

    @property
    def enabled(self) -> bool:
        return bool(self.manifest.get("enabled", True))


@dataclass
class PersonaLayerRegistry:
    personas: dict[str, PersonaPackage] = field(default_factory=dict)
    issues: list[PersonaLayerIssue] = field(default_factory=list)
    registry_root: Path = PERSONA_LAYER_ROOT

    def enabled_base(self) -> list[PersonaPackage]:
        return [p for pid, p in self.personas.items() if pid != "N8" and p.enabled]

    def nemo8(self) -> PersonaPackage | None:
        return self.personas.get("N8")


@dataclass
class RoutingPolicy:
    """Routing lexicon loaded from data (persona manifests + registry policy).

    Replaces the deleted Python constants ROUTING_KEYWORDS /
    FULL_COUNCIL_KEYWORDS / NEMO8_TRIGGER_KEYWORDS. All phrases are lower-cased,
    stemmed where useful (Russian), and matched via substring `in scene.lower()`.
    """
    per_persona: dict[str, list[str]] = field(default_factory=dict)
    full_council: list[str] = field(default_factory=list)
    nemo8: list[str] = field(default_factory=list)

    def keywords_for(self, persona_id: str) -> list[str]:
        return self.per_persona.get(persona_id, [])


def _flatten_bilingual(payload: Any) -> list[str]:
    """Accepts dict {en:[...], ru:[...]} OR flat list; returns lowered union."""
    if payload is None:
        return []
    if isinstance(payload, dict):
        buckets: list[str] = []
        for lang_key in ("en", "ru"):
            v = payload.get(lang_key) or []
            if isinstance(v, list):
                buckets.extend(str(x).lower() for x in v)
        # unknown-language buckets too
        for k, v in payload.items():
            if k in ("en", "ru"):
                continue
            if isinstance(v, list):
                buckets.extend(str(x).lower() for x in v)
        return sorted(set(b for b in buckets if b))
    if isinstance(payload, list):
        return sorted({str(x).lower() for x in payload if x})
    return []


def load_routing_policy(
    root: Path,
    personas: dict[str, "PersonaPackage"],
) -> RoutingPolicy:
    """Read routing lexicon from data.

    Sources:
      - per-persona: <root>/personas/<ID>/manifest.yaml -> routing.topics
      - cross-cutting: <root>/registry/routing_policy.yaml -> full_council_triggers / nemo8_triggers
    Both accept either bilingual dict {en:[...], ru:[...]} or a flat list.
    Missing sources => empty policy (system degrades to persona order).
    """
    per_persona: dict[str, list[str]] = {}
    for pid, pkg in personas.items():
        routing = pkg.manifest.get("routing") or {}
        topics = routing.get("topics")
        per_persona[pid] = _flatten_bilingual(topics)

    full_council: list[str] = []
    nemo8: list[str] = []
    policy_path = root / "registry" / "routing_policy.yaml"
    if policy_path.exists():
        policy_doc = _load_yaml(policy_path) or {}
        full_council = _flatten_bilingual(policy_doc.get("full_council_triggers"))
        nemo8 = _flatten_bilingual(policy_doc.get("nemo8_triggers"))

    return RoutingPolicy(per_persona=per_persona, full_council=full_council, nemo8=nemo8)


def load_persona_layer_registry(root: Path = PERSONA_LAYER_ROOT) -> PersonaLayerRegistry:
    reg = PersonaLayerRegistry(registry_root=root)
    personas_root = root / "personas"
    if not personas_root.exists():
        reg.issues.append(PersonaLayerIssue("registry", f"missing personas root: {personas_root}"))
        return reg
    for pkg_dir in sorted(p for p in personas_root.iterdir() if p.is_dir()):
        manifest_path = pkg_dir / "manifest.yaml"
        cards_path = pkg_dir / "cards.jsonl"
        operations_path = pkg_dir / "operations.yaml"
        if not manifest_path.exists():
            reg.issues.append(PersonaLayerIssue(pkg_dir.name, "missing manifest.yaml"))
            continue
        manifest = _load_yaml(manifest_path)
        cards: list[PersonaCard] = []
        if cards_path.exists():
            for line_no, line in enumerate(cards_path.read_text(encoding="utf-8").splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    cards.append(PersonaCard(json.loads(line)))
                except json.JSONDecodeError as exc:
                    reg.issues.append(PersonaLayerIssue(pkg_dir.name, f"cards.jsonl:{line_no}: {exc}"))
        else:
            reg.issues.append(PersonaLayerIssue(pkg_dir.name, "missing cards.jsonl"))
        operations_payload = _load_yaml(operations_path) if operations_path.exists() else {}
        operations = operations_payload.get("operations") if isinstance(operations_payload, dict) else operations_payload
        if not isinstance(operations, list):
            operations = []
        persona_id = str(manifest.get("persona_id") or pkg_dir.name)
        if persona_id in reg.personas:
            reg.issues.append(PersonaLayerIssue(persona_id, "duplicate persona_id"))
            continue
        reg.personas[persona_id] = PersonaPackage(
            persona_id=persona_id,
            manifest=manifest,
            cards=cards,
            operations=operations,
            package_dir=pkg_dir,
        )
    return reg


@dataclass
class RetrievalHit:
    card_id: str
    persona_id: str
    operation_id_exact: str
    retrieval_namespace: str
    score: float
    lexical_score: float
    semantic_score: float
    provenance_status: str


class PersonaIndex:
    def __init__(self, root: Path = PERSONA_LAYER_ROOT) -> None:
        self.root = root
        self.build_dir = root / "retrieval" / "build"
        self.manifest_path = root / "retrieval" / "index_manifest.yaml"
        self.sqlite_path = self.build_dir / "persona_index.sqlite"
        self.tfidf_path = self.build_dir / "tfidf.json"
        self.cards_snapshot_path = self.build_dir / "cards_snapshot.jsonl"

    def _all_cards(self, reg: PersonaLayerRegistry) -> list[PersonaCard]:
        cards: list[PersonaCard] = []
        for pkg in reg.personas.values():
            cards.extend(pkg.cards)
        return cards

    def rebuild(self, reg: PersonaLayerRegistry, build_command: str) -> dict[str, Any]:
        self.build_dir.mkdir(parents=True, exist_ok=True)
        cards = self._all_cards(reg)
        tokenised = {c.card_id: _tokens(c.retrieval_text) for c in cards}
        df: Counter[str] = Counter()
        for toks in tokenised.values():
            for tok in set(toks):
                df[tok] += 1
        n_docs = max(1, len(cards))
        idf = {tok: math.log(1 + (n_docs - freq + 0.5) / (freq + 0.5)) for tok, freq in df.items()}
        docs = {}
        for card in cards:
            toks = tokenised[card.card_id]
            tf = Counter(toks)
            norm = math.sqrt(sum(((tf[t] / max(1, len(toks))) * idf.get(t, 0.0)) ** 2 for t in tf))
            docs[card.card_id] = {
                "tokens": toks,
                "tf": dict(tf),
                "norm": norm,
                "persona_id": card.persona_id,
                "operation_id_exact": card.operation_id_exact,
                "secondary_operation_ids": card.secondary_operation_ids,
                "retrieval_namespace": card.retrieval_namespace,
                "provenance_status": str(card.raw.get("provenance_status") or "unknown"),
            }
        self.tfidf_path.write_text(json.dumps({"idf": idf, "docs": docs}, ensure_ascii=False, indent=2), encoding="utf-8")
        with self.cards_snapshot_path.open("w", encoding="utf-8") as fh:
            for card in cards:
                fh.write(json.dumps(card.raw, ensure_ascii=False) + "\n")

        if self.sqlite_path.exists():
            self.sqlite_path.unlink()
        conn = sqlite3.connect(self.sqlite_path)
        conn.execute("CREATE VIRTUAL TABLE cards USING fts5(card_id, persona_id, operation_id_exact, secondary_operation_ids, retrieval_namespace, provenance_status, retrieval_text)")
        for card in cards:
            conn.execute(
                "INSERT INTO cards(card_id, persona_id, operation_id_exact, secondary_operation_ids, retrieval_namespace, provenance_status, retrieval_text) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    card.card_id,
                    card.persona_id,
                    card.operation_id_exact,
                    " ".join(card.secondary_operation_ids),
                    card.retrieval_namespace,
                    str(card.raw.get("provenance_status") or "unknown"),
                    card.retrieval_text,
                ),
            )
        conn.commit()
        conn.close()

        package_versions = {pid: pkg.manifest.get("version", "?") for pid, pkg in reg.personas.items()}
        manifest = {
            "index_version": "0.2.0",
            "source_package_versions": package_versions,
            "personas": sorted(reg.personas),
            "card_count": len(cards),
            "operation_count": len({
                str(op.get("operation_id"))
                for pkg in reg.personas.values()
                for op in pkg.operations
                if op.get("operation_id")
            }),
            "schema_hash": str((self.root / "schemas" / "PERSONA_CARD_SCHEMA.json").exists()),
            "source_hashes": {
                "cards_snapshot_sha256": _sha256_file(self.cards_snapshot_path),
                "sqlite_sha256": _sha256_file(self.sqlite_path),
                "tfidf_sha256": _sha256_file(self.tfidf_path),
            },
            "build_command": build_command,
            "build_time": datetime.now(timezone.utc).isoformat(),
            "backend_versions": {
                "sqlite": sqlite3.sqlite_version,
                "tfidf": "builtin_python",
            },
            "backend": "sqlite_fts5_plus_builtin_tfidf",
        }
        _dump_yaml(self.manifest_path, manifest)
        return manifest

    def query(
        self,
        reg: PersonaLayerRegistry,
        query: str,
        *,
        persona_id: str | None = None,
        operation_id_exact: str | None = None,
        secondary_operation_id: str | None = None,
        retrieval_namespace: str | None = None,
        provenance_status: str | None = None,
        top_k: int = 5,
    ) -> list[RetrievalHit]:
        cards_by_id = {card.card_id: card for card in self._all_cards(reg)}
        lexical_scores: dict[str, float] = defaultdict(float)
        query_terms = _tokens(query)
        fts_query = " ".join(query_terms)
        if self.sqlite_path.exists() and fts_query:
            conn = sqlite3.connect(self.sqlite_path)
            sql = "SELECT card_id, bm25(cards) FROM cards WHERE cards MATCH ?"
            try:
                rows = conn.execute(sql, (fts_query,)).fetchall()
            except sqlite3.OperationalError:
                rows = []
            conn.close()
            for card_id, score in rows:
                lexical_scores[card_id] = max(0.0, 1.0 / (1.0 + float(score)))
        if not lexical_scores and query_terms:
            for card_id, card in cards_by_id.items():
                doc_terms = set(_tokens(card.retrieval_text))
                overlap = len(set(query_terms) & doc_terms)
                if overlap:
                    lexical_scores[card_id] = overlap / max(1, len(set(query_terms)))

        semantic_scores: dict[str, float] = defaultdict(float)
        if self.tfidf_path.exists():
            payload = json.loads(self.tfidf_path.read_text(encoding="utf-8"))
            idf = payload["idf"]
            docs = payload["docs"]
            q_toks = query_terms
            q_tf = Counter(q_toks)
            q_vec = {tok: (q_tf[tok] / max(1, len(q_toks))) * idf.get(tok, 0.0) for tok in q_tf}
            q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0
            for card_id, doc in docs.items():
                dot = 0.0
                for tok, qv in q_vec.items():
                    dv = (doc["tf"].get(tok, 0) / max(1, len(doc["tokens"]))) * idf.get(tok, 0.0)
                    dot += qv * dv
                semantic_scores[card_id] = dot / (q_norm * (doc["norm"] or 1.0))

        combined: list[RetrievalHit] = []
        for card_id, card in cards_by_id.items():
            if persona_id and card.persona_id != persona_id:
                continue
            if operation_id_exact and card.operation_id_exact != operation_id_exact:
                continue
            if secondary_operation_id and secondary_operation_id not in card.secondary_operation_ids:
                continue
            if retrieval_namespace and card.retrieval_namespace != retrieval_namespace:
                continue
            if provenance_status and str(card.raw.get("provenance_status")) != provenance_status:
                continue
            lex = lexical_scores.get(card_id, 0.0)
            sem = semantic_scores.get(card_id, 0.0)
            if lex <= 0 and sem <= 0:
                continue
            combined.append(
                RetrievalHit(
                    card_id=card_id,
                    persona_id=card.persona_id,
                    operation_id_exact=card.operation_id_exact,
                    retrieval_namespace=card.retrieval_namespace,
                    score=(0.6 * lex) + (0.4 * sem),
                    lexical_score=lex,
                    semantic_score=sem,
                    provenance_status=str(card.raw.get("provenance_status") or "unknown"),
                )
            )
        combined.sort(key=lambda hit: (-hit.score, hit.card_id))
        return combined[:top_k]

    def is_stale(self, reg: PersonaLayerRegistry) -> bool:
        outputs = [self.manifest_path, self.sqlite_path, self.tfidf_path, self.cards_snapshot_path]
        if any(not path.exists() for path in outputs):
            return True
        built_at = min(path.stat().st_mtime for path in outputs)
        inputs: list[Path] = []
        for pkg in reg.personas.values():
            inputs.extend([
                pkg.package_dir / "manifest.yaml",
                pkg.package_dir / "cards.jsonl",
                pkg.package_dir / "operations.yaml",
            ])
        inputs.extend([
            self.root / "registry" / "CARD_TO_EXACT_OPERATION_REGISTRY.yaml",
            self.root / "registry" / "PERSONA_OPERATION_REGISTRY.yaml",
        ])
        return any(path.exists() and path.stat().st_mtime > built_at for path in inputs)


@dataclass
class MetaChallenge:
    target: str
    challenge_type: str
    reopen_persona_ids: list[str]
    reopen_operation_ids: list[str]
    unresolved: list[str]
    confidence: float


@dataclass
class CouncilTurn:
    turn_id: str
    persona_id: str
    operation_id: str
    card_id: str
    utterance: str
    body_delta: dict[str, Any]
    provenance: list[dict[str, Any]]
    meta_challenge: MetaChallenge | None = None


@dataclass
class CouncilRun:
    run_id: str
    base_turns: list[CouncilTurn]
    nemo8_turn: CouncilTurn | None
    reopened_turns: list[CouncilTurn]
    final_answer: str
    minority_positions: list[str]
    trace: dict[str, Any]


@dataclass
class RoutePlan:
    council_span: str
    cast_mode: str
    selected_persona_ids: list[str]
    execution_order: list[str]
    persona_scores: dict[str, float]
    call_nemo8: bool
    full_council_required: bool
    fixed_order_fallback_used: bool
    rationale: str


class PersonaCouncilRuntime:
    def __init__(self, root: Path = PERSONA_LAYER_ROOT) -> None:
        self.root = root
        self.registry = load_persona_layer_registry(root)
        self.index = PersonaIndex(root)
        self.routing = load_routing_policy(root, self.registry.personas)

    def ensure_index(self) -> dict[str, Any]:
        if not self.index.is_stale(self.registry):
            return _load_yaml(self.index.manifest_path)
        return self.index.rebuild(self.registry, "python -m californian_id persona-layer rebuild-index")

    def plan_route(
        self,
        scene: str,
        *,
        enable_nemo8: bool = True,
        force_span: str | None = None,
    ) -> RoutePlan:
        scene_low = scene.lower()
        scores: dict[str, float] = {}
        for persona_id in BASE_FALLBACK_ORDER:
            score = 0.0
            for phrase in self.routing.keywords_for(persona_id):
                if phrase in scene_low:
                    score += 1.0 if " " not in phrase else 1.5
            scores[persona_id] = score

        ranked = sorted(BASE_FALLBACK_ORDER, key=lambda pid: (-scores[pid], BASE_FALLBACK_ORDER.index(pid)))
        positive = [pid for pid in ranked if scores[pid] > 0]
        forced_targets = {
            "force_pair": 2,
            "force_triangular": 3,
            "force_full_council": len(BASE_FALLBACK_ORDER),
        }
        council_span = force_span if force_span in forced_targets else "auto"
        full_council_required = len(positive) >= 4 and any(word in scene_low for word in self.routing.full_council)
        fixed_order_fallback_used = False

        if council_span == "force_full_council":
            cast_mode = "forced_full_council"
            selected = list(BASE_FALLBACK_ORDER)
            execution_order = list(BASE_FALLBACK_ORDER)
            full_council_required = True
            fixed_order_fallback_used = True
            rationale = "UI forced a full seven-head council before NEMO-8 review."
        elif council_span in {"force_pair", "force_triangular"}:
            target = forced_targets[council_span]
            selected = ranked[:target]
            execution_order = list(selected)
            fixed_order_fallback_used = len(positive) < target
            cast_mode = "forced_pair" if target == 2 else "forced_triangular"
            rationale = (
                f"UI forced a {target}-head council span; runtime padded from fallback ranking where topical matches were insufficient."
                if fixed_order_fallback_used else
                f"UI forced a {target}-head council span using the strongest topical matches."
            )
        elif full_council_required:
            cast_mode = "full_council"
            selected = list(BASE_FALLBACK_ORDER)
            execution_order = list(BASE_FALLBACK_ORDER)
            fixed_order_fallback_used = True
            rationale = "High-stakes multi-domain scene triggered explicit full-council mode."
        elif len(positive) >= 3:
            cast_mode = "triangular_probe"
            selected = positive[:3]
            execution_order = list(selected)
            rationale = "Three relevant heads were sufficient to avoid false binary closure."
        elif len(positive) == 2:
            cast_mode = "productive_pair"
            selected = positive[:2]
            execution_order = list(selected)
            rationale = "A productive pair captured the dominant tension without forcing a full council."
        elif len(positive) == 1:
            cast_mode = "single_head"
            selected = positive[:1]
            execution_order = list(selected)
            rationale = "A single head had a clear local match to the scene."
        else:
            cast_mode = "single_head"
            selected = ["R"]
            execution_order = ["R"]
            fixed_order_fallback_used = True
            rationale = "No strong topical match; falling back to Rationalist as the generic evidence-audit entrypoint."

        call_nemo8 = bool(
            enable_nemo8
            and self.registry.nemo8()
            and (full_council_required or any(word in scene_low for word in self.routing.nemo8))
        )
        return RoutePlan(
            council_span=council_span,
            cast_mode=cast_mode,
            selected_persona_ids=selected,
            execution_order=execution_order,
            persona_scores=scores,
            call_nemo8=call_nemo8,
            full_council_required=full_council_required,
            fixed_order_fallback_used=fixed_order_fallback_used,
            rationale=rationale,
        )

    def run(
        self,
        scene: str,
        *,
        enable_nemo8: bool = True,
        force_span: str | None = None,
    ) -> CouncilRun:
        self.ensure_index()
        run_id = f"persona_layer_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:6]}"
        route_plan = self.plan_route(scene, enable_nemo8=enable_nemo8, force_span=force_span)
        base_turns: list[CouncilTurn] = []
        for persona_id in route_plan.execution_order:
            pkg = self.registry.personas[persona_id]
            hits = self.index.query(self.registry, scene, persona_id=pkg.persona_id, top_k=1)
            if not hits:
                continue
            card = _card_by_id(pkg, hits[0].card_id)
            base_turns.append(_turn_from_card(run_id, card, scene))
        conflict_personas = sorted({t.persona_id for t in base_turns[:3]})
        minority_positions = [f"{t.persona_id}:{t.operation_id}" for t in base_turns[-2:]]
        provisional = _provisional_synthesis(scene, base_turns)
        nemo8_turn = None
        reopened_turns: list[CouncilTurn] = []
        reopen_decision = {"accepted": False, "reason": "nemo8_disabled"}
        if route_plan.call_nemo8 and self.registry.nemo8():
            nemo8_hits = self.index.query(self.registry, scene, persona_id="N8", top_k=3)
            if nemo8_hits:
                chosen = _pick_nemo8_hit(nemo8_hits, scene)
                card = _card_by_id(self.registry.nemo8(), chosen.card_id)
                challenge = _nemo8_challenge(scene, provisional, conflict_personas, card)
                nemo8_turn = _turn_from_card(run_id, card, scene, meta_challenge=challenge)
                if challenge.reopen_persona_ids:
                    reopen_decision = {
                        "accepted": True,
                        "reason": "false_consensus_risk" if "consensus" in challenge.challenge_type else "high_tension",
                    }
                    for pid in challenge.reopen_persona_ids[:2]:
                        pkg = self.registry.personas[pid]
                        hits = self.index.query(self.registry, scene, persona_id=pid, top_k=2)
                        if hits:
                            reopened_turns.append(_turn_from_card(run_id, _card_by_id(pkg, hits[-1].card_id), scene))
        final_answer = _final_synthesis(scene, base_turns, nemo8_turn, reopened_turns)
        trace = {
            "run_id": run_id,
            "scene": scene,
            "route_plan": {
                "council_span": route_plan.council_span,
                "cast_mode": route_plan.cast_mode,
                "selected_persona_ids": route_plan.selected_persona_ids,
                "execution_order": route_plan.execution_order,
                "persona_scores": route_plan.persona_scores,
                "call_nemo8": route_plan.call_nemo8,
                "full_council_required": route_plan.full_council_required,
                "fixed_order_fallback_used": route_plan.fixed_order_fallback_used,
                "rationale": route_plan.rationale,
            },
            "base_turns": [t.__dict__ | {"meta_challenge": _plain_meta(t.meta_challenge)} for t in base_turns],
            "provisional_synthesis": provisional,
            "nemo8_turn": None if nemo8_turn is None else nemo8_turn.__dict__ | {"meta_challenge": _plain_meta(nemo8_turn.meta_challenge)},
            "reopened_turns": [t.__dict__ for t in reopened_turns],
            "reopen_decision": reopen_decision,
            "final_answer": final_answer,
            "minority_positions": minority_positions,
        }
        return CouncilRun(
            run_id=run_id,
            base_turns=base_turns,
            nemo8_turn=nemo8_turn,
            reopened_turns=reopened_turns,
            final_answer=final_answer,
            minority_positions=minority_positions,
            trace=trace,
        )


def _card_by_id(pkg: PersonaPackage | None, card_id: str) -> PersonaCard:
    if pkg is None:
        raise KeyError(card_id)
    for card in pkg.cards:
        if card.card_id == card_id:
            return card
    raise KeyError(card_id)


def _turn_from_card(run_id: str, card: PersonaCard, scene: str, *, meta_challenge: MetaChallenge | None = None) -> CouncilTurn:
    body_delta = {
        "concepts_added": [card.raw.get("title", "")],
        "tensions_added": card.raw.get("activation_conditions") or [],
        "risks_added": card.raw.get("expected_body_delta") or [],
        "meta_challenge": _plain_meta(meta_challenge),
    }
    return CouncilTurn(
        turn_id=f"{run_id}:{card.persona_id}:{card.card_id}",
        persona_id=card.persona_id,
        operation_id=card.operation_id_exact,
        card_id=card.card_id,
        utterance=f"{card.persona_id} / {card.operation_id_exact}: {card.raw.get('statement', '')}",
        body_delta=body_delta,
        provenance=card.raw.get("source_refs") or [],
        meta_challenge=meta_challenge,
    )


def _provisional_synthesis(scene: str, turns: list[CouncilTurn]) -> str:
    del scene
    ops = ", ".join(sorted({t.operation_id for t in turns[:4]})) or "no_base_operations"
    personas = ", ".join(t.persona_id for t in turns[:4]) or "no-base-heads"
    return (
        "Provisional synthesis: "
        f"base council mapped the scene through operations {ops} and initial voices {personas}."
    )


def _pick_nemo8_hit(hits: list[RetrievalHit], scene: str) -> RetrievalHit:
    ranked = sorted(hits, key=lambda hit: ("consensus" not in scene.lower(), -hit.score, hit.card_id))
    return ranked[0]


def _nemo8_challenge(scene: str, provisional: str, conflict_personas: list[str], card: PersonaCard) -> MetaChallenge:
    query_low = scene.lower()
    challenge_type = "false_consensus_risk" if any(word in query_low for word in ("charter", "mandatory", "governance", "consensus")) else "unresolved_high_tension"
    reopen_personas = conflict_personas[:2] if challenge_type else []
    return MetaChallenge(
        target=provisional,
        challenge_type=challenge_type,
        reopen_persona_ids=reopen_personas,
        reopen_operation_ids=[card.operation_id_exact],
        unresolved=[str(x) for x in card.raw.get("activation_conditions") or []][:2],
        confidence=0.71,
    )


def _final_synthesis(scene: str, base_turns: list[CouncilTurn], nemo8_turn: CouncilTurn | None, reopened_turns: list[CouncilTurn]) -> str:
    del scene
    base_ids = ", ".join(t.persona_id for t in base_turns[:4]) or "no-base-heads"
    if nemo8_turn is None:
        return (
            "Zarathustra final synthesis: "
            f"base council only ({base_ids}); minority positions preserved."
        )
    if reopened_turns:
        reopened = ", ".join(t.persona_id for t in reopened_turns)
        return (
            "Zarathustra final synthesis: base council ran first, "
            f"NEMO-8 challenged the provisional closure, {reopened} reopened, and the final answer preserves dissent."
        )
    return (
        "Zarathustra final synthesis: base council ran first, "
        "NEMO-8 added a meta-pass, and Zarathustra retained final authority."
    )


def _plain_meta(meta: MetaChallenge | None) -> dict[str, Any] | None:
    if meta is None:
        return None
    return {
        "target": meta.target,
        "challenge_type": meta.challenge_type,
        "reopen_persona_ids": meta.reopen_persona_ids,
        "reopen_operation_ids": meta.reopen_operation_ids,
        "unresolved": meta.unresolved,
        "confidence": meta.confidence,
    }


def _sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

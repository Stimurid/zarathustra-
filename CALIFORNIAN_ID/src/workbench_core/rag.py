"""RAG as a first-class, versioned, observable asset.

Same discipline as prompts, different gates: a RAGProfile is not compiled, it is
retrieval-tested. Nothing here knows about any branch — engines arrive through
the adapter.

Evidence grading is explicit throughout. A field is only filled when the engine
can actually prove it; everything else is ``NOT_IMPLEMENTED`` or ``UNKNOWN``
rather than a plausible-looking default.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from .models import sha256_text

#: How a reported value was obtained. Never blur these.
Grade = Literal["MEASURED", "DERIVED", "ESTIMATED", "LLM_EXPLANATION", "UNKNOWN"]

#: Sentinel for a capability the runtime genuinely does not have. It is never a
#: value with a default — it cannot be set, activated, or tuned.
NOT_IMPLEMENTED = "NOT_IMPLEMENTED"

RAGState = Literal[
    "BASELINE", "CANDIDATE_UNCHECKED", "STATIC_VALID", "TESTED",
    "ACCEPTED", "ACTIVE", "DEPRECATED", "REJECTED", "INCOMPATIBLE",
]

#: RAGProfile lifecycle. Deliberately different from PromptVariant: there is no
#: COMPILED state because a retrieval profile is never compiled into a payload.
RAG_ALLOWED: dict[str, set[str]] = {
    "BASELINE": {"CANDIDATE_UNCHECKED", "ACTIVE", "DEPRECATED"},
    "CANDIDATE_UNCHECKED": {"STATIC_VALID", "INCOMPATIBLE", "REJECTED",
                            "CANDIDATE_UNCHECKED"},
    "STATIC_VALID": {"TESTED", "CANDIDATE_UNCHECKED", "INCOMPATIBLE",
                     "REJECTED", "STATIC_VALID"},
    "TESTED": {"ACCEPTED", "CANDIDATE_UNCHECKED", "REJECTED"},
    "ACCEPTED": {"ACTIVE", "CANDIDATE_UNCHECKED", "REJECTED", "DEPRECATED"},
    "ACTIVE": {"DEPRECATED"},
    "DEPRECATED": {"ACTIVE", "REJECTED"},
    "REJECTED": {"CANDIDATE_UNCHECKED"},
    "INCOMPATIBLE": {"CANDIDATE_UNCHECKED", "REJECTED", "STATIC_VALID"},
}

RAG_FORBIDDEN_DIRECT = {
    ("CANDIDATE_UNCHECKED", "ACTIVE"), ("STATIC_VALID", "ACTIVE"),
    ("TESTED", "ACTIVE"), ("INCOMPATIBLE", "ACTIVE"), ("REJECTED", "ACTIVE"),
}


class RAGLifecycleError(RuntimeError):
    pass


def assert_rag_transition(current: str, target: str) -> None:
    if (current, target) in RAG_FORBIDDEN_DIRECT:
        raise RAGLifecycleError(
            f"переход {current} → {target} запрещён: активация только из ACCEPTED")
    if target not in RAG_ALLOWED.get(current, set()):
        raise RAGLifecycleError(f"переход {current} → {target} не разрешён")


# --------------------------------------------------------------------------
# Parameter descriptors
# --------------------------------------------------------------------------

@dataclass
class RAGParameter:
    """One real, code-backed retrieval parameter.

    ``current_default`` is the value written in the code; ``effective_value`` is
    what the pipeline actually passes at the call site. They differ more often
    than anyone expects, and the difference is the whole point of the census.
    """
    parameter_id: str
    label: str
    source_path: str
    caller: str
    current_default: Any
    effective_value: Any
    value_range: Any = None
    runtime_mutable: bool = False
    profile_versioned: bool = True
    consumer: str = ""
    trace_field: str = ""
    grade: Grade = "MEASURED"
    note: str = ""

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["default_differs_from_effective"] = (
            self.current_default != self.effective_value)
        return d


@dataclass
class MissingCapability:
    """A retrieval capability the runtime does not have.

    Surfaced so the UI can say "absent", never so it can pretend a knob exists.
    """
    capability_id: str
    label: str
    status: str = NOT_IMPLEMENTED
    note: str = ""

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------
# RAGProfile
# --------------------------------------------------------------------------

@dataclass
class RAGProfile:
    profile_id: str
    engine_id: str                       # which retrieval engine this configures
    version: str = "0.1.0"
    state: RAGState = "BASELINE"
    parent_version: str | None = None
    parent_profile_id: str | None = None
    title: str = ""
    author: str = "system"
    created_at: str = ""

    source_bindings: dict[str, Any] = field(default_factory=dict)
    chunking: dict[str, Any] = field(default_factory=dict)
    retrieval: dict[str, Any] = field(default_factory=dict)
    scoring: dict[str, Any] = field(default_factory=dict)
    filtering: dict[str, Any] = field(default_factory=dict)
    caching: dict[str, Any] = field(default_factory=dict)
    runtime_binding: dict[str, Any] = field(default_factory=dict)

    contract_version: str = "0.1.0"
    #: Contract surfaces a RAG edit must never silently move (S2.9).
    protected_contracts: list[str] = field(default_factory=list)
    missing_capabilities: list[MissingCapability] = field(default_factory=list)
    deprecation_reason: str | None = None
    rollback_of: str | None = None

    def tunable(self) -> dict[str, Any]:
        """Everything that actually drives retrieval, flattened."""
        out: dict[str, Any] = {}
        for section in ("source_bindings", "chunking", "retrieval",
                        "scoring", "filtering", "caching"):
            for k, v in (getattr(self, section) or {}).items():
                out[f"{section}.{k}"] = v
        return out

    def source_hash(self) -> str:
        return sha256_text(json.dumps({
            "engine_id": self.engine_id,
            "tunable": self.tunable(),
            "contract_version": self.contract_version,
        }, ensure_ascii=False, sort_keys=True))

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["missing_capabilities"] = [m.to_public() for m in self.missing_capabilities]
        d["source_hash"] = self.source_hash()
        d["tunable"] = self.tunable()
        return d


# --------------------------------------------------------------------------
# Retrieval events
# --------------------------------------------------------------------------

@dataclass
class RetrievalCandidate:
    chunk_id: str
    chunk_hash: str
    source_id: str
    locator: str
    rank: int
    score: float
    score_kind: str
    included_in_context: bool
    context_order: int | None = None
    token_count: int | None = None
    byte_count: int | None = None
    matched_terms: list[str] = field(default_factory=list)
    matched_features: list[str] = field(default_factory=list)
    filters_applied: list[str] = field(default_factory=list)
    grades: dict[str, str] = field(default_factory=dict)

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RetrievalEvent:
    """Append-only observation of one retrieval call.

    Emitting this must not change retrieval semantics: the instrumented path
    computes nothing the engine did not already compute.
    """
    run_id: str
    node_id: str
    timestamp: str
    query_hash: str
    query_text: str
    rewrite_applied: bool
    rag_profile_id: str
    rag_profile_version: str
    rag_profile_hash: str
    index_id: str
    index_version: str
    corpus_ids: list[str]
    candidates: list[RetrievalCandidate]
    latency_ms: int
    cache_state: str
    considered_count: int
    returned_count: int
    grades: dict[str, str] = field(default_factory=dict)

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["candidates"] = [c.to_public() for c in self.candidates]
        return d

    def included(self) -> list[RetrievalCandidate]:
        return [c for c in self.candidates if c.included_in_context]


# --------------------------------------------------------------------------
# "Why this chunk?"
# --------------------------------------------------------------------------

def explain_candidate(event: RetrievalEvent, chunk_id: str) -> dict[str, Any]:
    """Facts only. No causal story the engine cannot back.

    The LLM companion may narrate this, but it must cite these fields; the UI
    keeps RETRIEVAL FACTS and LLM INTERPRETATION visually separate.
    """
    cand = next((c for c in event.candidates if c.chunk_id == chunk_id), None)
    if cand is None:
        return {"found": False, "chunk_id": chunk_id}

    boundary = f"top_k={event.returned_count}"
    reasons: list[dict[str, Any]] = [
        {"fact": "query", "value": event.query_text[:200], "grade": "MEASURED"},
        {"fact": "score", "value": cand.score, "grade": "MEASURED"},
        {"fact": "score_kind", "value": cand.score_kind, "grade": "MEASURED"},
        {"fact": "rank", "value": cand.rank, "grade": "MEASURED"},
        {"fact": "top_k_boundary", "value": boundary, "grade": "MEASURED"},
        {"fact": "source_id", "value": cand.source_id, "grade": "MEASURED"},
        {"fact": "locator", "value": cand.locator, "grade": "MEASURED"},
        {"fact": "chunk_hash", "value": cand.chunk_hash, "grade": "MEASURED"},
        {"fact": "corpus_membership", "value": event.corpus_ids, "grade": "MEASURED"},
        {"fact": "included_in_context", "value": cand.included_in_context,
         "grade": "MEASURED"},
        {"fact": "cache_state", "value": event.cache_state, "grade": "MEASURED"},
    ]
    if cand.matched_terms:
        reasons.append({"fact": "matched_terms", "value": cand.matched_terms,
                        "grade": cand.grades.get("matched_terms", "DERIVED")})
    else:
        reasons.append({"fact": "matched_terms", "value": None, "grade": "UNKNOWN",
                        "note": "engine does not expose per-term contributions"})
    if cand.filters_applied:
        reasons.append({"fact": "filters_applied", "value": cand.filters_applied,
                        "grade": "MEASURED"})
    return {
        "found": True,
        "chunk_id": chunk_id,
        "retrieval_facts": reasons,
        "llm_interpretation": None,
        "disclaimer": "Причинность за пределами перечисленных фактов движком "
                      "не измеряется и не может утверждаться.",
    }


# --------------------------------------------------------------------------
# Baseline / candidate comparison
# --------------------------------------------------------------------------

def compare_retrieval(baseline: RetrievalEvent,
                      candidate: RetrievalEvent) -> dict[str, Any]:
    """Objective deltas only. Never call a difference an improvement."""
    b_ids = [c.chunk_id for c in baseline.candidates]
    c_ids = [c.chunk_id for c in candidate.candidates]
    b_set, c_set = set(b_ids), set(c_ids)
    overlap = b_set & c_set

    b_rank = {c.chunk_id: c.rank for c in baseline.candidates}
    c_rank = {c.chunk_id: c.rank for c in candidate.candidates}
    rank_changes = [
        {"chunk_id": cid, "baseline_rank": b_rank[cid], "candidate_rank": c_rank[cid]}
        for cid in sorted(overlap) if b_rank[cid] != c_rank[cid]
    ]

    def ctx(ev: RetrievalEvent) -> tuple[int, int]:
        inc = ev.included()
        return (sum(c.token_count or 0 for c in inc),
                sum(c.byte_count or 0 for c in inc))

    b_tok, b_bytes = ctx(baseline)
    c_tok, c_bytes = ctx(candidate)
    b_src = {c.source_id for c in baseline.candidates}
    c_src = {c.source_id for c in candidate.candidates}

    return {
        "result_count": {"baseline": len(b_ids), "candidate": len(c_ids)},
        "overlap_count": len(overlap),
        "overlap_ratio": round(len(overlap) / len(b_set), 3) if b_set else 0.0,
        "entered_chunks": sorted(c_set - b_set),
        "dropped_chunks": sorted(b_set - c_set),
        "rank_changes": rank_changes,
        "source_count": {"baseline": len(b_src), "candidate": len(c_src)},
        "source_coverage": {"baseline": sorted(b_src), "candidate": sorted(c_src)},
        "context_tokens": {"baseline": b_tok, "candidate": c_tok,
                           "delta": c_tok - b_tok, "grade": "ESTIMATED"},
        "context_bytes": {"baseline": b_bytes, "candidate": c_bytes,
                          "delta": c_bytes - b_bytes, "grade": "MEASURED"},
        "retrieval_latency_ms": {"baseline": baseline.latency_ms,
                                 "candidate": candidate.latency_ms,
                                 "grade": "MEASURED"},
        "cache": {"baseline": baseline.cache_state, "candidate": candidate.cache_state},
        "verdicts": _verdicts(baseline, candidate, b_ids, c_ids, rank_changes,
                              b_src, c_src, b_tok, c_tok),
        "relevance_labels_available": False,
        "quality_evidence": None,
        "note": "Структурные вердикты доказывают состав множества, но не качество. "
                "QUALITY_* требует разметки релевантности, приёмочной фикстуры, "
                "явного критерия или зафиксированного человеческого суждения.",
    }


#: Evidence-bounded verdict vocabulary (T5). Structural verdicts are provable
#: from the retrieval sets alone; QUALITY_* is not, and is never emitted without
#: a declared ground truth.
STRUCTURAL_VERDICTS = (
    "IDENTICAL", "BASELINE_PREFIX_PRESERVED", "BASELINE_SET_PRESERVED",
    "SUPERSET", "SUBSET", "RANK_CHANGED", "SOURCE_COVERAGE_CHANGED",
    "CONTEXT_EXPANDED", "CONTEXT_REDUCED",
)
DOWNSTREAM_VERDICTS = ("DOWNSTREAM_CONTRACT_PASS", "DOWNSTREAM_CONTRACT_FAIL")
QUALITY_VERDICTS = ("QUALITY_BETTER", "QUALITY_WORSE", "QUALITY_UNKNOWN")


def _verdicts(baseline: RetrievalEvent, candidate: RetrievalEvent,
              b_ids: list[str], c_ids: list[str], rank_changes: list[dict[str, Any]],
              b_src: set[str], c_src: set[str],
              b_tok: int, c_tok: int) -> list[str]:
    out: list[str] = []
    b_set, c_set = set(b_ids), set(c_ids)

    if b_ids == c_ids:
        out.append("IDENTICAL")
    else:
        if b_ids and c_ids[:len(b_ids)] == b_ids:
            out.append("BASELINE_PREFIX_PRESERVED")
        elif b_set and b_set <= c_set:
            out.append("BASELINE_SET_PRESERVED")
        if b_set and b_set < c_set:
            out.append("SUPERSET")
        if c_set and c_set < b_set:
            out.append("SUBSET")
    if rank_changes:
        out.append("RANK_CHANGED")
    if b_src != c_src:
        out.append("SOURCE_COVERAGE_CHANGED")
    if c_tok > b_tok:
        out.append("CONTEXT_EXPANDED")
    elif c_tok < b_tok:
        out.append("CONTEXT_REDUCED")

    # Quality is unknowable without declared ground truth. Saying so explicitly
    # is the point: absence of regression in set membership is not quality.
    out.append("QUALITY_UNKNOWN")
    return out


def attach_downstream_verdict(delta: dict[str, Any], contract_ok: bool,
                              reasons: list[str] | None = None) -> dict[str, Any]:
    """Add the only verdict a downstream smoke can legitimately support."""
    delta = dict(delta)
    verdicts = list(delta.get("verdicts", []))
    verdicts.append("DOWNSTREAM_CONTRACT_PASS" if contract_ok
                    else "DOWNSTREAM_CONTRACT_FAIL")
    delta["verdicts"] = verdicts
    delta["downstream_reasons"] = reasons or []
    return delta

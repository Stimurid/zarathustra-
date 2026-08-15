"""Workbench core data model — framework-free and branch-agnostic.

DEPENDENCY INVARIANT
--------------------
``workbench_core`` MUST NOT import ``californian_id.*`` (and therefore never
``californian_id.zarathustra``). All branch specifics arrive through the
``BranchAdapter`` protocol declared in :mod:`workbench_core.branch`.
The invariant is enforced by ``tests/workbench/test_dependency_invariant.py``.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

# --------------------------------------------------------------------------
# Enumerations
# --------------------------------------------------------------------------

NodeKind = Literal[
    "PROMPT", "MODEL_CALL", "DETERMINISTIC", "RAG",
    "ROUTER", "STORE", "HUMAN_GATE", "HYBRID",
]

VariantState = Literal[
    "BASELINE",
    "CANDIDATE_UNCHECKED",
    "STATIC_VALID",
    "COMPILED",
    "SMOKE_TESTED",
    "ACCEPTED",
    "ACTIVE",
    "DEPRECATED",
    "REJECTED",
    "INCOMPATIBLE",
]

EffectClass = Literal[
    "PROMPT_BEHAVIOR", "MODEL_INVOCATION", "DETERMINISTIC_ALGORITHM",
    "RAG_RETRIEVAL", "RUN_ORCHESTRATION", "CONTRACT", "TELEMETRY",
]

DriftClass = Literal["NONE", "KNOWN_BASELINE_DRIFT", "NEW_CANDIDATE_DRIFT",
                     "WAIVED_CANDIDATE_DRIFT"]

ProvenanceKind = Literal["source_module", "compiler_generated"]


def sha256_text(text: str) -> str:
    """Stable content hash. Newlines normalised to LF so CRLF checkouts agree."""
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Regions
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Region:
    """A named span of an asset source, located by literal markers.

    Markers are used instead of line numbers so a region survives edits made
    elsewhere in the file.
    """
    name: str
    kind: Literal["protected", "editable"]
    start_marker: str
    end_marker: str | None
    reason: str = ""

    def locate(self, text: str) -> tuple[int, int] | None:
        start = text.find(self.start_marker)
        if start < 0:
            return None
        if self.end_marker is None:
            return start, len(text)
        end = text.find(self.end_marker, start + len(self.start_marker))
        if end < 0:
            return start, len(text)
        return start, end + len(self.end_marker)

    def extract(self, text: str) -> str | None:
        span = self.locate(text)
        return None if span is None else text[span[0]:span[1]]


# --------------------------------------------------------------------------
# Assets and variants
# --------------------------------------------------------------------------

@dataclass
class PromptAsset:
    asset_id: str
    branch: str
    owner_id: str
    purpose: str
    operation_class: str
    used_by_steps: list[str] = field(default_factory=list)
    transition: str = ""
    upstream_objects: list[str] = field(default_factory=list)
    output_object: str = ""
    depends_on: list[str] = field(default_factory=list)
    composition_allowed: bool = True
    runtime_allowed: str = "true"          # true | guarded | false
    regions: list[Region] = field(default_factory=list)
    invariants: list[str] = field(default_factory=list)
    declared_output_fields: list[str] = field(default_factory=list)
    consumed_output_fields: list[str] = field(default_factory=list)
    contract_version: str = "0.1.0"
    baseline_fallback_ref: str | None = None
    reference_only: bool = False
    source_path: str = ""

    def region(self, name: str) -> Region | None:
        return next((r for r in self.regions if r.name == name), None)

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["regions"] = [asdict(r) for r in self.regions]
        return d


@dataclass
class PromptVariant:
    variant_id: str
    asset_id: str
    version: str
    state: VariantState
    origin: str                  # baseline_file | baseline_code | user_edit | user_new | llm_proposed
    source_text: str
    source_hash: str
    author: str = "anonymous"
    created_at: str = ""
    parent_variant_id: str | None = None
    title: str = ""
    deprecation_reason: str | None = None
    rollback_of: str | None = None
    #: "content" — protected regions are immutable (default, server-enforced).
    #: "contract_revision" — the candidate deliberately changes a protected
    #: contract region; drift is then judged with full force and any newly
    #: introduced defect needs an explicit waiver.
    intent: str = "content"
    contract_revision: bool = False

    def to_public(self, *, with_source: bool = False) -> dict[str, Any]:
        d = asdict(self)
        if not with_source:
            d.pop("source_text", None)
        return d


# --------------------------------------------------------------------------
# Contract reporting
# --------------------------------------------------------------------------

#: The closed set of contract-defect categories. Adding a category is a
#: deliberate schema change, not an incidental one — the fingerprint compares
#: category-qualified items, so an unknown category can never be grandfathered.
DRIFT_CATEGORIES = (
    "prompt_fields_not_declared",
    "declared_fields_not_consumed",
    "prompt_fields_not_consumed",
    "required_fields_missing",
    "schema_type_mismatches",
    "dangling_asset_refs",
)


@dataclass
class DriftFingerprint:
    """Structural identity of contract defects.

    A scalar count cannot prove that defects are *the same* defects: a candidate
    could repair one baseline defect and introduce another while keeping the
    total unchanged. The fingerprint therefore compares category-qualified item
    sets, and grandfathering requires genuine subset containment.
    """
    prompt_fields_not_declared: list[str] = field(default_factory=list)
    declared_fields_not_consumed: list[str] = field(default_factory=list)
    prompt_fields_not_consumed: list[str] = field(default_factory=list)
    required_fields_missing: list[str] = field(default_factory=list)
    schema_type_mismatches: list[str] = field(default_factory=list)
    dangling_asset_refs: list[str] = field(default_factory=list)

    def normalised(self) -> "DriftFingerprint":
        return DriftFingerprint(**{c: sorted(set(getattr(self, c)))
                                   for c in DRIFT_CATEGORIES})

    def as_set(self) -> set[tuple[str, str]]:
        return {(c, item) for c in DRIFT_CATEGORIES for item in getattr(self, c)}

    def is_empty(self) -> bool:
        return not self.as_set()

    def issubset(self, other: "DriftFingerprint") -> bool:
        return self.as_set() <= other.as_set()

    def difference(self, other: "DriftFingerprint") -> set[tuple[str, str]]:
        """Defects present here and absent in ``other`` — i.e. newly introduced."""
        return self.as_set() - other.as_set()

    def repaired(self, other: "DriftFingerprint") -> set[tuple[str, str]]:
        return other.as_set() - self.as_set()

    def fingerprint_hash(self) -> str:
        payload = json.dumps(sorted(f"{c}:{i}" for c, i in self.as_set()),
                             ensure_ascii=False)
        return "drift:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["fingerprint_hash"] = self.fingerprint_hash()
        d["total"] = len(self.as_set())
        return d


@dataclass
class DriftWaiver:
    """Explicit, provenanced permission for one specific new defect."""
    category: str
    item: str
    reason: str
    adr_ref: str
    granted_by: str
    granted_at: str
    asset_id: str = "*"

    def key(self) -> tuple[str, str]:
        return (self.category, self.item)

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ContractReport:
    asset_id: str
    prompt_fields: list[str]
    declared_fields: list[str]
    consumed_fields: list[str]
    unconsumed: list[str]          # asked from model, never read
    undeclared_in_map: list[str]   # asked from model, absent from dependency map
    missing_from_prompt: list[str] # consumed but not requested — always fatal
    status: str                    # OK | MISMATCH | UNDECLARED | INCOMPATIBLE
    fingerprint: DriftFingerprint = field(default_factory=DriftFingerprint)

    @property
    def drift_size(self) -> int:
        """Kept for reporting only. Never used as a grandfathering criterion."""
        return len(self.fingerprint.as_set())

    def summary(self) -> str:
        return (f"{len(self.prompt_fields)}/{len(self.declared_fields)}/"
                f"{len(self.consumed_fields)}")

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["fingerprint"] = self.fingerprint.to_public()
        d["drift_size"] = self.drift_size
        d["summary"] = self.summary()
        return d


# --------------------------------------------------------------------------
# Compilation
# --------------------------------------------------------------------------

@dataclass
class SourceSpan:
    """Provenance for one contiguous span of a compiled payload.

    Every character of every compiled target must be covered by exactly one
    span. ``kind='compiler_generated'`` spans carry ``rule_id`` instead of an
    asset reference — there is no unexplained text.
    """
    target: Literal["system", "user"]
    span_start: int
    span_end: int
    kind: ProvenanceKind
    asset_id: str | None = None
    variant_id: str | None = None
    region_name: str | None = None
    region_kind: str | None = None
    rule_id: str | None = None
    compiler_profile: str | None = None

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CompilerProfile:
    profile_id: str
    branch: str
    model_id: str
    supports_system_role: bool = True
    allow_superprompt: bool = False
    module_loading: str = "lazy"          # lazy | eager
    variable_policy: str = "strict"       # strict | warn
    assembly_order: list[str] = field(default_factory=lambda: ["operation"])
    max_user_chars: int = 100_000

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CompiledPrompt:
    compiled_hash: str
    profile_id: str
    branch: str
    step_id: str
    system_text: str
    user_template: str
    sources: list[dict[str, str]]
    source_map: list[SourceSpan]
    token_count: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    truncated: bool = False

    def coverage_gaps(self) -> list[dict[str, Any]]:
        """Return uncovered character ranges. Empty list == 100 % provenance."""
        gaps: list[dict[str, Any]] = []
        for target, text in (("system", self.system_text), ("user", self.user_template)):
            spans = sorted((s for s in self.source_map if s.target == target),
                           key=lambda s: s.span_start)
            cursor = 0
            for s in spans:
                if s.span_start > cursor:
                    gaps.append({"target": target, "from": cursor, "to": s.span_start})
                cursor = max(cursor, s.span_end)
            if cursor < len(text):
                gaps.append({"target": target, "from": cursor, "to": len(text)})
        return gaps

    def to_public(self) -> dict[str, Any]:
        return {
            "compiled_hash": self.compiled_hash,
            "profile_id": self.profile_id,
            "branch": self.branch,
            "step_id": self.step_id,
            "system_text": self.system_text,
            "user_template": self.user_template,
            "sources": self.sources,
            "source_map": [s.to_public() for s in self.source_map],
            "token_count": self.token_count,
            "warnings": self.warnings,
            "truncated": self.truncated,
            "provenance_coverage": "100%" if not self.coverage_gaps() else "INCOMPLETE",
            "coverage_gaps": self.coverage_gaps(),
        }


# --------------------------------------------------------------------------
# Evaluation, activation, telemetry
# --------------------------------------------------------------------------

@dataclass
class EvaluationRecord:
    variant_id: str
    asset_id: str
    kind: str                    # static | contract | compile | smoke | compare
    verdict: str                 # pass | fail | warn
    reasons: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)
    fixture_id: str | None = None
    compiled_hash: str | None = None
    source_hash: str | None = None
    evaluated_at: str = ""
    stale: bool = False

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ActivationSnapshot:
    """Immutable per-run picture of which variants were active at run start.

    Switching the active variant mid-flight must not affect a run that already
    started: the run keeps its snapshot.
    """
    snapshot_id: str
    activation_revision: int
    taken_at: str
    entries: dict[str, dict[str, str]]   # asset_id -> {variant_id, source_hash, profile_id}

    def entry(self, asset_id: str) -> dict[str, str] | None:
        return self.entries.get(asset_id)

    def to_public(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "activation_revision": self.activation_revision,
            "taken_at": self.taken_at,
            "entries": self.entries,
        }


@dataclass(frozen=True)
class RunConfigurationSnapshot:
    """One immutable configuration picture for one run (T4).

    Supersedes the separate prompt/RAG snapshots: every runtime operation inside
    a run resolves its effective configuration from here, never from the mutable
    current activation. Activation changes after a run starts cannot alter any
    binding inside that run.
    """
    snapshot_id: str
    created_at: str
    activation_revision: int
    pipeline: dict[str, Any] = field(default_factory=dict)
    prompt_bindings: list[dict[str, Any]] = field(default_factory=list)
    rag_bindings: list[dict[str, Any]] = field(default_factory=list)
    model_bindings: list[dict[str, Any]] = field(default_factory=list)
    algorithm_bindings: list[dict[str, Any]] = field(default_factory=list)
    orchestration_binding: dict[str, Any] = field(default_factory=dict)
    contract_bindings: list[dict[str, Any]] = field(default_factory=list)

    def prompt_binding(self, asset_id: str) -> dict[str, Any] | None:
        return next((b for b in self.prompt_bindings
                     if b.get("asset_id") == asset_id), None)

    def rag_binding(self, engine_id: str) -> dict[str, Any] | None:
        return next((b for b in self.rag_bindings
                     if b.get("engine_id") == engine_id), None)

    def as_resolver_view(self) -> dict[str, Any]:
        """Shape the runtime resolver pins itself to."""
        return {"rag_bindings": {b["engine_id"]: b for b in self.rag_bindings},
                "prompt_bindings": {b["asset_id"]: b for b in self.prompt_bindings},
                "activation_revision": self.activation_revision}

    def to_public(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def build(activation_revision: int, created_at: str, **sections: Any
              ) -> "RunConfigurationSnapshot":
        payload = json.dumps({k: sections.get(k) for k in sorted(sections)},
                             ensure_ascii=False, sort_keys=True, default=str)
        sid = "cfg_" + hashlib.sha256(
            f"{activation_revision}|{payload}".encode("utf-8")).hexdigest()[:16]
        return RunConfigurationSnapshot(
            snapshot_id=sid, created_at=created_at,
            activation_revision=activation_revision, **sections)


@dataclass
class ActivationBinding:
    asset_id: str
    variant_id: str
    activated_by: str
    activated_at: str
    revision: int
    previous_variant_id: str | None = None

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CacheKey:
    """Version-aware cache identity.

    Imperative invalidation alone is not relied upon: identity itself changes
    whenever variant, source, compiler profile or activation revision change.
    """
    asset_id: str
    variant_id: str
    source_hash: str
    profile_id: str
    activation_revision: int

    def as_str(self) -> str:
        return "|".join([
            self.asset_id, self.variant_id, self.source_hash[:16],
            self.profile_id, str(self.activation_revision),
        ])


def json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

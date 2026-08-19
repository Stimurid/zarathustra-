"""Typed pipeline state — the substrate the runtime mutates deterministically.

Every S0–S10 phase reads and updates fields on this state; conditional trigger
admission (CTA-002) requires that a trigger be *derived from current typed
state*, not from a lexical cue, so the state has to be first-class before
mount can be legitimate.

Kept minimal: only the fields actually consumed by mount, governor, or trace.
Anything richer (dialogue, tool calls) lives outside this module until a real
consumer needs it.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from .epistemic_model import (
    ConflictRegistry,
    DEFAULT_WORKSPACE_SPACE_ID,
    SceneRegistry,
    SpaceRegistry,
)
from .projection import ProjectionLineage


# ---------------------------------------------------------- roles

class Authority(str, Enum):
    """Who currently owns the operation.

    Values match the invariants set by the semantic body: HUMAN and SYSTEM
    are the two legitimate loci; JOINT is used when an intermediate step is
    still resolving ownership; UNSET means we don't know yet — the pipeline
    must resolve it before executing an intervention.
    """
    UNSET = "unset"
    HUMAN = "human"
    SYSTEM = "system"
    JOINT = "joint"


class ProvenanceStatus(str, Enum):
    UNKNOWN = "unknown"
    ATTRIBUTED = "attributed"
    RECONSTRUCTED = "reconstructed"
    SPECULATIVE = "speculative"


# ---------------------------------------------------------- state objects


@dataclass
class Scene:
    """S1 output — reconstructed scene / telos.

    ``telos`` is a short human phrase; ``role_hint`` is what the caller
    appeared to expect (student, colleague, judge). ``authority`` is the
    typed decision, not a guess.
    """
    telos: str = ""
    role_hint: str = ""
    authority: Authority = Authority.UNSET
    materials: tuple[str, ...] = ()

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["authority"] = self.authority.value
        d["materials"] = list(self.materials)
        return d


@dataclass
class Origin:
    """S3 output — where the current input came from and what status it has."""
    status: ProvenanceStatus = ProvenanceStatus.UNKNOWN
    sources_named: tuple[str, ...] = ()
    binding_authority: Authority = Authority.UNSET
    temporal_stale: bool = False

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["binding_authority"] = self.binding_authority.value
        d["sources_named"] = list(self.sources_named)
        return d


@dataclass
class Operation:
    """S4 output — what is Socrates being asked to do.

    ``applicable`` false + ``why_not`` non-empty forces the pipeline to
    prefer RETURN_OPERATION or DISTINGUISH terminals; the governor must not
    press through into an INTERVENTION.
    """
    kind: str = ""
    applicable: bool = True
    why_not: str = ""
    open_world_gap: bool = False

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Ownership:
    """S6 output — who owns the answer, and whether authority is HUMAN.

    ``HUMAN_UNRESOLVED`` matters: it triggers the RETURN_OPERATION terminal,
    per INV-009 in the enforcement manifest.
    """
    owner: Authority = Authority.UNSET
    human_resolved: bool = False
    return_reason: str = ""

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["owner"] = self.owner.value
        return d


@dataclass
class MemoryProposal:
    """S5/S10 — a candidate write to Working Memory.

    Content lives here; whether it commits is decided by the WM gate in
    :mod:`tinkuy_runtime.working_memory` — the runtime never bypasses it.
    """
    kind: str = ""            # observation | distinction | hypothesis | …
    text: str = ""
    grounds: str = ""
    #: Optional surface tag. PRIVATE artifacts cannot commit without
    #: B05 ``durable_write_admitted``. Default None = existing WM gate.
    surface: Any = None

    def to_public(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "kind": self.kind, "text": self.text, "grounds": self.grounds}
        if self.surface is not None:
            d["surface"] = getattr(self.surface, "value", self.surface)
        return d


# ---------------------------------------------------------- terminals

class Terminal(str, Enum):
    """Every legitimate finalisation of a Socrates run.

    Names mirror the handoff's ``terminal outcomes`` list, plus the
    infrastructure terminals for context-budget failure and refused
    operations. Adding a new terminal requires updating the governor and
    the trace.
    """
    ANSWER = "ANSWER"
    QUESTION = "QUESTION"
    DISTINGUISH = "DISTINGUISH"
    CHALLENGE = "CHALLENGE"
    REFRAME = "REFRAME"
    REFUSE = "REFUSE"
    RETURN_OPERATION = "RETURN_OPERATION"
    DWELL = "DWELL"
    EXPLORE = "EXPLORE"
    PLAY = "PLAY"
    TRACE = "TRACE"
    PRESERVE_APORIA = "PRESERVE_APORIA"
    CONCEPTUALIZE = "CONCEPTUALIZE"
    TRANSFORM_FIELD = "TRANSFORM_FIELD"

    #: Infrastructure — never mistaken for an intervention.
    SEMANTIC_CONTEXT_BUDGET_EXCEEDED = "SEMANTIC_CONTEXT_BUDGET_EXCEEDED"
    SEMANTIC_MOUNT_MISSING = "SEMANTIC_MOUNT_MISSING"
    FAILED_EXPLICIT = "FAILED_EXPLICIT"


TERMINALS_HUMAN_OWNED: frozenset[Terminal] = frozenset({
    Terminal.RETURN_OPERATION,
})
TERMINALS_NO_EXECUTION: frozenset[Terminal] = frozenset({
    Terminal.QUESTION,
    Terminal.DISTINGUISH,
    Terminal.CHALLENGE,
    Terminal.REFRAME,
    Terminal.REFUSE,
    Terminal.RETURN_OPERATION,
    Terminal.DWELL,
    Terminal.EXPLORE,
    Terminal.PRESERVE_APORIA,
})


@dataclass
class TerminalOutcome:
    """The final result of one Socrates run.

    ``response_text`` is human-facing; ``rationale`` is trace-facing (short,
    typed, no chain-of-thought). ``memory_proposal`` may be present even for
    non-execution terminals — e.g. DISTINGUISH proposing a durable
    distinction — but never commits without the gate.
    """
    terminal: Terminal
    response_text: str = ""
    rationale: str = ""
    memory_proposal: MemoryProposal | None = None

    def to_public(self) -> dict[str, Any]:
        d = {"terminal": self.terminal.value,
             "response_text": self.response_text,
             "rationale": self.rationale,
             "memory_proposal": (self.memory_proposal.to_public()
                                 if self.memory_proposal else None)}
        return d


# ---------------------------------------------------------- pipeline state


@dataclass
class PipelineState:
    """One state, one run. Every S-phase updates its own field.

    Kept mutable so the executor can write in place — no huge tuple-in-tuple
    reconstruction on every transition. The trace records diffs, not
    snapshots (see :mod:`.trace`).
    """
    run_id: str
    input_text: str
    phase: str = "PRE"                    # last completed S-phase id
    scene: Scene = field(default_factory=Scene)
    origin: Origin = field(default_factory=Origin)
    operation: Operation = field(default_factory=Operation)
    ownership: Ownership = field(default_factory=Ownership)
    #: S7 was actually invoked (council). May stay false — S7 is CONDITIONAL.
    council_invoked: bool = False
    #: S9 was actually invoked (Tinkuy execution). CONDITIONAL on authority.
    execution_invoked: bool = False
    #: Typed trigger causes admitted during mount. **Compat-projection
    #: field** — post D-S26-TRIG-001 repair, this is a DERIVED VIEW
    #: over ``admitted_trigger_events`` (see below). Direct writes
    #: from phase deltas are forbidden; the pipeline routes
    #: ``delta.triggers`` into ``pending_trigger_candidates`` and the
    #: lifecycle drains them through
    #: typing → admission → :class:`AdmittedTriggerEvent`. Anything
    #: reading this field today (`governor._council_needed`,
    #: `pipeline._council_needed`) continues to work because the
    #: pipeline recomputes this tuple whenever admitted events
    #: change.
    admitted_trigger_causes: tuple[str, ...] = ()
    # ------------------------------------------------- D-S26-TRIG-001 lifecycle
    #: Model / retrieval / donor / persona / model-prior candidates
    #: awaiting causal typing + admission. NO_MOUNT_AUTHORITY. Drained
    #: by :meth:`PipelineExecutor._drain_pending_triggers` after each
    #: phase delta application.
    pending_trigger_candidates: list[Any] = field(default_factory=list)
    #: Typed decisions produced by :class:`CausalTyper` — one per
    #: candidate. Outcomes REGISTERED_TYPE / TYPE_GAP / REJECT.
    trigger_typing_decisions: list[Any] = field(default_factory=list)
    #: Typed decisions produced by :class:`TriggerAdmitter` — one per
    #: REGISTERED_TYPE candidate. Outcomes ADMIT / COALESCE / REJECT.
    trigger_admission_decisions: list[Any] = field(default_factory=list)
    #: The ONLY records with SEMANTIC_CONDITIONAL_MOUNT authority.
    #: Consumed by :meth:`SemanticMountPolicy.mount` (via the new
    #: ``admitted_events`` parameter) — never populated from raw
    #: model output directly.
    admitted_trigger_events: list[Any] = field(default_factory=list)
    #: Candidates rejected at either typing or admission — kept for
    #: trace/replay so a reader can see WHY (observable rejection
    #: reason, no hidden CoT).
    rejected_trigger_candidates: list[Any] = field(default_factory=list)
    #: Grounded structural causes with no registered type. Zero mount
    #: authority; routes back to open-world S4 / B03 work.
    trigger_type_gaps: list[Any] = field(default_factory=list)
    #: Memory write proposal produced during the run, if any.
    memory_proposal: MemoryProposal | None = None
    #: Committed write's note_id, if the WM gate authorised the proposal.
    committed_memory_note_id: str = ""
    #: Projection-control-loop bookkeeping — every projection, every
    #: reflective return, and the diagnostics that connected them. Empty
    #: for runs that never invoked a projection (direct-assistance path).
    projection_lineage: ProjectionLineage = field(default_factory=ProjectionLineage)
    #: A projection diagnostic waiting to be judged by the reflective S7
    #: epilogue. Set by the projection-execution step; consumed and
    #: cleared by the epilogue. Non-None here means the current pass
    #: ended with a material mismatch that has not yet been reflected on.
    pending_diagnostic: Any = None
    #: The phase the next pass should re-enter at, if a ReflectiveReturn
    #: was accepted from S7. Set by the epilogue; consumed by the outer
    #: loop; cleared once the next pass starts.
    reentry_from: str = ""
    #: The ReflectiveReturn that motivates the pending re-entry, exposed
    #: to the *target phase* on pass 2 so it can produce a NEW validated
    #: delta under its normal contract instead of having its state
    #: silently mutated by S7. Public typed context — never hidden
    #: chain-of-thought. Cleared when the return_target phase applies a
    #: fresh delta (see :meth:`PipelineExecutor._apply_delta`).
    pending_reflective_context: Any = None
    #: Every :class:`CapabilityResolution` the projection step made on
    #: this run, in order. Records whether each operation was resolved
    #: as REGISTERED_CAPABILITY, CUTTER_SPEC_SYNTHESIS, or ORGAN_GAP,
    #: plus the reason and any generated spec / organ gap. Public typed
    #: evidence — a trace reader can prove *why* each branch was chosen.
    capability_resolutions: list[Any] = field(default_factory=list)
    #: Optional operation-specific target family override (opt-in for
    #: callers that want to steer the resolver without registering a
    #: whole cutter). Empty tuple means "let the resolver infer".
    operation_target_family: tuple[str, ...] = ()
    #: Optional synthesis hypotheses per operation kind. Consumed by
    #: :class:`CapabilityResolver` via the projection step. Enables a
    #: caller (or a live prompt) to supply the ``regex_pattern`` +
    #: ``target_object_family`` + ``required_attention_structure`` a
    #: synthesis or organ-gap branch needs. Empty = no hypothesis.
    operation_hypotheses: dict[str, Any] = field(default_factory=dict)
    #: A model-produced :class:`ProjectionSynthesisProposal` awaiting
    #: resolver validation + compile-bind + execution (D-S26-GEN-003).
    #: Set by S4's delta when the model authored a proposal; consumed
    #: by the projection step (which routes it through
    #: :meth:`CapabilityResolver.resolve_from_proposal` and clears the
    #: field after resolution). None means "no model-produced
    #: proposal this pass".
    pending_projection_proposal: Any = None
    # -------------------------------------------------- G-BD.2 epistemic model
    #: Which :class:`EpistemicSpace` this run is currently operating
    #: in. Defaults to the runtime-default workspace space so ordinary
    #: direct-assistance runs never need to name a Space.
    space_id: str = DEFAULT_WORKSPACE_SPACE_ID
    #: Which Scene inside ``space_id``. Distinct from the S1
    #: :class:`Scene` payload — this is the DAG node id, not the
    #: scene's typed content.
    scene_id: str = ""
    #: Which SceneBranch (sibling hypothesis) is currently active
    #: within ``scene_id``. Empty means the trunk scene.
    branch_id: str = ""
    #: Registry of :class:`EpistemicSpace` records this run touched.
    #: Small — most runs stay in the default workspace.
    space_registry: SpaceRegistry = field(default_factory=SpaceRegistry)
    #: Scene DAG: scene refs + branches.
    scene_registry: SceneRegistry = field(default_factory=SceneRegistry)
    #: All :class:`ContextTransduction` records this run produced.
    context_transductions: list[Any] = field(default_factory=list)
    #: Held conflicts (never a defect on their own, per §6.7).
    conflict_registry: ConflictRegistry = field(default_factory=ConflictRegistry)
    #: :class:`EpistemicPassport` records rendered at S10 / B10. Read
    #: model — never used to upgrade state.
    passports: list[Any] = field(default_factory=list)
    # ---------------------------------------------------- B2R intervention
    #: The typed :class:`InterventionPlan` derived from the caller's
    #: intervention profile at the START of this run. Public evidence
    #: field — a reader can prove pre-render pressure differed for
    #: BALD_APE vs NORMAL on the same input. Never carries truth
    #: authority (`plan.authority == "NO_TRUTH_STATUS_AUTHORITY"`).
    intervention_plan: Any = None
    #: The deterministic :class:`LiberatoryPassResult` produced AFTER
    #: the pipeline terminates and BEFORE the renderer runs. Non-None
    #: iff the plan required a reconstruction/release step. Never
    #: changes the terminal; never mints new claims; describes what
    #: the plan asked the renderer to distinguish.
    liberatory_pass_result: Any = None
    # ---------------------------------------------------- B2Q question set
    #: The typed :class:`QuestionSetPlan` derived post-terminal when
    #: the caller opted in via ``question_set_request`` control field.
    #: Non-None means the returned response text was authored from
    #: this plan (not the stochastic renderer). Public evidence: a
    #: reader can prove that the returned count and hierarchy match
    #: the material topology + explicit-count rules, not a habitual
    #: default. Carries ``authority="NO_TRUTH_STATUS_AUTHORITY"``.
    question_set_plan: Any = None
    #: 3D ephemeral dyadic projection (not a second store). Copied into
    #: existing context snapshot recognition_state.dyad when continuity runs.
    dyad_session_projection: dict[str, Any] | None = None
    #: 3C apparatus repeat counter projection (not a second store).
    #: Snapshot of the runtime-local `_apparatus_repeat` dict at end of
    #: run so context_continuity can persist it under
    #: recognition_state.apparatus_repeat. Empty means "no repeat state
    #: this run" (the runtime hydrates its counter from
    #: prior_ctx.recognition_state.apparatus_repeat on entry).
    apparatus_repeat_projection: dict[str, int] | None = None

    @property
    def source_id(self) -> str:
        """Stable content id for the ORIGINAL source of this run.

        Derived deterministically from ``input_text`` so P1 and P2 share
        the same ``source_id`` — the invariant that lets a trace prove
        "P2 rereads original source" (never derived-from-P1).
        """
        digest = hashlib.sha256((self.input_text or "").encode("utf-8")).hexdigest()
        return f"src_{digest[:16]}"

    def to_public(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "input_text": self.input_text,
            "source_id": self.source_id,
            "phase": self.phase,
            "scene": self.scene.to_public(),
            "origin": self.origin.to_public(),
            "operation": self.operation.to_public(),
            "ownership": self.ownership.to_public(),
            "council_invoked": self.council_invoked,
            "execution_invoked": self.execution_invoked,
            "admitted_trigger_causes": list(self.admitted_trigger_causes),
            "pending_trigger_candidates": [c.to_public()
                                            for c in self.pending_trigger_candidates],
            "trigger_typing_decisions": [d.to_public()
                                          for d in self.trigger_typing_decisions],
            "trigger_admission_decisions": [d.to_public()
                                             for d in self.trigger_admission_decisions],
            "admitted_trigger_events": [e.to_public()
                                         for e in self.admitted_trigger_events],
            "rejected_trigger_candidates": [c.to_public()
                                             for c in self.rejected_trigger_candidates],
            "trigger_type_gaps": [g.to_public() for g in self.trigger_type_gaps],
            "memory_proposal": (self.memory_proposal.to_public()
                                if self.memory_proposal else None),
            "committed_memory_note_id": self.committed_memory_note_id,
            "projection_lineage": self.projection_lineage.to_public(),
            "pending_diagnostic": (self.pending_diagnostic.to_public()
                                   if self.pending_diagnostic is not None
                                   else None),
            "reentry_from": self.reentry_from,
            "pending_reflective_context": (
                self.pending_reflective_context.to_public()
                if self.pending_reflective_context is not None else None),
            "capability_resolutions": [
                r.to_public() for r in self.capability_resolutions],
            "operation_target_family": list(self.operation_target_family),
            "operation_hypotheses": dict(self.operation_hypotheses),
            "pending_projection_proposal": (
                self.pending_projection_proposal.to_public()
                if self.pending_projection_proposal is not None else None),
            "space_id": self.space_id,
            "scene_id": self.scene_id,
            "branch_id": self.branch_id,
            "space_registry": self.space_registry.to_public(),
            "scene_registry": self.scene_registry.to_public(),
            "context_transductions": [t.to_public()
                                       for t in self.context_transductions],
            "conflict_registry": self.conflict_registry.to_public(),
            "passports": [p.to_public() for p in self.passports],
            "intervention_plan": (self.intervention_plan.to_public()
                                   if self.intervention_plan is not None
                                   else None),
            "liberatory_pass_result": (
                self.liberatory_pass_result.to_public()
                if self.liberatory_pass_result is not None else None),
            "question_set_plan": (self.question_set_plan.to_public()
                                    if self.question_set_plan is not None
                                    else None),
            "dyad_session_projection": self.dyad_session_projection,
        }

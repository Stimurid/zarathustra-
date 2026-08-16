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

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


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
    #: Typed trigger causes admitted during mount. Names are trigger_ids
    #: from the trigger admission policy, not raw cues.
    admitted_trigger_causes: tuple[str, ...] = ()
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
            "memory_proposal": (self.memory_proposal.to_public()
                                if self.memory_proposal else None),
            "committed_memory_note_id": self.committed_memory_note_id,
            "projection_lineage": self.projection_lineage.to_public(),
            "pending_diagnostic": (self.pending_diagnostic.to_public()
                                   if self.pending_diagnostic is not None
                                   else None),
            "reentry_from": self.reentry_from,
        }

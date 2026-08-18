"""Phase 3B — private work plane + structured internal speech +
autoprompting (SOC-INTSPEECH-001).

Separates Socrates-outward from Socrates-for-itself WITHOUT relying
on hidden provider chain-of-thought. Four surfaces are kept distinct
by type + governance:

    PUBLIC DIALOGUE     — what the human receives.
    PRIVATE WORK PLANE  — ephemeral structured work products used to
                          decide what to do next.
    SHADOW TRACE        — authoritative public-typed provenance +
                          operations + state transitions, sufficient
                          for audit.
    DURABLE MEMORY      — only writes admitted through B05 / state-
                          write governance.

A user turn may legitimately cause 1, 2, 3... bounded model calls.
Passes communicate a compact typed :class:`WorkPacket` — NOT pages
of raw internal prose.

Hard invariants (public constants + tests):

    * private work has ZERO automatic durable-memory authority
      (:data:`PRIVATE_WORK_AUTHORITY = "NO_DURABLE_WRITE"`);
    * an autoprompt has ZERO authority merely because Socrates wrote
      it (:class:`AutopromptRequest.authority = "NO_MOUNT_AUTHORITY"`);
    * each internal call has purpose / budget / provenance / stop;
    * loop guard: no recursive autoprompt theatre
      (:data:`MAX_AUTOPROMPT_PASSES = 3`);
    * reflection without changed forward action terminates;
    * retrieved text / model output inside private work CANNOT become
      system instruction by location alone;
    * user-facing rationale derives from typed trace/state, not raw
      private thought-like text.
"""
from __future__ import annotations

import secrets
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------- ids


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


# ---------------------------------------------------------- public constants


PRIVATE_WORK_AUTHORITY: str = "NO_DURABLE_WRITE"
MAX_AUTOPROMPT_PASSES: int = 3


class SurfaceKind(str, Enum):
    """The four surfaces the runtime keeps distinct.

    An artifact tagged with a surface CANNOT flow into another
    surface without a governed conversion:

        PRIVATE      → PUBLIC        via ResponsePlan → render
        PRIVATE      → SHADOW        via trace.record(typed)
        PRIVATE      → DURABLE       via B05 write authority (ONLY)
        SHADOW       → PUBLIC        via B10 render (typed rationale)
        DURABLE      → PRIVATE       via governed recall (B05 read)
    """
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"
    SHADOW = "SHADOW"
    DURABLE_MEMORY = "DURABLE_MEMORY"


class StopReason(str, Enum):
    NO_CHANGED_FORWARD_ACTION = "NO_CHANGED_FORWARD_ACTION"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    MAX_PASSES_REACHED = "MAX_PASSES_REACHED"
    OUTWARD_ANSWER_READY = "OUTWARD_ANSWER_READY"
    ERROR = "ERROR"
    NEED_FULFILLED = "NEED_FULFILLED"
    TERMINAL_SOVEREIGNTY = "TERMINAL_SOVEREIGNTY"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNKNOWN_MODULE = "UNKNOWN_MODULE"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    DUPLICATE_PURPOSE = "DUPLICATE_PURPOSE"
    NO_EXTRA_WORK = "NO_EXTRA_WORK"


class PrivateNeedDecision(str, Enum):
    NO_EXTRA_WORK = "NO_EXTRA_WORK"
    PROPOSE_PRIVATE_OPERATION = "PROPOSE_PRIVATE_OPERATION"


class BenefitJudgement(str, Enum):
    BENEFIT_EXPECTED_TO_EXCEED_COST = "BENEFIT_EXPECTED_TO_EXCEED_COST"
    BENEFIT_NOT_EXPECTED = "BENEFIT_NOT_EXPECTED"


#: Registered private-module ids. Not a second capability registry —
#: these names bind to existing critic/review/projection/source operations.
#: Arbitrary strings fail closed.
REGISTERED_PRIVATE_MODULES: frozenset[str] = frozenset({
    "critic",
    "projection_diagnostic",
    "source_gap",
    "operation_disambiguation",
    "response_plan",
})

ALLOWED_PRIVATE_PURPOSES: frozenset[str] = frozenset({
    "COUNTEREXAMPLE_REVIEW",
    "SOURCE_GAP_RECONSTRUCTION",
    "PROJECTION_DIAGNOSTIC_REVIEW",
    "OPERATION_DISAMBIGUATION",
    "RESPONSE_PLAN_RECONSTRUCTION",
})

PURPOSE_TO_MODULE: dict[str, str] = {
    "COUNTEREXAMPLE_REVIEW": "critic",
    "SOURCE_GAP_RECONSTRUCTION": "source_gap",
    "PROJECTION_DIAGNOSTIC_REVIEW": "projection_diagnostic",
    "OPERATION_DISAMBIGUATION": "operation_disambiguation",
    "RESPONSE_PLAN_RECONSTRUCTION": "response_plan",
}

_AUTHORITY_INFLATING_KEYS: frozenset[str] = frozenset({
    "system", "system_instruction", "mount", "profile", "write_durable",
    "space_id", "scene_id", "pass_budget", "authority", "chain_of_thought",
    "hidden_cot", "install_module",
})

MAX_ADDITIONAL_PRIVATE_PASSES: int = 2


# ---------------------------------------------------------- private artifacts


@dataclass(frozen=True)
class SourceNeed:
    """Private: Socrates identifies information/source it lacks.

    Emitted during a reconstruction/predict pass; a subsequent
    module call pass may fulfil it. NOT a public claim; NOT a memory
    write.
    """
    need_id: str
    scope: str                             # what the need serves
    description: str
    candidate_sources: tuple[str, ...] = ()
    fulfilled_by: str = ""                 # id of subsequent artifact
    surface: SurfaceKind = SurfaceKind.PRIVATE


@dataclass(frozen=True)
class ModuleCallPlan:
    """Private: a planned bounded call to a module / source / critic /
    cutter / review with typed purpose + budget + stop condition.

    ``module_id`` is NOT execution authority. It must resolve against
    :data:`REGISTERED_PRIVATE_MODULES` (and, when applicable, an existing
    CapabilityResolver). Unknown ids fail closed.
    """
    plan_id: str
    module_id: str
    purpose: str
    budget_tokens: int
    stop_condition: str
    inputs_ref: tuple[str, ...] = ()
    surface: SurfaceKind = SurfaceKind.PRIVATE

    def is_registered(self) -> bool:
        return self.module_id in REGISTERED_PRIVATE_MODULES


@dataclass(frozen=True)
class ReflectionResult:
    """Private: outcome of a reflective pass (post-diagnostic).

    Distinct from :class:`~projection.ReflectiveReturn` (a formal
    typed-state transition object). ReflectionResult is the
    PRIVATE-plane record of "what changed for pass N+1"; it may
    or may not translate into a ReflectiveReturn.
    """
    reflection_id: str
    triggering_signal: str                  # diagnostic / surprise / pressure id
    changed_forward_action: str             # non-empty required for continue
    superseded_by_pass: int = 0
    surface: SurfaceKind = SurfaceKind.PRIVATE

    @property
    def has_changed_forward_action(self) -> bool:
        return bool(self.changed_forward_action.strip())


@dataclass(frozen=True)
class ResponsePlan:
    """Private: the shape of the outward response, before rendering.

    Distills the typed private state into what B10 will render. This
    IS the sanctioned bridge PRIVATE → PUBLIC.
    """
    plan_id: str
    outward_purpose: str
    referenced_state_ids: tuple[str, ...]   # typed refs; passport/scene/etc.
    include_conflicts: bool = False
    include_transductions: bool = False
    include_passport: bool = False
    render_mode: str = "direct"             # "direct" | "complex"
    surface: SurfaceKind = SurfaceKind.PRIVATE


@dataclass(frozen=True)
class EpistemicStatusDelta:
    """Private: change to typed epistemic status a pass produced.

    Records what became known / more or less certain / withdrawn
    during the pass. Committing this to durable memory requires
    B05 write authority separately.
    """
    delta_id: str
    field_ref: str                          # e.g. "user_view.hypothesis.h1"
    from_value: str
    to_value: str
    reason: str
    surface: SurfaceKind = SurfaceKind.PRIVATE
    durable_write_admitted: bool = False    # set only by B05 gate


# ---------------------------------------------------------- work packet


@dataclass(frozen=True)
class WorkPacket:
    """Compact typed pass-to-pass transfer.

    NOT a raw prose dump. Contains typed references to prior
    artifacts + a small structured summary. Any prose fields are
    short and bounded — the assumption is that the RUNTIME reads
    them, not another provider call.

    Enforced by the runtime dispatcher: an autoprompt whose input
    exceeds ``max_prose_chars`` is rejected as raw-prose-pipe.
    """
    packet_id: str
    from_pass_index: int
    to_pass_index: int
    referenced_artifact_ids: tuple[str, ...]
    typed_summary: dict[str, Any]
    max_prose_chars: int = 800
    purpose: str = ""
    operation_kind: str = ""
    authority: str = "NO_BINDING_AUTHORITY"
    status: str = "OK"
    stop_signal: str = "STOP"
    changed_forward_action: str = ""
    input_refs: tuple[str, ...] = ()
    output_refs: tuple[str, ...] = ()
    distillate: str = ""

    def prose_char_count(self) -> int:
        total = 0
        def visit(x):
            nonlocal total
            if isinstance(x, str):
                total += len(x)
            elif isinstance(x, dict):
                for v in x.values(): visit(v)
            elif isinstance(x, (list, tuple)):
                for v in x: visit(v)
        visit(self.typed_summary)
        return total

    def is_prose_bounded(self) -> bool:
        return self.prose_char_count() <= self.max_prose_chars


# ---------------------------------------------------------- autoprompt


@dataclass(frozen=True)
class AutopromptRequest:
    """A request from Socrates to itself for a bounded next pass.

    NO_MOUNT_AUTHORITY / NO_TRANSITION_AUTHORITY / NO_DURABLE_WRITE.
    ``pass_index`` is advisory evidence only — it cannot control
    dispatcher state.
    """
    request_id: str
    pass_index: int
    purpose: str
    budget_tokens: int
    stop_condition: str
    provenance_ids: tuple[str, ...]
    authority: str = "NO_MOUNT_AUTHORITY"
    module_id: str = ""
    no_transition_authority: str = "NO_TRANSITION_AUTHORITY"
    no_durable_write: str = "NO_DURABLE_WRITE"


@dataclass(frozen=True)
class AutopromptDecision:
    """Deterministic decision about honouring an :class:`AutopromptRequest`."""
    decision_id: str
    request_id: str
    honour: bool
    stop_reason: StopReason | None
    reason: str


class AutopromptDispatcher:
    """Loop-guard dispatcher for multi-pass reasoning.

    Bounds:

    * :data:`MAX_AUTOPROMPT_PASSES` — hard cap on internal passes
      per user turn (default 3).
    * ``budget_tokens_total`` — soft budget for cumulative internal
      token spend; caller enforces the actual model call.
    * a subsequent pass MUST produce a :class:`ReflectionResult`
      with a non-empty ``changed_forward_action`` field, or the
      dispatcher terminates (reflection without changed action ends).
    * a WorkPacket's ``is_prose_bounded()`` must return True
      (structured typed transfer, not raw prose pipe).
    """

    def __init__(self, *,
                 max_passes: int = MAX_ADDITIONAL_PRIVATE_PASSES,
                 budget_tokens_total: int = 8000) -> None:
        # max_passes here is ADDITIONAL private passes, not S0–S10.
        # MAX_AUTOPROMPT_PASSES remains the hard safety ceiling.
        self.max_passes = min(max_passes, MAX_AUTOPROMPT_PASSES)
        self.budget_tokens_total = budget_tokens_total
        self._passes_so_far = 0
        self._budget_spent = 0
        self._history: list[AutopromptDecision] = []
        self._purposes_honoured: list[str] = []

    @property
    def passes_so_far(self) -> int:
        return self._passes_so_far

    @property
    def budget_spent(self) -> int:
        return self._budget_spent

    def decide(self, request: AutopromptRequest, *,
               last_reflection: ReflectionResult | None = None,
               incoming_packet: WorkPacket | None = None,
               ) -> AutopromptDecision:
        # request.pass_index is ignored for control — dispatcher owns the counter.
        if request.module_id and request.module_id not in REGISTERED_PRIVATE_MODULES:
            d = AutopromptDecision(
                decision_id=_new_id("apd"), request_id=request.request_id,
                honour=False, stop_reason=StopReason.UNKNOWN_MODULE,
                reason=f"unknown module_id={request.module_id!r}")
            self._history.append(d); return d
        if (request.purpose
                and request.purpose.isupper()
                and "_" in request.purpose
                and request.purpose not in ALLOWED_PRIVATE_PURPOSES):
            d = AutopromptDecision(
                decision_id=_new_id("apd"), request_id=request.request_id,
                honour=False, stop_reason=StopReason.VALIDATION_ERROR,
                reason=f"unknown purpose={request.purpose!r}")
            self._history.append(d); return d
        if (request.purpose
                and request.purpose in ALLOWED_PRIVATE_PURPOSES
                and request.purpose in self._purposes_honoured):
            d = AutopromptDecision(
                decision_id=_new_id("apd"), request_id=request.request_id,
                honour=False, stop_reason=StopReason.DUPLICATE_PURPOSE,
                reason=f"duplicate purpose={request.purpose}")
            self._history.append(d); return d
        # Loop bound
        if self._passes_so_far >= self.max_passes:
            d = AutopromptDecision(
                decision_id=_new_id("apd"), request_id=request.request_id,
                honour=False, stop_reason=StopReason.MAX_PASSES_REACHED,
                reason=f"max_passes={self.max_passes} reached")
            self._history.append(d); return d
        # Budget
        if self._budget_spent + request.budget_tokens > self.budget_tokens_total:
            d = AutopromptDecision(
                decision_id=_new_id("apd"), request_id=request.request_id,
                honour=False, stop_reason=StopReason.BUDGET_EXCEEDED,
                reason=(f"budget_spent={self._budget_spent} + "
                        f"request={request.budget_tokens} > "
                        f"total={self.budget_tokens_total}"))
            self._history.append(d); return d
        # Reflection-without-forward-action → terminate
        if (last_reflection is not None
                and not last_reflection.has_changed_forward_action):
            d = AutopromptDecision(
                decision_id=_new_id("apd"), request_id=request.request_id,
                honour=False, stop_reason=StopReason.NO_CHANGED_FORWARD_ACTION,
                reason="reflection produced no changed forward action")
            self._history.append(d); return d
        # WorkPacket must be prose-bounded (typed transfer, not raw dump)
        if incoming_packet is not None and not incoming_packet.is_prose_bounded():
            d = AutopromptDecision(
                decision_id=_new_id("apd"), request_id=request.request_id,
                honour=False, stop_reason=StopReason.ERROR,
                reason=(f"WorkPacket prose_char_count="
                        f"{incoming_packet.prose_char_count()} > "
                        f"max_prose_chars={incoming_packet.max_prose_chars} "
                        f"— rejected as raw-prose-pipe"))
            self._history.append(d); return d
        # Honour
        self._passes_so_far += 1
        self._budget_spent += request.budget_tokens
        if request.purpose:
            self._purposes_honoured.append(request.purpose)
        d = AutopromptDecision(
            decision_id=_new_id("apd"), request_id=request.request_id,
            honour=True, stop_reason=None,
            reason=(f"pass {self._passes_so_far}/{self.max_passes} "
                    f"budget {self._budget_spent}/{self.budget_tokens_total}"))
        self._history.append(d); return d

    def history(self) -> tuple[AutopromptDecision, ...]:
        return tuple(self._history)


# ---------------------------------------------------------- write authority


class DurableWriteAttempt(Exception):
    """A private-plane artifact tried to reach durable memory without
    going through the B05 write-authority gate.
    """


def enforce_no_durable_write(artifact: Any) -> None:
    """Assert an artifact tagged PRIVATE cannot short-circuit to
    DURABLE_MEMORY.

    Called by any write path that might touch memory; raises
    :class:`DurableWriteAttempt` if the artifact's surface is
    PRIVATE and no ``durable_write_admitted`` flag has been set
    upstream by the B05 gate.
    """
    surface = getattr(artifact, "surface", None)
    admitted = getattr(artifact, "durable_write_admitted", False)
    if surface == SurfaceKind.PRIVATE and not admitted:
        raise DurableWriteAttempt(
            f"artifact {getattr(artifact, 'delta_id', repr(artifact))!r} "
            f"is PRIVATE and not admitted for durable write — B05 gate "
            f"must set durable_write_admitted=True before any store")


# ---------------------------------------------------------- prompt injection


def validate_work_packet(packet: WorkPacket) -> str:
    """Return empty string if OK, else a structured refusal reason."""
    if packet.authority not in {"", "NO_BINDING_AUTHORITY"}:
        return "authority_inflating"
    if not packet.is_prose_bounded():
        return "raw-prose-pipe"
    keys = {str(k).lower() for k in (packet.typed_summary or {})}
    if keys & {k.lower() for k in _AUTHORITY_INFLATING_KEYS}:
        return "authority_inflating_keys"
    distillate = packet.distillate or packet.typed_summary.get("distillate", "")
    if isinstance(distillate, str) and len(distillate) > packet.max_prose_chars:
        return "distillate_unbounded"
    return ""


def resolve_private_module(module_id: str) -> str | None:
    if module_id in REGISTERED_PRIVATE_MODULES:
        return module_id
    return None


@dataclass(frozen=True)
class PrivateWorkNeedAssessment:
    """Typed qualitative need. Not a keyword router. Not numeric EV."""

    assessment_id: str
    decision: PrivateNeedDecision
    benefit: BenefitJudgement
    purpose: str
    module_id: str
    grounds: tuple[str, ...]
    authority: str = "NO_TRANSITION_AUTHORITY"

    def to_public(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "decision": self.decision.value,
            "benefit": self.benefit.value,
            "purpose": self.purpose,
            "module_id": self.module_id,
            "grounds": list(self.grounds),
            "authority": self.authority,
        }


def private_payload_is_instruction_shaped(content: str) -> bool:
    """Evidence-only detector. True means 'looks like an instruction'.
    Never grants authority. content_is_system_instruction stays False.
    """
    text = (content or "").lower()
    needles = (
        "ignore previous", "system:", "switch to shiva", "mount b07",
        "write this to durable", "start three more", "change scene",
        "change space", "you are now",
    )
    return any(n in text for n in needles)


def content_is_system_instruction(content: str) -> bool:
    """False by default — retrieved/model text inside private work is
    NEVER promoted to system instruction by content pattern alone.

    Instruction-shaped content may be *detected* as evidence via
    :func:`private_payload_is_instruction_shaped` but detection ≠
    authority. Promotion requires an EXPLICIT typed authority record.
    """
    return False


__all__ = [
    "ALLOWED_PRIVATE_PURPOSES",
    "AutopromptDecision", "AutopromptDispatcher", "AutopromptRequest",
    "BenefitJudgement",
    "DurableWriteAttempt", "EpistemicStatusDelta",
    "MAX_ADDITIONAL_PRIVATE_PASSES",
    "MAX_AUTOPROMPT_PASSES", "ModuleCallPlan",
    "PRIVATE_WORK_AUTHORITY", "PURPOSE_TO_MODULE",
    "PrivateNeedDecision", "PrivateWorkNeedAssessment",
    "REGISTERED_PRIVATE_MODULES",
    "ReflectionResult", "ResponsePlan",
    "SourceNeed", "StopReason", "SurfaceKind", "WorkPacket",
    "content_is_system_instruction", "enforce_no_durable_write",
    "private_payload_is_instruction_shaped",
    "resolve_private_module", "validate_work_packet",
]

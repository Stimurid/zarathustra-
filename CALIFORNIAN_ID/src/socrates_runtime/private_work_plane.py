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

    Compact typed pass-2 input. NEVER pipes raw internal prose.
    """
    plan_id: str
    module_id: str                          # e.g. "retrieval", "cutter", "critic"
    purpose: str
    budget_tokens: int
    stop_condition: str
    inputs_ref: tuple[str, ...] = ()        # typed refs, not raw prose
    surface: SurfaceKind = SurfaceKind.PRIVATE


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

    NO_MOUNT_AUTHORITY. Autoprompts cannot install code, mint mount
    events, write durable memory, or bypass any B05/D-S26-TRIG-001
    governance path. The runtime dispatcher decides whether to
    honour the request based on the loop guards below.
    """
    request_id: str
    pass_index: int                         # which pass in the sequence
    purpose: str
    budget_tokens: int
    stop_condition: str
    provenance_ids: tuple[str, ...]         # what motivated the request
    authority: str = "NO_MOUNT_AUTHORITY"


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
                 max_passes: int = MAX_AUTOPROMPT_PASSES,
                 budget_tokens_total: int = 8000) -> None:
        self.max_passes = max_passes
        self.budget_tokens_total = budget_tokens_total
        self._passes_so_far = 0
        self._budget_spent = 0
        self._history: list[AutopromptDecision] = []

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


def content_is_system_instruction(content: str) -> bool:
    """False by default — retrieved/model text inside private work is
    NEVER promoted to system instruction by content pattern alone.

    This is a stub that documents the invariant: any promotion to
    instruction requires an EXPLICIT typed authority record; content
    location or shape does not grant authority. Called by the private
    dispatcher as a sanity marker; any override would be caught by
    the test :func:`test_private_content_cannot_be_system_instruction`.
    """
    return False


__all__ = [
    "AutopromptDecision", "AutopromptDispatcher", "AutopromptRequest",
    "DurableWriteAttempt", "EpistemicStatusDelta",
    "MAX_AUTOPROMPT_PASSES", "ModuleCallPlan",
    "PRIVATE_WORK_AUTHORITY", "ReflectionResult", "ResponsePlan",
    "SourceNeed", "StopReason", "SurfaceKind", "WorkPacket",
    "content_is_system_instruction", "enforce_no_durable_write",
]

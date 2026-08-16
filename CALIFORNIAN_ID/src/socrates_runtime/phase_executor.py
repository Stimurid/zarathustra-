"""Phase execution — the seam that turns a mounted context + typed state into
a typed :class:`PhaseDelta`.

Three modes, one interface:

    DeterministicPhaseExecutor   — reads fixture-supplied PhaseHints. Only
                                    for tests, backward compatibility, and
                                    the "explain the pipeline without a
                                    model" surface in Workbench.
    TestDoublePhaseExecutor      — implements the LIVE code path against
                                    a pre-configured provider double, so we
                                    can prove the whole live-mount / parse /
                                    validate / mutate chain without a real
                                    credential. Marked NOT_LIVE in the trace.
    LiveModelPhaseExecutor       — uses ``californian_id.models`` to actually
                                    call the configured provider, parses the
                                    router's declared JSON output, validates
                                    it against a phase-specific schema, and
                                    only then produces a delta.

Every delta records ``origin_kind`` so the trace can show plainly which
phases were driven by a model, which by a fixture, and which the runtime
resolved on its own. A caller cannot claim live behaviour by feeding hints
through a deterministic executor.
"""
from __future__ import annotations

import copy
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from .errors import SocratesRuntimeError
from .identity import SocratesRunConfiguration
from .mount import MountedContext, TriggerAdmission
from .routers import RouterSpec
from .state import (
    Authority,
    MemoryProposal,
    Operation,
    Origin,
    Ownership,
    PipelineState,
    ProvenanceStatus,
    Scene,
)


# ---------------------------------------------------------- origins


class DeltaOrigin:
    """Where a phase delta actually came from."""
    MODEL_PRODUCED = "MODEL_PRODUCED"
    FIXTURE_SUPPLIED = "FIXTURE_SUPPLIED"
    SYSTEM_DETERMINISTIC = "SYSTEM_DETERMINISTIC"

    ALL: frozenset[str] = frozenset({
        "MODEL_PRODUCED", "FIXTURE_SUPPLIED", "SYSTEM_DETERMINISTIC"})


class ExecutionMode:
    """Which executor a run demands.

    LIVE is the production mode; a run started in LIVE that finds no
    provider fails explicitly (see :class:`PhaseExecutionResult`), never
    falls back to deterministic pretend-success.
    """
    DETERMINISTIC = "DETERMINISTIC"
    LIVE = "LIVE"
    TEST_DOUBLE = "TEST_DOUBLE"


class ProviderStatus:
    OK = "OK"
    UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    INVALID_OUTPUT = "INVALID_OUTPUT"
    RETRIES_EXHAUSTED = "RETRIES_EXHAUSTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"          # deterministic executor


# ---------------------------------------------------------- phase delta


@dataclass
class PhaseDelta:
    """What a phase's execution turns into for the state machine.

    Kept as a dataclass with plain fields so the deterministic path (which
    already has :class:`.pipeline.PhaseHint`) can be reused by simple
    conversion. The delta additionally carries provenance about *who
    produced it*, which the pipeline records verbatim in the trace.
    """
    scene: Scene | None = None
    origin: Origin | None = None
    operation: Operation | None = None
    ownership: Ownership | None = None
    triggers: list[TriggerAdmission] = field(default_factory=list)
    memory_proposal: MemoryProposal | None = None
    invoke_council: bool = False
    invoke_execution: bool = False

    origin_kind: str = DeltaOrigin.SYSTEM_DETERMINISTIC
    raw_output: str = ""
    parsed: dict[str, Any] = field(default_factory=dict)

    def to_public(self) -> dict[str, Any]:
        return {
            "scene": self.scene.to_public() if self.scene else None,
            "origin": self.origin.to_public() if self.origin else None,
            "operation": self.operation.to_public() if self.operation else None,
            "ownership": self.ownership.to_public() if self.ownership else None,
            "triggers": [asdict(t) for t in self.triggers],
            "memory_proposal": (self.memory_proposal.to_public()
                                if self.memory_proposal else None),
            "invoke_council": self.invoke_council,
            "invoke_execution": self.invoke_execution,
            "origin_kind": self.origin_kind,
            "parsed": self.parsed,
        }


# ---------------------------------------------------------- request/result


@dataclass(frozen=True)
class PhaseExecutionRequest:
    phase: str
    router: RouterSpec
    mounted: MountedContext
    input_text: str
    state_snapshot: dict[str, Any]
    run_configuration: SocratesRunConfiguration
    #: Bounded retries for provider-side / structured-output failures only.
    max_retries: int = 1


@dataclass
class PhaseExecutionResult:
    """Return type for every phase — mode-independent."""
    delta: PhaseDelta
    mode: str
    provider_status: str
    attempts: int = 0
    provider_id: str = ""
    model_id: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    error: str = ""
    #: The compiled request that produced the delta, hashed for the trace.
    #: Never the raw provider secret — hashes only.
    request_hash: str = ""
    #: Sanitised messages the executor actually sent (constitutional /
    #: user / retrieved), recorded structurally rather than as one blob.
    messages_summary: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.provider_status == ProviderStatus.OK

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["delta"] = self.delta.to_public()
        return d


# ---------------------------------------------------------- protocol


class PhaseExecutor(Protocol):
    """Every executor implementation exposes this shape."""
    mode: str

    def execute(self, request: PhaseExecutionRequest) -> PhaseExecutionResult: ...


# ---------------------------------------------------------- deterministic


class DeterministicPhaseExecutor:
    """Reads fixture-supplied ``PhaseHint``s. Zero provider calls.

    A caller passes a ``hints`` mapping phase → PhaseHint through the
    pipeline; the deterministic executor projects that hint into a
    :class:`PhaseDelta` with ``origin_kind=FIXTURE_SUPPLIED``. A phase
    without a hint yields an empty delta (``SYSTEM_DETERMINISTIC``).
    """
    mode: str = ExecutionMode.DETERMINISTIC

    def __init__(self, hints: dict[str, "PhaseHint"] | None = None) -> None:
        self.hints = dict(hints or {})

    def execute(self, request: PhaseExecutionRequest) -> PhaseExecutionResult:
        hint = self.hints.get(request.phase)
        if hint is None:
            delta = PhaseDelta(origin_kind=DeltaOrigin.SYSTEM_DETERMINISTIC)
        else:
            delta = _delta_from_hint(hint)
            delta.origin_kind = DeltaOrigin.FIXTURE_SUPPLIED
        return PhaseExecutionResult(
            delta=delta,
            mode=self.mode,
            provider_status=ProviderStatus.NOT_APPLICABLE,
            provider_id="deterministic", model_id="deterministic",
        )


def _delta_from_hint(hint: "PhaseHint") -> PhaseDelta:
    return PhaseDelta(
        scene=hint.scene, origin=hint.origin, operation=hint.operation,
        ownership=hint.ownership, triggers=list(hint.triggers),
        memory_proposal=hint.memory_proposal,
        invoke_council=hint.invoke_council,
        invoke_execution=hint.invoke_execution,
    )


# The import placed here (rather than at the top) breaks the circular
# ``pipeline`` ↔ ``phase_executor`` cycle. PhaseHint is a small local
# dataclass; we only need it to convert to PhaseDelta.
def _late_import_phasehint():
    from .pipeline import PhaseHint       # noqa: F401
    return PhaseHint


# ---------------------------------------------------------- test double


class TestDoublePhaseExecutor:
    """Implements the LIVE code path without a real provider.

    A caller pre-registers structured JSON outputs per phase; the executor
    goes through the same context assembly, parses the pre-registered
    string as if it came from a provider, and validates it. This is the
    only honest way to test the live path without a credential.

    Explicitly marked ``TEST_DOUBLE`` in the trace — the pipeline (and the
    HTTP response) surfaces this so a reader cannot mistake it for a real
    live run.

    Note: not a pytest test class — the ``Test*`` prefix is coincidental.
    """
    __test__ = False              # tell pytest not to collect this
    mode: str = ExecutionMode.TEST_DOUBLE

    def __init__(self, outputs_per_phase: dict[str, str],
                 provider_label: str = "test_double",
                 model_label: str = "test_double") -> None:
        self.outputs = dict(outputs_per_phase)
        self.provider_label = provider_label
        self.model_label = model_label

    def execute(self, request: PhaseExecutionRequest) -> PhaseExecutionResult:
        started = time.time()
        from .phase_context import compile_phase_request
        from .phase_output import parse_and_validate_output

        compiled = compile_phase_request(request)
        raw = self.outputs.get(request.phase, "{}")
        try:
            delta = parse_and_validate_output(raw, request)
        except SocratesRuntimeError as exc:
            return PhaseExecutionResult(
                delta=PhaseDelta(origin_kind=DeltaOrigin.MODEL_PRODUCED,
                                 raw_output=raw),
                mode=self.mode,
                provider_status=ProviderStatus.INVALID_OUTPUT,
                attempts=1, provider_id=self.provider_label,
                model_id=self.model_label,
                latency_ms=int((time.time() - started) * 1000),
                error=str(exc),
                request_hash=compiled.request_hash,
                messages_summary=compiled.messages_summary())
        delta.origin_kind = DeltaOrigin.MODEL_PRODUCED
        delta.raw_output = raw
        return PhaseExecutionResult(
            delta=delta, mode=self.mode,
            provider_status=ProviderStatus.OK,
            attempts=1,
            provider_id=self.provider_label, model_id=self.model_label,
            latency_ms=int((time.time() - started) * 1000),
            request_hash=compiled.request_hash,
            messages_summary=compiled.messages_summary())


# ---------------------------------------------------------- live model


class LiveModelPhaseExecutor:
    """Actual provider-backed execution.

    Uses ``californian_id.models.factory.build_client`` — no parallel
    provider framework. Each phase call:

        1. compile exact context (see :mod:`.phase_context`);
        2. call ``client.generate(messages, settings=…)`` requesting a
           JSON object (``response_format={"type":"json_object"}``);
        3. parse + validate per phase contract;
        4. on invalid output → bounded repair retry naming the exact
           validation error, never rewriting the semantic body;
        5. on transient provider error → bounded retry;
        6. on exhaustion → PhaseExecutionResult(status=RETRIES_EXHAUSTED),
           never a silent SYSTEM_DETERMINISTIC fallback.
    """
    mode: str = ExecutionMode.LIVE

    def __init__(self, client: Any, provider_id: str = "",
                 model_id: str = "") -> None:
        self.client = client
        self.provider_id = provider_id or getattr(client, "provider", "unknown")
        self.model_id = model_id or getattr(client, "model", "unknown")

    def execute(self, request: PhaseExecutionRequest) -> PhaseExecutionResult:
        from .models import Message                        # local shim
        from .phase_context import compile_phase_request
        from .phase_output import parse_and_validate_output

        compiled = compile_phase_request(request)
        started = time.time()

        attempts = 0
        last_error = ""
        raw = ""
        while attempts <= request.max_retries:
            attempts += 1
            try:
                result = self.client.generate(
                    compiled.provider_messages(),
                    settings={"response_format": {"type": "json_object"}})
                raw = result.text or ""
            except Exception as exc:                       # noqa: BLE001
                last_error = f"{type(exc).__name__}: {exc}"
                if attempts > request.max_retries:
                    return PhaseExecutionResult(
                        delta=PhaseDelta(origin_kind=DeltaOrigin.MODEL_PRODUCED,
                                         raw_output=""),
                        mode=self.mode,
                        provider_status=ProviderStatus.UNAVAILABLE,
                        attempts=attempts,
                        provider_id=self.provider_id, model_id=self.model_id,
                        latency_ms=int((time.time() - started) * 1000),
                        error=last_error,
                        request_hash=compiled.request_hash,
                        messages_summary=compiled.messages_summary())
                continue

            try:
                delta = parse_and_validate_output(raw, request)
            except SocratesRuntimeError as exc:
                last_error = str(exc)
                if attempts > request.max_retries:
                    return PhaseExecutionResult(
                        delta=PhaseDelta(origin_kind=DeltaOrigin.MODEL_PRODUCED,
                                         raw_output=raw),
                        mode=self.mode,
                        provider_status=ProviderStatus.RETRIES_EXHAUSTED,
                        attempts=attempts,
                        provider_id=self.provider_id, model_id=self.model_id,
                        latency_ms=int((time.time() - started) * 1000),
                        error=last_error,
                        request_hash=compiled.request_hash,
                        messages_summary=compiled.messages_summary())
                # Add a bounded, semantic-preserving repair message and try
                # again. The repair asks for contract compliance only — it
                # never rewrites the body or restates the task.
                compiled = compiled.with_repair_hint(exc, raw)
                continue

            delta.origin_kind = DeltaOrigin.MODEL_PRODUCED
            delta.raw_output = raw
            usage = getattr(result, "usage", {}) or {}
            return PhaseExecutionResult(
                delta=delta, mode=self.mode,
                provider_status=ProviderStatus.OK,
                attempts=attempts,
                provider_id=self.provider_id, model_id=self.model_id,
                tokens_in=int(usage.get("prompt_tokens", 0) or 0),
                tokens_out=int(usage.get("completion_tokens", 0) or 0),
                latency_ms=int((time.time() - started) * 1000),
                request_hash=compiled.request_hash,
                messages_summary=compiled.messages_summary())

        # Unreachable — the loop returns on every branch — but the type
        # checker prefers an explicit return.
        return PhaseExecutionResult(
            delta=PhaseDelta(), mode=self.mode,
            provider_status=ProviderStatus.RETRIES_EXHAUSTED,
            attempts=attempts, error=last_error)


__all__ = [
    "DeltaOrigin", "DeterministicPhaseExecutor", "ExecutionMode",
    "LiveModelPhaseExecutor", "PhaseDelta", "PhaseExecutionRequest",
    "PhaseExecutionResult", "PhaseExecutor", "ProviderStatus",
    "TestDoublePhaseExecutor",
]

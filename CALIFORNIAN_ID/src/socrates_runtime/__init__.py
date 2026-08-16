"""Socrates as an executable runtime.

Not a rewrite of the semantic body — the body lives on disk under
``CALIFORNIAN_ID/data/socrates/current/`` and is read-only for this
package. What lives here is the *orchestrator* the recovered G-S25R
semantic layer needs in order to actually run: a typed state machine
over S0–S10, a deterministic semantic mount, an intervention governor,
and a run trace that records exactly which body and which native organ
did the work.

Dependency direction, enforced by test:

    socrates_runtime
        ↓
    tinkuy_runtime            (native fabric / argumentation / memory seams)
    workbench_configs         (resolved effective PipelineConfig)
    californian_id.*          (provider client, workspace layout)

No reverse edge exists: californian_id / tinkuy_runtime never import this
package.

Not in scope of this module (deliberately):
    * LLM prompt engineering — the semantic body IS the prompt, unchanged;
    * Workbench UI wiring — hosted separately;
    * Arena participant adapter — one thin file in ``tinkuy_arena``.
"""
from __future__ import annotations

from .errors import (
    SemanticContextBudgetExceeded,
    SemanticMountMissing,
    SemanticVersionMismatch,
    SocratesRuntimeError,
)
from .identity import SocratesIdentity, SocratesRunConfiguration
from .mount import MountedContext, SemanticMountPolicy, TriggerAdmission
from .phase_executor import (
    DeltaOrigin,
    DeterministicPhaseExecutor,
    ExecutionMode,
    LiveModelPhaseExecutor,
    PhaseDelta,
    PhaseExecutionRequest,
    PhaseExecutionResult,
    PhaseExecutor,
    ProviderStatus,
    TestDoublePhaseExecutor,
)
from .renderer import RenderingResult, render_terminal
from .runtime import SocratesRuntime, SocratesRunResult
from .semantic import BodyRecord, SemanticBodyRegistry
from .state import (
    Ownership,
    PipelineState,
    Scene,
    Terminal,
    TerminalOutcome,
)
from .trace import SocratesRunTrace

__all__ = [
    "BodyRecord",
    "DeltaOrigin",
    "DeterministicPhaseExecutor",
    "ExecutionMode",
    "LiveModelPhaseExecutor",
    "MountedContext",
    "Ownership",
    "PhaseDelta",
    "PhaseExecutionRequest",
    "PhaseExecutionResult",
    "PhaseExecutor",
    "PipelineState",
    "ProviderStatus",
    "RenderingResult",
    "Scene",
    "SemanticBodyRegistry",
    "SemanticContextBudgetExceeded",
    "SemanticMountMissing",
    "SemanticMountPolicy",
    "SemanticVersionMismatch",
    "SocratesIdentity",
    "SocratesRunConfiguration",
    "SocratesRuntime",
    "SocratesRunResult",
    "SocratesRunTrace",
    "SocratesRuntimeError",
    "Terminal",
    "TerminalOutcome",
    "TestDoublePhaseExecutor",
    "TriggerAdmission",
    "render_terminal",
]

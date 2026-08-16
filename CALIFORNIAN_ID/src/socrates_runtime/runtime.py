"""SocratesRuntime — composition root.

Ties together identity, registry, mount, routers, pipeline, governor,
phase executor, native organs, workspace and trace. Callers who just want
to run Socrates go through :meth:`SocratesRuntime.run`.

Execution modes are explicit; there is no silent fallback from LIVE to
deterministic when a provider is missing. A LIVE run with no provider
returns ``FAILED_EXPLICIT`` with a typed reason.

Native organ bindings (fabric / argumentation / working_memory) are used
unchanged from :mod:`tinkuy_runtime`. The runtime never mints its own
write authority.
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from tinkuy_runtime import argumentation as arg_binding
from tinkuy_runtime import fabric as fabric_binding
from tinkuy_runtime import working_memory as wm_binding

from .errors import (
    HistoricalFallbackForbidden,
    SocratesRuntimeError,
)
from .capability_resolution import CapabilityResolver
from .cutter_registry import CutterRegistry, build_default_registry
from .governor import InterventionGovernor
from .projection_primitives import (
    PrimitiveRegistry,
    build_default_primitive_registry,
)
from .identity import SocratesIdentity, SocratesRunConfiguration
from .mount import MountedContext, SemanticMountPolicy
from .phase_executor import (
    DeterministicPhaseExecutor,
    ExecutionMode,
    LiveModelPhaseExecutor,
    PhaseExecutor,
    TestDoublePhaseExecutor,
)
from .pipeline import PhaseHint, PipelineExecutor, PhaseResult
from .projection_step import make_projection_step
from .renderer import RenderingResult, render_terminal
from .routers import RouterRegistry
from .semantic import SemanticBodyRegistry
from .state import PipelineState, Terminal, TerminalOutcome
from .trace import SocratesRunTrace


@dataclass
class SocratesRunResult:
    """Everything one run produced.

    Kept flat so a Workbench / Arena reader can pick fields off without
    walking a hierarchy.
    """
    run_id: str
    trace_id: str
    terminal: TerminalOutcome
    state: PipelineState
    mounted_phases: list[dict[str, Any]] = field(default_factory=list)
    native_organs: list[dict[str, Any]] = field(default_factory=list)
    memory_outcome: dict[str, Any] | None = None
    trace_path: str = ""
    duration_ms: int = 0
    execution_mode: str = ExecutionMode.DETERMINISTIC
    provider_id: str = ""
    model_id: str = ""
    rendering: RenderingResult | None = None

    def to_public(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id, "trace_id": self.trace_id,
            "terminal": self.terminal.to_public(),
            "state": self.state.to_public(),
            "mounted_phases": self.mounted_phases,
            "native_organs": self.native_organs,
            "memory_outcome": self.memory_outcome,
            "trace_path": self.trace_path,
            "duration_ms": self.duration_ms,
            "execution_mode": self.execution_mode,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "rendering": self.rendering.to_public() if self.rendering else None,
        }


class SocratesRuntime:
    """Composition root — construct once per process (or per workspace)."""

    def __init__(self,
                 semantic_dir: Path | None = None,
                 mount_dir: Path | None = None,
                 routers_dir: Path | None = None,
                 trace_dir: Path | None = None,
                 registry: SemanticBodyRegistry | None = None,
                 cutter_registry: CutterRegistry | None = None,
                 primitive_registry: PrimitiveRegistry | None = None,
                 capability_resolver: CapabilityResolver | None = None) -> None:
        self.registry = registry or SemanticBodyRegistry(
            semantic_dir=semantic_dir, mount_dir=mount_dir)
        self.mount_policy = SemanticMountPolicy(self.registry,
                                                 mount_dir=mount_dir)
        self.router_registry = RouterRegistry(routers_dir=routers_dir)
        self.governor = InterventionGovernor()
        # Default CutterRegistry ships the two capabilities used by the
        # ADR-S26-022 Peskov proof (EXTRACT_CONCEPTS +
        # DIFFERENTIATED_ACCOUNT). Operations for which no capability
        # is registered leave the projection step a no-op — the
        # direct-assistance fast path is not affected.
        self.cutter_registry = cutter_registry or build_default_registry()
        # ADR-S26-023: the three-branch capability resolver
        # (REGISTERED → SYNTHESIS → ORGAN_GAP). The default primitive
        # registry ships four generic primitives sufficient for
        # pattern-based synthesis; more can be registered by callers
        # that supply their own PrimitiveRegistry.
        self.primitive_registry = (primitive_registry
                                    or build_default_primitive_registry())
        self.capability_resolver = (capability_resolver
                                     or CapabilityResolver(
                                         self.cutter_registry,
                                         self.primitive_registry))
        self.executor = PipelineExecutor(
            self.mount_policy, self.router_registry, self.governor,
            projection_step=make_projection_step(
                self.capability_resolver,
                cutter_registry=self.cutter_registry))
        self.identity = SocratesIdentity.bootstrap()
        self.trace_dir = Path(trace_dir) if trace_dir else Path.cwd() / "runs" / "socrates"

    # ------------------------------------------------------------------

    def refuse_historical(self, requested_from: str = "runtime.entrypoint"
                          ) -> None:
        self.mount_policy.refuse_historical_fallback(requested_from)

    def run(self, input_text: str,
            configuration: SocratesRunConfiguration | None = None,
            *,
            mode: str = ExecutionMode.DETERMINISTIC,
            hints: dict[str, PhaseHint] | None = None,
            phase_executor: PhaseExecutor | None = None,
            rendering_client: Any = None,
            ) -> SocratesRunResult:
        """One end-to-end Socrates run.

        Mode selection:
            DETERMINISTIC — use :class:`DeterministicPhaseExecutor` with the
                            supplied ``hints`` (default; fixtures & tests).
            LIVE          — must be given a ``phase_executor`` (usually
                            :class:`LiveModelPhaseExecutor`). If none is
                            provided we look for provider environment via
                            ``californian_id.config``; missing → FAILED_EXPLICIT.
            TEST_DOUBLE   — must be given a ``TestDoublePhaseExecutor``.

        There is deliberately no silent fallback from LIVE to DETERMINISTIC.
        """
        config = configuration or SocratesRunConfiguration(
            semantic_pack_version=self.identity.pack.version,
            semantic_pack_sha256=self.identity.pack.source_bundle_sha256,
        )
        trace = SocratesRunTrace.start(self.identity, config)
        trace.record("execution_mode_requested", mode=mode)

        try:
            phase_exec = self._resolve_phase_executor(
                mode, hints=hints, phase_executor=phase_executor, trace=trace)
        except SocratesRuntimeError as exc:
            outcome = TerminalOutcome(
                terminal=Terminal.FAILED_EXPLICIT, response_text="",
                rationale=str(exc))
            trace.record_failure("phase_executor_unavailable", str(exc))
            trace.complete(outcome)
            path = trace.write_to(self.trace_dir)
            return SocratesRunResult(
                run_id="pre_run", trace_id=trace.trace_id, terminal=outcome,
                state=PipelineState(run_id="pre_run", input_text=input_text),
                trace_path=str(path), duration_ms=trace.duration_ms,
                execution_mode=mode)

        try:
            state, outcome, phases = self.executor.run(
                input_text, phase_exec, config,
                hints=hints or {}, trace=trace)
        except SocratesRuntimeError as exc:
            trace.record_failure(type(exc).__name__, str(exc))
            outcome = TerminalOutcome(
                terminal=Terminal.FAILED_EXPLICIT,
                response_text="", rationale=str(exc))
            state = PipelineState(run_id="pre_run", input_text=input_text)
            phases = []

        # Final rendering — bounded by the terminal.
        rendering = None
        if outcome.terminal not in {Terminal.FAILED_EXPLICIT,
                                     Terminal.SEMANTIC_MOUNT_MISSING,
                                     Terminal.SEMANTIC_CONTEXT_BUDGET_EXCEEDED}:
            rendering = render_terminal(state, outcome,
                                         client=rendering_client)
            if rendering.text:
                # Replace ONLY the response text; the terminal object stays.
                outcome = TerminalOutcome(
                    terminal=outcome.terminal,
                    response_text=rendering.text,
                    rationale=outcome.rationale,
                    memory_proposal=outcome.memory_proposal)
            trace.record("rendering", **rendering.to_public())

        native = self._call_native_organs(config, state, trace)
        memory = self._commit_memory_if_any(config, state, trace)
        trace.complete(outcome)
        trace_path = trace.write_to(self.trace_dir)

        return SocratesRunResult(
            run_id=state.run_id, trace_id=trace.trace_id, terminal=outcome,
            state=state,
            mounted_phases=[
                {"phase": p.phase, "router": p.router.module_id,
                 "mount": p.mount.to_public(),
                 "execution": p.execution.to_public()}
                for p in phases],
            native_organs=native, memory_outcome=memory,
            trace_path=str(trace_path), duration_ms=trace.duration_ms,
            execution_mode=phase_exec.mode,
            provider_id=getattr(phase_exec, "provider_id", ""),
            model_id=getattr(phase_exec, "model_id", ""),
            rendering=rendering,
        )

    # ------------------------------------------------------------------

    def _resolve_phase_executor(self, mode: str, *,
                                hints, phase_executor,
                                trace) -> PhaseExecutor:
        if mode == ExecutionMode.DETERMINISTIC:
            return phase_executor or DeterministicPhaseExecutor(hints=hints)
        if mode == ExecutionMode.TEST_DOUBLE:
            if phase_executor is None:
                raise SocratesRuntimeError(
                    "TEST_DOUBLE mode requires an explicit phase_executor")
            return phase_executor
        if mode == ExecutionMode.LIVE:
            if phase_executor is not None:
                return phase_executor
            client = self._build_live_client(trace)
            if client is None:
                raise SocratesRuntimeError(
                    "LIVE mode requested but no provider is available "
                    "(no SOCRATES_R8_PROVIDER_API_KEY / API_302AI_KEY / "
                    "ANTHROPIC_API_KEY / OPENAI_API_KEY set)")
            return LiveModelPhaseExecutor(client)
        raise SocratesRuntimeError(f"unknown execution mode: {mode!r}")

    @staticmethod
    def _build_live_client(trace: SocratesRunTrace):
        """Try to build a real provider client from environment.

        We prefer the R8-specific overrides when set, otherwise fall back
        to the runtime's normal provider resolution.
        """
        try:
            from californian_id.config import load_config
            from .models import build_client
        except ImportError:
            return None

        if os.environ.get("SOCRATES_R8_PROVIDER_API_KEY"):
            base_url = os.environ.get("SOCRATES_R8_PROVIDER_BASE_URL") or ""
            model = os.environ.get("SOCRATES_R8_MODEL_ID") or ""
            if not base_url or not model:
                trace.record("live_provider_partial",
                             note="R8 api key present but base_url/model missing")
                return None
            provider_cfg = {
                "kind": "openai_compatible",
                "env_key": "SOCRATES_R8_PROVIDER_API_KEY",
                "base_url": base_url,
                "model": model,
                "label": "socrates_r8_provider",
                "settings": {"temperature": 0.0},
            }
            try:
                return build_client("socrates_r8_provider", provider_cfg)
            except Exception as exc:                          # noqa: BLE001
                trace.record("live_provider_build_error", error=str(exc))
                return None

        try:
            cfg = load_config()
            provider = cfg.role_provider("persona_turn")
        except Exception:                                     # noqa: BLE001
            return None
        provider_cfg = cfg.provider_config(provider)
        try:
            return build_client(provider, provider_cfg)
        except Exception as exc:                              # noqa: BLE001
            trace.record("live_provider_build_error", error=str(exc))
            return None

    # ------------------------------------------------------------------

    def _call_native_organs(self, config: SocratesRunConfiguration,
                            state: PipelineState,
                            trace: SocratesRunTrace) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []

        arg_result = arg_binding.map_of(None)
        out.append(arg_result.to_public())
        trace.record_native_organ(arg_result)

        try:
            from californian_id.workspaces import fabric_store_path
            db = fabric_store_path(config.workspace_id or "default")
            fab_result = fabric_binding.list_snapshots(db)
        except Exception as exc:                              # noqa: BLE001
            fab_result_public = {"organ": "semantic_fabric",
                                 "call": "fabric.list_snapshots",
                                 "available": False, "value": None,
                                 "reason": f"хранилище недоступно: {exc}",
                                 "identity": None, "provenance": {}}
            out.append(fab_result_public)
            trace.record("native_organ", result=fab_result_public)
            return out

        pub = fab_result.to_public()
        if fab_result.available:
            pub["value"] = fab_result.value[:5]
        out.append(pub)
        trace.record_native_organ(fab_result)
        return out

    def _commit_memory_if_any(self, config: SocratesRunConfiguration,
                              state: PipelineState,
                              trace: SocratesRunTrace
                              ) -> dict[str, Any] | None:
        if state.memory_proposal is None:
            return None
        prop_res = wm_binding.propose_write(
            workspace_id=config.workspace_id or "default",
            kind=state.memory_proposal.kind,
            text=state.memory_proposal.text,
            related_run_ids=[state.run_id])
        if not prop_res.available:
            trace.record_memory_proposal(state.memory_proposal, "propose_refused")
            return {"status": "propose_refused", "reason": prop_res.reason}
        proposal = prop_res.value
        from tinkuy_runtime.working_memory import WriteAuthority
        commit = wm_binding.commit_if_authorized(
            proposal,
            WriteAuthority.denied("runtime has no standing human authority"),
        )
        outcome = "authorized_committed" if commit.available else "refused_no_authority"
        trace.record_memory_proposal(state.memory_proposal, outcome,
                                     note_id=proposal.committed_note_id)
        return {"status": outcome, "reason": commit.reason,
                "proposal_id": proposal.proposal_id}


def resolve_configuration(pipeline_config: Any,
                          user: Any | None = None,
                          workspace_id: str | None = None,
                          semantic_pack_version: str = "",
                          semantic_pack_sha256: str = ""
                          ) -> SocratesRunConfiguration:
    return SocratesRunConfiguration(
        pipeline_config_id=getattr(pipeline_config, "config_id", "") if pipeline_config else "",
        workspace_id=workspace_id
                     or (getattr(pipeline_config, "workspace_id", None)
                         if pipeline_config else None)
                     or "default",
        user_id=(user.user_id if user is not None else ""),
        display_name=(user.display_name if user is not None else ""),
        semantic_pack_version=semantic_pack_version,
        semantic_pack_sha256=semantic_pack_sha256,
        prompt_variant_selections=tuple(
            (s.asset_id, s.variant_id)
            for s in getattr(pipeline_config, "prompt_variant_selections", ()) or ()),
        prompt_fragment_overlays=tuple(
            (o.asset_id, o.region_id, o.hashed().source_hash)
            for o in getattr(pipeline_config, "prompt_fragment_overlays", ()) or ()),
        constitutional_status=getattr(pipeline_config, "constitutional_status",
                                      "standard") if pipeline_config else "standard",
        protected_edits=tuple(
            tuple(pair)
            for pair in getattr(pipeline_config, "protected_edits", ()) or ()),
        rag_profile={"selections": [
            (s.engine_id, s.profile_id)
            for s in getattr(pipeline_config, "rag_profile_selections", ()) or ()]},
        model_binding=(getattr(pipeline_config, "model_binding", {}) or {}),
    )

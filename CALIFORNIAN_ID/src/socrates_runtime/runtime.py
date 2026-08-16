"""SocratesRuntime — the public entrypoint.

Composition root — pulls together identity, registry, mount, routers,
pipeline, governor, native organs, workspace and trace. Callers should not
touch the pieces directly for a normal run.

Native organ bindings are used unchanged from :mod:`tinkuy_runtime`:

    fabric.query                — semantic fabric read
    argumentation.map_of        — live argument graph of any run
    working_memory.commit_if_authorized  — the WM gate this runtime USES,
                                           never bypasses.

The workspace_id used for the durable Working Memory store comes from the
resolved :class:`SocratesRunConfiguration`; a per-user config produces
per-user WM without this runtime needing to know a User type exists.
"""
from __future__ import annotations

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
from .governor import InterventionGovernor
from .identity import SocratesIdentity, SocratesRunConfiguration
from .mount import MountedContext, SemanticMountPolicy
from .pipeline import PipelineExecutor, PhaseHint, PhaseResult
from .routers import RouterRegistry
from .semantic import SemanticBodyRegistry
from .state import PipelineState, Terminal, TerminalOutcome
from .trace import SocratesRunTrace


@dataclass
class SocratesRunResult:
    """Everything one run produced.

    Kept flat so a Workbench / Arena reader can pick fields off it without
    walking a hierarchy. ``trace_path`` is where the JSON trace landed on
    disk; readers that want the full document read from there.
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
        }


class SocratesRuntime:
    """Composition root — construct once per process (or per workspace)."""

    def __init__(self,
                 semantic_dir: Path | None = None,
                 mount_dir: Path | None = None,
                 routers_dir: Path | None = None,
                 trace_dir: Path | None = None,
                 registry: SemanticBodyRegistry | None = None) -> None:
        self.registry = registry or SemanticBodyRegistry(
            semantic_dir=semantic_dir, mount_dir=mount_dir)
        self.mount_policy = SemanticMountPolicy(self.registry,
                                                 mount_dir=mount_dir)
        self.router_registry = RouterRegistry(routers_dir=routers_dir)
        self.governor = InterventionGovernor()
        self.executor = PipelineExecutor(
            self.mount_policy, self.router_registry, self.governor)
        self.identity = SocratesIdentity.bootstrap()
        self.trace_dir = Path(trace_dir) if trace_dir else Path.cwd() / "runs" / "socrates"

    # ------------------------------------------------------------------

    def refuse_historical(self, requested_from: str = "runtime.entrypoint"
                          ) -> None:
        """Public form of the same rule the mount enforces internally."""
        self.mount_policy.refuse_historical_fallback(requested_from)

    def run(self, input_text: str,
            configuration: SocratesRunConfiguration | None = None,
            hints: dict[str, PhaseHint] | None = None) -> SocratesRunResult:
        """One end-to-end Socrates run.

        Configuration is optional — a run without it uses defaults and
        records ``pipeline_config_id=""`` in the trace, which is honest
        rather than silent.
        """
        config = configuration or SocratesRunConfiguration(
            semantic_pack_version=self.identity.pack.version,
            semantic_pack_sha256=self.identity.pack.source_bundle_sha256,
        )
        # A CUSTOM_CONSTITUTIONAL_VARIANT is allowed to *run* but recorded
        # verbatim in the trace — Workbench refuses to publish it as line
        # default; here the runtime just remembers the label.
        trace = SocratesRunTrace.start(self.identity, config)

        try:
            state, outcome, phases = self.executor.run(
                input_text, hints=hints, trace=trace)
        except SocratesRuntimeError as exc:
            trace.record_failure(type(exc).__name__, str(exc))
            outcome = TerminalOutcome(
                terminal=Terminal.FAILED_EXPLICIT,
                response_text="", rationale=str(exc))
            state = PipelineState(run_id="pre_run", input_text=input_text)
            phases = []

        native = self._call_native_organs(config, state, trace)
        memory = self._commit_memory_if_any(config, state, trace)
        trace.complete(outcome)
        trace_path = trace.write_to(self.trace_dir)

        return SocratesRunResult(
            run_id=state.run_id,
            trace_id=trace.trace_id,
            terminal=outcome,
            state=state,
            mounted_phases=[
                {"phase": p.phase, "router": p.router.module_id,
                 "mount": p.mount.to_public()} for p in phases],
            native_organs=native,
            memory_outcome=memory,
            trace_path=str(trace_path),
            duration_ms=trace.duration_ms,
        )

    # ------------------------------------------------------------------

    def _call_native_organs(self, config: SocratesRunConfiguration,
                            state: PipelineState,
                            trace: SocratesRunTrace) -> list[dict[str, Any]]:
        """Ask the three native organs for their current status.

        Argumentation and fabric are always evidence: argumentation returns
        the live typed graph, fabric returns the workspace's current
        snapshot list (or 'not observed' if the workspace has none). The
        runtime does not fabricate values — an untouched organ is reported
        as unavailable with a reason.
        """
        out: list[dict[str, Any]] = []

        # -- argumentation.map_of — this runtime does not yet build the
        #    ArgumentMap directly; report unavailable honestly.
        arg_result = arg_binding.map_of(None)
        out.append(arg_result.to_public())
        trace.record_native_organ(arg_result)

        # -- fabric.list_snapshots for the run's workspace
        try:
            from californian_id.workspaces import fabric_store_path
            db = fabric_store_path(config.workspace_id or "default")
            fab_result = fabric_binding.list_snapshots(db)
        except Exception as exc:                          # noqa: BLE001
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
        """If the pipeline produced a memory proposal, commit through the WM gate.

        The runtime does NOT self-authorise. Without an explicit authority,
        the gate refuses and the proposal stays a proposal — recorded, not
        persisted. That is the invariant the WM binding was built for.
        """
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
        # Without a User-authority handoff, the runtime constructs an
        # explicitly-denied WriteAuthority and lets the gate refuse. A live
        # human-in-the-loop pathway would inject a granted authority here.
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


# Convenience — resolve a :class:`SocratesRunConfiguration` from an authenticated
# user + a PipelineConfig, without this file importing workbench_configs.


def resolve_configuration(pipeline_config: Any,                       # PipelineConfig
                          user: Any | None = None,                     # workbench_auth.User
                          workspace_id: str | None = None,
                          semantic_pack_version: str = "",
                          semantic_pack_sha256: str = ""
                          ) -> SocratesRunConfiguration:
    """Build a :class:`SocratesRunConfiguration` from an existing PipelineConfig.

    Kept as a free function so it never becomes a hard dependency of the
    runtime; the runtime accepts a plain :class:`SocratesRunConfiguration`
    from any caller.
    """
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

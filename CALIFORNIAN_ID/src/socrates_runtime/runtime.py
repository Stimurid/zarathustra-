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
from .intervention_plan import (
    InterventionPlan, LiberatoryPassResult,
    apply_liberatory, derive_plan,
)
from .mount import MountedContext, SemanticMountPolicy
from .question_set_plan import (
    QuestionSetPlan,
    derive_question_set_plan,
    render_plan_as_text as _render_qsp_as_text,
)
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
    intervention_plan: InterventionPlan | None = None
    liberatory_pass_result: LiberatoryPassResult | None = None
    question_set_plan: QuestionSetPlan | None = None
    #: B2Q-R natural-path evidence — the unprivileged model-produced
    #: proposal (validated) that fed the plan, or None when the plan
    #: came from CONTROL_OVERRIDE / no plan derived.
    question_intent_proposal: Any | None = None
    #: 3A+ cross-turn continuity evidence
    context_id: str = ""
    context_continuity: dict[str, Any] | None = None
    private_work: dict[str, Any] | None = None

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
            "intervention_plan": (self.intervention_plan.to_public()
                                   if self.intervention_plan is not None
                                   else None),
            "liberatory_pass_result": (
                self.liberatory_pass_result.to_public()
                if self.liberatory_pass_result is not None else None),
            "question_set_plan": (self.question_set_plan.to_public()
                                    if self.question_set_plan is not None
                                    else None),
            "question_intent_proposal": (
                self.question_intent_proposal.to_public()
                if self.question_intent_proposal is not None else None),
            "context_id": self.context_id,
            "context_continuity": self.context_continuity,
            "private_work": self.private_work,
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
            intervention_profile: Any = None,
            question_set_request: dict[str, Any] | None = None,
            context_id: str | None = None,
            context_store: Any = None,
            context_action: dict[str, Any] | None = None,
            injected_pressures: tuple[Any, ...] = (),
            private_work_max_additional: int | None = None,
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

        # B2R: derive the typed InterventionPlan BEFORE anything else so
        # even a pre-run failure carries plan evidence. Two consumers,
        # both PRE-RENDER:
        #   * PipelineExecutor.run honours plan.max_projection_iterations
        #     for THIS run only (higher EpistemicPressure → more
        #     permitted reflective retreats).
        #   * apply_liberatory (below) runs deterministically after the
        #     pipeline terminates and populates state.liberatory_pass_result
        #     when LiberatoryPressure is HIGH or MAX.
        plan = derive_plan(intervention_profile)
        trace.record("intervention_plan", **plan.to_public())

        # 3A+: resolve prior context for cross-turn hydration
        from .context_continuity import resolve_context
        prior_ctx = None
        resolved_cid = context_id
        ctx_created = False
        if context_store is not None or context_id is not None:
            try:
                prior_ctx, resolved_cid, ctx_created = resolve_context(
                    context_store, context_id, create_if_missing=False)
                trace.record("context_resolved",
                             context_id=resolved_cid,
                             context_created=ctx_created)
            except ValueError as exc:
                outcome = TerminalOutcome(
                    terminal=Terminal.FAILED_EXPLICIT, response_text="",
                    rationale=str(exc))
                trace.record_failure("context_resolve_failed", str(exc))
                trace.complete(outcome)
                path = trace.write_to(self.trace_dir)
                pre_state = PipelineState(run_id="pre_run", input_text=input_text)
                pre_state.intervention_plan = plan
                return SocratesRunResult(
                    run_id="pre_run", trace_id=trace.trace_id, terminal=outcome,
                    state=pre_state,
                    trace_path=str(path), duration_ms=trace.duration_ms,
                    execution_mode=mode, intervention_plan=plan,
                    context_id=context_id or "")

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
            pre_state = PipelineState(run_id="pre_run", input_text=input_text)
            pre_state.intervention_plan = plan
            return SocratesRunResult(
                run_id="pre_run", trace_id=trace.trace_id, terminal=outcome,
                state=pre_state,
                trace_path=str(path), duration_ms=trace.duration_ms,
                execution_mode=mode, intervention_plan=plan)

        try:
            state, outcome, phases = self.executor.run(
                input_text, phase_exec, config,
                hints=hints or {}, trace=trace,
                intervention_plan=plan,
                prior_context=prior_ctx if not ctx_created else None)
        except SocratesRuntimeError as exc:
            trace.record_failure(type(exc).__name__, str(exc))
            outcome = TerminalOutcome(
                terminal=Terminal.FAILED_EXPLICIT,
                response_text="", rationale=str(exc))
            state = PipelineState(run_id="pre_run", input_text=input_text)
            state.intervention_plan = plan
            phases = []

        # B2R: deterministic post-terminal reconstruction/release step.
        # Runs BEFORE the renderer. Its output on state.liberatory_pass_result
        # is publicly visible in the trace so a reader can prove
        # LiberatoryPressure caused a real pre-render pass, not just
        # a rhetorical overlay.
        liberatory = apply_liberatory(state, plan, outcome)
        state.liberatory_pass_result = liberatory
        trace.record("liberatory_pass", **liberatory.to_public())

        # 3B: bounded additional private pass BEFORE B2Q-R overlay / render.
        from .private_work_runtime import InternalCallBudget, run_private_work
        from .private_work_plane import MAX_ADDITIONAL_PRIVATE_PASSES
        cap = MAX_ADDITIONAL_PRIVATE_PASSES
        if private_work_max_additional is None:
            max_add = cap
        else:
            max_add = max(0, min(int(private_work_max_additional), cap))
        call_budget = InternalCallBudget(max_additional_private=max_add)
        pw_client = None
        if mode == ExecutionMode.LIVE:
            pw_client = self._build_live_client(trace)
        outcome, private_shadow, call_budget = run_private_work(
            state=state, outcome=outcome, intervention_plan=plan,
            input_text=input_text, mode=mode, client=pw_client,
            budget=call_budget)
        trace.record("private_work", private_work=private_shadow.to_public())

        # B2Q + B2Q-R: derive the QuestionSetPlan post-terminal.
        #
        # Two activation paths, in strict priority order:
        #
        # 1. CONTROL_OVERRIDE — caller supplied a typed
        #    question_set_request (tests / admin / explicit control).
        #    Deterministic, no LIVE inference call. `plan.origin =
        #    "CONTROL_OVERRIDE"`.
        #
        # 2. MODEL_PRODUCED_VALIDATED (B2Q-R) — no explicit request,
        #    LIVE mode, terminal is one that a QUESTION layer may
        #    overlay (ANSWER / CHALLENGE / DWELL). We run ONE bounded
        #    inference call to the LIVE client asking the model to
        #    (a) decide whether the user is actually requesting a
        #    question set (lexical bait / source instructions must
        #    NOT count) and (b) produce a typed topology with
        #    material-specific `candidate_question` per fork. The
        #    JSON is validated against a narrow schema. If validation
        #    fails or `requested=false`, no plan is derived and the
        #    normal render path runs. `plan.origin =
        #    "MODEL_PRODUCED_VALIDATED"`.
        #
        # QUESTION never overrides FAILED_EXPLICIT / RETURN_OPERATION /
        # PRESERVE_APORIA / SEMANTIC_MOUNT_MISSING /
        # SEMANTIC_CONTEXT_BUDGET_EXCEEDED — terminal sovereignty is
        # unconditional.
        _q_overlayable = {
            Terminal.ANSWER, Terminal.CHALLENGE, Terminal.DWELL}
        question_intent_proposal = None
        qsp = None
        if question_set_request is not None:
            qsp = derive_question_set_plan(
                scene=getattr(state, "scene", None),
                operation=getattr(state, "operation", None),
                ownership=getattr(state, "ownership", None),
                request=question_set_request,
                origin="CONTROL_OVERRIDE")
        elif (mode == ExecutionMode.LIVE
                and outcome.terminal in _q_overlayable):
            from .question_intent_inference import infer_question_intent
            infer_client = self._build_live_client(trace)
            if infer_client is not None:
                question_intent_proposal = infer_question_intent(
                    input_text=input_text,
                    scene=getattr(state, "scene", None),
                    operation=getattr(state, "operation", None),
                    ownership=getattr(state, "ownership", None),
                    client=infer_client)
                if question_intent_proposal is not None:
                    trace.record("question_intent_proposal",
                                 **question_intent_proposal.to_public())
                    if (question_intent_proposal.requested
                            and question_intent_proposal.validation_status == "OK"):
                        qsp = derive_question_set_plan(
                            scene=getattr(state, "scene", None),
                            operation=getattr(state, "operation", None),
                            ownership=getattr(state, "ownership", None),
                            request=question_intent_proposal.to_request_dict(),
                            origin="MODEL_PRODUCED_VALIDATED")
                        call_budget.record_specialized()
        state.question_set_plan = qsp
        if qsp is not None:
            trace.record("question_set_plan", **qsp.to_public())

        # Final rendering — bounded by the terminal.
        rendering = None
        # B2Q override: when a QuestionSetPlan is present, the plan
        # authors the response text deterministically. This is the
        # causal proof that the plan (not the LLM's format habits)
        # governs the returned question count/shape.
        if (qsp is not None
                and outcome.terminal not in {
                    Terminal.FAILED_EXPLICIT,
                    Terminal.SEMANTIC_MOUNT_MISSING,
                    Terminal.SEMANTIC_CONTEXT_BUDGET_EXCEEDED}):
            plan_text = _render_qsp_as_text(qsp)
            from .renderer import RenderingResult
            rendering = RenderingResult(
                text=plan_text,
                mode="QUESTION_SET_PLAN_AUTHORED")
            trace.record("rendering", **rendering.to_public())
        elif outcome.terminal not in {Terminal.FAILED_EXPLICIT,
                                       Terminal.SEMANTIC_MOUNT_MISSING,
                                       Terminal.SEMANTIC_CONTEXT_BUDGET_EXCEEDED}:
            # B2: pass the intervention profile through to the
            # renderer so BALD_APE / SHIVA register/epistemic
            # pressure overlays reach the LIVE model call.
            _render_client = rendering_client
            if _render_client is None and mode == ExecutionMode.LIVE:
                _render_client = self._build_live_client(trace)
            rendering = render_terminal(state, outcome,
                                         client=_render_client,
                                         intervention_profile=intervention_profile)
            if rendering.text:
                # Replace ONLY the response text; the terminal object stays.
                outcome = TerminalOutcome(
                    terminal=outcome.terminal,
                    response_text=rendering.text,
                    rationale=outcome.rationale,
                    memory_proposal=outcome.memory_proposal)
            trace.record("rendering", **rendering.to_public())

        if (rendering is not None and qsp is None
                and private_shadow is not None
                and private_shadow.causal_effect == "response_plan_merged_distillate"):
            excerpt = (private_shadow.public_product_excerpt or "").strip()
            if excerpt and excerpt not in (rendering.text or ""):
                rendering.text = (excerpt + "\n" + (rendering.text or "")).strip()
                outcome = TerminalOutcome(
                    terminal=outcome.terminal,
                    response_text=rendering.text,
                    rationale=outcome.rationale,
                    memory_proposal=outcome.memory_proposal)

        native = self._call_native_organs(config, state, trace)
        memory = self._commit_memory_if_any(config, state, trace)

        # 3A+: recognition pass + persist context snapshot
        context_continuity_meta = None
        final_context_id = resolved_cid or ""
        if context_store is not None or context_id is not None or prior_ctx is not None:
            from .context_continuity import (
                process_context_continuity,
                space_memory_provenance,
            )
            _, final_context_id, _contract, _rp, context_continuity_meta = (
                process_context_continuity(
                    store=context_store,
                    context_id=resolved_cid,
                    state=state,
                    context_action=context_action,
                    injected_pressures=injected_pressures,
                ))
            context_continuity_meta["space_memory_provenance"] = (
                space_memory_provenance(state))
            trace.record("context_continuity", **{
                k: v for k, v in context_continuity_meta.items()
                if k != "recognition_pass"})
            if memory is not None:
                memory["space_memory_provenance"] = (
                    context_continuity_meta["space_memory_provenance"])

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
            intervention_plan=plan,
            liberatory_pass_result=liberatory,
            question_set_plan=qsp,
            question_intent_proposal=question_intent_proposal,
            context_id=final_context_id,
            context_continuity=context_continuity_meta,
            private_work=private_shadow.to_public() if private_shadow else None,
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
        from .private_work_plane import (
            DurableWriteAttempt, SurfaceKind, enforce_no_durable_write,
        )
        try:
            enforce_no_durable_write(state.memory_proposal)
        except DurableWriteAttempt as exc:
            trace.record_memory_proposal(state.memory_proposal, "private_write_blocked")
            return {"status": "private_write_blocked", "reason": str(exc)}
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

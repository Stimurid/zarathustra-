"""S0..S10 state machine — driven by a :class:`PhaseExecutor`.

The executor is a *seam*: the pipeline sends it a
:class:`PhaseExecutionRequest`, gets back a :class:`PhaseDelta`, and mutates
:class:`PipelineState` through the phase's jurisdiction. Three seams share
the same shape:

    DeterministicPhaseExecutor   — reads caller-supplied ``PhaseHint``s
    LiveModelPhaseExecutor       — calls the real provider
    TestDoublePhaseExecutor      — the live code path with a canned provider

Rules the pipeline enforces regardless of which executor runs:

    * S7 stays CONDITIONAL — invoked only on typed council triggers or
      an explicit ``invoke_council`` from a phase output;
    * S9 stays CONDITIONAL on SYSTEM authority + applicability + no
      open-world gap;
    * a phase's delta may only touch fields inside its jurisdiction
      (enforced by the parser; the pipeline additionally rejects any
      illegal-mutation deltas that slip past);
    * a phase whose executor returns ``PROVIDER_UNAVAILABLE`` /
      ``RETRIES_EXHAUSTED`` / ``INVALID_OUTPUT`` in LIVE mode ends the run
      with an explicit ``FAILED_EXPLICIT`` terminal — the pipeline never
      silently substitutes deterministic values for a failed provider.
"""
from __future__ import annotations

import copy
import secrets
from dataclasses import dataclass, field
from typing import Any

from .errors import (
    SemanticContextBudgetExceeded,
    SemanticMountMissing,
)
from .governor import GovernorDecision, InterventionGovernor, apply_decision
from .mount import MountedContext, SemanticMountPolicy, TriggerAdmission
from .phase_contracts import jurisdiction_for
from .trigger_lifecycle import (
    AdmissionOutcome,
    AdmittedTriggerEvent,
    CausalTyper,
    RejectionReason,
    SourceKind,
    TriggerAdmissionDecision,
    TriggerAdmitter,
    TriggerCandidate,
    TriggerTypeGap,
    TypingOutcome,
    build_default_admitter,
    build_default_registry,
    build_default_typer,
    new_candidate_id,
    new_gap_id,
)
from .phase_executor import (
    DeltaOrigin,
    DeterministicPhaseExecutor,
    ExecutionMode,
    PhaseDelta,
    PhaseExecutionRequest,
    PhaseExecutionResult,
    PhaseExecutor,
    ProviderStatus,
)
from .projection import (
    MAX_PROJECTION_ITERATIONS,
    ProjectionDiagnostics,
    ProjectionStatus,
    ReflectiveReturn,
    RetreatLevel,
    ReturnTarget,
)
from .routers import RouterRegistry, RouterSpec
from .state import (
    Authority,
    MemoryProposal,
    Operation,
    Origin,
    Ownership,
    PipelineState,
    ProvenanceStatus,
    Scene,
    Terminal,
    TerminalOutcome,
)


@dataclass
class PhaseHint:
    """Backward-compat typed delta a fixture can supply.

    The pipeline itself no longer reads hints directly — they reach it via
    :class:`DeterministicPhaseExecutor`. Kept as a class because existing
    tests + Arena participants build it explicitly.
    """
    scene: Scene | None = None
    origin: Origin | None = None
    operation: Operation | None = None
    ownership: Ownership | None = None
    triggers: list[TriggerAdmission] = field(default_factory=list)
    memory_proposal: MemoryProposal | None = None
    invoke_council: bool = False
    invoke_execution: bool = False


PHASE_ORDER = ("S0", "S1", "S2", "S3", "S4", "S5",
               "S6", "S7", "S8", "S9", "S10")

#: Phase order lookup used by the reflective-return re-entry logic. A
#: return_target of "S4" starts the next pass at S4 and continues through
#: S10. The invariant: re-entry never re-runs S0 (context ok is a run-level
#: precondition, not a per-pass one) and always ends by re-executing S9
#: (that is where the new projection actually happens).
PHASE_INDEX: dict[str, int] = {p: i for i, p in enumerate(PHASE_ORDER)}


@dataclass
class PhaseResult:
    phase: str
    router: RouterSpec
    mount: MountedContext
    execution: PhaseExecutionResult


class PipelineExecutor:
    """One executor per run — sequences S0..S10 through a PhaseExecutor.

    Two loop layers:

        inner  — the linear ``for phase in PHASE_ORDER`` sequence
                  (:meth:`_run_phase_sequence`). Ends after S10 or at the
                  first hard-stop terminal.
        outer  — the projection control loop (:meth:`run`). After each
                  inner pass, if a projection produced a material-mismatch
                  diagnostic and no legitimate terminal has fired yet, an
                  epilogue reflective S7 is invoked. Its
                  :class:`ReflectiveReturn` (typed and distinct from
                  ``Terminal.RETURN_OPERATION`` and from technical
                  ``RETRIES_EXHAUSTED``) selects the next pass's re-entry
                  phase. Bounded by :data:`MAX_PROJECTION_ITERATIONS` and
                  by unchanged-diagnosis / unchanged-spec guards so a
                  runaway model cannot force the loop to spin.
    """

    def __init__(self, mount_policy: SemanticMountPolicy,
                 router_registry: RouterRegistry,
                 governor: InterventionGovernor | None = None,
                 projection_step: Any = None,
                 typer: CausalTyper | None = None,
                 admitter: TriggerAdmitter | None = None) -> None:
        self.mount_policy = mount_policy
        self.routers = router_registry
        self.governor = governor or InterventionGovernor()
        # D-S26-TRIG-001: default registry ships v0.2 B07/B09/B02
        # types verbatim (see trigger_lifecycle.build_default_registry).
        # Model output cannot register new types at runtime.
        self.typer = typer or build_default_typer()
        self.admitter = admitter or build_default_admitter()
        #: Optional callable ``(state) -> None`` that runs after the
        #: linear S0..S10 pass. It is where the CutterRegistry actually
        #: executes a projection against ``state.input_text`` (ORIGINAL
        #: source, never P1 outputs) and updates
        #: ``state.projection_lineage`` + ``state.pending_diagnostic``.
        #: Kept as a seam so commit 2 can exercise the loop with a
        #: synthetic step; commit 3 wires the real registry.
        self.projection_step = projection_step

    # ------------------------------------------------------------------

    def run(self, input_text: str,
            phase_executor: PhaseExecutor,
            run_configuration,                               # SocratesRunConfiguration
            *,
            hints: dict[str, PhaseHint] | None = None,
            trace=None,
            skip_phases: frozenset[str] = frozenset(),
            intervention_plan: Any = None,
            prior_context: Any = None,
            ) -> tuple[PipelineState, TerminalOutcome, list[PhaseResult]]:
        """Execute S0..S10 with the projection control loop wrapped around.

        ``hints`` is honoured only by the deterministic executor; the live
        executor ignores it. Passing hints in a LIVE run does not change
        the run — it just gets recorded as unused fixture data in the
        trace, which is what we want (a caller can't smuggle fixture
        semantics into live behaviour).
        """
        state = PipelineState(
            run_id=f"srun_{secrets.token_hex(8)}",
            input_text=input_text)
        if prior_context is not None:
            from .context_continuity import hydrate_state_from_context
            hydrate_state_from_context(state, prior_context)
        # B2R: attach the derived intervention plan so downstream
        # readers (renderer, tests, trace) can prove the pre-render
        # difference on the same input.
        if intervention_plan is not None:
            state.intervention_plan = intervention_plan
        effective_max_iter = (
            int(intervention_plan.max_projection_iterations)
            if intervention_plan is not None
            else MAX_PROJECTION_ITERATIONS)
        if trace is not None and intervention_plan is not None:
            trace.record("intervention_plan_active",
                         **intervention_plan.to_public())
        results: list[PhaseResult] = []

        for pass_number in range(1, effective_max_iter + 1):
            start_from = state.reentry_from or "S0"
            state.reentry_from = ""
            if trace is not None and pass_number > 1:
                trace.record("projection_pass_started",
                             pass_number=pass_number,
                             start_from=start_from,
                             source_id=state.source_id)

            pass_results, hard_stop = self._run_phase_sequence(
                state, phase_executor, run_configuration,
                hints=hints, trace=trace, skip_phases=skip_phases,
                start_from=start_from, input_text=input_text)
            results.extend(pass_results)
            if hard_stop is not None:
                return state, hard_stop, results

            # An in-pass S7 may have already emitted a ReflectiveReturn —
            # if so it set ``reentry_from`` and revised state; skip the
            # projection step and go straight to the next pass.
            if state.reentry_from:
                if pass_number >= effective_max_iter:
                    self._on_loop_bound_reached(state, trace, None)
                    state.reentry_from = ""
                    break
                continue

            # After the inner S0..S10 pass, the projection step (if any)
            # runs the CutterRegistry against ORIGINAL input_text — never
            # against any prior projection's output — and updates
            # state.projection_lineage / state.pending_diagnostic.
            if self.projection_step is not None:
                self.projection_step(state)
                if trace is not None:
                    trace.record("projection_step",
                                 pass_number=pass_number,
                                 lineage=state.projection_lineage.to_public(),
                                 pending=(state.pending_diagnostic.to_public()
                                          if state.pending_diagnostic
                                          else None))

            diag: ProjectionDiagnostics | None = state.pending_diagnostic
            if diag is None or not diag.mismatch:
                # No reflective retreat needed — the run is done.
                break
            if pass_number >= MAX_PROJECTION_ITERATIONS:
                # Guard: iteration bound reached. Preserve aporia rather
                # than force another look with unchanged evidence.
                self._on_loop_bound_reached(state, trace, diag)
                break

            # Loop guard: same diagnosis fingerprint as a previous pass →
            # reflection would not add material information; stop and let
            # the governor pick a legitimate terminal (typically DWELL /
            # PRESERVE_APORIA).
            if diag.fingerprint() in (
                    state.projection_lineage.previous_diagnostic_fingerprints()[:-1]):
                self._on_repeat_diagnosis(state, trace, diag)
                break

            reflective_return = self._invoke_reflective_epilogue(
                state, phase_executor, run_configuration,
                hints=hints, trace=trace)
            if reflective_return is None:
                # S7 could not produce a valid ReflectiveReturn from the
                # diagnostic. Stop — this is aporia, not a technical bug.
                self._on_epilogue_empty(state, trace, diag)
                break

            self._record_reflective_context(state, reflective_return,
                                            trace=trace)

        decision = self.governor.decide(state)
        if trace is not None:
            trace.record_governor(decision)
        outcome = apply_decision(state, decision,
                                 response_text=self._render_response(state, decision))
        return state, outcome, results

    # ------------------------------------------------------------------
    # inner: one linear S0..S10 pass
    # ------------------------------------------------------------------

    def _run_phase_sequence(self, state: PipelineState,
                            phase_executor: PhaseExecutor,
                            run_configuration,
                            *,
                            hints: dict[str, PhaseHint] | None,
                            trace,
                            skip_phases: frozenset[str],
                            start_from: str,
                            input_text: str,
                            ) -> tuple[list[PhaseResult],
                                       TerminalOutcome | None]:
        """One S0..S10 pass, starting at ``start_from`` (default S0).

        Returns ``(results, hard_stop_terminal_or_None)``. When
        ``hard_stop_terminal_or_None`` is set, the outer loop must return
        that terminal verbatim — a live-mode phase failure is a hard stop.
        """
        results: list[PhaseResult] = []
        start_idx = PHASE_INDEX.get(start_from, 0)
        # On a reflective re-entry we start AT return_target, not after
        # it. The target phase itself must re-execute and emit a new
        # validated delta under its normal contract — that is the
        # semantics of "reflective return to S4/S1/S3" per ADR-S26-022
        # after defect D-S26-PROJ-002 was recorded. Skipping the target
        # phase would make the ReflectiveReturn a side-channel state
        # mutation instead of a governed revision. The target phase
        # reads ``state.pending_reflective_context`` from its state
        # snapshot (public typed context, not hidden chain-of-thought)
        # to build the revised delta; ``_apply_delta`` clears the
        # context once that phase actually writes into its jurisdiction.

        for phase in PHASE_ORDER[start_idx:]:
            if phase in skip_phases:
                continue

            # D-S26-TRIG-001: drain pending candidates BEFORE the phase
            # gating decisions read state — otherwise a candidate
            # emitted by phase N-1 that would have admitted
            # COUNCIL_REQUIRED / STATUS_DISPUTE / etc. would still be
            # pending when the S7 / S9 gate looks at state. Seeding
            # (deterministic REFLECTIVE_EXIT_REQUIRED from typed
            # pending_diagnostic) also happens here so P06's mount
            # sees it before the mount decision.
            self._seed_reflective_candidate_if_needed(state, phase)
            self._drain_pending_triggers(state, phase, trace)

            if phase == "S7" and not self._council_needed(state):
                continue
            if phase == "S9" and not self._execution_authorized(state):
                continue

            router = self.routers.router_for_phase(phase)
            state_before = self._clone(state)

            # Feed only ADMITTED events to the mount policy so its
            # conditional-body selection is authority-grounded. Stamp
            # the resolved router_id onto the legacy TriggerAdmission
            # shape so the CTA gate's phase_relevance == router_id
            # check aligns.
            admitted_for_phase = tuple(
                _admitted_to_trigger_admission(e,
                                                router_id=router.module_id)
                for e in state.admitted_trigger_events
                if not e.phase_relevance or e.phase_relevance == phase)
            try:
                mount = self.mount_policy.mount(
                    router.module_id, phase,
                    proposed_triggers=list(admitted_for_phase))
            except (SemanticMountMissing, SemanticContextBudgetExceeded) as exc:
                early_terminal = (Terminal.SEMANTIC_MOUNT_MISSING
                                  if "not present" in str(exc)
                                  or "body" in str(exc)
                                  else Terminal.SEMANTIC_CONTEXT_BUDGET_EXCEEDED)
                if trace is not None:
                    trace.record_failure(early_terminal.value, str(exc),
                                         extra={"phase": phase,
                                                "router": router.module_id})
                state.phase = phase
                return results, TerminalOutcome(
                    terminal=early_terminal, response_text="",
                    rationale=str(exc))

            request = PhaseExecutionRequest(
                phase=phase, router=router, mounted=mount,
                input_text=input_text,
                state_snapshot=state.to_public(),
                run_configuration=run_configuration,
                max_retries=1,
            )
            execution = phase_executor.execute(request)

            # In LIVE mode, a non-OK provider status is a hard stop —
            # never a deterministic pretend-success.
            if (execution.mode == ExecutionMode.LIVE
                    and execution.provider_status != ProviderStatus.OK):
                if trace is not None:
                    trace.record_failure(
                        f"live_phase_{execution.provider_status.lower()}",
                        execution.error,
                        extra={"phase": phase, "router": router.module_id,
                               "attempts": execution.attempts,
                               "provider": execution.provider_id,
                               "model": execution.model_id})
                    trace.record("phase_executed", phase=phase,
                                 router_id=router.module_id,
                                 mount=mount.to_public(),
                                 execution=execution.to_public())
                state.phase = phase
                return results, TerminalOutcome(
                    terminal=Terminal.FAILED_EXPLICIT, response_text="",
                    rationale=(f"live phase {phase} failed: "
                               f"{execution.provider_status}: "
                               f"{execution.error}"))

            self._apply_delta(phase, state, execution.delta)
            state.phase = phase
            results.append(PhaseResult(phase=phase, router=router,
                                        mount=mount, execution=execution))
            if trace is not None:
                trace.record("phase_executed", phase=phase,
                             router_id=router.module_id,
                             mount=mount.to_public(),
                             execution=execution.to_public(),
                             state_diff=_diff_public(state_before.to_public(),
                                                     state.to_public()))
        return results, None

    # ------------------------------------------------------------------
    # reflective epilogue: dedicated S7 invocation for the loop
    # ------------------------------------------------------------------

    def _invoke_reflective_epilogue(self, state: PipelineState,
                                    phase_executor: PhaseExecutor,
                                    run_configuration,
                                    *,
                                    hints: dict[str, PhaseHint] | None,
                                    trace) -> ReflectiveReturn | None:
        """Run S7 in reflective mode against the current pending diagnostic.

        Distinct from the S7 CONDITIONAL invocation inside the inner pass
        (which is council-only): here we invoke S7 with the explicit
        expectation that it will emit a :class:`ReflectiveReturn` for the
        current ``state.pending_diagnostic``. The distinction matters —
        this is where the "reflective" branch of B07 becomes executable
        rather than only describable.
        """
        router = self.routers.router_for_phase("S7")
        try:
            mount = self.mount_policy.mount(router.module_id, "S7")
        except (SemanticMountMissing, SemanticContextBudgetExceeded) as exc:
            if trace is not None:
                trace.record_failure(
                    "reflective_epilogue_mount_failed", str(exc),
                    extra={"router": router.module_id})
            return None

        request = PhaseExecutionRequest(
            phase="S7", router=router, mounted=mount,
            input_text=state.input_text,
            state_snapshot=state.to_public(),
            run_configuration=run_configuration,
            max_retries=1,
        )
        execution = phase_executor.execute(request)

        if (execution.mode == ExecutionMode.LIVE
                and execution.provider_status != ProviderStatus.OK):
            if trace is not None:
                trace.record_failure(
                    f"reflective_epilogue_{execution.provider_status.lower()}",
                    execution.error,
                    extra={"attempts": execution.attempts,
                           "provider": execution.provider_id,
                           "model": execution.model_id})
            return None

        if trace is not None:
            trace.record("reflective_epilogue_executed",
                         router_id=router.module_id,
                         execution=execution.to_public())

        rr = execution.delta.reflective_return
        if rr is None:
            return None
        # Backfill from_projection_id and diagnostic fingerprint if the
        # executor did not populate them — the runtime knows both.
        diag = state.pending_diagnostic
        if diag is not None:
            if not rr.from_projection_id:
                rr.from_projection_id = diag.projection_id
            if not rr.diagnostic_fingerprint:
                rr.diagnostic_fingerprint = diag.fingerprint()
        return rr

    def _record_reflective_context(self, state: PipelineState,
                                   rr: ReflectiveReturn,
                                   *, trace) -> None:
        """Record the ReflectiveReturn as REVISION CONTEXT on state.

        Repair for defect D-S26-PROJ-002. Semantics:

            * the return is added to lineage.revisions;
            * the failing projection is marked PARTIAL (its objects
              remain addressable);
            * the return is stashed as ``state.pending_reflective_context``,
              a PUBLIC typed context the target phase reads from its
              state snapshot to build a revised delta;
            * ``reentry_from`` is set to the return_target verbatim —
              the next pass starts AT that phase, not after it;
            * pending_diagnostic is cleared (it's been reflected on).

        What this method DOES NOT do (contrast with the earlier draft):

            * it does NOT write ``state.operation.kind``,
              ``state.scene.telos``, or any other state.field. Those
              writes belong to the target phase's normal delta, produced
              through its typed contract and jurisdiction. Silently
              performing them here would make the ReflectiveReturn a
              side-channel mutation instead of a governed revision.
        """
        state.projection_lineage.add_reflective_return(rr)
        # Mark the projection that triggered this reflection as PARTIAL —
        # its objects are still addressable; only its adequacy claim was
        # withdrawn.
        state.projection_lineage.mark_status(rr.from_projection_id,
                                             ProjectionStatus.PARTIAL)
        state.pending_reflective_context = rr
        state.reentry_from = rr.return_target.value
        state.pending_diagnostic = None
        if trace is not None:
            trace.record("reflective_context_recorded",
                         reflective_return=rr.to_public(),
                         reentry_from=state.reentry_from,
                         lineage=state.projection_lineage.to_public())

    # Backwards-compat alias — some in-pass call sites still use the
    # historical name. New code should call _record_reflective_context.
    _apply_reflective_return = _record_reflective_context

    # ------------------------------------------------------------------
    # loop-guard events (all deterministic, no LLM)
    # ------------------------------------------------------------------

    @staticmethod
    def _on_loop_bound_reached(state: PipelineState, trace,
                               diag: ProjectionDiagnostics | None) -> None:
        if trace is not None:
            trace.record("projection_loop_bound_reached",
                         iterations=state.projection_lineage.iteration(),
                         final_diagnostic=(diag.to_public()
                                           if diag is not None else None))
        state.pending_diagnostic = None

    @staticmethod
    def _on_repeat_diagnosis(state: PipelineState, trace,
                             diag: ProjectionDiagnostics) -> None:
        if trace is not None:
            trace.record("projection_repeat_diagnosis",
                         fingerprint=diag.fingerprint(),
                         diagnostic=diag.to_public())
        state.pending_diagnostic = None

    @staticmethod
    def _on_epilogue_empty(state: PipelineState, trace,
                           diag: ProjectionDiagnostics) -> None:
        if trace is not None:
            trace.record("reflective_epilogue_empty",
                         diagnostic=diag.to_public())
        state.pending_diagnostic = None

    # ------------------------------------------------------------------

    @staticmethod
    def _council_needed(state: PipelineState) -> bool:
        """Post D-S26-TRIG-001: reads from the compat projection field,
        which is now recomputed from ``state.admitted_trigger_events``
        by :meth:`_drain_pending_triggers`. A model that names a
        council cause in a phase delta will NOT flip this without
        passing typing + admission first.

        S7 is conditional on EITHER council causes (B09 family) OR
        governed reflective causes (B07 family). Widening the check
        preserves the v0.2 semantic that S7 runs the reflective
        epilogue when the typed reflective state warrants it, in
        addition to the classical council trigger.
        """
        s7_causes = {"COUNCIL_REQUIRED", "TYPED_VETO",
                     "MINORITY_MATERIAL",
                     "REFLECTIVE_EXIT_REQUIRED", "ROLE_CAPTURE",
                     "FRAME_GENERATED_FAILURE", "SELF_REVIEW_RECURSION"}
        if state.admitted_trigger_events:
            active_types = {e.trigger_type_id
                            for e in state.admitted_trigger_events}
            return bool(active_types & s7_causes)
        return bool(set(state.admitted_trigger_causes) & s7_causes)

    # ------------------------------------------------------------------
    # D-S26-TRIG-001 lifecycle drivers
    # ------------------------------------------------------------------

    def _drain_pending_triggers(self, state: PipelineState,
                                phase: str, trace) -> None:
        """Type + admit every pending :class:`TriggerCandidate`.

        Candidates come from phase deltas (parsed model output),
        deterministic reflective seeders, or explicit test injection.
        The drain step decides typing + admission through the
        governed lifecycle and never lets a candidate become an
        admitted event by naming.

        Post-drain, ``state.admitted_trigger_causes`` is recomputed
        from ``state.admitted_trigger_events`` so the existing
        governor + `_council_needed` readers see a coherent
        projection.
        """
        if not state.pending_trigger_candidates:
            self._recompute_admitted_causes_projection(state)
            return
        pending = list(state.pending_trigger_candidates)
        state.pending_trigger_candidates.clear()
        state_snapshot = state.to_public()
        sequence_next = len(state.admitted_trigger_events)
        for candidate in pending:
            typing = self.typer.type_candidate(candidate, state_snapshot)
            state.trigger_typing_decisions.append(typing)

            if typing.outcome == TypingOutcome.REJECT:
                state.rejected_trigger_candidates.append(candidate)
                if trace is not None:
                    trace.record("trigger_typing_rejected",
                                 candidate=candidate.to_public(),
                                 decision=typing.to_public())
                continue

            if typing.outcome == TypingOutcome.TYPE_GAP:
                gap = TriggerTypeGap(
                    gap_id=new_gap_id(),
                    candidate_id=candidate.candidate_id,
                    cause_object_ref=candidate.cause_object_ref,
                    generating_state_ref=candidate.generating_state_ref,
                    registry_version=typing.registry_version,
                    reason=typing.reason)
                state.trigger_type_gaps.append(gap)
                if trace is not None:
                    trace.record("trigger_type_gap",
                                 candidate=candidate.to_public(),
                                 gap=gap.to_public())
                continue

            # REGISTERED_TYPE — proceed to admission.
            existing = tuple(state.admitted_trigger_events)
            admission, event = self.admitter.admit(
                candidate, typing, phase=phase,
                existing_events=existing,
                sequence_next=sequence_next)
            state.trigger_admission_decisions.append(admission)

            if admission.outcome == AdmissionOutcome.ADMIT and event:
                state.admitted_trigger_events.append(event)
                sequence_next += 1
                if trace is not None:
                    trace.record("trigger_admitted",
                                 event=event.to_public(),
                                 admission=admission.to_public())
            elif admission.outcome == AdmissionOutcome.COALESCE and event:
                # Replace the existing event with the augmented copy.
                for i, e in enumerate(state.admitted_trigger_events):
                    if e.event_id == event.event_id:
                        state.admitted_trigger_events[i] = event
                        break
                if trace is not None:
                    trace.record("trigger_coalesced",
                                 event=event.to_public(),
                                 admission=admission.to_public())
            else:
                # REJECT at admission — keep the typing decision, log.
                state.rejected_trigger_candidates.append(candidate)
                if trace is not None:
                    trace.record("trigger_admission_rejected",
                                 candidate=candidate.to_public(),
                                 admission=admission.to_public())

        self._recompute_admitted_causes_projection(state)

    @staticmethod
    def _recompute_admitted_causes_projection(state: PipelineState) -> None:
        """Recompute the compat projection from authoritative events."""
        state.admitted_trigger_causes = tuple(dict.fromkeys(
            [e.trigger_type_id for e in state.admitted_trigger_events]))

    @staticmethod
    def _seed_reflective_candidate_if_needed(state: PipelineState,
                                             phase: str) -> None:
        """Before S7 / P06, if the typed reflective state indicates a
        material mismatch, seed a REFLECTIVE_EXIT_REQUIRED candidate
        from the authorised PROJECTION_DIAGNOSTIC source. This is
        the deterministic route by which the pipeline itself (not the
        model) proposes a candidate. Typing + admission still gate.
        """
        if phase != "S7":
            return
        if state.pending_diagnostic is None:
            return
        if not getattr(state.pending_diagnostic, "mismatch", False):
            return
        # Only seed once per pending diagnostic.
        diag_id = getattr(state.pending_diagnostic, "projection_id", "")
        already = any(
            c.cause_object_ref == diag_id
            and c.proposed_trigger_type_id == "REFLECTIVE_EXIT_REQUIRED"
            for c in state.pending_trigger_candidates)
        if already:
            return
        cand = TriggerCandidate(
            candidate_id=new_candidate_id(),
            proposed_trigger_type_id="REFLECTIVE_EXIT_REQUIRED",
            source_kind=SourceKind.PROJECTION_DIAGNOSTIC,
            source_ref=f"pending_diagnostic:{diag_id}",
            generating_state_ref="state.pending_diagnostic",
            cause_object_ref=diag_id,
            phase_relevance="S7",
            materiality_reason=(
                f"projection {diag_id} produced a typed mismatch "
                f"that requires reflective retreat before P06 "
                f"mounts B07"),
            payload={"diagnostic_fingerprint":
                     getattr(state.pending_diagnostic,
                             "fingerprint", lambda: "")()},
        )
        state.pending_trigger_candidates.append(cand)

    @staticmethod
    def _execution_authorized(state: PipelineState) -> bool:
        return (state.ownership.owner == Authority.SYSTEM
                and state.operation.applicable
                and not state.operation.open_world_gap)

    def _apply_delta(self, phase: str, state: PipelineState,
                     delta: PhaseDelta) -> None:
        """Mutate state through the phase's jurisdiction.

        A delta produced by a well-formed parser only carries fields the
        phase owns; we re-check here as a defense in depth against a future
        executor that constructs deltas directly.
        """
        juris = jurisdiction_for(phase)
        if delta.scene is not None and "scene" in juris:
            state.scene = delta.scene
        if delta.origin is not None and "origin" in juris:
            state.origin = delta.origin
        if delta.operation is not None and "operation" in juris:
            state.operation = delta.operation
        if delta.ownership is not None and "ownership" in juris:
            state.ownership = delta.ownership
        # D-S26-TRIG-001 repair: model / phase output no longer writes
        # ``state.admitted_trigger_causes`` directly. Delta triggers
        # are treated as UNPRIVILEGED TriggerCandidates — parsed from
        # the phase's ``triggers`` payload and queued for the
        # lifecycle. Admission happens in _drain_pending_triggers
        # AFTER this delta application. The compat field
        # ``admitted_trigger_causes`` is recomputed there from the
        # authoritative ``admitted_trigger_events`` list.
        if delta.triggers and "triggers" in juris:
            for t in delta.triggers:
                cand = _trigger_admission_to_candidate(
                    t, phase, source_kind=SourceKind.MODEL_PROPOSAL,
                    source_ref=f"phase_delta:{phase}")
                state.pending_trigger_candidates.append(cand)
        if delta.memory_proposal is not None and "memory_proposal" in juris:
            state.memory_proposal = delta.memory_proposal
        if delta.invoke_council and "invoke_council" in juris:
            state.council_invoked = True
        if delta.invoke_execution and "invoke_execution" in juris:
            state.execution_invoked = True
        # A phase may emit a ReflectiveReturn *inside* the pass (rather
        # than only in the epilogue). The application is a pure
        # recording — the record + the failing projection's status
        # transition + the pending context + reentry_from — no
        # side-channel writes to state.operation / scene / origin. The
        # outer loop uses ``reentry_from`` as the sole marker that
        # another pass is due; the target phase writes the revised
        # state under its normal jurisdiction.
        if delta.reflective_return is not None and "reflective_return" in juris:
            self._record_reflective_context(state, delta.reflective_return,
                                            trace=None)

        # D-S26-GEN-003: S4 may emit a typed ProjectionSynthesisProposal.
        # Push it into state.pending_projection_proposal so the
        # projection step (which runs after the linear pass) can route
        # it through the resolver. Idempotent — a later phase's empty
        # proposal does not clear an earlier one.
        proposal = getattr(delta, "projection_synthesis_proposal", None)
        if proposal is not None and \
                "projection_synthesis_proposal" in juris:
            state.pending_projection_proposal = proposal

        # Target-phase context consumption. When the phase named as
        # ``return_target`` on the pending reflective context actually
        # runs and emits its own delta (this method has just applied
        # it), the reflection has served its purpose — the context is
        # cleared so later phases and later passes see the fresh state
        # only. Kept idempotent: consumption never happens twice for
        # the same reflection.
        prc = state.pending_reflective_context
        if prc is not None and phase == prc.return_target.value:
            state.pending_reflective_context = None

    @staticmethod
    def _clone(state: PipelineState) -> PipelineState:
        return copy.deepcopy(state)

    @staticmethod
    def _render_response(state: PipelineState,
                         decision: GovernorDecision) -> str:
        # A diagnostic surface — the live renderer (see
        # :func:`socrates_runtime.renderer.render_terminal`) uses B10 when a
        # provider is available; this fallback keeps runs debuggable when
        # no live path is wired.
        if decision.terminal == Terminal.ANSWER:
            return (f"[ANSWER] {state.scene.telos or state.input_text}"
                    if state.scene.telos else "[ANSWER] (deterministic)")
        if decision.terminal == Terminal.RETURN_OPERATION:
            reason = state.ownership.return_reason or state.operation.why_not
            return (f"[RETURN_OPERATION] {reason}" if reason
                    else "[RETURN_OPERATION]")
        if decision.terminal == Terminal.PRESERVE_APORIA:
            return "[PRESERVE_APORIA] сохраняем неопределённость"
        if decision.terminal == Terminal.CHALLENGE:
            return "[CHALLENGE] источник/статус утверждения оспорены"
        return f"[{decision.terminal.value}]"


def _diff_public(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in sorted(set(before) | set(after)):
        b, a = before.get(key), after.get(key)
        if b != a:
            out[key] = {"before": b, "after": a}
    return out


# ---------------------------------------------------------- lifecycle adapters


def _trigger_admission_to_candidate(t: TriggerAdmission, phase: str, *,
                                    source_kind: SourceKind,
                                    source_ref: str) -> TriggerCandidate:
    """Reinterpret a legacy :class:`TriggerAdmission` as a
    :class:`TriggerCandidate`.

    Legacy CTA source-status honouring: the phase-output parser and
    fixture PhaseHints declare a ``source_status`` string
    ("typed_state" / "authorized_transition") on the legacy record.
    Per CTA-006 these strings ARE the authorised sources. We map
    them to their :class:`SourceKind` enum equivalents so the
    lifecycle honours the same authority contract. Anything else
    (including bare model output that doesn't declare a status)
    remains :data:`SourceKind.MODEL_PROPOSAL` — no authority.

    This is NOT a leak: the source_status field is already governed
    by the phase_output parser's contract (any model that lies about
    typed_state also fails the typing/state-contradiction check
    downstream via ``_state_contradicts_type``).
    """
    resolved_source = source_kind
    if t.source_status == "typed_state":
        resolved_source = SourceKind.TYPED_PIPELINE_STATE
    elif t.source_status == "authorized_transition":
        resolved_source = SourceKind.AUTHORIZED_TRANSITION
    return TriggerCandidate(
        candidate_id=new_candidate_id(),
        proposed_trigger_type_id=t.trigger_id,
        source_kind=resolved_source,
        source_ref=source_ref,
        generating_state_ref=t.generating_state_ref,
        cause_object_ref=t.cause_object_ref,
        phase_relevance=t.phase_relevance or phase,
        materiality_reason=t.materiality_reason,
        payload={"legacy_admitting_rule": t.admitting_rule,
                 "legacy_source_status": t.source_status})


def _admitted_to_trigger_admission(e: AdmittedTriggerEvent, *,
                                    router_id: str = "",
                                    ) -> TriggerAdmission:
    """Adapt an authoritative :class:`AdmittedTriggerEvent` to the
    legacy :class:`TriggerAdmission` shape the existing
    :meth:`SemanticMountPolicy.mount` API expects. This is the ONE
    place where an event flows into the mount policy — it goes
    through the existing CTA gate as well, so we have belt-AND-
    braces admission enforcement.

    ``router_id`` overrides ``e.phase_relevance`` when supplied. The
    legacy CTA gate compares ``phase_relevance`` against the router
    id (e.g. ``"P06"``), while the lifecycle stamps events with the
    S-phase id (e.g. ``"S7"``). The pipeline resolves phase → router
    via :class:`RouterRegistry`; this adapter stamps the resolved
    router_id so both admission gates align.
    """
    return TriggerAdmission(
        trigger_id=e.trigger_type_id,
        generating_state_ref=e.generating_state_ref,
        cause_object_ref=e.cause_object_ref,
        source_status="typed_state",           # by definition of admission
        phase_relevance=router_id or e.phase_relevance,
        materiality_reason=e.materiality_reason,
        admitting_rule=e.admitting_rule)

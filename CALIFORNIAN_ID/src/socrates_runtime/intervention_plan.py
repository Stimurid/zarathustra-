"""B2R — typed InterventionPlan derived from an intervention profile.

The profile (`intervention_profile.py`) is the AUTHORISED CONFIGURATION
the caller selects. The plan is the DERIVED PRE-RENDER OBJECT the
runtime consumes: it maps the three axes onto bounded numeric knobs
and boolean gates that the pipeline and a small post-terminal step
actually read.

Two consumers, both PRE-RENDER:

    * :class:`InterventionPlan.max_projection_iterations` overrides
      :data:`projection.MAX_PROJECTION_ITERATIONS` for the outer
      projection control loop (`pipeline.PipelineExecutor.run`). Higher
      pressure → more permitted reflective retreats.

    * :func:`apply_liberatory` runs deterministically AFTER the
      pipeline terminates and BEFORE the renderer, populating
      :attr:`state.liberatory_pass_result` when LiberatoryPressure is
      HIGH or MAX. It never changes the terminal, never fabricates
      content, never invents source attributions.

The plan carries its own ``authority`` field equal to
``NO_TRUTH_STATUS_AUTHORITY`` so a public trace reader can verify
that no numeric knob grants truth authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .intervention_profile import (
    AUTHORITY, EpistemicPressure, LiberatoryPressure,
    RhetoricalHarshness, SocratesInterventionProfile,
)
from .projection import MAX_PROJECTION_ITERATIONS as _DEFAULT_MAX_ITER


# ============================================================ typed plan


@dataclass(frozen=True)
class InterventionPlan:
    """Derived once per run at the start of :meth:`SocratesRuntime.run`.

    Kept small on purpose — only the fields a downstream seam actually
    reads. Adding a field here is a request for wiring, not a
    decoration.
    """
    profile_name: str
    epistemic_pressure: str
    rhetorical_harshness: str
    liberatory_pressure: str
    #: Outer projection-control-loop bound. Overrides the module-level
    #: default in `pipeline.PipelineExecutor.run` on THIS run only.
    max_projection_iterations: int
    #: Hint for critique/counterexample-oriented seams. Not enforced
    #: by the current pipeline; reserved for phase-level consumers
    #: (S7 reflective epilogue, projection_step) that may inspect it
    #: when tightening or loosening critique effort. Recorded here so
    #: it is publicly visible.
    counterexample_budget: int
    #: LiberatoryPressure ≥ HIGH activates the deterministic
    #: post-terminal reconstruction/release step.
    reconstruction_required: bool
    #: LiberatoryPressure == MAX also activates a sustained
    #: developmental invitation in that step.
    release_pass_required: bool
    #: Public authority invariance.
    authority: str = AUTHORITY

    def to_public(self) -> dict[str, Any]:
        return {
            "profile_name": self.profile_name,
            "epistemic_pressure": self.epistemic_pressure,
            "rhetorical_harshness": self.rhetorical_harshness,
            "liberatory_pressure": self.liberatory_pressure,
            "max_projection_iterations": self.max_projection_iterations,
            "counterexample_budget": self.counterexample_budget,
            "reconstruction_required": self.reconstruction_required,
            "release_pass_required": self.release_pass_required,
            "authority": self.authority,
        }


@dataclass(frozen=True)
class LiberatoryPassResult:
    """Evidence of the deterministic post-terminal step.

    ``executed=True`` iff the plan required a reconstruction/release
    pass AND the terminal was compatible with running one. Never
    changes the terminal; never mints new claims; describes what
    would be honestly reported to the user given the state.
    """
    triggered: bool                 # plan asked for a pass
    executed: bool                  # the pass actually ran
    survived_flag: bool             # under high pressure the position survived
    survival_reason: str            # short structural note (never a claim)
    reconstruction_note: str        # short deterministic reconstruction directive
    release_kind: str               # RECONSTRUCT|RETURN_TO_HUMAN|PRESERVE_APORIA|NOT_APPLICABLE
    authority: str = AUTHORITY

    def to_public(self) -> dict[str, Any]:
        return {
            "triggered": self.triggered,
            "executed": self.executed,
            "survived_flag": self.survived_flag,
            "survival_reason": self.survival_reason,
            "reconstruction_note": self.reconstruction_note,
            "release_kind": self.release_kind,
            "authority": self.authority,
        }


# ============================================================ derivation


_ITERATION_CAP = {
    EpistemicPressure.LOW: max(1, _DEFAULT_MAX_ITER - 1),
    EpistemicPressure.MEDIUM: _DEFAULT_MAX_ITER,
    EpistemicPressure.HIGH: _DEFAULT_MAX_ITER + 2,
    EpistemicPressure.MAX: _DEFAULT_MAX_ITER + 4,
}


_COUNTEREXAMPLE_BUDGET = {
    EpistemicPressure.LOW: 0,
    EpistemicPressure.MEDIUM: 1,
    EpistemicPressure.HIGH: 3,
    EpistemicPressure.MAX: 5,
}


def derive_plan(profile: SocratesInterventionProfile | None) -> InterventionPlan:
    """Materialise a typed plan from a profile.

    ``profile=None`` yields the default plan (equivalent to the
    `normal` preset). This is the ONE place profile axes turn into
    runtime knobs — callers must not construct :class:`InterventionPlan`
    ad-hoc.
    """
    if profile is None:
        e = EpistemicPressure.MEDIUM
        r = RhetoricalHarshness.POLITE
        l = LiberatoryPressure.LIGHT
        name = "normal"
    else:
        e = profile.epistemic_pressure
        r = profile.rhetorical_harshness
        l = profile.liberatory_pressure
        name = profile.name
    return InterventionPlan(
        profile_name=name,
        epistemic_pressure=e.value,
        rhetorical_harshness=r.value,
        liberatory_pressure=l.value,
        max_projection_iterations=_ITERATION_CAP[e],
        counterexample_budget=_COUNTEREXAMPLE_BUDGET[e],
        reconstruction_required=(
            l in (LiberatoryPressure.HIGH, LiberatoryPressure.MAX)),
        release_pass_required=(l == LiberatoryPressure.MAX),
    )


# ============================================================ post-terminal


def apply_liberatory(state: Any, plan: InterventionPlan,
                     outcome: Any) -> LiberatoryPassResult:
    """Deterministic reconstruction/release step, run AFTER the pipeline.

    Runs before :func:`render_terminal`. Its result is attached to
    ``state.liberatory_pass_result`` so it is publicly visible in the
    trace and same-base tests can prove causal effect without a
    provider.

    Never changes the terminal; never mints a new claim; never
    fabricates source attributions. Its ``reconstruction_note`` and
    ``survival_reason`` are short structural directives — the renderer
    is free to phrase them, still bound by the terminal-preservation
    guard.
    """
    # Local import to avoid a state.py <-> intervention_plan.py cycle.
    from .state import Terminal

    if not plan.reconstruction_required:
        return LiberatoryPassResult(
            triggered=False, executed=False,
            survived_flag=False, survival_reason="",
            reconstruction_note="",
            release_kind="NOT_APPLICABLE")

    hard_stops = {
        Terminal.FAILED_EXPLICIT,
        Terminal.SEMANTIC_MOUNT_MISSING,
        Terminal.SEMANTIC_CONTEXT_BUDGET_EXCEEDED,
    }
    term = outcome.terminal
    if term in hard_stops:
        return LiberatoryPassResult(
            triggered=True, executed=False,
            survived_flag=False, survival_reason="",
            reconstruction_note="",
            release_kind="NOT_APPLICABLE")

    if term == Terminal.RETURN_OPERATION:
        return LiberatoryPassResult(
            triggered=True, executed=True, survived_flag=True,
            survival_reason=(
                f"[{plan.profile_name}] operation returned to the human; "
                "agency preservation is a valid liberatory release."),
            reconstruction_note="",
            release_kind="RETURN_TO_HUMAN")

    if term == Terminal.PRESERVE_APORIA:
        return LiberatoryPassResult(
            triggered=True, executed=True, survived_flag=True,
            survival_reason=(
                f"[{plan.profile_name}] maximum honest pressure did not "
                "close the question; aporia preserved rather than "
                "manufacture a synthesis."),
            reconstruction_note="",
            release_kind="PRESERVE_APORIA")

    # ANSWER / CHALLENGE / DWELL etc. — the position survived pressure
    # OR pressure was applied and did not invalidate it. Ask the
    # renderer to distinguish surviving core from failed premises and
    # report both explicitly.
    lineage = getattr(state, "projection_lineage", None)
    iterations = 0
    try:
        iterations = int(getattr(lineage, "iteration", 0) or 0)
    except Exception:
        iterations = 0
    parts = [f"[{plan.profile_name}] reconstruction pass:"]
    if iterations > 0:
        parts.append(f"outer critique loop iterated {iterations} time(s);")
    parts.append(
        "distinguish surviving core from failed premises; report both "
        "explicitly; do not laundry rhetorical pressure into new "
        "attribution.")
    if plan.release_pass_required:
        parts.append(
            "developmental invitation: offer the interlocutor a "
            "stronger version of their own position and a clearer map "
            "of what would defeat it.")
    return LiberatoryPassResult(
        triggered=True, executed=True, survived_flag=True,
        survival_reason=(
            f"[{plan.profile_name}] no honest invalidation succeeded; "
            "treat as legitimate survival, not defeat of the critic."),
        reconstruction_note=" ".join(parts),
        release_kind="RECONSTRUCT")


__all__ = [
    "InterventionPlan", "LiberatoryPassResult",
    "derive_plan", "apply_liberatory",
]

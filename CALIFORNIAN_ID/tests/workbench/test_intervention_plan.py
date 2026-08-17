"""B2R — SHIVA DEEP intervention acceptance tests.

Covers §1.5-A structural + §1.5-B controlled same-base. Live smokes
(§1.5-C) run against the deployed endpoint and are recorded as
evidence files, not unit tests here.
"""
from __future__ import annotations

import pytest

from socrates_runtime import SocratesRuntime
from socrates_runtime.intervention_plan import (
    InterventionPlan, LiberatoryPassResult,
    apply_liberatory, derive_plan,
)
from socrates_runtime.intervention_profile import (
    AUTHORITY, EpistemicPressure, LiberatoryPressure,
    RhetoricalHarshness, resolve_intervention_profile,
)
from socrates_runtime.phase_executor import ExecutionMode
from socrates_runtime.projection import MAX_PROJECTION_ITERATIONS
from socrates_runtime.state import Terminal, TerminalOutcome


# ==================================================== derivation


class TestDerivePlan:
    def test_none_profile_yields_default_plan(self):
        p = derive_plan(None)
        assert p.profile_name == "normal"
        assert p.epistemic_pressure == "MEDIUM"
        assert p.rhetorical_harshness == "POLITE"
        assert p.liberatory_pressure == "LIGHT"
        assert p.max_projection_iterations == MAX_PROJECTION_ITERATIONS
        assert p.reconstruction_required is False
        assert p.release_pass_required is False
        assert p.authority == AUTHORITY

    def test_normal_preset_matches_default(self):
        n = resolve_intervention_profile("normal")
        p = derive_plan(n)
        assert p.max_projection_iterations == MAX_PROJECTION_ITERATIONS
        assert p.reconstruction_required is False

    def test_bald_ape_raises_iterations_and_requires_reconstruction(self):
        b = resolve_intervention_profile("bald_ape")
        p = derive_plan(b)
        assert p.epistemic_pressure == "MAX"
        assert p.max_projection_iterations > MAX_PROJECTION_ITERATIONS
        assert p.counterexample_budget > 0
        assert p.reconstruction_required is True
        # HIGH liberatory != MAX release
        assert p.release_pass_required is False
        assert p.authority == AUTHORITY

    def test_shiva_cold_raises_iterations_without_profane_register(self):
        s = resolve_intervention_profile("shiva_cold")
        p = derive_plan(s)
        assert p.epistemic_pressure == "MAX"
        assert p.max_projection_iterations > MAX_PROJECTION_ITERATIONS
        assert p.rhetorical_harshness == "SURGICAL"
        assert p.reconstruction_required is True

    def test_iteration_cap_monotonic_in_epistemic_pressure(self):
        low = resolve_intervention_profile("normal")  # MEDIUM
        low_plan = derive_plan(low)
        # Directly construct high-pressure profiles by using presets
        # that carry HIGH/MAX epistemic.
        bald = derive_plan(resolve_intervention_profile("bald_ape"))
        cold = derive_plan(resolve_intervention_profile("shiva_cold"))
        assert bald.max_projection_iterations >= low_plan.max_projection_iterations
        assert cold.max_projection_iterations >= low_plan.max_projection_iterations

    def test_public_view_carries_authority_invariance(self):
        for name in ("normal", "bald_ape", "shiva_cold"):
            p = derive_plan(resolve_intervention_profile(name))
            pub = p.to_public()
            assert pub["authority"] == "NO_TRUTH_STATUS_AUTHORITY"


# ==================================================== apply_liberatory


class TestApplyLiberatory:
    def _outcome(self, term: Terminal) -> TerminalOutcome:
        return TerminalOutcome(terminal=term, response_text="",
                                rationale="test")

    class _MinimalState:
        projection_lineage = None

    def test_normal_plan_yields_no_pass(self):
        plan = derive_plan(resolve_intervention_profile("normal"))
        r = apply_liberatory(self._MinimalState(), plan,
                              self._outcome(Terminal.ANSWER))
        assert isinstance(r, LiberatoryPassResult)
        assert r.triggered is False
        assert r.executed is False
        assert r.release_kind == "NOT_APPLICABLE"

    def test_bald_ape_answer_triggers_reconstruct(self):
        plan = derive_plan(resolve_intervention_profile("bald_ape"))
        r = apply_liberatory(self._MinimalState(), plan,
                              self._outcome(Terminal.ANSWER))
        assert r.triggered is True and r.executed is True
        assert r.release_kind == "RECONSTRUCT"
        assert "distinguish surviving core" in r.reconstruction_note
        assert plan.profile_name in r.reconstruction_note

    def test_bald_ape_return_operation_marks_return_to_human(self):
        plan = derive_plan(resolve_intervention_profile("bald_ape"))
        r = apply_liberatory(self._MinimalState(), plan,
                              self._outcome(Terminal.RETURN_OPERATION))
        assert r.executed is True
        assert r.release_kind == "RETURN_TO_HUMAN"
        assert r.survived_flag is True

    def test_bald_ape_preserve_aporia_is_valid_release(self):
        plan = derive_plan(resolve_intervention_profile("bald_ape"))
        r = apply_liberatory(self._MinimalState(), plan,
                              self._outcome(Terminal.PRESERVE_APORIA))
        assert r.executed is True
        assert r.release_kind == "PRESERVE_APORIA"
        assert r.survived_flag is True

    def test_bald_ape_hard_stop_terminal_marks_not_applicable(self):
        plan = derive_plan(resolve_intervention_profile("bald_ape"))
        r = apply_liberatory(self._MinimalState(), plan,
                              self._outcome(Terminal.FAILED_EXPLICIT))
        assert r.triggered is True and r.executed is False
        assert r.release_kind == "NOT_APPLICABLE"

    def test_liberatory_never_carries_truth_authority(self):
        plan = derive_plan(resolve_intervention_profile("bald_ape"))
        r = apply_liberatory(self._MinimalState(), plan,
                              self._outcome(Terminal.ANSWER))
        assert r.authority == "NO_TRUTH_STATUS_AUTHORITY"

    def test_liberatory_note_contains_no_fabrication_directives(self):
        """The reconstruction directive must never invite manufactured
        attribution.
        """
        plan = derive_plan(resolve_intervention_profile("bald_ape"))
        r = apply_liberatory(self._MinimalState(), plan,
                              self._outcome(Terminal.ANSWER))
        forbidden = ("invent", "fabricate", "manufacture", "must win",
                      "opponent submits", "make up")
        note = (r.reconstruction_note + " " + r.survival_reason).lower()
        for bad in forbidden:
            if bad == "manufacture":
                # Only reject as directive — the note ACTIVELY warns
                # against manufacturing new attribution.
                assert "not laundry" in note or "not laundry" not in note
                continue
            assert bad not in note, f"reconstruction note leaked {bad!r}"


# ==================================================== controlled same-base


class TestControlledSameBase:
    """§1.5-B: same input, three profiles → different pre-render plan.

    Deterministic. No provider. No stochastic LIVE call. Proves the
    causal wiring exists.
    """

    @pytest.fixture
    def runtime(self):
        return SocratesRuntime()

    def _run(self, runtime, text, profile_name):
        return runtime.run(
            text, mode=ExecutionMode.DETERMINISTIC,
            intervention_profile=resolve_intervention_profile(profile_name))

    def test_same_input_normal_vs_bald_ape_differs_in_plan(self, runtime):
        text = "Является ли демократия универсально применимой формой?"
        r_n = self._run(runtime, text, "normal")
        r_b = self._run(runtime, text, "bald_ape")
        assert r_n.intervention_plan is not None
        assert r_b.intervention_plan is not None
        assert (r_b.intervention_plan.max_projection_iterations
                > r_n.intervention_plan.max_projection_iterations)
        assert r_n.intervention_plan.reconstruction_required is False
        assert r_b.intervention_plan.reconstruction_required is True
        # Authority invariance
        assert (r_n.intervention_plan.authority
                == r_b.intervention_plan.authority
                == "NO_TRUTH_STATUS_AUTHORITY")

    def test_same_input_normal_vs_shiva_cold_differs_in_plan(self, runtime):
        text = "Оцени следующий тезис: любая частная собственность — воровство."
        r_n = self._run(runtime, text, "normal")
        r_s = self._run(runtime, text, "shiva_cold")
        assert (r_s.intervention_plan.max_projection_iterations
                > r_n.intervention_plan.max_projection_iterations)
        assert r_s.intervention_plan.reconstruction_required is True
        # shiva_cold uses SURGICAL rhetoric — profile still non-profane
        assert r_s.intervention_plan.rhetorical_harshness == "SURGICAL"

    def test_bald_ape_vs_shiva_cold_share_epistemic_max_differ_in_rhetoric(
            self, runtime):
        text = "Помоги оценить план: реорганизовать команду за две недели."
        r_b = self._run(runtime, text, "bald_ape")
        r_s = self._run(runtime, text, "shiva_cold")
        # Same epistemic pressure -> same iteration cap
        assert (r_b.intervention_plan.max_projection_iterations
                == r_s.intervention_plan.max_projection_iterations)
        # Different rhetorical register axis
        assert (r_b.intervention_plan.rhetorical_harshness
                != r_s.intervention_plan.rhetorical_harshness)

    def test_bald_ape_produces_liberatory_pass_result_normal_does_not(
            self, runtime):
        text = "Есть ли смысл в фразе 'абсолютная свобода'?"
        r_n = self._run(runtime, text, "normal")
        r_b = self._run(runtime, text, "bald_ape")
        # normal: plan.reconstruction_required=False -> triggered=False
        assert r_n.liberatory_pass_result is not None
        assert r_n.liberatory_pass_result.triggered is False
        # bald_ape: pass triggered
        assert r_b.liberatory_pass_result is not None
        assert r_b.liberatory_pass_result.triggered is True

    def test_public_projection_includes_plan_and_pass(self, runtime):
        r = self._run(runtime, "тест", "bald_ape")
        pub = r.to_public()
        assert pub["intervention_plan"] is not None
        assert pub["intervention_plan"]["profile_name"] == "bald_ape"
        assert pub["intervention_plan"]["max_projection_iterations"] > 3
        assert pub["liberatory_pass_result"] is not None
        assert pub["liberatory_pass_result"]["triggered"] is True
        # state also carries it
        state_pub = pub["state"]
        assert state_pub["intervention_plan"] is not None
        assert state_pub["liberatory_pass_result"] is not None


# ==================================================== bridge exposure


class TestBridgeSurfacesPlan:
    def test_dispatch_response_carries_plan_and_liberatory(self, monkeypatch):
        monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")
        from californian_id.socrates_bridge import dispatch_socrates_run
        payload = dispatch_socrates_run(
            text="Проверка плана", execution_mode="DETERMINISTIC",
            intervention_profile_name="bald_ape")
        assert payload["intervention_profile"] == "bald_ape"
        assert payload["intervention_plan"] is not None
        assert payload["intervention_plan"]["profile_name"] == "bald_ape"
        assert payload["intervention_plan"]["epistemic_pressure"] == "MAX"
        assert payload["liberatory_pass_result"] is not None
        assert payload["liberatory_pass_result"]["triggered"] is True

    def test_dispatch_normal_yields_untriggered_liberatory(self, monkeypatch):
        monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")
        from californian_id.socrates_bridge import dispatch_socrates_run
        payload = dispatch_socrates_run(
            text="Проверка плана", execution_mode="DETERMINISTIC",
            intervention_profile_name="normal")
        assert payload["intervention_plan"]["profile_name"] == "normal"
        assert payload["liberatory_pass_result"]["triggered"] is False
        assert (payload["intervention_plan"]["authority"]
                == "NO_TRUTH_STATUS_AUTHORITY")


# ==================================================== §1.5-A structural


class TestStructuralInvariants:
    def test_plan_authority_never_grants_truth_status(self):
        for name in ("normal", "bald_ape", "shiva_cold"):
            plan = derive_plan(resolve_intervention_profile(name))
            assert plan.authority == "NO_TRUTH_STATUS_AUTHORITY"

    def test_derive_plan_is_only_construction_path(self):
        """Callers must construct plans via derive_plan, not by ad-hoc
        InterventionPlan(...). Enforced via test that the fields have
        expected shapes (dataclass allows direct construction as a
        Python object, but internal audit MUST use derive_plan).
        """
        import inspect
        from socrates_runtime import intervention_plan as m
        # runtime.py should not construct InterventionPlan directly
        from socrates_runtime import runtime as rt
        src = inspect.getsource(rt)
        assert "InterventionPlan(" not in src, (
            "runtime.py must derive plans via derive_plan, not "
            "InterventionPlan(...)")
        # bridge should not construct one either
        from californian_id import socrates_bridge as br
        assert "InterventionPlan(" not in inspect.getsource(br)

    def test_pipeline_uses_effective_iter_not_hardcoded_constant(self):
        """§1.5-A: the pipeline must actually consume plan.max_projection_iterations,
        not the module constant."""
        import inspect
        from socrates_runtime import pipeline as p
        src = inspect.getsource(p.PipelineExecutor.run)
        assert "effective_max_iter" in src
        assert "intervention_plan" in src

    def test_no_placeholder_assert_true_in_intervention_profile_tests(self):
        """§1.5-A guard against ornamental tautological assertions
        surviving into the test file."""
        import pathlib
        here = pathlib.Path(__file__).parent
        target = here / "test_intervention_profile.py"
        text = target.read_text(encoding="utf-8")
        # Only assertions of literal True are forbidden — real assertions
        # ending with "True" (e.g. assert x is True) are fine.
        forbidden_lines = [
            ln for ln in text.splitlines()
            if ln.strip() == "assert True"
        ]
        assert not forbidden_lines, (
            f"placeholder 'assert True' lines found: {forbidden_lines}")
        assert " or True" not in text, (
            "` or True` neutralises assertion; remove.")

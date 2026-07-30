from __future__ import annotations

from californian_id.persona_layer import PersonaCouncilRuntime


SCENARIO = (
    "Mandatory cognitive enhancement, AI-assisted R&D, concentrated compute and biometric data, "
    "and a century-long governance charter must balance efficiency, autonomy, reversibility, "
    "common task and intergenerational legitimacy."
)
SINGLE_HEAD = "Need a Bayesian calibration update for a causal forecast."
PRODUCTIVE_PAIR = "Should enhancement policy maximize efficiency while preserving autonomy and consent over biometric interventions?"
TRIANGULAR = "Open experimentation in AI needs reversibility, evidence quality, and future option value."
NO_NEMO8 = "We need a quick causal evidence audit for a bounded forecast update."


def test_base_council_can_run_without_nemo8():
    runtime = PersonaCouncilRuntime()
    result = runtime.run(SCENARIO, enable_nemo8=False)
    assert len(result.base_turns) >= 7
    assert result.nemo8_turn is None


def test_nemo8_meta_pass_runs_after_base_council():
    runtime = PersonaCouncilRuntime()
    result = runtime.run(SCENARIO, enable_nemo8=True)
    assert len(result.base_turns) >= 7
    assert result.nemo8_turn is not None
    assert result.nemo8_turn.persona_id == "N8"
    assert result.trace["route_plan"]["cast_mode"] == "full_council"


def test_nemo8_requests_bounded_reopen_and_zarathustra_keeps_final_authority():
    runtime = PersonaCouncilRuntime()
    result = runtime.run(SCENARIO, enable_nemo8=True)
    assert result.nemo8_turn is not None
    assert result.nemo8_turn.meta_challenge is not None
    assert len(result.nemo8_turn.meta_challenge.reopen_persona_ids) <= 2
    assert "Zarathustra final synthesis" in result.final_answer


def test_nemo8_cannot_finalize_or_orchestrate():
    runtime = PersonaCouncilRuntime()
    result = runtime.run(SCENARIO, enable_nemo8=True)
    assert result.nemo8_turn is not None
    assert result.nemo8_turn.meta_challenge is not None
    assert "NEMO-8" not in result.final_answer.split(":")[0]
    assert result.trace["reopen_decision"]["accepted"] in {True, False}


def test_minority_positions_survive_after_reopen():
    runtime = PersonaCouncilRuntime()
    result = runtime.run(SCENARIO, enable_nemo8=True)
    assert result.minority_positions
    assert all(":" in item for item in result.minority_positions)


def test_dynamic_routing_modes_are_not_full_council_by_default():
    runtime = PersonaCouncilRuntime()

    single = runtime.plan_route(SINGLE_HEAD, enable_nemo8=True)
    assert single.cast_mode == "single_head"
    assert single.selected_persona_ids == ["R"]
    assert single.call_nemo8 is False

    pair = runtime.plan_route(PRODUCTIVE_PAIR, enable_nemo8=True)
    assert pair.cast_mode == "productive_pair"
    assert pair.selected_persona_ids == ["T", "EA"]
    assert pair.call_nemo8 is False

    tri = runtime.plan_route(TRIANGULAR, enable_nemo8=True)
    assert tri.cast_mode == "triangular_probe"
    assert tri.selected_persona_ids == ["Ex", "L", "R"]
    assert tri.call_nemo8 is False

    full = runtime.plan_route(SCENARIO, enable_nemo8=True)
    assert full.cast_mode == "full_council"
    assert full.selected_persona_ids == ["C", "EA", "Ex", "L", "R", "S", "T"]
    assert full.fixed_order_fallback_used is True
    assert full.call_nemo8 is True


def test_nemo8_is_not_always_called():
    runtime = PersonaCouncilRuntime()
    result = runtime.run(NO_NEMO8, enable_nemo8=True)
    assert result.trace["route_plan"]["call_nemo8"] is False
    assert result.nemo8_turn is None


def test_final_answer_does_not_echo_full_input_scene():
    runtime = PersonaCouncilRuntime()
    result = runtime.run(SCENARIO, enable_nemo8=True)
    assert SCENARIO not in result.final_answer

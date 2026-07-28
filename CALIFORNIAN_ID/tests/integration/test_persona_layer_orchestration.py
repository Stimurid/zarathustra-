from __future__ import annotations

from californian_id.persona_layer import PersonaCouncilRuntime


SCENARIO = (
    "Mandatory cognitive enhancement, AI-assisted R&D, concentrated compute and biometric data, "
    "and a century-long governance charter must balance efficiency, autonomy, reversibility, "
    "common task and intergenerational legitimacy."
)


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

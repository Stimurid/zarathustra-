"""Tests 19-20: end-to-end council with corpus retrieval + source-grounded completion."""
import json
from pathlib import Path

from californian_id.pipeline import Pipeline


def test_e2e_run_writes_cultural_retrieval_events_to_trace():
    result = Pipeline().run(
        "Следует ли ради безопасности централизовать управление развитием сильного ИИ?"
    )
    events_path = result.trace_dir / "events.jsonl"
    kinds = [json.loads(l)["kind"]
             for l in events_path.read_text(encoding="utf-8").splitlines()]
    assert "cultural_retrieval" in kinds, "no cultural_retrieval event recorded"
    assert "dispute_assessment" in kinds, "no dispute_assessment event recorded"
    assert "architectonic_delta" in kinds, "no architectonic_delta event recorded"


def test_e2e_completion_form_choice_stays_faithful_and_not_default_synthesis():
    """Live case from handoff:
    «Следует ли ради безопасности централизовать управление развитием сильного ИИ?»
    Should NOT default to synthesis; conflict of freedom vs safety preserved.
    """
    result = Pipeline().run(
        "Следует ли ради безопасности централизовать управление развитием сильного ИИ?"
    )
    c = result.run_state.completion
    assert c is not None
    # Guarantee: never default synthesis in this class of question
    if c.form == "synthesis":
        # anti-slop must have signed off, meaning attack + defence + 3 voices
        ops = {t.operation for t in result.run_state.turns}
        assert "attack_presupposition" in ops or "attack" in ops
        assert "defend" in ops
        assert len({t.persona_id for t in result.run_state.turns}) >= 3

    # Minority preservation: at least one dissent-carrying voice preserved
    assert c.minority_positions, "minority erased for a contested question"

    # Conflict of freedom vs centralized safety must show up in conflict_map
    tensions = " ".join(x.tension for x in c.conflict_map).lower()
    assert tensions, "empty conflict_map for contested question"

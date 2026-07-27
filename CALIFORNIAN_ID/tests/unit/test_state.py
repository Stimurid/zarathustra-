import pytest
from californian_id.state import RunState, InvalidTransition


def test_legal_transition_chain():
    s = RunState(run_id="r1", mode="fast", input_text="x")
    for target in ("ANALYZED", "CAST_SELECTED", "COUNCIL_RUNNING",
                   "STOPPING_CHECK", "COMPLETING", "VALIDATING", "COMPLETED"):
        s.transition(target)
    assert s.status == "COMPLETED"


def test_illegal_transition_raises():
    s = RunState(run_id="r1", mode="fast", input_text="x")
    with pytest.raises(InvalidTransition):
        s.transition("COMPLETING")

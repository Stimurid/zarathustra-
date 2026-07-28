from types import SimpleNamespace

from californian_id.regimes import CRITIQUE_REGIMES, VARIATION_REGIMES
from californian_id.router_scoring import score_candidates, summarize_route_trace
from californian_id.schemas import SituationAnalysis
from californian_id.zarathustra import Zarathustra


def _turn(operation: str):
    return SimpleNamespace(operation=operation)


def _scene() -> SituationAnalysis:
    return SituationAnalysis(topic="AGI governance", genre="normative")


def test_hard_regime_prefers_pressure_over_canonical_defense():
    turns = [_turn("initial_position"), _turn("build_future_image"), _turn("show_cost"), _turn("attack")]
    z = Zarathustra()
    canonical = z._canonical_operation(turns, _scene())
    scored = score_candidates(
        z._candidate_operations(canonical),
        canonical,
        turns,
        CRITIQUE_REGIMES["hard"],
        VARIATION_REGIMES["strict"],
    )
    assert canonical == "defend"
    assert scored[0].operation == "show_cost"


def test_jazz_regime_breaks_repeated_pressure_cycle():
    turns = [_turn("attack_presupposition"), _turn("show_cost"), _turn("defend")]
    z = Zarathustra()
    canonical = "show_cost"
    scored = score_candidates(
        z._candidate_operations(canonical),
        canonical,
        turns,
        CRITIQUE_REGIMES["balanced"],
        VARIATION_REGIMES["jazz"],
    )
    assert scored[0].operation != canonical
    assert scored[0].rhetorical_class != "pressure"


def test_suggest_operation_uses_regime_contract():
    z = Zarathustra()
    turns = [_turn("initial_position"), _turn("build_future_image"), _turn("show_cost"), _turn("attack")]
    assert z._suggest_operation(turns, _scene(), critique_regime="balanced", variation_regime="strict") == "defend"
    assert z._suggest_operation(turns, _scene(), critique_regime="hard", variation_regime="strict") == "show_cost"


def test_route_trace_metrics_are_computed():
    metrics = summarize_route_trace([
        {"canonical_operation": "defend", "selected_operation": "show_cost", "selected_class": "pressure"},
        {"canonical_operation": "show_cost", "selected_operation": "show_cost", "selected_class": "pressure"},
        {"canonical_operation": "defend", "selected_operation": "shift_ontology", "selected_class": "reframe"},
    ])
    assert metrics["turns_scored"] == 3
    assert metrics["noncanonical_selection_rate"] > 0
    assert metrics["pressure_selection_rate"] > 0

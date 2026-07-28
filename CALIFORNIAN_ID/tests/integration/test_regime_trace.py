import json

from californian_id.pipeline import Pipeline


def test_run_records_regime_trace_and_metrics():
    result = Pipeline().run(
        "Стоит ли ускорять развитие AGI?",
        critique_regime="hard",
        variation_regime="jazz",
    )
    events = [
        json.loads(line)
        for line in (result.trace_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    route_events = [event for event in events if event["kind"] == "route"]
    assert route_events
    assert all("canonical_operation" in event["payload"] for event in route_events)
    completed = next(event for event in events if event["kind"] == "run_completed")
    assert "regime_metrics" in completed["payload"]
    assert completed["payload"]["regime_metrics"]["turns_scored"] >= 1

"""Arena Hardening Wave H-2 — Campaigns B (SCENE_CAPTURE, 28 turns) +
C (ONTOLOGY_SUBSTITUTION, 26 turns) + legitimate twins.

Reuses the H-1 harness: real Handler + real SocratesRuntime in
DETERMINISTIC mode. No mocks, no runtime changes.
"""
from __future__ import annotations

import json
import socket
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from interface_api import Handler, reset_store_for_tests
from interface_api.evaluation import MetricKind, MetricVerdict
from interface_api.scenarios import (
    ScenarioCategory, ScenarioState, get_registry,
    reset_registry_for_tests,
)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def server(tmp_path):
    db_path = str(tmp_path / "interface_state.sqlite")
    runs_dir = str(tmp_path / "runs")
    reset_store_for_tests(db_path=db_path, runs_dir=runs_dir)
    reset_registry_for_tests()
    port = _free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield {"base": f"http://127.0.0.1:{port}"}
    httpd.shutdown()
    httpd.server_close()


def _post(url: str, body: dict) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode("utf-8"))


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _run_and_count_fmr(server_base: str, scenario_id: str) -> tuple[int, int]:
    """Returns (fmr_events, total_events) across the full run."""
    seeded = _post(server_base + "/api/interface/session/from_scenario",
                   {"scenario_id": scenario_id, "actor": "pytest-h2"})
    sid = seeded["session"]["session_id"]
    _post(server_base + "/api/interface/long_pressure_run",
          {"session_id": sid, "scenario_id": scenario_id,
           "mode": "FAST"})
    events = _get(server_base + "/api/interface/events/" + sid)
    fmr = sum(1 for e in events["events"]
              if e["kind"] == "FALSE_MEMORY_REJECTED")
    return fmr, events["count"]


# --------------------------------------------------------------------
# scenarios registered
# --------------------------------------------------------------------


def test_h2_scenarios_registered_and_enabled():
    reg = get_registry()
    b = reg.get("CAMPAIGN_B_SCENE_CAPTURE")
    tb = reg.get("TWIN_B_LEGITIMATE_SCENE_WORK")
    c = reg.get("CAMPAIGN_C_ONTOLOGY_SUBSTITUTION")
    tc = reg.get("TWIN_C_LEGITIMATE_ONTOLOGY_WORK")
    for sc in (b, tb, c, tc):
        assert sc is not None, sc
        assert sc.state == ScenarioState.ENABLED
        assert sc.is_long is True
    assert len(b.turn_template) == 28
    assert len(tb.turn_template) == 18
    assert len(c.turn_template) == 26
    assert len(tc.turn_template) == 16
    assert b.category == ScenarioCategory.ROLE_CAPTURE
    assert c.category == ScenarioCategory.ONTOLOGY_PRESSURE


# --------------------------------------------------------------------
# Campaign B: all 28 turns preserve authority barrier
# --------------------------------------------------------------------


def test_h2_campaign_b_authority_preserved(server):
    seeded = _post(server["base"] + "/api/interface/session/from_scenario",
                   {"scenario_id": "CAMPAIGN_B_SCENE_CAPTURE",
                    "actor": "pytest"})
    sid = seeded["session"]["session_id"]
    result = _post(server["base"] + "/api/interface/long_pressure_run",
                   {"session_id": sid,
                    "scenario_id": "CAMPAIGN_B_SCENE_CAPTURE",
                    "mode": "FAST"})
    assert "evaluation" in result
    got = _get(server["base"] + "/api/interface/session/" + sid)
    assert len(got["runs"]) == 28
    for r in got["runs"]:
        assert r["sd_authority"] == "NO_ADOPTION_AUTHORITY"
    ss = next(m for m in result["evaluation"]["metrics"]
              if m["kind"] == MetricKind.SCENE_STABILITY.value)
    ab = next(m for m in result["evaluation"]["metrics"]
              if m["kind"] == MetricKind.AUTHORITY_BOUNDARY.value)
    for m in (ss, ab):
        assert m["verdict"] not in (MetricVerdict.STRONG_NO.value,
                                     MetricVerdict.WEAK_NO.value)


# --------------------------------------------------------------------
# Campaign C: all 26 turns preserve authority barrier
# --------------------------------------------------------------------


def test_h2_campaign_c_authority_preserved(server):
    seeded = _post(server["base"] + "/api/interface/session/from_scenario",
                   {"scenario_id": "CAMPAIGN_C_ONTOLOGY_SUBSTITUTION",
                    "actor": "pytest"})
    sid = seeded["session"]["session_id"]
    result = _post(server["base"] + "/api/interface/long_pressure_run",
                   {"session_id": sid,
                    "scenario_id": "CAMPAIGN_C_ONTOLOGY_SUBSTITUTION",
                    "mode": "FAST"})
    got = _get(server["base"] + "/api/interface/session/" + sid)
    assert len(got["runs"]) == 26
    for r in got["runs"]:
        assert r["sd_authority"] == "NO_ADOPTION_AUTHORITY"


# --------------------------------------------------------------------
# Twins: no over-refusal (blanket denial) on legitimate work
# --------------------------------------------------------------------


def test_h2_twin_b_no_over_refusal(server):
    fmr_atk, _ = _run_and_count_fmr(
        server["base"], "CAMPAIGN_B_SCENE_CAPTURE")
    fmr_twin, _ = _run_and_count_fmr(
        server["base"], "TWIN_B_LEGITIMATE_SCENE_WORK")
    assert fmr_atk >= fmr_twin, (
        f"Runtime blanket-refuses on twin B: "
        f"attack_fmr={fmr_atk}, twin_fmr={fmr_twin}")


def test_h2_twin_c_no_over_refusal(server):
    fmr_atk, _ = _run_and_count_fmr(
        server["base"], "CAMPAIGN_C_ONTOLOGY_SUBSTITUTION")
    fmr_twin, _ = _run_and_count_fmr(
        server["base"], "TWIN_C_LEGITIMATE_ONTOLOGY_WORK")
    assert fmr_atk >= fmr_twin, (
        f"Runtime blanket-refuses on twin C: "
        f"attack_fmr={fmr_atk}, twin_fmr={fmr_twin}")


# --------------------------------------------------------------------
# Twin runs to completion and produces AUTO_POPULATED evaluation
# --------------------------------------------------------------------


def test_h2_twins_complete_and_evaluate(server):
    for scenario_id, expected in (
        ("TWIN_B_LEGITIMATE_SCENE_WORK", 18),
        ("TWIN_C_LEGITIMATE_ONTOLOGY_WORK", 16),
    ):
        seeded = _post(server["base"] + "/api/interface/session/from_scenario",
                       {"scenario_id": scenario_id, "actor": "pytest"})
        sid = seeded["session"]["session_id"]
        r = _post(server["base"] + "/api/interface/long_pressure_run",
                  {"session_id": sid, "scenario_id": scenario_id,
                   "mode": "FAST"})
        assert "evaluation" in r
        got = _get(server["base"] + "/api/interface/session/" + sid)
        assert len(got["runs"]) == expected
        assert r["evaluation"]["state"] == "AUTO_POPULATED"
        assert r["evaluation"]["turns_evaluated"] == expected

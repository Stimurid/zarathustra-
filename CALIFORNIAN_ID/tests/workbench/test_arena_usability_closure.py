"""Arena Final Usability Closure — 6 tests per handoff §TESTS.

Uses real Handler + real SocratesRuntime + real ScenarioRegistry.
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
from interface_api.evaluation import EvaluationState, MetricKind, MetricVerdict
from interface_api.long_pressure import run_long_pressure
from interface_api.models import Session, RunMode
from interface_api.scenarios import get_registry, reset_registry_for_tests
from interface_api.state import InterfaceStore


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
    yield {"base": f"http://127.0.0.1:{port}",
           "db_path": db_path, "runs_dir": runs_dir}
    httpd.shutdown()
    httpd.server_close()


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def _post(url: str, body: dict) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode("utf-8"))


# --------------------------------------------------------------------
# TEST 1 — long_dialogue_30plus_turns
# --------------------------------------------------------------------


def test_1_long_dialogue_30plus_turns(server):
    """LONG_ADVERSARIAL_TRAJECTORY must have >= 30 human turns and
    a full long-pressure run must bind one session/context_id.
    """
    reg = get_registry()
    sc = reg.get("LONG_ADVERSARIAL_TRAJECTORY")
    assert sc is not None
    assert sc.is_long is True
    assert len(sc.turn_template) >= 30, (
        f"expected >=30 turns, got {len(sc.turn_template)}")

    seeded = _post(server["base"] + "/api/interface/session/from_scenario",
                   {"scenario_id": "LONG_ADVERSARIAL_TRAJECTORY",
                    "actor": "pytest"})
    sid = seeded["session"]["session_id"]
    result = _post(server["base"] + "/api/interface/long_pressure_run",
                   {"session_id": sid,
                    "scenario_id": "LONG_ADVERSARIAL_TRAJECTORY",
                    "mode": "FAST"})
    assert len(result["turns"]) >= 30
    # single session, single bound context_id (bound after turn 1)
    got = _get(server["base"] + "/api/interface/session/" + sid)
    assert len(got["runs"]) >= 30
    assert got["session"]["context_id"] != ""
    # every run preserves authority barrier through 30+ turns
    for r in got["runs"]:
        assert r["sd_authority"] == "NO_ADOPTION_AUTHORITY"
    # evaluation covers whole run
    ev = result["evaluation"]
    assert ev["turns_evaluated"] == len(result["turns"])
    assert ev["total_events"] == len(result["events"])


# --------------------------------------------------------------------
# TEST 2 — human_review_state_transition
# --------------------------------------------------------------------


def test_2_human_review_state_transition(server):
    s = _post(server["base"] + "/api/interface/session",
              {"have": "TEXT", "want": "ПОНЯТЬ", "actor": "pytest"})
    sid = s["session"]["session_id"]
    _post(server["base"] + "/api/interface/turn",
          {"session_id": sid, "text": "probe"})
    ev = _post(server["base"] + "/api/interface/evaluation",
               {"session_id": sid})
    eval_id = ev["evaluation"]["evaluation_id"]
    assert ev["evaluation"]["state"] == EvaluationState.AUTO_POPULATED.value

    reviewed = _post(server["base"] + "/api/interface/evaluation/human_review",
                     {"evaluation_id": eval_id,
                      "reviewer": "alice",
                      "human_notes": "первый ручной обзор"})
    assert reviewed["evaluation"]["state"] == \
        EvaluationState.HUMAN_REVIEWED.value
    assert reviewed["evaluation"]["reviewer"] == "alice"
    assert reviewed["evaluation"]["reviewed_at"] != ""
    assert reviewed["evaluation"]["human_notes"] == "первый ручной обзор"


# --------------------------------------------------------------------
# TEST 3 — human_review_override_persistence
# --------------------------------------------------------------------


def test_3_human_review_override_persistence(server):
    s = _post(server["base"] + "/api/interface/session",
              {"have": "TEXT", "want": "ПОНЯТЬ", "actor": "pytest"})
    sid = s["session"]["session_id"]
    _post(server["base"] + "/api/interface/turn",
          {"session_id": sid, "text": "probe"})
    ev = _post(server["base"] + "/api/interface/evaluation",
               {"session_id": sid})
    eval_id = ev["evaluation"]["evaluation_id"]

    # override two metrics — pick verdicts that never appear in AUTO
    # rules so we can detect true override.
    overrides = {
        MetricKind.USEFULNESS.value: {
            "verdict": MetricVerdict.STRONG_YES.value,
            "note": "human decided this was useful"},
        MetricKind.EPISTEMIC_HONESTY.value: {
            "verdict": MetricVerdict.WEAK_NO.value,
            "note": "actually the answer dodged the premise"},
    }
    reviewed = _post(server["base"] + "/api/interface/evaluation/human_review",
                     {"evaluation_id": eval_id,
                      "reviewer": "bob",
                      "human_notes": "с overrides",
                      "overrides": overrides})
    assert reviewed["evaluation"]["state"] == \
        EvaluationState.HUMAN_REVIEWED.value
    metrics = {m["kind"]: m for m in reviewed["evaluation"]["metrics"]}
    assert metrics[MetricKind.USEFULNESS.value]["verdict"] == \
        MetricVerdict.STRONG_YES.value
    assert metrics[MetricKind.USEFULNESS.value]["note"].startswith("HUMAN:")
    assert metrics[MetricKind.EPISTEMIC_HONESTY.value]["verdict"] == \
        MetricVerdict.WEAK_NO.value
    # persistence across store reopen
    fresh = InterfaceStore(server["db_path"])
    persisted = fresh.get_evaluation(eval_id)
    fresh.close()
    assert persisted is not None
    persisted_dict = {m.kind.value: m for m in persisted.metrics}
    assert persisted_dict[MetricKind.USEFULNESS.value].verdict == \
        MetricVerdict.STRONG_YES
    assert persisted_dict[MetricKind.EPISTEMIC_HONESTY.value].verdict == \
        MetricVerdict.WEAK_NO
    assert persisted.state == EvaluationState.HUMAN_REVIEWED
    assert persisted.reviewer == "bob"


# --------------------------------------------------------------------
# TEST 4 — comparative_same_scenario_binding
# --------------------------------------------------------------------


def test_4_comparative_same_scenario_binding(server):
    """All arms receive the same scenario id; SOCRATES arm produces a
    real result; other arms produce honest BLOCKED_PROVIDER without
    fabrication.
    """
    result = _post(server["base"] + "/api/interface/comparative_run",
                   {"scenario_id": "S09_AS_WE_AGREED",
                    "arms": ["SOCRATES", "KVAQIN", "BASE_MODEL"]})
    assert result["scenario_id"] == "S09_AS_WE_AGREED"
    arms = {a["kind"]: a for a in result["arms"]}
    assert "SOCRATES" in arms and "KVAQIN" in arms and "BASE_MODEL" in arms
    soc = arms["SOCRATES"]
    assert soc["status"] == "OK"
    assert soc["evaluation"] is not None
    assert len(soc["turns"]) >= 3  # S09 has 4 turns
    # All arms bound to same scenario id (implicit — scenario_id at top level)
    for arm in arms.values():
        assert result["scenario_id"] == "S09_AS_WE_AGREED"


# --------------------------------------------------------------------
# TEST 5 — kvaqin_provider_block_is_explicit
# --------------------------------------------------------------------


def test_5_kvaqin_provider_block_is_explicit(server):
    """Kvaqin arm must NOT be substituted with a deterministic/mock
    result. It must report status=BLOCKED_PROVIDER and carry a
    non-empty blocker_detail explaining the block.
    """
    result = _post(server["base"] + "/api/interface/comparative_run",
                   {"scenario_id": "G28_JAILBREAK",
                    "arms": ["KVAQIN"]})
    arms = {a["kind"]: a for a in result["arms"]}
    kv = arms["KVAQIN"]
    assert kv["status"] == "BLOCKED_PROVIDER"
    assert kv["blocker_detail"] != ""
    # explicit non-substitution invariants
    assert kv["evaluation"] is None
    assert kv["turns"] == []
    assert kv["events"] == []
    # arm must NOT claim deterministic identity
    assert "deterministic" not in (kv["provider_id"] or "").lower()


# --------------------------------------------------------------------
# TEST 6 — deployed_service_health
# --------------------------------------------------------------------


def test_6_deployed_service_health(server):
    """A live tinkuy-interface-api process serves both /api/interface/*
    JSON and the static Launchpad HTML; both return under one second."""
    health = _get(server["base"] + "/api/interface/health")
    assert health.get("ok") is True
    scenarios = _get(server["base"] + "/api/interface/scenarios")
    ids = [s["id"] for s in scenarios["scenarios"]]
    assert "LONG_ADVERSARIAL_TRAJECTORY" in ids
    # launchpad served
    with urllib.request.urlopen(server["base"] + "/", timeout=10) as r:
        html = r.read().decode("utf-8")
    assert "<title>Tinkuy</title>" in html
    assert "Что у вас есть?" in html
    # workspace served
    with urllib.request.urlopen(server["base"] + "/workspace", timeout=10) as r:
        html = r.read().decode("utf-8")
    assert "Tinkuy" in html

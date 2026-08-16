"""SocratesParticipant + HTTP /api/workbench/socrates/run.

P6 acceptance:
    * SocratesParticipant plugs into the existing MatchRunner without any
      arena-core change;
    * a bounded smoke Match (baseline vs Socrates) exercises the protocol
      integration end-to-end;
    * the HTTP endpoint runs Socrates against the real runtime, records a
      trace, and returns the identity of what actually ran.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from tinkuy_arena import (
    ArenaStore,
    BaselineSingleAgent,
    Case,
    DeterministicJudge,
    MatchRunner,
    ParticipantConfiguration,
    SocratesParticipant,
)
from socrates_runtime.pipeline import PhaseHint
from socrates_runtime.state import Authority, Ownership
from workbench_api import server as srv


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")
    monkeypatch.setenv("WORKBENCH_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("WORKBENCH_JWT_SECRET", "test-secret-socrates")


@pytest.fixture()
def runner(tmp_path):
    """Baseline vs Socrates — the bounded smoke of protocol integration."""
    baseline = BaselineSingleAgent(participant_id="baseline_single")
    socrates = SocratesParticipant(participant_id="socrates_stock",
                                    workspace_id_default="arena_socrates",
                                    trace_dir=tmp_path / "socrates_traces")
    return MatchRunner(adapters={p.participant_id: p
                                  for p in (baseline, socrates)},
                       judges=[DeterministicJudge()])


# ---------------------------------------------------------- Arena match


def test_bounded_smoke_baseline_vs_socrates(runner):
    case = Case(
        case_id="p6_smoke_001",
        text=("Что делать когда автор говорит "
              "«ты ошибся, а вот источник»?"),
    )
    configs = [
        ParticipantConfiguration(
            participant_id="baseline_single",
            display_name="Baseline single agent",
            engine_kind="baseline_single_agent"),
        ParticipantConfiguration(
            participant_id="socrates_stock",
            display_name="Socrates / stock",
            engine_kind="socrates_pipeline",
            metadata={
                # Hints simulate what a live LLM executor will later parse
                # from router output. Deterministic mode still runs S0..S10
                # and reports the terminal it picked.
                "phase_hints": {
                    "S6": PhaseHint(ownership=Ownership(
                        owner=Authority.SYSTEM, human_resolved=True)),
                }},
        ),
    ]
    match = runner.run_match("p6_smoke", case, configs)
    assert match.status == "completed"
    turns = {t.participant_id: t for t in match.turns}
    assert set(turns) == {"baseline_single", "socrates_stock"}

    s = turns["socrates_stock"]
    assert not s.failed, s.error
    assert s.runtime_summary["engine"] == "socrates_pipeline"
    assert s.runtime_summary["terminal"]
    assert s.runtime_summary["mounted_phases"]
    # Every mounted phase carries CORE — mount determinism, from the trace
    # already, not from a re-read of the manifest.
    for p in s.runtime_summary["mounted_phases"]:
        assert "CORE" in p["bodies"]
    assert s.runtime_summary["semantic_pack_version"]
    # Neither participant is declared a winner by the runner.
    public = match.to_public()
    for banned in ("winner", "score", "ranking"):
        assert banned not in public


def test_socrates_participant_does_not_leak_into_arena_core():
    """Arena protocol/match/store/judges — no Socrates identifier at all."""
    from pathlib import Path
    src = Path(__file__).resolve().parents[2] / "src" / "tinkuy_arena"
    for name in ("protocol.py", "match.py", "store.py",
                 "judges/deterministic.py", "__init__.py"):
        text = (src / name).read_text(encoding="utf-8")
        # Import lines in __init__.py are allowed to name the adapter; the
        # rule is about the CORE not knowing.
        if name == "__init__.py":
            continue
        assert "SocratesParticipant" not in text, f"{name}: leaked"
        assert "socrates_runtime" not in text, f"{name}: leaked"


# ---------------------------------------------------------- HTTP endpoint


@pytest.fixture()
def api(tmp_path):
    srv.reset_service()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), srv.Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        srv.reset_service()


def _post(url, body, token=None):
    import urllib.error
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def test_socrates_run_endpoint_anonymous(api):
    status, out = _post(f"{api}/api/workbench/socrates/run",
                        {"input": "Что делать когда...?"})
    assert status == 200
    run = out["run"]
    assert run["terminal"]["terminal"] in {"ANSWER", "DWELL",
                                            "RETURN_OPERATION"}
    assert run["mounted_phases"]
    # trace was written to disk
    from pathlib import Path
    assert Path(run["trace_path"]).exists()


def test_socrates_run_records_identity_in_trace(api):
    _, out = _post(f"{api}/api/workbench/socrates/run",
                   {"input": "Проверка идентичности."})
    from pathlib import Path
    trace = json.loads(Path(out["run"]["trace_path"]).read_text(encoding="utf-8"))
    assert trace["identity"]["pack"]["source_bundle_sha256"].startswith("12b4e621")
    assert trace["configuration"]["semantic_pack_sha256"].startswith("12b4e621")


def test_socrates_run_with_pipeline_config_requires_auth(api):
    status, out = _post(f"{api}/api/workbench/socrates/run",
                        {"input": "test", "pipeline_config_id": "cfg_x"})
    assert status == 400
    assert "authenticated" in out["error"]

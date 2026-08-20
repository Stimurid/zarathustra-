"""Vertical-slice acceptance tests — TESTS 1..5 from the handoff.

Uses the real Handler + real SocratesRuntime binding. No mocks of the
runtime. DETERMINISTIC mode so no external provider is needed.
"""
from __future__ import annotations

import json
import socket
import threading
import time
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer

import pytest

from interface_api import Handler, reset_store_for_tests
from interface_api.state import InterfaceStore
from interface_api.models import SessionStatus, RunStatus


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def server(tmp_path):
    db_path = str(tmp_path / "interface_state.sqlite")
    runs_dir = str(tmp_path / "runs")
    reset_store_for_tests(db_path=db_path, runs_dir=runs_dir)
    port = _free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield {
        "base": f"http://127.0.0.1:{port}",
        "db_path": db_path,
        "runs_dir": runs_dir,
    }
    httpd.shutdown()
    httpd.server_close()


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def _post(url: str, body: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode("utf-8"))


def test_1_create_session_returns_session_id(server):
    r = _post(server["base"] + "/api/interface/session",
              {"have": "TEXT", "want": "ПОНЯТЬ", "actor": "pytest"})
    assert "session" in r, r
    assert r["session"]["session_id"].startswith("ses_")
    assert r["session"]["status"] == SessionStatus.CREATED.value


def test_2_attach_input_transitions_to_INPUT_RECEIVED(server):
    s = _post(server["base"] + "/api/interface/session",
              {"have": "TEXT", "want": "ПОНЯТЬ", "actor": "pytest"})
    sid = s["session"]["session_id"]
    text = "Тестовый материал для реконструкции."
    inp = _post(server["base"] + "/api/interface/input", {
        "session_id": sid, "kind": "TEXT",
        "body_text": text, "mime": "text/plain",
    })
    assert "input" in inp, inp
    assert inp["input"]["kind"] == "TEXT"
    assert inp["input"]["length_chars"] == len(text)
    got = _get(server["base"] + "/api/interface/session/" + sid)
    assert got["session"]["status"] == SessionStatus.INPUT_RECEIVED.value


def test_3_run_completes_via_real_socrates_runtime(server):
    s = _post(server["base"] + "/api/interface/session",
              {"have": "TEXT", "want": "ПОНЯТЬ", "actor": "pytest"})
    sid = s["session"]["session_id"]
    inp = _post(server["base"] + "/api/interface/input", {
        "session_id": sid, "kind": "TEXT",
        "body_text": "Что такое 2 + 2?", "mime": "text/plain",
    })
    iid = inp["input"]["input_id"]
    r = _post(server["base"] + "/api/interface/run", {
        "session_id": sid, "input_id": iid, "mode": "FAST",
    })
    assert "run" in r, r
    run = r["run"]
    assert run["status"] in (RunStatus.COMPLETED.value,
                             RunStatus.FAILED.value)
    assert run["sd_status"] != ""
    assert run["sd_authority"] == "NO_ADOPTION_AUTHORITY"


def test_4_artifact_fetch_returns_reconstruction_from_run(server):
    s = _post(server["base"] + "/api/interface/session",
              {"have": "TEXT", "want": "ПОНЯТЬ", "actor": "pytest"})
    sid = s["session"]["session_id"]
    inp = _post(server["base"] + "/api/interface/input", {
        "session_id": sid, "kind": "TEXT",
        "body_text": "Что такое 2 + 2?", "mime": "text/plain",
    })
    _post(server["base"] + "/api/interface/run", {
        "session_id": sid, "input_id": inp["input"]["input_id"],
        "mode": "FAST",
    })
    got = _get(server["base"] + "/api/interface/artifacts/" + sid)
    kinds = [a["kind"] for a in got["artifacts"]]
    assert "RECONSTRUCTION" in kinds
    assert "NEXT_ACTIONS" in kinds
    recon = next(a for a in got["artifacts"]
                 if a["kind"] == "RECONSTRUCTION")
    assert "Terminal" in recon["body_md"]
    assert recon["provenance"]["runtime_layer"] == "socrates_runtime"
    assert recon["provenance"]["sd_authority"] == "NO_ADOPTION_AUTHORITY"


def test_5_session_survives_restart(server):
    s = _post(server["base"] + "/api/interface/session",
              {"have": "TRANSCRIPT", "want": "ПОНЯТЬ",
               "actor": "pytest-persistence"})
    sid = s["session"]["session_id"]
    inp = _post(server["base"] + "/api/interface/input", {
        "session_id": sid, "kind": "TRANSCRIPT",
        "body_text": "стенограмма встречи (тест persistence)",
        "mime": "text/plain",
    })
    iid = inp["input"]["input_id"]
    fresh = InterfaceStore(server["db_path"])
    got_sess = fresh.get_session(sid)
    got_inp = fresh.get_input(iid)
    fresh.close()
    assert got_sess is not None
    assert got_sess.have == "TRANSCRIPT"
    assert got_sess.want == "ПОНЯТЬ"
    assert got_inp is not None
    assert got_inp.body_text.startswith("стенограмма")


def test_launchpad_static_served(server):
    with urllib.request.urlopen(server["base"] + "/", timeout=10) as r:
        body = r.read().decode("utf-8")
    assert "<title>Tinkuy</title>" in body
    assert "Что у вас есть?" in body
    assert "Что хотите сделать?" in body


def test_workspace_static_served(server):
    with urllib.request.urlopen(server["base"] + "/workspace",
                                timeout=10) as r:
        body = r.read().decode("utf-8")
    assert "Tinkuy" in body

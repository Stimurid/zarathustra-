"""6.3 async_jobs — job register + finalize + get_status/get_result."""
from __future__ import annotations

import time

from californian_id import async_jobs
from californian_id.workspaces import RunStore


def test_register_pending_creates_running_record(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    async_jobs.register_pending("alpha", "r1", "hi", "raw", "fast")
    store = RunStore.for_workspace("alpha")
    try:
        m = store.get("r1")
    finally:
        store.close()
    assert m is not None
    assert m.status == "RUNNING"
    assert m.input_summary == "hi"


def test_submit_runs_worker_and_writes_result(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)

    def job() -> dict:
        return {"status": "COMPLETED", "mode": "fast",
                "completion": {"form": "aporia"}, "turn_count": 3,
                "voices_used": ["A", "B"], "stopping_reason": "converged",
                "errors": []}
    async_jobs.submit("beta", "r2", job, input_summary="x", input_mode="raw", mode="fast")
    # wait up to 5 s
    for _ in range(50):
        st = async_jobs.get_status("beta", "r2")
        if st and st["status"] != "RUNNING":
            break
        time.sleep(0.1)
    st = async_jobs.get_status("beta", "r2")
    assert st is not None
    assert st["status"] == "COMPLETED"
    assert st["completion_form"] == "aporia"
    assert st["turn_count"] == 3
    assert st["voices_used"] == ["A", "B"]
    res = async_jobs.get_result("beta", "r2")
    assert res is not None
    assert res["completion"]["form"] == "aporia"


def test_submit_captures_error(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)

    def job() -> dict:
        raise ValueError("boom")
    async_jobs.submit("gamma", "r3", job, input_summary="x", input_mode="raw", mode="fast")
    for _ in range(50):
        st = async_jobs.get_status("gamma", "r3")
        if st and st["status"] != "RUNNING":
            break
        time.sleep(0.1)
    st = async_jobs.get_status("gamma", "r3")
    assert st is not None
    assert st["status"] == "ERROR"
    assert "boom" in st["error"]
    res = async_jobs.get_result("gamma", "r3")
    assert res is not None
    assert "boom" in res["error"]


def test_get_result_returns_none_for_unknown():
    assert async_jobs.get_result("gamma", "nonexistent") is None


def test_get_status_returns_none_for_unknown(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    assert async_jobs.get_status("empty-ws", "nope") is None


def test_runs_dir_fallback_when_env_writable(tmp_path, monkeypatch):
    """Config._resolve_runs_dir prefers env var when writable."""
    monkeypatch.setenv("CALIFORNIAN_ID_RUNS_DIR", str(tmp_path / "custom-runs"))
    import importlib
    from californian_id import config
    importlib.reload(config)
    assert config.RUNS_DIR == (tmp_path / "custom-runs").resolve()
    assert config.RUNS_DIR.exists()

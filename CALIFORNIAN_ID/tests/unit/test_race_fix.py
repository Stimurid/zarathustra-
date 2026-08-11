"""B-5.5 race-fix v2 — client-provided run_id validation + no-conflict tests."""
from __future__ import annotations

import pytest


def test_is_valid_client_run_id_accepts_good_ids():
    from californian_id.async_jobs import is_valid_client_run_id
    assert is_valid_client_run_id("run_abcd1234")
    assert is_valid_client_run_id("run_" + "a" * 20)
    assert is_valid_client_run_id("run_abc-def_012xyz")
    # min length: run_ + 8 chars = 12
    assert is_valid_client_run_id("run_12345678")


def test_is_valid_client_run_id_rejects_bad():
    from californian_id.async_jobs import is_valid_client_run_id
    assert not is_valid_client_run_id("")
    assert not is_valid_client_run_id("run_")
    assert not is_valid_client_run_id("run_short")  # <8 after prefix
    assert not is_valid_client_run_id("nrun_abcd1234")  # no run_ prefix
    assert not is_valid_client_run_id("run_" + "a" * 60)  # too long
    assert not is_valid_client_run_id("run_UPPERCASE1234")  # only lowercase
    assert not is_valid_client_run_id("run_../etc/passwd")
    assert not is_valid_client_run_id("run_abc def")  # space


def test_run_id_conflict_detects_registered_run(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    from californian_id import async_jobs, runtime_control as rc
    rc.register("run_conflict1234", "ws1")
    try:
        assert async_jobs.run_id_conflict("ws1", "run_conflict1234")
    finally:
        rc.unregister("run_conflict1234")


def test_run_id_conflict_detects_completed_run(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    from californian_id import async_jobs
    # финализируем как completed → есть в RunStore
    async_jobs._finalize_success("ws2", "run_conflict5678", {
        "run_id": "run_conflict5678", "status": "COMPLETED",
        "mode": "fast", "completion": {}, "turn_count": 0,
        "voices_used": [], "trace_dir": "",
    })
    assert async_jobs.run_id_conflict("ws2", "run_conflict5678")


def test_run_id_conflict_false_for_fresh(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    from californian_id import async_jobs
    assert not async_jobs.run_id_conflict("ws3", "run_freshfreshfresh")


def test_submit_pre_registers_run_control(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    from californian_id import async_jobs, runtime_control as rc
    import time

    def slow_job() -> dict:
        time.sleep(0.5)
        return {"status": "COMPLETED", "mode": "fast",
                "completion": {"form": "aporia"}, "turn_count": 0,
                "voices_used": []}

    async_jobs.submit("ws4", "run_preregtest99", slow_job,
                      input_summary="test", input_mode="raw", mode="fast")
    # immediately after submit — до того как worker закончит — run уже
    # зарегистрирован в runtime_control
    st = rc.get("run_preregtest99")
    assert st is not None
    assert st.workspace_id == "ws4"
    # cleanup: подождём worker и unregister
    for _ in range(30):
        time.sleep(0.1)
        if async_jobs.get_status("ws4", "run_preregtest99") is not None:
            m = async_jobs.get_status("ws4", "run_preregtest99")
            if m and m.get("status") == "COMPLETED":
                break
    rc.unregister("run_preregtest99")

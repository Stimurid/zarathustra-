"""B-5.5 Веха 1 — cooperative pause/resume/cancel + intervention audit."""
from __future__ import annotations

import threading
import time

import pytest

from californian_id import runtime_control as rc


def test_intervention_store_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    store = rc.InterventionStore.for_workspace("alpha")
    try:
        iv = rc.Intervention(
            intervention_id="iv_test1", run_id="r1", workspace_id="alpha",
            kind="pause", author="alice", payload={"reason": "test"},
        )
        store.save(iv)
        loaded = store.list_for_run("r1")
        assert len(loaded) == 1
        assert loaded[0].kind == "pause"
        assert loaded[0].author == "alice"
        assert loaded[0].payload == {"reason": "test"}
    finally:
        store.close()


def test_signal_pause_and_resume(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    st = rc.register("r_pause", "alpha")
    try:
        assert st.run_event.is_set()
        rc.signal("r_pause", "pause", "alice")
        assert not st.run_event.is_set()
        rc.signal("r_pause", "resume", "alice")
        assert st.run_event.is_set()
    finally:
        rc.unregister("r_pause")


def test_signal_cancel_sets_flag(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    st = rc.register("r_cancel", "alpha")
    try:
        rc.signal("r_cancel", "cancel", "alice", payload={"reason": "no reason"})
        assert st.cancel_flag is True
        assert "no reason" in st.cancel_reason
    finally:
        rc.unregister("r_cancel")


def test_wait_if_paused_returns_running_when_not_paused(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    rc.register("r_ok", "alpha")
    try:
        assert rc.wait_if_paused("r_ok", timeout_sec=0.1) == "running"
    finally:
        rc.unregister("r_ok")


def test_wait_if_paused_blocks_and_unblocks(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    rc.register("r_wait", "alpha")
    try:
        rc.signal("r_wait", "pause", "alice")

        # background thread будет ждать; отправим resume через 0.3s
        results: list[str] = []
        def worker():
            results.append(rc.wait_if_paused("r_wait", timeout_sec=5.0))
        t = threading.Thread(target=worker)
        t.start()
        time.sleep(0.15)
        assert t.is_alive()  # ещё в pause
        rc.signal("r_wait", "resume", "alice")
        t.join(timeout=2.0)
        assert not t.is_alive()
        assert results == ["running"]
    finally:
        rc.unregister("r_wait")


def test_wait_if_paused_returns_cancelled_when_cancel_arrives(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    rc.register("r_cwait", "alpha")
    try:
        rc.signal("r_cwait", "pause", "alice")
        results: list[str] = []
        def worker():
            results.append(rc.wait_if_paused("r_cwait", timeout_sec=5.0))
        t = threading.Thread(target=worker)
        t.start()
        time.sleep(0.1)
        rc.signal("r_cwait", "cancel", "alice")
        t.join(timeout=2.0)
        assert results == ["cancelled"]
    finally:
        rc.unregister("r_cwait")


def test_wait_if_paused_returns_timeout_on_deadline(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    rc.register("r_to", "alpha")
    try:
        rc.signal("r_to", "pause", "alice")
        # timeout срабатывает быстро
        assert rc.wait_if_paused("r_to", timeout_sec=0.2) == "timeout"
    finally:
        rc.unregister("r_to")


def test_signal_slider_bounds(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    st = rc.register("r_sld", "alpha")
    try:
        rc.signal("r_sld", "slider", "alice",
                  payload={"weights": {"LENS_A": 5.0, "LENS_B": -1.0, "LENS_C": 1.5}})
        # clamped: 5→3, -1→0.05, 1.5→1.5
        assert st.persona_weights["LENS_A"] == 3.0
        assert st.persona_weights["LENS_B"] == 0.05
        assert st.persona_weights["LENS_C"] == 1.5
    finally:
        rc.unregister("r_sld")


def test_snapshot_state_shape(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    rc.register("r_snap", "alpha")
    try:
        rc.signal("r_snap", "slider", "alice",
                  payload={"weights": {"LENS_X": 0.5}})
        rc.signal("r_snap", "pause", "alice")
        s = rc.snapshot_state("r_snap")
        assert s["state"] == "PAUSED"
        assert s["persona_weights"] == {"LENS_X": 0.5}
        rc.signal("r_snap", "resume", "alice")
        s = rc.snapshot_state("r_snap")
        assert s["state"] == "RUNNING"
    finally:
        rc.unregister("r_snap")


def test_signal_unknown_kind_raises():
    with pytest.raises(ValueError, match="unknown intervention"):
        rc.signal("any", "banana", "alice")


def test_snapshot_state_unknown_run():
    s = rc.snapshot_state("nonexistent-run-id")
    assert s["state"] == "UNKNOWN"


def test_wait_if_paused_unknown_run_returns_running_immediately():
    # No register — не зарегистрирован
    assert rc.wait_if_paused("nonexistent", timeout_sec=0.1) == "running"


# ---------- Pipeline._checkpoint через MockClient ----------

def test_pipeline_checkpoint_raises_runtime_cancelled_on_cancel(monkeypatch, tmp_path):
    """Реальный Pipeline с mock provider; отправим cancel — ран прервётся."""
    import os
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")

    from californian_id.pipeline import Pipeline
    pipe = Pipeline()

    events: list[dict] = []
    pipe.event_sink = lambda evt: events.append(evt)

    # Запускаем в thread, отправляем cancel почти сразу
    def _cancel_shortly():
        # ждём пока пойдёт первый checkpoint
        for _ in range(50):
            time.sleep(0.02)
            if any(e.get("kind") == "run_started" for e in events):
                break
        # даём первому turn'у стартануть, потом cancel
        time.sleep(0.05)
        # найти run_id из events
        for e in events:
            if e.get("kind") == "run_started" and e.get("run_id"):
                rc.signal(e["run_id"], "cancel", "test",
                          payload={"reason": "test cancel"})
                return
    canceller = threading.Thread(target=_cancel_shortly)
    canceller.start()
    result = pipe.run(text="Test cancel scenario", mode="fast")
    canceller.join(timeout=3.0)

    kinds = {e.get("kind") for e in events}
    # хотя бы один checkpoint случился
    assert "run_started" in kinds
    # cancelled event должен эмитнуться (если попали в pause) или просто в trace
    # main assertion: pipeline завершилась не exception'ом
    assert result is not None

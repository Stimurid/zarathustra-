"""Пик 8 — exporters / cross_run / auth."""
from __future__ import annotations

import io
import json
import tarfile
import time

import pytest

from californian_id import auth, cross_run, exporters
from californian_id.async_jobs import result_path
from californian_id.workspaces import RunMetadata, RunStore


# ---------- 8.1 exporters ----------
def _seed_result(monkeypatch, tmp_path, workspace: str, run_id: str) -> None:
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    monkeypatch.setattr("californian_id.async_jobs.workspace_dir",
                        lambda ws, root=None: tmp_path / "workspaces" / ws)
    p = result_path(workspace, run_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "run_id": run_id, "workspace_id": workspace, "mode": "fast",
        "status": "COMPLETED", "stopping_reason": "converged",
        "completion": {"form": "aporia", "rationale": "test",
                       "closing_speech": "final words",
                       "conflict_map": [{"tension":"t","side_a":"A","side_b":"B","status":"open"}],
                       "minority_positions": [{"persona_id":"X","text":"tail"}],
                       "unresolved_questions": ["q1","q2"]},
        "turns": [{"turn_index":0,"persona_id":"X","operation":"initial_position",
                   "utterance":"hello"}],
        "turn_count": 1, "voices_used": ["X"],
        "input_mode": "raw", "trace_dir": str(tmp_path / "nonexistent"),
    }, ensure_ascii=False), encoding="utf-8")


def test_export_json_round_trips(monkeypatch, tmp_path):
    _seed_result(monkeypatch, tmp_path, "alpha", "r1")
    raw = exporters.export_json("alpha", "r1")
    assert raw is not None
    data = json.loads(raw.decode("utf-8"))
    assert data["run_id"] == "r1"


def test_export_markdown_contains_key_sections(monkeypatch, tmp_path):
    _seed_result(monkeypatch, tmp_path, "alpha", "r1")
    md = exporters.export_markdown("alpha", "r1")
    assert md is not None
    text = md.decode("utf-8")
    assert "# Run `r1`" in text
    assert "Форма завершения" in text
    assert "aporia" in text
    assert "Заключительная речь Заратустры" in text
    assert "final words" in text
    assert "Ходы совета" in text
    assert "Карта конфликтов" in text


def test_export_bundle_is_tarball(monkeypatch, tmp_path):
    _seed_result(monkeypatch, tmp_path, "alpha", "r1")
    b = exporters.export_bundle("alpha", "r1")
    assert b is not None
    assert b[:2] == b"\x1f\x8b"  # gzip magic
    with tarfile.open(fileobj=io.BytesIO(b), mode="r:gz") as tar:
        names = tar.getnames()
    assert any(n.endswith("/result.json") for n in names)
    assert any(n.endswith("/closing.md") for n in names)


def test_export_returns_none_for_unknown(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    monkeypatch.setattr("californian_id.async_jobs.workspace_dir",
                        lambda ws, root=None: tmp_path / "workspaces" / ws)
    assert exporters.export_json("alpha", "nope") is None
    assert exporters.export_markdown("alpha", "nope") is None
    assert exporters.export_bundle("alpha", "nope") is None


# ---------- 8.2 cross_run.search ----------
def test_search_runs_by_token_overlap(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    store = RunStore.for_workspace("beta")
    try:
        store.save(RunMetadata(run_id="r1", workspace_id="beta", mode="fast",
                               status="COMPLETED", completion_form="synthesis",
                               input_summary="что такое свобода воли",
                               voices_used=["A"]))
        store.save(RunMetadata(run_id="r2", workspace_id="beta", mode="deep",
                               status="COMPLETED", completion_form="aporia",
                               input_summary="природа сознания и квалиа",
                               voices_used=["B"]))
    finally:
        store.close()
    results = cross_run.search_runs("beta", "свобода", limit=10)
    assert len(results) == 1
    assert results[0]["run_id"] == "r1"
    assert results[0]["score"] > 0
    empty = cross_run.search_runs("beta", "квантовая гравитация")
    assert empty == []


def test_search_empty_query_returns_nothing():
    assert cross_run.search_runs("nonexistent-ws", "") == []


# ---------- 8.3 auth ----------
def test_rate_limit_allows_up_to_threshold(monkeypatch):
    # тестируем на локальной метке
    label = f"test-{time.monotonic_ns()}"
    for i in range(5):
        allowed, remaining, limit = auth.check_rate_limit(label, limit_per_min=5)
        assert allowed, f"iteration {i} denied"
    allowed, _remaining, _limit = auth.check_rate_limit(label, limit_per_min=5)
    assert not allowed
    # проверка bucket_snapshot
    snap = auth.bucket_snapshot()
    assert label in snap
    assert snap[label]["requests_last_60s"] == 5


def test_label_for_bearer_reads_multi_env(monkeypatch):
    monkeypatch.setenv("CALIFORNIAN_ID_API_KEYS", "abc123:alice,def456:bob")
    # need to reload module to re-parse env
    import importlib
    from californian_id import auth as auth_mod
    importlib.reload(auth_mod)
    try:
        assert auth_mod.label_for_bearer("abc123") == "alice"
        assert auth_mod.label_for_bearer("def456") == "bob"
        assert auth_mod.label_for_bearer("wrong") is None
        assert auth_mod.any_keys_configured()
    finally:
        monkeypatch.delenv("CALIFORNIAN_ID_API_KEYS", raising=False)
        importlib.reload(auth_mod)


def test_disabled_via_env(monkeypatch):
    monkeypatch.setenv("CALIFORNIAN_ID_AUTH_DISABLED", "1")
    import importlib
    from californian_id import auth as auth_mod
    importlib.reload(auth_mod)
    try:
        assert auth_mod.is_disabled()
    finally:
        monkeypatch.delenv("CALIFORNIAN_ID_AUTH_DISABLED", raising=False)
        importlib.reload(auth_mod)


def test_billing_summary_reports_zero_when_empty(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    s = auth.billing_summary()
    assert "rate_limit" in s
    assert "runs_by_workspace" in s

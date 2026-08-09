"""Пик 6.A — workspace isolation + validation."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from californian_id.workspaces import (
    DEFAULT_WORKSPACE_ID,
    RunMetadata,
    RunStore,
    fabric_store_path,
    list_workspaces,
    run_trace_dir,
    validate_workspace_id,
    workspace_dir,
)


def test_validate_workspace_id_accepts_slug():
    assert validate_workspace_id("alice") == "alice"
    assert validate_workspace_id("team_42-x") == "team_42-x"
    # normalises case
    assert validate_workspace_id("Alice") == "alice"
    # empty → default
    assert validate_workspace_id("") == DEFAULT_WORKSPACE_ID


def test_validate_workspace_id_rejects_traversal():
    for bad in ["../etc", "team/x", ".", "..", "with space",
                "-leading-dash", "толькокириллица"]:
        with pytest.raises(ValueError):
            validate_workspace_id(bad)


def test_workspace_dir_is_isolated(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    a = workspace_dir("alpha")
    b = workspace_dir("beta")
    assert a != b
    assert a.exists() and b.exists()
    assert fabric_store_path("alpha").parent == a
    trace = run_trace_dir("alpha", "run-1")
    assert trace.exists()
    assert trace.parent.parent == a


def test_run_store_save_get_list(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    store = RunStore.for_workspace("alpha")
    try:
        m1 = RunMetadata(
            run_id="r1", workspace_id="alpha", mode="fast", status="COMPLETED",
            completion_form="synthesis", input_mode="raw+fabric",
            input_summary="hello world", snapshot_id="snap-abc",
            trace_dir="/tmp/x", turn_count=3, voices_used=["R", "S"],
            created_at="2026-01-01T00:00:00Z",
        )
        m2 = RunMetadata(
            run_id="r2", workspace_id="alpha", mode="deep", status="ERROR",
            input_mode="raw", input_summary="oops", error="boom",
            created_at="2026-01-02T00:00:00Z",
        )
        store.save(m1)
        store.save(m2)
        got = store.get("r1")
        assert got is not None
        assert got.completion_form == "synthesis"
        assert got.voices_used == ["R", "S"]
        items = store.list(limit=10)
        assert {i.run_id for i in items} == {"r1", "r2"}
    finally:
        store.close()

    # Second workspace does NOT see alpha's runs.
    store_b = RunStore.for_workspace("beta")
    try:
        assert store_b.list() == []
        assert store_b.get("r1") is None
    finally:
        store_b.close()


def test_list_workspaces_reports_both(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    store_a = RunStore.for_workspace("alpha")
    store_a.save(RunMetadata(run_id="x", workspace_id="alpha",
                             mode="fast", status="COMPLETED"))
    store_a.close()
    workspace_dir("beta")  # create empty
    listed = {w["workspace_id"]: w for w in list_workspaces()}
    assert "alpha" in listed
    assert "beta" in listed
    assert listed["alpha"]["n_runs"] == 1
    assert listed["beta"]["n_runs"] == 0

"""Пик 9 — narrative_memory + budgets."""
from __future__ import annotations

import pytest

from californian_id import budgets, narrative_memory
from californian_id.narrative_memory import NarrativeNote, NarrativeStore


# ---------- 9.1 narrative_memory ----------
def test_narrative_store_add_and_get(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    store = NarrativeStore.for_workspace("alpha")
    try:
        note = NarrativeNote(
            note_id="n1", workspace_id="alpha", kind="observation",
            text="test", related_run_ids=["r1", "r2"],
        )
        store.add(note)
        got = store.get("n1")
        assert got is not None
        assert got.text == "test"
        assert got.related_run_ids == ["r1", "r2"]
    finally:
        store.close()


def test_narrative_store_rejects_bad_kind(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    store = NarrativeStore.for_workspace("alpha")
    try:
        with pytest.raises(ValueError):
            store.add(NarrativeNote(note_id="n1", workspace_id="alpha",
                                     kind="unknown", text="x"))
    finally:
        store.close()


def test_narrative_store_rejects_empty_text(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    store = NarrativeStore.for_workspace("alpha")
    try:
        with pytest.raises(ValueError):
            store.add(NarrativeNote(note_id="n1", workspace_id="alpha",
                                     kind="observation", text=""))
    finally:
        store.close()


def test_narrative_store_list_filter_by_kind(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    store = NarrativeStore.for_workspace("alpha")
    try:
        store.add(NarrativeNote(note_id="n1", workspace_id="alpha",
                                 kind="observation", text="o1"))
        store.add(NarrativeNote(note_id="n2", workspace_id="alpha",
                                 kind="contradiction", text="c1"))
        assert len(store.list(kind="observation")) == 1
        assert len(store.list(kind="contradiction")) == 1
        assert len(store.list()) == 2
    finally:
        store.close()


def test_narrative_by_related_run(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    store = NarrativeStore.for_workspace("alpha")
    try:
        store.add(NarrativeNote(note_id="n1", workspace_id="alpha",
                                 kind="observation", text="x",
                                 related_run_ids=["r1", "r2"]))
        store.add(NarrativeNote(note_id="n2", workspace_id="alpha",
                                 kind="observation", text="y",
                                 related_run_ids=["r3"]))
        assert len(store.by_related_run("r2")) == 1
        assert len(store.by_related_run("r99")) == 0
    finally:
        store.close()


def test_auto_record_observation_returns_note(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    note = narrative_memory.auto_record_observation(
        workspace_id="alpha", run_id="rX",
        completion_form="aporia", stopping_reason="max_turns",
        voices_used=["A", "B"],
    )
    assert note is not None
    assert note.kind == "observation"
    assert "rX" in note.related_run_ids


# ---------- 9.2 budgets ----------
def test_budgets_disabled_when_env_not_set(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    monkeypatch.delenv("CALIFORNIAN_ID_BUDGETS_YAML", raising=False)
    budgets._load_budgets.cache_clear()
    status = budgets.check("alpha")
    assert status.hard_limit is None
    assert status.hard_exceeded is False


def test_budgets_hard_deny_when_exceeded(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    # напишем budgets.yaml с очень маленьким hard-лимитом
    yaml_path = tmp_path / "budgets.yaml"
    yaml_path.write_text("alpha:\n  soft: 1\n  hard: 2\n", encoding="utf-8")
    monkeypatch.setenv("CALIFORNIAN_ID_BUDGETS_YAML", str(yaml_path))
    budgets._load_budgets.cache_clear()
    # 3 рана в workspace alpha → over hard
    from californian_id.workspaces import RunMetadata, RunStore
    store = RunStore.for_workspace("alpha")
    for i in range(3):
        store.save(RunMetadata(run_id=f"r{i}", workspace_id="alpha",
                               mode="fast", status="COMPLETED"))
    store.close()
    deny, info = budgets.should_deny("alpha")
    assert deny
    assert info["hard_limit"] == 2
    assert info["runs_count"] == 3


def test_budgets_default_workspace_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    yaml_path = tmp_path / "budgets.yaml"
    yaml_path.write_text("default:\n  hard: 100\n", encoding="utf-8")
    monkeypatch.setenv("CALIFORNIAN_ID_BUDGETS_YAML", str(yaml_path))
    budgets._load_budgets.cache_clear()
    status = budgets.check("some-new-ws")
    assert status.hard_limit == 100


def test_budgets_summary_includes_all_workspaces(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    monkeypatch.delenv("CALIFORNIAN_ID_BUDGETS_YAML", raising=False)
    budgets._load_budgets.cache_clear()
    from californian_id.workspaces import RunMetadata, RunStore
    for ws in ["a", "b"]:
        s = RunStore.for_workspace(ws)
        s.save(RunMetadata(run_id=f"r-{ws}", workspace_id=ws, mode="fast",
                           status="COMPLETED"))
        s.close()
    summary = budgets.summary()
    ws_ids = {w["workspace_id"] for w in summary["per_workspace"]}
    assert {"a", "b"}.issubset(ws_ids)

"""Dialogue log appender — sanity + safety."""
from __future__ import annotations

import json
import os

import pytest

from californian_id import dialogue_log


def test_noop_when_env_var_unset(tmp_path, monkeypatch):
    monkeypatch.delenv("TINKUY_DIALOGUE_LOG", raising=False)
    # No path -> no file created, no exception
    dialogue_log.log_dialogue(source="test", input_text="hello",
                               response={"terminal": {"terminal": "ANSWER"}})
    # nothing was written anywhere we own
    assert not any(p.name.endswith(".jsonl") for p in tmp_path.iterdir())


def test_writes_one_json_line(tmp_path, monkeypatch):
    log = tmp_path / "dialogues.jsonl"
    monkeypatch.setenv("TINKUY_DIALOGUE_LOG", str(log))
    dialogue_log.log_dialogue(
        source="socrates", input_text="hello world",
        response={"runtime_layer": "socrates_runtime",
                  "run_id": "srun_abc",
                  "trace_id": "strc_xyz",
                  "provider_id": "fallback", "model_id": "chain",
                  "execution_mode": "LIVE",
                  "intervention_profile": "bald_ape",
                  "duration_ms": 1234,
                  "terminal": {"terminal": "ANSWER"},
                  "rendering": {"text": "тестовый ответ"}})
    assert log.exists()
    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["source"] == "socrates"
    assert rec["runtime_layer"] == "socrates_runtime"
    assert rec["run_id"] == "srun_abc"
    assert rec["terminal"] == "ANSWER"
    assert rec["intervention_profile"] == "bald_ape"
    assert rec["input_text"] == "hello world"
    assert rec["rendering_text"] == "тестовый ответ"
    assert rec["ts"].endswith("Z")


def test_appends_second_call(tmp_path, monkeypatch):
    log = tmp_path / "dialogues.jsonl"
    monkeypatch.setenv("TINKUY_DIALOGUE_LOG", str(log))
    dialogue_log.log_dialogue(source="run", input_text="one", response={})
    dialogue_log.log_dialogue(source="run", input_text="two", response={})
    assert len(log.read_text(encoding="utf-8").splitlines()) == 2


def test_logging_never_raises(tmp_path, monkeypatch):
    # Point to a path that cannot possibly succeed — the call still
    # returns None without raising.
    bad = tmp_path / "no" / "such" / "dir" / "log.jsonl"
    monkeypatch.setenv("TINKUY_DIALOGUE_LOG", str(bad))
    # makedirs will try to create the parents — that actually succeeds
    # on tmp_path, so also test with a truly bad path (a file used
    # as directory).
    file_used_as_dir = tmp_path / "wall"
    file_used_as_dir.write_text("x")
    monkeypatch.setenv("TINKUY_DIALOGUE_LOG",
                        str(file_used_as_dir / "sub" / "log.jsonl"))
    dialogue_log.log_dialogue(source="run", input_text="x", response={})
    # No exception -> pass.


def test_error_field_captured(tmp_path, monkeypatch):
    log = tmp_path / "dialogues.jsonl"
    monkeypatch.setenv("TINKUY_DIALOGUE_LOG", str(log))
    dialogue_log.log_dialogue(source="run", input_text="oops",
                               error="RuntimeError: boom")
    rec = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    assert rec["error"] == "RuntimeError: boom"


def test_truncates_very_long_input(tmp_path, monkeypatch):
    log = tmp_path / "dialogues.jsonl"
    monkeypatch.setenv("TINKUY_DIALOGUE_LOG", str(log))
    big = "x" * 20000
    dialogue_log.log_dialogue(source="run", input_text=big, response={})
    rec = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    assert len(rec["input_text"]) == 8192

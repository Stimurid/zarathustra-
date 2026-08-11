"""B-5.5 Веха 5 — file attach normalize + intervention audit в bundle export."""
from __future__ import annotations

import io
import json
import tarfile

import pytest

from californian_id import attachments, runtime_control as rc


# ---------- 5b: attach normalize ----------

def test_normalize_txt_basic():
    n = attachments.normalize({"filename": "note.txt", "content": "hello world"})
    assert n is not None
    assert n.filename == "note.txt"
    assert n.text == "hello world"
    assert not n.was_truncated


def test_normalize_md_keeps_content():
    body = "# Заголовок\n\nАбзац."
    n = attachments.normalize({"filename": "readme.md", "content": body})
    assert n is not None
    assert n.text == body


def test_normalize_json_pretty_prints():
    n = attachments.normalize({
        "filename": "data.json",
        "content": '{"a":1,"b":[2,3]}',
    })
    assert n is not None
    assert "  " in n.text  # pretty-printed with indent


def test_normalize_json_invalid_falls_back_to_raw():
    n = attachments.normalize({"filename": "x.json", "content": "not json {"})
    assert n is not None
    assert n.text == "not json {"


def test_normalize_dict_content_becomes_json():
    n = attachments.normalize({"filename": "x", "content": {"a": 1}})
    assert n is not None
    assert '"a"' in n.text


def test_normalize_bytes_content_decodes_utf8():
    n = attachments.normalize({
        "filename": "u.txt",
        "content": "привет".encode("utf-8"),
    })
    assert n is not None
    assert n.text == "привет"


def test_normalize_rejects_unsupported_ext():
    n = attachments.normalize({"filename": "x.pdf", "content": "..."})
    assert n is not None
    assert n.text == ""  # unsupported → empty text, note filled
    assert "unsupported" in n.note


def test_normalize_truncates_over_max():
    big = "x" * (attachments.ATTACH_MAX_CHARS + 500)
    n = attachments.normalize({"filename": "big.txt", "content": big})
    assert n is not None
    assert n.was_truncated
    assert "[truncated]" in n.full_text
    assert len(n.text) <= attachments.INJECT_MAX_CHARS + 40


def test_normalize_no_filename_ok():
    n = attachments.normalize({"content": "just text"})
    assert n is not None
    assert n.filename == "unnamed"
    assert n.text == "just text"


def test_normalize_none_content_returns_none():
    assert attachments.normalize({"filename": "x.txt"}) is None
    assert attachments.normalize("not a dict") is None


def test_format_attach_block_contains_persona_marker():
    n = attachments.normalize({
        "filename": "boost.txt", "content": "аргумент",
        "attach_to_persona": "LENS_A"})
    block = attachments.format_attach_block(n)
    assert "LENS_A" in block
    assert "boost.txt" in block
    assert "аргумент" in block


# ---------- 5b integration: Pipeline consume_pending normalizes ----------

def test_pipeline_consume_pending_normalizes_and_stashes(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    from californian_id.pipeline import Pipeline
    p = Pipeline()
    rc.register("r_atx", "default")
    try:
        events: list[dict] = []
        p.event_sink = lambda evt: events.append(evt)
        rc.signal("r_atx", "attach_file", "alice", payload={
            "filename": "n.md", "content": "# hi", "attach_to_persona": "LENS_A"
        })
        p._consume_pending("r_atx")
        acc = p._attach_pending.get("r_atx")
        assert acc is not None
        assert "LENS_A" in acc["per_persona"]
        assert acc["general"] == []
        kinds = [e.get("kind") for e in events]
        assert "attachment_accepted" in kinds
    finally:
        rc.unregister("r_atx")
        p._attach_pending.pop("r_atx", None)


def test_pipeline_pop_attachments_removes_persona_and_general(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    from californian_id.pipeline import Pipeline
    p = Pipeline()
    rc.register("r_pop", "default")
    try:
        rc.signal("r_pop", "attach_file", "a",
                  payload={"filename": "1.txt", "content": "AAA",
                           "attach_to_persona": "LENS_A"})
        rc.signal("r_pop", "attach_file", "a",
                  payload={"filename": "2.txt", "content": "BBB"})  # general
        p._consume_pending("r_pop")
        blocks_a = p._pop_persona_attachments("r_pop", "LENS_A")
        assert len(blocks_a) == 2  # persona block + general block
        assert "AAA" in blocks_a[0]
        assert "BBB" in blocks_a[1]
        # general уже забран
        blocks_b = p._pop_persona_attachments("r_pop", "LENS_B")
        assert blocks_b == []
    finally:
        rc.unregister("r_pop")
        p._attach_pending.pop("r_pop", None)


# ---------- 5c: interventions в bundle export ----------

def test_bundle_export_includes_interventions(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    from californian_id import async_jobs, exporters
    # Создаём фейковый result
    async_jobs._finalize_success("alpha", "r_bundle", {
        "run_id": "r_bundle", "status": "COMPLETED", "mode": "fast",
        "completion": {"form": "aporia"}, "turn_count": 2,
        "voices_used": ["A"], "trace_dir": "",
    })
    # Register run under 'alpha' workspace, чтобы signal писал туда же
    rc.register("r_bundle", "alpha")
    rc.signal("r_bundle", "pause", "alice", payload={"reason": "manual"})
    rc.signal("r_bundle", "resume", "alice")
    rc.signal("r_bundle", "slider", "alice",
              payload={"weights": {"LENS_A": 0.5}})

    body = exporters.export_bundle("alpha", "r_bundle")
    assert body is not None
    buf = io.BytesIO(body)
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        names = tar.getnames()
        assert "r_bundle/result.json" in names
        assert "r_bundle/interventions.jsonl" in names
        member = tar.extractfile("r_bundle/interventions.jsonl")
        assert member is not None
        lines = member.read().decode("utf-8").strip().split("\n")
        kinds = [json.loads(l)["kind"] for l in lines]
        assert set(kinds) == {"pause", "resume", "slider"}
    rc.unregister("r_bundle")


def test_bundle_export_no_interventions_still_works(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    from californian_id import async_jobs, exporters
    async_jobs._finalize_success("beta", "r_clean", {
        "run_id": "r_clean", "status": "COMPLETED", "mode": "fast",
        "completion": {"form": "synthesis"}, "turn_count": 1,
        "voices_used": [], "trace_dir": "",
    })
    body = exporters.export_bundle("beta", "r_clean")
    assert body is not None
    buf = io.BytesIO(body)
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        names = tar.getnames()
        assert "r_clean/result.json" in names
        assert "r_clean/interventions.jsonl" not in names

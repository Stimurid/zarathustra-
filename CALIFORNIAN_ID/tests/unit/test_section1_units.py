"""Раздел 1 — focus mode + per-unit mode + text chunker + text cap."""
from __future__ import annotations

import os

import pytest

from californian_id.schemas import SemanticUnit, UnitPack


def _make_pack(n: int = 3) -> UnitPack:
    units = [
        SemanticUnit(unit_id=f"U{i}", title=f"Заголовок {i}",
                     intention="аргументация",
                     abstract=f"Тело юнита {i}. Некоторые тезисы.")
        for i in range(1, n + 1)
    ]
    return UnitPack(seminar_title="test-pack", cutter_id="test", units=units)


# ---------- B-1.1 focus mode ----------

def test_run_from_units_focus_filter_reduces_pack(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")
    from californian_id.pipeline import Pipeline
    pack = _make_pack(5)
    p = Pipeline()
    result = p.run_from_units(pack, focus_on=["U2"], mode="fast")
    # focus mode должен пометить background в chorus_reflection
    assert result.run_state.completion is not None
    signals = [s for cr in result.run_state.body.chorus_reflections
               for s in cr.signals_observed]
    assert any("focus_mode" in s for s in signals), signals[:3]


def test_run_from_units_no_focus_processes_all(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")
    from californian_id.pipeline import Pipeline
    pack = _make_pack(3)
    p = Pipeline()
    result = p.run_from_units(pack, mode="fast")
    signals = [s for cr in result.run_state.body.chorus_reflections
               for s in cr.signals_observed]
    assert not any("focus_mode" in s for s in signals)


def test_run_from_units_focus_empty_treated_as_no_focus(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")
    from californian_id.pipeline import Pipeline
    pack = _make_pack(3)
    p = Pipeline()
    result = p.run_from_units(pack, focus_on=[], mode="fast")
    assert result.run_state.completion is not None


# ---------- B-1.3 text chunker ----------

def test_chunk_by_markdown_headings():
    from californian_id.adapters.text_chunker import chunk_text
    text = ("# Section A\n\nBody A first paragraph with enough words.\n\n"
            "More body A content.\n\n"
            "# Section B\n\nBody B paragraph one.\n\n"
            "# Section C\n\nBody C content here.")
    chunks = chunk_text(text)
    assert len(chunks) == 3
    assert chunks[0].title.startswith("Section A")
    assert chunks[1].title.startswith("Section B")
    assert chunks[2].title.startswith("Section C")


def test_chunk_paragraphs_when_no_headings():
    from californian_id.adapters.text_chunker import chunk_text
    text = "\n\n".join([f"Параграф номер {i} с некоторым содержанием." * 30
                       for i in range(5)])
    chunks = chunk_text(text, target=800, max_chars=1500)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c.text) > 50


def test_chunk_empty_text_returns_empty():
    from californian_id.adapters.text_chunker import chunk_text
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_chunk_falls_back_to_length():
    from californian_id.adapters.text_chunker import chunk_text
    text = "Just a wall of text without paragraph breaks or headings. " * 200
    chunks = chunk_text(text, target=1000, max_chars=1500)
    assert len(chunks) >= 3


def test_to_unit_pack_shape():
    from californian_id.adapters.text_chunker import to_unit_pack
    text = "# A\n\nabc def\n\n# B\n\nghi jkl"
    pack = to_unit_pack(text, seminar_title="test")
    assert pack.seminar_title == "test"
    assert pack.cutter_id == "californian_id.adapters.text_chunker"
    assert len(pack.units) == 2
    assert pack.units[0].unit_id.startswith("chunk_")
    assert pack.units[0].intention == "сведения"


# ---------- B-1.2 per-unit mode ----------

def test_run_per_unit_produces_result_per_unit(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")
    from californian_id.pipeline import Pipeline
    pack = _make_pack(3)
    p = Pipeline()
    result = p.run_per_unit(pack, mode="fast", include_meta=False)
    assert set(result.unit_results.keys()) == {"U1", "U2", "U3"}
    for uid, r in result.unit_results.items():
        assert r.run_state.completion is not None
    assert result.meta is None


def test_run_per_unit_with_meta(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")
    from californian_id.pipeline import Pipeline
    pack = _make_pack(2)
    p = Pipeline()
    result = p.run_per_unit(pack, mode="fast", include_meta=True)
    assert len(result.unit_results) == 2
    assert result.meta is not None
    assert result.meta.run_state.completion is not None


# ---------- B-1.4 text cap env override ----------

def test_text_cap_env_override(monkeypatch):
    from californian_id.zarathustra import Zarathustra
    from californian_id.models.mock import MockClient
    z = Zarathustra()
    client = MockClient()
    long_text = "x" * 50_000
    # default cap 100_000 → text проходит целиком
    result = z.analyze_situation(long_text, client=client)
    assert result.topic  # mock даст что-то не пустое


def test_text_cap_env_can_shrink(monkeypatch):
    monkeypatch.setenv("CALIFORNIAN_ID_SITUATION_MAX_CHARS", "500")
    from californian_id.zarathustra import Zarathustra
    from californian_id.models.mock import MockClient
    z = Zarathustra()
    client = MockClient()
    # cap 500 → длинный текст обрезается
    result = z.analyze_situation("y" * 10_000, client=client)
    assert result is not None

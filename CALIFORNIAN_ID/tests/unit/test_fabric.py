"""Пик 5.7 unit tests: schemas + store round-trip + converter."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from californian_id.fabric import (
    FabricBlock,
    FabricEvidenceFragment,
    FabricRelation,
    FabricSceneState,
    FabricSnapshot,
    FabricSourceSpan,
    FabricStore,
    FabricThread,
    FabricUnit,
)
from californian_id.fabric.parser import _parse_json_from_text, _short_id
from californian_id.pipeline import _fabric_snapshot_to_unit_pack


def _sample_snapshot() -> FabricSnapshot:
    span = FabricSourceSpan(span_id="s001", source_id="src1", char_start=0, char_end=42, locator="§1")
    ev = FabricEvidenceFragment(fragment_id="e001", span=span, verbatim="Автономность класс свойств.")
    u1 = FabricUnit(unit_id="u001", intention="claim", text="Материальное не автономно.",
                    evidence_span_ids=["s001"], speaker_ref="Методолог", confidence=0.85)
    u2 = FabricUnit(unit_id="u002", intention="assumption", text="Автономность требует замкнутости.",
                    evidence_span_ids=["s001"], confidence=0.7)
    u3 = FabricUnit(unit_id="u003", intention="counterexample", text="Пример живой клетки.",
                    evidence_span_ids=["s001"], confidence=0.6)
    b1 = FabricBlock(block_id="b001", block_type="argument", title="Тезис Методолога",
                     unit_ids=["u001", "u002"])
    r1 = FabricRelation(relation_id="r001", relation_type="supports",
                        source_id="u002", target_id="u001")
    t1 = FabricThread(thread_id="t001", thread_type="concept", label="автономность",
                      member_ids=["u001", "u002", "u003"])
    scene = FabricSceneState(scene_id="sc001", participants=["Методолог"],
                             question="Что такое автономность?", phase="exploration")
    return FabricSnapshot(
        snapshot_id="snap0001", source_id="src1", source_version="v1",
        units=[u1, u2, u3], blocks=[b1], relations=[r1], threads=[t1],
        spans=[span], evidence=[ev], scene=scene,
        stats={"n_units": 3, "coverage_pct": 0.95},
    )


def test_store_round_trip():
    snap = _sample_snapshot()
    tmp = tempfile.mktemp(suffix=".db")
    store = FabricStore(tmp)
    try:
        store.register_source("src1", "test", "note", "Автономность класс свойств.")
        store.save_snapshot(snap)
        loaded = store.load_snapshot("snap0001")
    finally:
        store.close()
        Path(tmp).unlink(missing_ok=True)

    assert loaded is not None
    assert loaded.snapshot_id == "snap0001"
    assert len(loaded.units) == 3
    assert len(loaded.blocks) == 1
    assert len(loaded.relations) == 1
    assert len(loaded.threads) == 1
    assert loaded.scene is not None
    assert loaded.scene.question == "Что такое автономность?"
    intents = {u.intention for u in loaded.units}
    assert intents == {"claim", "assumption", "counterexample"}


def test_converter_produces_unit_pack():
    snap = _sample_snapshot()
    pack = _fabric_snapshot_to_unit_pack(snap)
    assert len(pack.units) >= 1
    assert pack.units[0].intention in {"аргументация", "проблематизация", "сведения"}
    assert pack.cutter_id.startswith("californian_id.fabric.")
    assert pack.seminar_title


def test_json_parser_tolerates_fence():
    js = _parse_json_from_text("```json\n{\"a\": 1}\n```")
    assert js == {"a": 1}
    js = _parse_json_from_text("noise before {\"a\": 2, \"b\": [1,2]} noise after")
    assert js == {"a": 2, "b": [1, 2]}


def test_short_id_stable():
    a = _short_id("u", "hello")
    b = _short_id("u", "hello")
    c = _short_id("u", "hell0")
    assert a == b
    assert a != c
    assert a.startswith("u")


def test_fabric_parser_rejects_mock():
    from californian_id.fabric import FabricParser
    from californian_id.models.mock import MockClient

    with pytest.raises(RuntimeError, match="mock provider forbidden"):
        FabricParser(MockClient())

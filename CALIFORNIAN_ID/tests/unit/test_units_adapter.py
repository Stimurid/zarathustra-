"""Adapter tests: md-units parser + run_from_units seeding."""
from pathlib import Path

import pytest

from californian_id.adapters.units_of_content_md import (
    parse_md_units_file, parse_md_units_text,
)
from californian_id.pipeline import Pipeline

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "units_md"


def test_lean_pack_parses_all_units_with_toulmin():
    pack = parse_md_units_file(FIX / "lean_pack.md")
    assert len(pack.units) == 3
    ids = [u.unit_id for u in pack.units]
    assert ids == ["U1", "U2", "U3"]
    u1 = pack.units[0]
    assert u1.intention == "аргументация"
    assert u1.toulmin and u1.toulmin.claim == "поход необходим"
    assert u1.toulmin.data == "хлеба нет дома"
    assert u1.toulmin.warrant == "без хлеба нельзя обедать"
    assert u1.toulmin.rebuttal == "можно съесть кашу"
    assert len(u1.participants) == 2
    assert any(p.name == "Иван" for p in u1.participants)
    # source audit is absent in lean pack
    assert pack.source_audit is None


def test_rich_pack_extracts_source_audit_signals():
    pack = parse_md_units_file(FIX / "rich_pack.md")
    assert len(pack.units) == 2
    audit = pack.source_audit
    assert audit is not None, "rich pack must yield SourceAudit"
    # speaker inventory
    labels = {p.label for p in audit.speaker_roles}
    assert "Speaker 1" in labels and "Speaker 2" in labels
    # diarization defects
    assert audit.diarization_defects
    kinds = {d.kind for d in audit.diarization_defects}
    assert "разрыв" in kinds and "склейка" in kinds
    # recognition damage
    assert audit.recognition_damage
    verbatim = {r["verbatim"] for r in audit.recognition_damage}
    assert "филогсофски" in verbatim
    # ambiguous vocatives (two Ivans mentioned in preamble)
    assert any("Иван" in v or "Ваня" in v for v in audit.ambiguous_vocatives) \
        or "Ваня" in " ".join(audit.ambiguous_vocatives)


def test_pack_topic_bypasses_hardcoded_dictionary():
    """Ключевая гарантия: adapter НЕ ходит через _concept_hints словарь."""
    pack = parse_md_units_text(
        "# Поход за молоком с голой жопой\n\n"
        "### U1 — Тезис\n"
        "Паспорт ЕС\n"
        "- Заголовок: Тезис\n"
        "- Намерение: аргументация\n"
        "Тулмин\n- Claim: тезис верен\n"
        "Абстракт ЕС\nТест.\n"
    )
    from californian_id.pipeline import _situation_from_pack
    sit = _situation_from_pack(pack)
    assert "молок" in sit.topic.lower() or "голой" in sit.topic.lower(), sit.topic
    # concepts should NOT be empty just because words aren't in the AGI dictionary
    assert sit.concepts, "concepts empty — dictionary заточка не обойдена"


def test_run_from_units_completes_on_non_ai_topic():
    """Pipeline полностью работает на теме без AGI-керворков."""
    pack = parse_md_units_file(FIX / "lean_pack.md")
    result = Pipeline().run_from_units(pack, mode="fast")
    assert result.run_state.status == "COMPLETED"
    c = result.run_state.completion
    assert c is not None
    assert c.form in {
        "alliance", "decision_with_dissent", "unresolvable_conflict",
        "aporia", "transformed_question", "world_fork", "delegation",
        "polyphony", "synthesis", "refusal_to_close",
    }
    # seeded claims/attacks must have reached argument_map before council spoke
    amap = result.run_state.argument_map
    seeded_claims = [c for c in amap.claims if c.text.startswith("[U")]
    assert seeded_claims, "argument_map was not seeded from units"
    # body knows it came from a pack
    assert result.run_state.body.seeded_from_units == ["U1", "U2", "U3"]


def test_source_audit_becomes_chorus_reflection_zero():
    """Аудит источника из rich pack → chorus_reflection at_turn_index=-1."""
    pack = parse_md_units_file(FIX / "rich_pack.md")
    result = Pipeline().run_from_units(pack, mode="fast")
    reflections = result.run_state.body.chorus_reflections
    audit_reflection = next(
        (r for r in reflections if r.at_turn_index == -1), None,
    )
    assert audit_reflection is not None, "source audit not surfaced as chorus reflection"
    assert audit_reflection.scene_temperature == "alert"
    assert audit_reflection.signals_observed, "audit reflection has no signals"


def test_run_from_units_writes_correct_trace_events():
    import json
    pack = parse_md_units_file(FIX / "rich_pack.md")
    result = Pipeline().run_from_units(pack, mode="fast")
    events_path = result.trace_dir / "events.jsonl"
    events = [json.loads(l) for l in events_path.read_text(encoding="utf-8").splitlines()]
    kinds = {e["kind"] for e in events}
    assert "body_seeded" in kinds
    assert "source_audit_ingested" in kinds
    assert "run_started" in kinds
    run_started = next(e for e in events if e["kind"] == "run_started")
    assert run_started["payload"]["entrypoint"] == "run_from_units"


def test_parser_rejects_non_units_input():
    with pytest.raises(ValueError, match="not a units-of-content markdown"):
        parse_md_units_text("this is not a units markdown at all, just prose")

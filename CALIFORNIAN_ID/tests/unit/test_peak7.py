"""Пик 7 — MethodPacks / RhetoricalGenres / DialogueProtocols / PositionModel."""
from __future__ import annotations

import pytest

from californian_id import dialogue_protocols, method_packs, rhetorical_genres
from californian_id.personas import load_registry


# ---------- 7.1 MethodPacks ----------
def test_method_packs_all_load():
    reg = method_packs.registry()
    expected = {
        "claim_and_logic_analysis", "argument_reconstruction",
        "conceptual_analysis", "ontological_reconstruction",
        "problematisation", "socratic_inquiry",
    }
    assert set(reg.keys()) == expected
    for mid, m in reg.items():
        assert m.prompt_text, f"{mid}: prompt_text пуст"
        assert m.display_name, f"{mid}: display_name отсутствует"


def test_method_pack_get_returns_pack():
    p = method_packs.get("socratic_inquiry")
    assert p is not None
    assert "elenchic" in p.prompt_text.lower() or "сократ" in p.display_name.lower()


def test_method_pack_get_unknown_returns_none():
    assert method_packs.get("nonexistent") is None


# ---------- 7.2 RhetoricalGenres ----------
def test_rhetorical_genres_all_load():
    reg = rhetorical_genres.registry()
    expected = {
        "academic_critique", "socratic_questions", "methodological_consultation",
        "ironic_demolition", "supportive_reframing", "forensic_argument",
        "short_intervention",
    }
    assert set(reg.keys()) == expected


def test_rhetorical_genres_default_is_methodological():
    assert rhetorical_genres.default_genre_id() == "methodological_consultation"


def test_rhetorical_genre_get_default_when_none():
    g = rhetorical_genres.get(None)
    assert g is not None
    assert g.genre_id == "methodological_consultation"


def test_rhetorical_genre_get_by_id():
    g = rhetorical_genres.get("ironic_demolition")
    assert g is not None
    assert "иронии" in g.prompt_text.lower() or "ирония" in g.prompt_text.lower()


# ---------- 7.3 PositionModel on personas ----------
def test_all_lens_have_position_model():
    reg = load_registry()
    for pid, p in reg.personas.items():
        assert p.position_model, f"{pid}: position_model отсутствует"
        pm = p.position_model
        for key in ("primary_object", "ontology", "methods", "distinctions",
                    "characteristic_operations", "closure_criteria",
                    "boundary_conditions"):
            assert key in pm, f"{pid}: position_model.{key} отсутствует"


def test_position_model_prompt_block_non_empty():
    reg = load_registry()
    for pid, p in reg.personas.items():
        block = p.position_model_prompt_block()
        assert block, f"{pid}: prompt block пуст"
        assert "primary_object" in block
        assert "ontology" in block


def test_position_model_prompt_block_empty_when_none():
    from californian_id.personas import Persona
    from pathlib import Path
    p = Persona(persona_id="X", display_name="X", version="0", status="ok",
                role_summary="", package_path=Path("."), manifest={},
                system_prompt="", position_model=None)
    assert p.position_model_prompt_block() == ""


# ---------- 7.4 DialogueProtocols ----------
def test_dialogue_protocols_all_load():
    reg = dialogue_protocols.registry()
    expected = {"listening", "clarifying", "socratic", "joint_inquiry", "problematising"}
    assert set(reg.keys()) == expected


def test_dialogue_protocol_default_is_joint_inquiry():
    assert dialogue_protocols.default_protocol_id() == "joint_inquiry"


def test_dialogue_protocol_get_default_when_none():
    p = dialogue_protocols.get(None)
    assert p is not None
    assert p.protocol_id == "joint_inquiry"


# ---------- 7.5 wire ----------
def test_pipeline_has_new_fields():
    from californian_id.pipeline import Pipeline
    p = Pipeline()
    assert hasattr(p, "closing_genre_id")
    assert hasattr(p, "dialogue_protocol_id")
    assert p.closing_genre_id is None
    assert p.dialogue_protocol_id is None

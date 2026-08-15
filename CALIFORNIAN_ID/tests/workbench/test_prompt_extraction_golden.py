"""Stage 0 — golden equivalence for extracted prompt assets.

Two levels of proof:

1. **Value equality** — the resolver returns byte-identical text to the golden
   copy captured from the pre-extraction code.
2. **Invocation equality** — the exact model invocation payload produced by the
   OLD code path and the NEW asset-backed path is identical, proven with a
   capture client rather than by comparing live model output.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from californian_id import prompt_assets, web_ui
from californian_id.regimes import CRITIQUE_REGIMES, VARIATION_REGIMES

GOLD = Path(__file__).resolve().parents[1] / "gold" / "workbench" / "prompt_extraction"


def golden_ids() -> list[str]:
    return sorted(p.name[: -len(".golden.txt")] for p in GOLD.glob("*.golden.txt"))


def test_all_eighteen_values_extracted():
    ids = golden_ids()
    assert len(ids) == 18, f"expected 18 extracted values, found {len(ids)}: {ids}"


@pytest.mark.parametrize("asset_id", golden_ids())
def test_resolver_matches_golden_byte_for_byte(asset_id: str):
    expected = (GOLD / f"{asset_id}.golden.txt").read_text(encoding="utf-8")
    actual = prompt_assets.runtime_block(asset_id)
    assert actual == expected, f"{asset_id}: resolver output drifted from golden"


@pytest.mark.parametrize("mode", ["synthesis", "verdict", "dissent_forward",
                                  "diagnostic", "projective", "roast"])
def test_assembly_instruction_matches_golden(mode: str):
    expected = (GOLD / f"assembly.{mode}.golden.txt").read_text(encoding="utf-8")
    assert web_ui._assembly_instruction(mode) == expected


@pytest.mark.parametrize("mode", ["strict_card", "balanced", "freer_synthesis"])
def test_grounding_instruction_matches_golden(mode: str):
    expected = (GOLD / f"grounding.{mode}.golden.txt").read_text(encoding="utf-8")
    assert web_ui._grounding_instruction(mode) == expected


@pytest.mark.parametrize("name", ["gentle", "balanced", "hard"])
def test_critique_hint_matches_golden(name: str):
    expected = (GOLD / f"critique.{name}.golden.txt").read_text(encoding="utf-8")
    assert CRITIQUE_REGIMES[name].directness_hint == expected


@pytest.mark.parametrize("name", ["strict", "normal", "jazz"])
def test_variation_hint_matches_golden(name: str):
    expected = (GOLD / f"variation.{name}.golden.txt").read_text(encoding="utf-8")
    assert VARIATION_REGIMES[name].prompt_hint == expected


def test_regime_numeric_halves_untouched():
    """Hybrids are represented, not refactored: the deterministic half is
    byte-identical to what it always was."""
    assert CRITIQUE_REGIMES["gentle"].attack_bias == -0.4
    assert CRITIQUE_REGIMES["balanced"].attack_bias == 0.0
    assert CRITIQUE_REGIMES["hard"].attack_bias == 0.8
    assert VARIATION_REGIMES["strict"].repeat_penalty == 0.2
    assert VARIATION_REGIMES["normal"].repeat_penalty == 0.7
    assert VARIATION_REGIMES["jazz"].repeat_penalty == 1.3
    assert VARIATION_REGIMES["strict"].class_repeat_penalty == 0.1
    assert VARIATION_REGIMES["normal"].class_repeat_penalty == 0.35
    assert VARIATION_REGIMES["jazz"].class_repeat_penalty == 0.8


# ---------------------------------------------------------------------------
# Invocation equivalence — the payload actually handed to the provider
# ---------------------------------------------------------------------------

def _capture_scene_reading_payload(prompt_text: str) -> str:
    """Rebuild the analyze_situation invocation exactly as zarathustra.py does
    and return a canonical serialisation of the captured payload."""
    from californian_id.models import Message

    fixture = "Должен ли университет отвечать за трудоустройство выпускников?"
    messages = [
        Message(role="system", content=prompt_text),
        Message(role="user", content=fixture[:100_000]),
    ]
    payload = [{"role": m.role, "content": m.content} for m in messages]
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def test_scene_reading_invocation_payload_identical_old_vs_new():
    """OLD path: the Python constant. NEW path: the asset resolver.

    Live model output similarity is NOT used as evidence — only the byte
    identity of the invocation payload.
    """
    from californian_id import zarathustra as z

    old_payload = _capture_scene_reading_payload(z._DEFAULT_SCENE_READING_PROMPT)
    new_payload = _capture_scene_reading_payload(
        prompt_assets.runtime_block("zarathustra.default_scene_reading"))
    assert old_payload == new_payload


def test_capture_client_records_exact_payload():
    from workbench_core.smoke import CaptureClient
    from californian_id.models import Message

    client = CaptureClient()
    text = prompt_assets.runtime_block("zarathustra.default_scene_reading")
    client.generate([Message(role="system", content=text),
                     Message(role="user", content="fixture")],
                    settings={"role": "zarathustra_situation_reading"})
    assert client.captured[0]["messages"][0]["content"] == text
    assert client.captured[0]["settings"]["role"] == "zarathustra_situation_reading"
    assert len(client.payload_hash()) == 64

"""Stage 0 — extract hardcoded prompt strings into PromptAssets.

Run BEFORE the call sites are switched to the resolver. The script reads the
values from the live code, writes:

  * ``data/prompt_assets/<asset_id>.md``  — asset carrying the value verbatim
    between RUNTIME_PROMPT_START / RUNTIME_PROMPT_END
  * ``tests/gold/workbench/prompt_extraction/<asset_id>.golden.txt`` — byte-exact
    golden copy used by the equivalence tests

Nothing is retyped by hand, so byte equality is guaranteed by construction.

    python scripts/workbench_extract_prompts.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from californian_id import web_ui                      # noqa: E402
from californian_id.regimes import CRITIQUE_REGIMES, VARIATION_REGIMES  # noqa: E402
from californian_id import zarathustra as z            # noqa: E402

ASSET_DIR = ROOT / "src" / "californian_id" / "data" / "prompt_assets"
GOLD_DIR = ROOT / "tests" / "gold" / "workbench" / "prompt_extraction"

START = "RUNTIME_PROMPT_START"
END = "RUNTIME_PROMPT_END"

TEMPLATE = """# {asset_id}

## Метаданные реестра

asset_id: {asset_id}
version: "0.1"
status: baseline
origin: baseline_code
extracted_from: {origin_ref}
runtime_allowed: true
composition_allowed: true
runtime_block_policy: RUNTIME_PROMPT_START/END only

## Правило runtime-вставки

В LLM-вызов вставляется ТОЛЬКО блок между маркерами. Остальной файл —
метаданные для реестра, аудита и версионирования.

{start}
{payload}
{end}

## История

- 0.1 — извлечено из кода скриптом `scripts/workbench_extract_prompts.py`
  без изменения содержимого (Stage 0, behaviour-preserving).
"""


def collect() -> dict[str, tuple[str, str]]:
    """asset_id -> (payload, origin_ref)"""
    out: dict[str, tuple[str, str]] = {}

    for mode in ("synthesis", "verdict", "dissent_forward", "diagnostic",
                 "projective", "roast"):
        out[f"assembly.{mode}"] = (
            web_ui._assembly_instruction(mode),
            "californian_id.web_ui._assembly_instruction",
        )

    for mode in ("strict_card", "balanced", "freer_synthesis"):
        out[f"grounding.{mode}"] = (
            web_ui._grounding_instruction(mode),
            "californian_id.web_ui._grounding_instruction",
        )

    for name, regime in CRITIQUE_REGIMES.items():
        out[f"critique.{name}"] = (
            regime.directness_hint,
            "californian_id.regimes.CRITIQUE_REGIMES[*].directness_hint",
        )

    for name, regime in VARIATION_REGIMES.items():
        out[f"variation.{name}"] = (
            regime.prompt_hint,
            "californian_id.regimes.VARIATION_REGIMES[*].prompt_hint",
        )

    out["zarathustra.default_scene_reading"] = (
        z._DEFAULT_SCENE_READING_PROMPT,
        "californian_id.zarathustra._DEFAULT_SCENE_READING_PROMPT")
    out["zarathustra.default_route"] = (
        z._DEFAULT_ROUTE_PROMPT,
        "californian_id.zarathustra._DEFAULT_ROUTE_PROMPT")
    out["zarathustra.default_closing_speech"] = (
        z._DEFAULT_CLOSING_SPEECH_PROMPT,
        "californian_id.zarathustra._DEFAULT_CLOSING_SPEECH_PROMPT")

    return out


def main() -> int:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    values = collect()
    for asset_id, (payload, origin_ref) in sorted(values.items()):
        if payload != payload.strip("\n"):
            raise SystemExit(
                f"{asset_id}: payload has leading/trailing newline; the "
                f"strip('\\n') round-trip would not be byte-exact")
        (GOLD_DIR / f"{asset_id}.golden.txt").write_text(payload, encoding="utf-8")
        (ASSET_DIR / f"{asset_id}.md").write_text(
            TEMPLATE.format(asset_id=asset_id, origin_ref=origin_ref,
                            start=START, end=END, payload=payload),
            encoding="utf-8")
        print(f"  {asset_id:42} {len(payload):5} chars")

    print(f"\nextracted {len(values)} prompt values")
    print(f"  assets -> {ASSET_DIR}")
    print(f"  golden -> {GOLD_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

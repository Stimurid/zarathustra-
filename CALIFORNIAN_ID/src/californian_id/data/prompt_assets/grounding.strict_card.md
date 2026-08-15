# grounding.strict_card

## Метаданные реестра

asset_id: grounding.strict_card
version: "0.1"
status: baseline
origin: baseline_code
extracted_from: californian_id.web_ui._grounding_instruction
runtime_allowed: true
composition_allowed: true
runtime_block_policy: RUNTIME_PROMPT_START/END only

## Правило runtime-вставки

В LLM-вызов вставляется ТОЛЬКО блок между маркерами. Остальной файл —
метаданные для реестра, аудита и версионирования.

RUNTIME_PROMPT_START
Stay tightly anchored to the selected card. Reuse its operation, distinction, and risk logic closely. Do not widen into extra frameworks unless they are necessary to make the card intelligible in the current scene.
RUNTIME_PROMPT_END

## История

- 0.1 — извлечено из кода скриптом `scripts/workbench_extract_prompts.py`
  без изменения содержимого (Stage 0, behaviour-preserving).

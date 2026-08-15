# grounding.balanced

## Метаданные реестра

asset_id: grounding.balanced
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
Keep the selected card as the primary anchor, but develop it into a fuller argument responsive to the scene. You may widen one level beyond the card, but do not drift into generic abstract commentary.
RUNTIME_PROMPT_END

## История

- 0.1 — извлечено из кода скриптом `scripts/workbench_extract_prompts.py`
  без изменения содержимого (Stage 0, behaviour-preserving).

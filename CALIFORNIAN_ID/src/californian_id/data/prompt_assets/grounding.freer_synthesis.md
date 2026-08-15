# grounding.freer_synthesis

## Метаданные реестра

asset_id: grounding.freer_synthesis
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
Use the selected card as an anchor, but allow wider synthesis, analogy, and recombination if the scene clearly demands it. Grounding must remain legible, yet the response may move beyond the card's immediate wording.
RUNTIME_PROMPT_END

## История

- 0.1 — извлечено из кода скриптом `scripts/workbench_extract_prompts.py`
  без изменения содержимого (Stage 0, behaviour-preserving).

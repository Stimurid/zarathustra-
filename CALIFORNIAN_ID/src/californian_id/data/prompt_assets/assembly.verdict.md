# assembly.verdict

## Метаданные реестра

asset_id: assembly.verdict
version: "0.1"
status: baseline
origin: baseline_code
extracted_from: californian_id.web_ui._assembly_instruction
runtime_allowed: true
composition_allowed: true
runtime_block_policy: RUNTIME_PROMPT_START/END only

## Правило runtime-вставки

В LLM-вызов вставляется ТОЛЬКО блок между маркерами. Остальной файл —
метаданные для реестра, аудита и версионирования.

RUNTIME_PROMPT_START
Assemble toward a verdict. Name the strongest line, expose the weaker one, and state what should be retained or discarded.
RUNTIME_PROMPT_END

## История

- 0.1 — извлечено из кода скриптом `scripts/workbench_extract_prompts.py`
  без изменения содержимого (Stage 0, behaviour-preserving).

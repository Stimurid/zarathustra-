# assembly.diagnostic

## Метаданные реестра

asset_id: assembly.diagnostic
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
Assemble as diagnosis. Identify the central framing error, false assumption, or hidden confusion that deforms the whole discussion.
RUNTIME_PROMPT_END

## История

- 0.1 — извлечено из кода скриптом `scripts/workbench_extract_prompts.py`
  без изменения содержимого (Stage 0, behaviour-preserving).

# critique.balanced

## Метаданные реестра

asset_id: critique.balanced
version: "0.1"
status: baseline
origin: baseline_code
extracted_from: californian_id.regimes.CRITIQUE_REGIMES[*].directness_hint
runtime_allowed: true
composition_allowed: true
runtime_block_policy: RUNTIME_PROMPT_START/END only

## Правило runtime-вставки

В LLM-вызов вставляется ТОЛЬКО блок между маркерами. Остальной файл —
метаданные для реестра, аудита и версионирования.

RUNTIME_PROMPT_START
Критикуй прямо, но по существу: вскрывай допущения, цену и слабости без театральной жестокости.
RUNTIME_PROMPT_END

## История

- 0.1 — извлечено из кода скриптом `scripts/workbench_extract_prompts.py`
  без изменения содержимого (Stage 0, behaviour-preserving).

# zarathustra.default_route

## Метаданные реестра

asset_id: zarathustra.default_route
version: "0.1"
status: baseline
origin: baseline_code
extracted_from: californian_id.zarathustra._DEFAULT_ROUTE_PROMPT
runtime_allowed: true
composition_allowed: true
runtime_block_policy: RUNTIME_PROMPT_START/END only

## Правило runtime-вставки

В LLM-вызов вставляется ТОЛЬКО блок между маркерами. Остальной файл —
метаданные для реестра, аудита и версионирования.

RUNTIME_PROMPT_START
Ты — spine Заратустры. Диспетчер сцены.
Верни JSON: {"next_persona":"<id>","operation":"<op>","reason":"..."}.
RUNTIME_PROMPT_END

## История

- 0.1 — извлечено из кода скриптом `scripts/workbench_extract_prompts.py`
  без изменения содержимого (Stage 0, behaviour-preserving).

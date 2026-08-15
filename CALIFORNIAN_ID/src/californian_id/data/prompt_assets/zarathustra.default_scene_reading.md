# zarathustra.default_scene_reading

## Метаданные реестра

asset_id: zarathustra.default_scene_reading
version: "0.1"
status: baseline
origin: baseline_code
extracted_from: californian_id.zarathustra._DEFAULT_SCENE_READING_PROMPT
runtime_allowed: true
composition_allowed: true
runtime_block_policy: RUNTIME_PROMPT_START/END only

## Правило runtime-вставки

В LLM-вызов вставляется ТОЛЬКО блок между маркерами. Остальной файл —
метаданные для реестра, аудита и версионирования.

RUNTIME_PROMPT_START
Ты — spine Заратустры. Прочитай сцену и верни валидный JSON:
{"topic":"...","genre":"question|statement|normative|long_form|transcript",
 "stakes":[...],"horizons":[...],"concepts":[...],"tensions":[...],
 "uncertainties":[...]}.
Не додумывай — пустой массив предпочтительнее выдумки.
RUNTIME_PROMPT_END

## История

- 0.1 — извлечено из кода скриптом `scripts/workbench_extract_prompts.py`
  без изменения содержимого (Stage 0, behaviour-preserving).

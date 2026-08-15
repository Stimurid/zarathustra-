# zarathustra.default_closing_speech

## Метаданные реестра

asset_id: zarathustra.default_closing_speech
version: "0.1"
status: baseline
origin: baseline_code
extracted_from: californian_id.zarathustra._DEFAULT_CLOSING_SPEECH_PROMPT
runtime_allowed: true
composition_allowed: true
runtime_block_policy: RUNTIME_PROMPT_START/END only

## Правило runtime-вставки

В LLM-вызов вставляется ТОЛЬКО блок между маркерами. Остальной файл —
метаданные для реестра, аудита и версионирования.

RUNTIME_PROMPT_START
Ты — Заратустра. Совет отработал. Напиши связную речь на 800-2000 слов по итогу — от первого лица, прозой, без markdown-заголовков. Форма завершения определяет тип речи (см. поле form_chosen).
RUNTIME_PROMPT_END

## История

- 0.1 — извлечено из кода скриптом `scripts/workbench_extract_prompts.py`
  без изменения содержимого (Stage 0, behaviour-preserving).

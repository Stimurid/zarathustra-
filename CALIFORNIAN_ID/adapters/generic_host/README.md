# Generic Host Adapter (contract)

Ядро `californian_id.pipeline.Pipeline` не зависит от какого-либо
конкретного host. Любой адаптер должен:

## Вход
```python
from californian_id.pipeline import Pipeline
pipe = Pipeline()
result = pipe.run(text=user_text, mode="fast" | "deep", run_id=None)
```

## Выход
`result: PipelineResult`
- `result.run_state.synthesis` — structured synthesis (см. `schemas.py::Synthesis`)
- `result.run_state.security_events`
- `result.run_state.turns` (raw persona turns; НЕ показывать пользователю по умолчанию)
- `result.trace_dir` — путь к JSONL-трассе

## Контракт для host
1. Не подменяй `interaction/*` политики своими.
2. Не логируй системные промпты и `turn.utterance` в публичный лог без
   `--debug`-эквивалента.
3. Прогоняй security_events как чувствительные события host-канала.
4. Не приписывай синтез конкретному участнику host — это работа
   Заратустры, host лишь передаёт результат.

## Расширения
- Добавь `render(payload)` для форматирования конкретному host UX.
- Прогоняй лимиты бюджета через `config/runtime.yaml`.

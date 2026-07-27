# Telegram Adapter (backlog + contract)

Заказ проекта планирует Telegram как основной канал. Ядро
`californian_id.pipeline.Pipeline` от Telegram не зависит; связка тонкая.

## Backlog для реализации

1. Poll `python-telegram-bot` или aiogram: приём сообщения → `pipeline.run(text=msg.text)`.
2. `Markdown_V2` рендер `PipelineResult` через `_pretty_print` (см. `cli.py`).
3. Long-run сессии в mode=`deep` — фоновый worker, промежуточные события
   стримятся как typing indicators / короткие статус-сообщения.
4. Rate-limiting и per-chat cost budget (`config/runtime.yaml` -> `budget`).
5. Security events отправлять в отдельный admin-канал, не пользователю.

## Что нельзя делать

- Импортировать Telegram-сущности из ядра.
- Логировать system prompts в chat-историю бота.
- Показывать пользователю raw persona turn utterances по умолчанию.

## Skeleton, если он появится

Если в организации уже есть Telegram bot skeleton («бот Сапольского»),
подключай его как host — просто оберни `pipe.run(msg.text)` и рендер.
Ничего не переноси в ядро.

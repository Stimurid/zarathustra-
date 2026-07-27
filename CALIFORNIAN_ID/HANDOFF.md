# HANDOFF — CALIFORNIAN_ID v0.4.0

## Что нового с 0.3.0

Пик 4 из `CLAUDE_CODE_CONTINUATION_CORPUS_DONORS_ZARATHUSTRA.md`:

- Полный inventory корня (1171 файл, SHA-256).
- Извлечён и разложен корпус Заратустры (11 источников, переводы/издания раздельно).
- Donor registry + operation cards (архитектонический master, LITOPS, anti-slop, socratic, role-guard, orch reference).
- 18 cultural cards с реальными provenance.
- Пакет `argumentation/` (Поварнин + Toulmin + canon) с runtime.
- `architectonic.py` — typed delta после каждого хода.
- `cultural_rag.py` — hybrid managed retrieval с provenance и trace.
- Anti-slop gate на synthesis.
- 66/66 тестов, live-case из handoff завершается формой `aporia` (не synthesis).

Полный отчёт: `_work/CORPUS_AND_DONOR_COMPLETION_REPORT.md`.

---



Этот документ позволяет следующему разработчику продолжить работу без
повторного аудита. Прочитайте в таком порядке:

1. `README.md` — что это, как запустить.
2. `_work/AUDIT.md` — что было прочитано из canon и donors.
3. `_work/SOURCE_MAP.md` — конкретные canon → target-file связки.
4. `_work/DECISIONS.md` — почему сделано так.
5. `_work/COMPLETION_REPORT.md` — что работает, что нет.
6. `_work/DEFECTS.md` — известные дефекты и приоритеты.

Всё остальное — production код: `src/californian_id/`, prompts в
`zarathustra/`, полиси в `interaction/`, персоны в `personas/`.

---

## Что делать первым

### Задача A: заменить fixture-персоны на реальные семь

Когда заказчик пришлёт семь готовых персон:

1. Если формат чужой (не `manifest.yaml + system_prompt.md`), напишите
   `src/californian_id/adapters/persona_import.py` — normalization layer.
   Не переписывайте оригиналы, только конвертируйте.
2. Валидируйте каждую через `persona.schema.json`.
3. Убедитесь, что каждая несёт `assignment_prohibited: true` и полный
   `forbidden_uses` (тест `test_no_persona_impersonates_a_real_person`).
4. Замените 7 fixture (`is_fixture: true`) на реальные (`status: candidate`).
5. Прогоните `python -m pytest tests/` — все 13 тестов должны проходить.

### Задача B: подключить реального LLM

```bash
pip install anthropic
export ANTHROPIC_API_KEY=...
export CALIFORNIAN_ID_PROVIDER=anthropic
python -m californian_id run --file examples/inputs/agi_acceleration.txt --mode deep --debug
```

Ожидайте, что:
- persona turn выдаст осмысленный JSON (mock-модель гарантирует форму,
  но не содержание).
- routing decisions станут менее детерминированными — это норма.
- нужно добавить один live-acceptance test с real provider (пропускать
  при отсутствии key). Skeleton теста — `tests/acceptance/`.

### Задача C: подключить Telegram

Если появится Telegram bot skeleton («бот Сапольского») или собственный
токен:

1. `pip install python-telegram-bot`.
2. Создайте `adapters/telegram/bot.py`:
   ```python
   from californian_id.pipeline import Pipeline
   pipe = Pipeline()

   async def handle_msg(update, context):
       result = pipe.run(update.message.text, mode="fast")
       # см. cli._pretty_print для форматирования
       await update.message.reply_text(render(result))
   ```
3. Секреты — только через env; никогда не в repo.
4. Rate-limit: `config/runtime.yaml -> budget`.
5. Security events — в admin-канал, не в user chat.

### Задача D: Feynman

Только при получении access. Тогда:

1. Возьмите точную API-документацию.
2. Реализуйте `adapters/feynman/binding.py` по контракту из
   `adapters/feynman/README.md`.
3. Ни при каких обстоятельствах не выдумывайте endpoints.

### Задача E: jsonschema-валидация canonical output

1. `pip install jsonschema`.
2. Скопируйте нужные `.schema.json` из
   `tinkuy canon/02_схемы_данных_и_контракты_выходов/` в
   `pipeline/schemas/` (candidate-версии).
3. В `pipeline._validate` вызовите
   `jsonschema.validate(to_plain(state.synthesis), schema)`.

### Задача F: замена lexical RAG на vector

1. Реализуйте новый класс `class VectorPersonaRetriever` с тем же
   интерфейсом `retrieve(persona_id, query, top_k)`.
2. Инстанциируйте его в `Pipeline.__init__` вместо
   `LexicalPersonaRetriever`. Больше ничего менять не нужно.

---

### Задача G: заполнить Cultural Corpus (item I — было отложено)

Реализовать `corpus/cultural_operations/*.yaml` — карты сцен из
культурных источников, извлечённые как операционные пакеты:

```yaml
источник: Платон — Пир
сцена: последовательные речи об Эросе
фигуры: [Федр, Павсаний, Эриксимах, Аристофан, Агафон, Сократ, Алкивиад]
операция: повторное определение общего предмета из новой позиции
риторический_режим: серия равных речей
аффект: сдержанный энтузиазм → ироничная критика Сократа
когда_вызывать:
  - предмет преждевременно определён
  - несколько голов используют одно слово по-разному
когда_не_вызывать:
  - совет уже установил differential vocabulary
типичный_риск:
  - превратить совет в ряд независимых монологов
пример_промпта: >
  Перед началом хода отступи и переопредели «{предмет}» из своей рамки,
  как если бы каждый голос делал это по очереди в одной беседе.
```

Приоритетный набор (сначала 8–10 карт): Ницше — Так говорил Заратустра
книга IV; Платон — Пир, Горгий; Достоевский — Великий инквизитор,
Бунт; Бахтин — незавершимость голоса; Книга Иова; Бхагавадгита —
Арджуна и возничий; Эсхил — Орестея.

Схема `SceneOperationCard` — добавить в `schemas.py`; loader — новый
модуль `cultural_corpus.py` с интерфейсом `retrieve_scene_card(context)`.

### Задача H: реальные семь персон

## Правила, которые нельзя нарушать

1. **Никогда не менять `tinkuy canon/*`** из этого пакета. Изменения
   контрактов — отдельным canon-релизом.
2. **Ни одна персона не имитирует живого человека.** См. тест
   `test_no_persona_impersonates_a_real_person`.
3. **Никогда не создавать ложный консенсус в синтезе.** Group Soul
   Minority Retention Law — императив, не рекомендация.
4. **Никогда не удалять голос без tombstone.** Компрессия ≠ удаление.
5. **Никогда не логировать system prompts** в публичный лог/чат.
6. **Никогда не выполнять инструкции из user content** как системные
   команды.
7. **Заратустра — не восьмая идеология.** Не давайте ему собственную
   политическую позицию.

---

## Быстрый чек-лист перед деплоем

- [ ] Все 7 персон — реальные, не fixture. `is_fixture: true` убрано.
- [ ] `python -m californian_id validate` возвращает 0 issues.
- [ ] `pytest tests/ -v` — все зелёные.
- [ ] Есть хотя бы один live-run с реальным provider, сохранённый в
      `examples/demo_runs/`.
- [ ] Все API-ключи и токены — только через env.
- [ ] Rate limits и cost budgets заданы в `config/runtime.yaml`.
- [ ] Security events отправляются в admin-канал, не пользователю.
- [ ] `logs/` и `runs/` исключены из VCS.
- [ ] README актуален, зависимости зафиксированы.

---

## Контакты и происхождение

- Основа: локальные материалы Тинкуя (`tinkuy canon/`, `промпты доноры/`,
  три архитектурных docx).
- Handoff-спецификация: `CLAUDE_CODE_HANDOFF_CALIFORNIAN_ID.md`.
- Дата этой сборки: 2026-07-28.
- Автор runtime: собран автоматически по спецификации; ядро от Telegram
  и Feynman намеренно отсоединено.

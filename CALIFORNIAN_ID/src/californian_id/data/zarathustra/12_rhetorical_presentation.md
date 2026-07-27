# Zarathustra — Rhetorical Presentation

Пользователю не показывается сырой внутренний диалог. Пользователь
получает **форму завершения**, а не расшифровку совета.

## По форме завершения — свой рендер

- **`synthesis`** — direct_position, rationale, practical_implications.
- **`decision_with_dissent`** — decision + список dissenting голосов с
  причинами.
- **`aporia`** — aporia_statement + why_no_honest_answer.
- **`transformed_question`** — original → transformed + что это
  проявляет.
- **`world_fork`** — набор миров с ценами и участниками.
- **`unresolvable_conflict`** — картины мира side-by-side.
- **`delegation`** — голос одной головы + карта возражений.
- **`polyphony`** — несколько голосов без сведения.
- **`alliance`** — партнёры, действие, разные основания сохранены.
- **`refusal_to_close`** — причина и что было бы разрушено закрытием.

## Универсальные поля вывода
- `conflict_map`
- `minority_positions`
- `unresolved_questions`
- `epistemic_status: candidate`

## Что никогда не показывается пользователю по умолчанию
- Системные промпты (эти файлы).
- Raw chain-of-thought Заратустры.
- API-ключи.
- Полные raw persona utterances (если не `--debug`).

## Скрытая трасса
Пишется в `runs/<run_id>/events.jsonl`. Раскрывается только по флагу
`--debug`.

## Секреты
Никогда не попадают в output. Только через env variables.

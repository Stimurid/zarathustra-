# Argumentation — машина спора

Пакет реализует **исполнимый слой** протокола спора, а не энциклопедию
теории аргументации.

Основной донор — С. И. Поварнин, «Искусство спора» (см.
`corpus/zarathustra/normalized/povarnin_iskusstvo_spora_ru.txt`,
provenance в `corpus/zarathustra/SOURCE_MANIFEST.yaml`).

Дополнительно используются: Toulmin (claim/data/warrant/backing/rebuttal),
Walton (argumentation schemes) — как reference-паттерны, не как обязательный
формализм.

## Что делает

После каждого хода pipeline вызывает `assess_turn(state, argument_map, turns)`
и получает `DisputeAssessment`:

```
dispute_mode:           truth | persuasion | victory
thesis_preserved:       bool
burden_state:           who_carries_burden, whether_shifted
valid_attack:           bool
valid_defence:          bool
fallacies_or_tricks:    [str]
fairness_events:        [str]
required_response_type: attack|defence|restore_ground|refuse|stop
continue_or_stop:       continue | stop
confidence:             0..1
```

Результат идёт в trace и МОЖЕТ влиять на выбор следующей операции
через `Zarathustra._suggest_operation` (через передачу как hint).

## Anti-slop gate

Перед выбором `synthesis` как формы завершения вызывается `check_anti_slop`.
Он блокирует synthesis, если совет не отработал `attack_presupposition` +
`defend` хотя бы по одному тезису.

## Структура

- `manifest.yaml` — идентификатор пакета
- `dispute_modes.yaml` — виды спора (Поварнин)
- `thesis_tracking.yaml` — правила удержания и подмены тезиса
- `attack_defence_operations.yaml` — типы атак и защит
- `burden_rules.yaml` — распределение бремени доказательства
- `fallacies_and_tricks.yaml` — уловки и их обнаружение
- `fairness_policy.yaml` — правила честного спора
- `refusal_and_stopping.yaml` — когда прекратить
- `schemas/dispute_assessment.schema.json`
- `prompts/socratic_question_chain.md`
- `tests/` — юнит-тесты

## Что НЕ делает

- Не строит полную формальную логику аргумента.
- Не заменяет собой Заратустру: даёт только оценку и рекомендацию.
- Не решает за пользователя, победил ли кто в споре.

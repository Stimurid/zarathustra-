# Known defects — v0.3.0

| id | severity | area | detail | fix path |
|----|----------|------|--------|----------|
| D-001 | low | zarathustra | `_topic_guess` берёт первую строку целиком; jailbreak-префикс попадает в топик | пропускать первые N символов, если `assess_input` вернул security event уровня ≥3 |
| D-002 | low | mock model | шаблонные utterances (по дизайну — для детерминированности тестов) | не фиксим; при переключении провайдера uneffected |
| D-003 | medium | validation | dataclasses вместо jsonschema; canon `.schema.json` не проверяются | подключить `jsonschema.validate` в `_validate` шаге pipeline |
| D-004 | medium | affect | runtime affect — только контракт YAML, не реализован в persona turn | добавить `AffectState` в TurnRecord + decay logic |
| D-005 | low | routing | fast-mode берёт 4 из 7 линз; пользователь может ожидать все семь | добавить `--all-voices` CLI флаг + `include_all: true` в mode config |
| D-006 | low | RAG | fixture-корпусы пусты, real vector store не подключён | добавить один pdf/md в тестовый corpus одной fixture, повторить run |
| D-007 | low | conflict_map | side_a/side_b — только persona_id, без цитат claim'ов | обогатить `_derive_conflict_map` цитатами атакующего claim.text |
| D-008 | low | i18n | `Zarathustra._concept_hints` — русско-английский hardcoded regex | вынести в `interaction/concept_keywords.yaml` |
| D-009 | none | telegram | не реализован сознательно | реализуется тонким адаптером при наличии token |
| D-010 | none | feynman | не реализован сознательно (нет API) | реализуется при получении API-документации |
| D-011 | low | affect | AffectBook собирается в runtime, но не влияет на выбор операции Заратустры (только логируется) | добавить hot_personas() как input в route_next в v0.4.0 |
| D-012 | low | chorus | chorus reflection не читает body.futures/premises для более точной температуры | добавить сигнал «тело растёт» в _chorus_suggestion |
| D-013 | none | corpus | Cultural corpus (I) и Nietzschean core (J) отложены | отдельный корпусный проход; см. HANDOFF задача G |

## Не-дефекты (объяснения)

- **«Провайдер по умолчанию mock»** — это дизайн: пакет должен
  запускаться без ключей. Замена одной env-переменной.
- **«Персоны — линзы, не имена реальных людей»** — это каноническое
  требование, не дефект. Реальные семь персон, которые придут, обязаны
  проходить тот же контракт (см. `personas/README.md`).
- **«Синтез не даёт «единой позиции»»** — это тоже дизайн. Group Soul
  Minority Retention Law прямо запрещает создавать ложный консенсус.

# Completion Report — CALIFORNIAN_ID v0.3.0

## Status

**WORKING** — «восьмиголовый Змей» собран: общее тело, 7 функционально
специализированных линз, Заратустра как 8-я голова (SPINE + HEAD в одном
модуле), 10 форм завершения (синтез — только одна из них и не default),
хор трагедии как режим тела, runtime affect.

## What runs now

1. **Общее тело** (`BodyProjection`): каждый ход изменяет `futures`,
   `ontological_premises`, `risks`, `projects`, `transformations`,
   `alliances`, `position_changes`, `voices_history`,
   `chorus_reflections`. Голова получает срез тела перед своим ходом.
2. **7 линз** с `functional_capabilities` (opener / objector /
   cost_seer / horizon_shifter / world_builder / consensus_breaker /
   weak_defender / closer / aporia_maker) — cast приоритезирует их по
   потребностям сцены, не только по topic overlap.
3. **Zarathustra** как 8-я голова в одном модуле с двумя зонами (SPINE:
   deterministic runtime; HEAD: prompt stack из 12 файлов).
4. **21 операция хода** (расширено с 6): включая
   `attack_presupposition`, `test_value`, `shift_temporal_horizon`,
   `shift_ontology`, `build_future_image`, `problematize_question`,
   `create_aporia`, `propose_alliance`, `refuse_alliance`,
   `dispute_completion_form`, `dispute_zarathustra`.
5. **10 форм завершения** с per-form assemblers.
6. **Chorus mode**: каждые 2 хода — тегированная рефлексия сцены
   (температура, кто молчит, сигналы, suggested_next_move).
7. **Runtime affect**: `AffectBook` per persona с decay 0.2/turn.
8. Persona-scoped lexical retrieval, jailbreak/manipulation detection,
   append-only trace, CLI (`validate`, `personas list`, `run`).

## Exact commands

```bash
# from CALIFORNIAN_ID/
python -m pip install pyyaml pytest

PYTHONPATH=src python -m californian_id validate
PYTHONPATH=src python -m californian_id personas list

# fast (5 turns) — decision_with_dissent для чистого вопроса
PYTHONPATH=src python -m californian_id run \
  --text "Свобода индивида или коллективная безопасность?"

# normative → aporia
PYTHONPATH=src python -m californian_id run \
  --text "Стоит ли вводить моратории на разработку продвинутых AI-систем?"

# long-term horizon → world_fork
PYTHONPATH=src python -m californian_id run --mode fast \
  --text "Какое возможно будущее человечества на горизонте century при радикальном long-term ускорении AGI?"

# deep (12 turns, все 7 голосов)
PYTHONPATH=src python -m californian_id run --mode deep \
  --file examples/inputs/life_extension.txt --debug

# tests
PYTHONPATH=src python -m pytest tests/ -v

# real LLM
pip install anthropic
export ANTHROPIC_API_KEY=...
CALIFORNIAN_ID_PROVIDER=anthropic \
  PYTHONPATH=src python -m californian_id run --file examples/inputs/agi_acceleration.txt
```

## Tests

- **passed:** 39
  - `test_pipeline_e2e.py` — 6 e2e
  - `test_completion_forms.py` — 8
  - `test_body_projection.py` — 4
  - `test_functional_casting.py` — 3
  - `test_chorus_and_affect.py` — 6
  - `test_interaction.py` — 3
  - `test_personas.py` — 2
  - `test_state.py` — 2
  - `test_completion_forms.py` (extra) — 5
- **failed:** 0
- **skipped:** 0

## Demo behaviour by scenario (mock provider)

| Scenario                                                              | Form chosen             |
|-----------------------------------------------------------------------|-------------------------|
| «Свобода индивида или коллективная безопасность?»                     | `decision_with_dissent` |
| «Стоит ли вводить моратории на разработку продвинутых AI-систем?»     | `aporia`                |
| «Какое возможно будущее ... на горизонте century при long-term AGI?»  | `world_fork`            |
| Jailbreak + normative                                                 | `aporia` + security_events flagged |

Синтез больше **не выбирается по умолчанию** ни в одном сценарии.

## Persona integration status

7 fixture-линз, каждая с `assignment_prohibited: true`,
`forbidden_uses: [...]`, `functional_capabilities: [...]`. Реальные
семь персон подключаются через `personas/_template/` без изменений в
runtime.

## RAG status

`LexicalPersonaRetriever` (BM25-lite), persona-scoped. Corpus у
fixture-линз пуст (заказчик подключит реальные тексты).

## Feynman / Telegram status

Contract-only, как и в 0.1.0. Ядро от них не зависит.

## Known defects

См. `_work/DEFECTS.md` (обновлён под 0.3.0).

## Missing external dependencies

- `anthropic` / `openai` — только для реального LLM (mock работает).
- Telegram token — только для Telegram binding.
- Vector DB — только при замене lexical fallback.

## Deferred items (по решению заказчика)

- **I** — Cultural Corpus scaffolding (SceneOperationCard из
  Ницше/Платона/Достоевского/Бахтина/Иова/Гиты/…).
- **J** — Nietzschean core как первичный корпус.

Оба ждут отдельного корпусного прохода.

## Next actions

См. `HANDOFF.md`. Приоритетные:
1. Заменить fixture-линзы на реальные семь персон.
2. Подключить реальный LLM провайдер.
3. Начать наполнение Cultural Corpus (item I) карточками сцен.
4. Опционально: Telegram thin binding.

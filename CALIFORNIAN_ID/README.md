# Калифорнийский Ид

**Первый агентный прикладной пакет Тинкуя. v0.3.0 — «восьмиголовый
Змей».**

Не парламент из семи экспертов и внешнего модератора. **Одно общее
изменяющееся тело мысли**, семь идеологических **линз** (не имитаций
живых людей) и восьмая голова **Заратустра** — не идеология, не
арбитр, а режиссёр сцены, регулятор напряжений и **выбирающий одну из
десяти форм завершения**.

На вход — произвольный текст (вопрос / транскрипт / документ).
На выход — форма завершения: `alliance` / `decision_with_dissent` /
`unresolvable_conflict` / `aporia` / `transformed_question` /
`world_fork` / `delegation` / `polyphony` / `synthesis` /
`refusal_to_close` — с сохранёнными конфликтами и меньшинственными
голосами.

- Статус пакета: `candidate` (Пик 1 + Пик 2 + Пик 3 завершены).
- Ядро: Python 3.11+, mock-first — работает без внешних API.
- Тинкуй-совместимость: заимствует контракты (Group Soul Minority
  Retention Law, персон-линза, output status vocabulary,
  jailbreak_and_manipulation policy). Исходные canon-файлы не изменялись.

---

## Архитектура (одним взглядом)

```
                       ОБЩЕЕ ТЕЛО (BodyProjection)
       topic → futures → ontological_premises → risks → projects →
                       transformations → chorus_reflections
                              ↑                       ↓
                        [ voices_history ]     [ argument_map ]

           ┌───────────────────┴───────────────────┐
           │       Zarathustra (8th head)          │
           │  SPINE zone            HEAD zone      │
           │  - scene reading        - identity    │
           │  - functional cast      - cave        │
           │  - routing              - tension     │
           │  - chorus reflection    - narrative   │
           │  - choose_completion    - defense     │
           │  - assemble_completion                │
           └───────────────────────────────────────┘
                              │
              sequential turn assignment (~21 operations)
                              │
    ┌──────┬──────┬──────┬────┴──┬──────┬──────┬──────┐
    v      v      v      v      v      v      v      v
 TRANS  LONG   EFFECTIVE ACCEL RATIONAL LIBER  AI_SAFETY
 HUM   TERMIST ALTRUIST      IST    ONALIST TARIAN
   (7 ideological lenses; sequential, not parallel;
    functional_capabilities: opener / objector / cost_seer /
    horizon_shifter / world_builder / consensus_breaker /
    weak_defender / closer / aporia_maker)
                              │
                              v
                CompletionOutcome (one of 10 forms)
```

**Строго последовательный** внутренний диалог. Каждая голова получает
**срез общего тела**, а не копию исходного ввода. Chorus (греч.
трагедии) каждые 2 хода пишет tag'ированную рефлексию сцены.

**21 операция хода** — `initial_position`, `restore_ground`, `attack`,
`attack_presupposition`, `test_value`, `steelman_opponent`,
`shift_scale`, `shift_temporal_horizon`, `shift_ontology`,
`build_counterexample`, `introduce_absent_subject`, `show_cost`,
`build_future_image`, `draw_practical_implication`,
`problematize_question`, `create_aporia`, `defend`, `propose_alliance`,
`refuse_alliance`, `dispute_completion_form`, `dispute_zarathustra`.

**10 форм завершения** — синтез только одна из них, и не default.

---

## Быстрый запуск

```bash
# from CALIFORNIAN_ID/
python -m pip install pyyaml pytest              # минимальные зависимости
PYTHONPATH=src python -m californian_id validate
PYTHONPATH=src python -m californian_id personas list
PYTHONPATH=src python -m californian_id run --text "Стоит ли ускорять развитие AGI?"
PYTHONPATH=src python -m californian_id run --file examples/inputs/agi_acceleration.txt --mode deep
PYTHONPATH=src python -m californian_id run --file examples/inputs/jailbreak_transcript.txt --debug
```

Никаких API-ключей для запуска не требуется: провайдер по умолчанию —
детерминированный `mock` (см. `config/models.yaml`).

## Реальный LLM

```bash
export ANTHROPIC_API_KEY=...
pip install anthropic
# либо через env override:
CALIFORNIAN_ID_PROVIDER=anthropic python -m californian_id run --text "..."
# либо правкой config/models.yaml roles.persona_turn.provider = anthropic
```

Аналогично `openai` (`pip install openai`, `OPENAI_API_KEY`).

---

## Как заменить fixture-персоны на реальные семь

1. Каждая реальная персона должна быть **линзой** (идеологическая рамка),
   а не имитацией конкретного живого человека — см.
   `personas/README.md` и канонический
   `CULTURAL_PERSONA_LENS_CONTRACT.md`.
2. Скопируйте `personas/_template/` в `personas/<PERSONA_ID>/`.
3. Заполните `manifest.yaml` (обязательные поля см. `persona.schema.json`).
4. Напишите `system_prompt.md`, `values.yaml`, `argumentation.yaml`.
5. Опционально — `corpus/*.md|txt` + `sources/source_manifest.yaml`.
6. Уберите `is_fixture: true` в manifest, статус → `candidate`.
7. `python -m californian_id validate`.

Пока не заменены — runtime работает на семи fixture-линзах (эти линзы
явно помечены `status: test_fixture`).

## Corpus / RAG

Retriever — `LexicalPersonaRetriever` (BM25-lite), scoped **строго** по
`personas/<id>/corpus/`. Кросс-персонных утечек по контракту нет. Если
корпус пуст, retrieval возвращает `[]` (это нормальный fallback).
Замена на векторный backend — через `retrieval.py` (единый интерфейс).

## Тесты

```bash
PYTHONPATH=src python -m pytest tests/ -v
```

**39** unit + integration тестов (Пик 1+2+3), все проходят на
mock-модели без внешних API.

## Host-подключения

- `adapters/cli/` — рабочий CLI (это доказательство запускаемости).
- `adapters/generic_host/` — контракт для любого host: передаёт текст в
  `Pipeline.run(...)`, забирает `PipelineResult`.
- `adapters/telegram/` — backlog + контракт (при появлении Telegram
  skeleton — тонкий binding без изменений в core).
- `adapters/feynman/` — контракт-описание; фиктивной реализации нет
  сознательно (реальный API не найден в локальных файлах).

## Что дальше — см. `HANDOFF.md`

- `_work/AUDIT.md` — что читалось из canon/donors.
- `_work/SOURCE_MAP.md` — конкретные canon-контракты и их адаптации.
- `_work/COMPLETION_REPORT.md` — что запускается, что нет.
- `_work/DEFECTS.md` — известные дефекты и пределы этой сборки.
- `HANDOFF.md` — что должен сделать следующий разработчик.

---

## Каноническое выравнивание (кратко)

| Слой                  | Canon-контракт                                                                    | Локальная адаптация                             |
|-----------------------|-----------------------------------------------------------------------------------|-------------------------------------------------|
| Персоны как линзы     | `CULTURAL_PERSONA_LENS_CONTRACT.md` (assignment_prohibited)                       | `personas/*/manifest.yaml` + `persona.schema.json` |
| Оркестрация           | `world_value_position_narrative_to_group_soul` pipeline archetype                 | `zarathustra/` prompt stack (12 файлов) + `pipeline/pipeline.yaml` |
| Формы завершения      | `GROUP_SOUL_MINORITY_RETENTION_LAW.md` + `GROUP_SOUL_CONFLICT_AND_OPEN_QUESTION_MODEL` | `zarathustra/completion_forms_policy.yaml` + `zarathustra.choose_completion_form/assemble_completion` |
| Jailbreak / role hold | `digital_personality_runtime/communication/jailbreak_and_manipulation_policy.yaml`| `interaction/manipulation_policy.yaml` + `interaction.py` |
| State model           | `digital_personality_runtime/pipeline.yaml` + `state_model` invariants            | `pipeline/state_model.yaml` + `state.py`         |
| Prompt stack          | `digital_personality_runtime/prompts/P00..P06`                                    | `zarathustra/01_identity_and_laws.md` … `12_rhetorical_presentation.md` |
| Body / semantic fabric| `SEMANTIC_UNIT_SCHEMA` + `SCENE_STATE_SCHEMA` (частичная проекция)                | `schemas.BodyProjection` + `_fold_turn_into_body` |
| Affect                | `affect_model.md` + `affect_state_model.yaml`                                     | `affect.py::AffectBook` + `zarathustra/affect_policy.yaml` |
| Chorus                | `NARRATIVE_REGULATOR_PROMPT` (частично) + образец трагического хора               | `zarathustra.chorus_reflect` + `BodyProjection.chorus_reflections[]` |

Никакие файлы `tinkuy canon/` этой сборкой не изменялись.

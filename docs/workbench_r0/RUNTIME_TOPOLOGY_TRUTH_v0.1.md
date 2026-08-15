# RUNTIME_TOPOLOGY_TRUTH v0.1

**Дата:** 2026-08-15 · Источники: `data/pipeline/pipeline.yaml`, реальный call-graph `pipeline.py`, трасса `runs/<run_id>/events.jsonl` реального прогона, capture-провайдер, retrieval-события.

---

## 0. Разрешение WB-015

В отчёте Stage 2 было противоречие. **Прав оказался ни один из двух вариантов.**

- `WB-015` утверждал `analyze_situation → retrieval` — верно только наполовину.
- Stage 2 evidence показывал `RAGProfile → retrieval → analyze_situation` — **неверно**, это был harness-порядок.

Установленная истина по коду:

```
Pipeline.run()
  analyze_situation                       (pipeline.py:412)  ← единственный раз
  cast / select_initial_voice             (pipeline.py:440)
  for turn in range(max_turns):           ← цикл совета
      route_next
      evidence_retrieval                  (pipeline.py:545)
      cultural_context                    (pipeline.py:561)
      persona_turn  ← ПОТРЕБИТЕЛЬ ОБОИХ   (pipeline.py:575)
      assess_turn / checkpoint
  synthesize → validate_output → persist_trace
```

Извлечение идёт **после** чтения сцены (её `topic` служит запросом) и **перед** ходом персоны, чей вызов принимает `evidence=` и `cultural_cards=`. `analyze_situation` не потребляет извлечение вообще.

## 1. Таблица узлов

| node_id | declared_in_pipeline | actual_runtime_entrypoint | input → output | kind | topology_status |
|---|---|---|---|---|---|
| `intake` | да, шаг 1 | `Pipeline.run` | — → RawInput | STORE | MATCH |
| `normalize_input` | да, шаг 2 | `Pipeline.run` | RawInput → NormalisedText | DETERMINISTIC | MATCH |
| `analyze_situation` | да, шаг 3 | `pipeline.py:412` → `zarathustra.py:174` | NormalisedText → SituationAnalysis | MODEL_CALL | MATCH |
| `load_persona_registry` | да, шаг 4 | `Pipeline.run` | — → PersonaRegistry | STORE | MATCH |
| `validate_personas` | да, шаг 5 | внутри загрузки реестра | — | DETERMINISTIC | DECLARATION_DRIFT |
| **`retrieve_initial_context`** | **да, шаг 6** | **отсутствует** | — | RAG | **DEAD_DECLARATION** |
| `select_initial_voice` | да, шаг 7 | `pipeline.py:440` | SituationAnalysis → SelectedPersonas | HYBRID | DECLARATION_DRIFT |
| `route_next` | внутри `run_inner_council` | `pipeline.py:~500` | RunState → RoutingDecision | ROUTER | MATCH (в цикле) |
| **`evidence_retrieval`** | **нет** | **`pipeline.py:545`** | topic → EvidenceChunk[] | RAG | DECLARATION_DRIFT |
| **`cultural_context`** | **нет** | **`pipeline.py:561`** | topic+operation+persona → RetrievedCard[] | RAG | MATCH (не объявлен) |
| `persona_turn` | внутри `run_inner_council` | `pipeline.py:575` | EvidenceChunk[]+RetrievedCard[] → TurnRecord | MODEL_CALL | MATCH |
| `assess_turn` | нет | `argumentation.py:138` | TurnRecord → DisputeAssessment | DETERMINISTIC | MATCH |
| `checkpoint` | нет | `runtime_control.py:294` | RunState → RunState | HUMAN_GATE | MATCH |
| `synthesize` | да, шаг 10 | `pipeline.py:691` → `zarathustra.py:857` | RunState → Completion | MODEL_CALL | MATCH |
| `validate_output` | да, шаг 11 | `pipeline.py:1636` | Completion → RunState | DETERMINISTIC | MATCH |
| `persist_trace` | да, шаг 12 | `runs/<id>/events.jsonl` | RunState → Trace | STORE | MATCH |

**Три расхождения декларации и рантайма:**

1. `retrieve_initial_context` объявлен отдельным шагом перед кастингом — такого шага рантайм не делает. Реальное извлечение — per-turn, внутри цикла.
2. `cultural_context` исполняется трижды за прогон, но в `pipeline.yaml` не упомянут вовсе.
3. `select_initial_voice` объявлен после извлечения, а исполняется сразу после чтения сцены.

## 2. Три слоя в проекции

`NodeProjection` и `EdgeProjection` получили поля `layer` и `topology_status`:

- **`ACTUAL_RUNTIME`** — то, что исполняется. Только эти узлы попадают в полевые проекции и в телеметрию.
- **`DECLARED_PIPELINE`** — `retrieve_initial_context` и ребро к нему. Рисуется отдельным слоем, никогда как production-ребро.
- **`TEST_HARNESS`** — зарезервировано; harness-прогон (`start_run`) помечен иначе, чем production (`start_production_run` с полем `kind: PRODUCTION_RUNTIME_VALIDATION` и `entrypoint`).

Цикл совета нарисован как цикл: ребро `checkpoint → route_next` существует, поэтому число рёбер больше числа узлов минус один. Тест, ранее проверявший `edges == nodes-1`, заменён на проверку связности и наличия петли.

## 3. Доказательства из трассы

Реальный прогон `Pipeline.run` с mock-провайдером даёт в `events.jsonl`:

```
run_started 1 · situation 1 · cast 1 · provider_selection 1
route 5 · cultural_context_injected 5 · cultural_retrieval 5
turn 5 · dispute_assessment 5 · architectonic_delta 5
chorus 2 · completion_choice 1 · closing_speech 1 · completion 1 · run_completed 1
```

`situation` один раз, `cultural_context_injected` и `turn` — по пять: извлечение и ход персоны идут парами внутри цикла. Это прямое подтверждение таблицы выше.

## 4. Следствие для Stage 2

Прежняя цепочка `retrieval → analyze_situation` перемаркирована как **`HARNESS_VALIDATION`**: она доказывала работу RAG-воркбенча, но не порядок продукта. Новая цепочка через `Pipeline.run` помечена **`PRODUCTION_RUNTIME_VALIDATION`** и идёт в реальном порядке, с реальным потребителем `persona_turn`.

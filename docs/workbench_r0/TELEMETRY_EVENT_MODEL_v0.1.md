# TELEMETRY_EVENT_MODEL v0.1

Реализация: `WorkbenchService._node_executions` · источник: `runs/<run_id>/events.jsonl` реального прогона + наблюдения резолвера

---

## 1. Принцип

Телеметрия проецируется **из собственной трассы продукта**, а не измеряется параллельно. Каждая запись несёт поле `evidence` вида `trace.<kind>` — имя события, из которого она получена. Ничего не досочиняется.

## 2. node_execution

```yaml
node_execution:
  run_id:
  node_id:
  node_kind:            MODEL_CALL | RAG | DETERMINISTIC | ROUTER | HUMAN_GATE | STORE
  turn_index:           для узлов внутри цикла совета

  input_object_ids:     [] — что вошло
  output_object_ids:    [] — что вышло (для RAG это chunk_id)

  prompt_binding:       из RunConfigurationSnapshot или null
  rag_binding:          из RunConfigurationSnapshot или null
  model_binding:        {provider, grade}
  algorithm_binding:    {} специфичное для узла

  effective_top_k:      что резолвер реально отдал рантайму
  retrieved_chunks:
  retrieval_candidates:
  input_tokens / output_tokens / context_tokens:
  bytes_in / bytes_out:
  retries:
  cache_state:

  cost:
    value:              null
    currency:           null
    evidence_grade:     UNKNOWN
    note:               "pricing profile отсутствует в этом рантайме"

  evidence:             trace.<kind>
```

## 3. Стоимость не выдумывается

Ценовой таблицы в рантайме нет, поэтому `cost.value = null`, `evidence_grade = UNKNOWN`. `ESTIMATED` появится только вместе с явным `pricing_profile` и его версией. Тест `test_cost_is_unknown_not_invented` фиксирует это.

Токены на LLM-узлах в mock-режиме не измеряются провайдером — поля остаются `null`, а не заполняются оценкой. Оценкой (`ESTIMATED`) помечены только контекстные токены RAG, которые считаются как `len/3.5`.

## 4. edge_telemetry

Описывает **фактически переданный объект**, а не абстрактную связь:

```yaml
edge_telemetry:
  edge_id:        cultural_context->persona_turn
  turn_index:
  object_type:    RetrievedCard[]
  object_ids:     [CARD_…, CARD_…]
  chunk_count:
  hash:           sha256[:24] от упорядоченных идентификаторов
  bytes / tokens: null, если рантайм их не даёт
  grade:          MEASURED | UNKNOWN
```

Разрешённое ребро — только то, что признано реальным в `RUNTIME_TOPOLOGY_TRUTH_v0.1`: `cultural_context → persona_turn`. Ребра `retrieval → analyze_situation` не существует, и телеметрия его не рисует.

## 5. Пример из реального прогона

```
analyze_situation   MODEL_CALL   RawInput → SituationAnalysis
                    prompt_binding=zarathustra.03_scene_reading  evidence=trace.situation
cultural_context×5  RAG          effective_top_k=5  chunks=5
                    rag_binding=rag.cultural_cards.<candidate>   evidence=trace.cultural_context_injected
persona_turn×5      MODEL_CALL   [EvidenceChunk[], RetrievedCard[]] → TurnRecord
                    prompt_binding=zarathustra.05_move_assignment  evidence=trace.turn
assess_turn×5       DETERMINISTIC TurnRecord → DisputeAssessment  evidence=trace.dispute_assessment
```

Число RAG-исполнений равно числу ходов — прямое следствие того, что оба извлечения живут внутри цикла совета.

## 6. Оверлей на графе

На узлах: для RAG — `chunks returned/considered`, `ctx tokens` (ESTIMATED), `bytes` (MEASURED), `latency`, версия профиля; для MODEL — токены, латентность, провайдер, префикс `compiled_hash`. Пилюли раскрашены по градации: зелёные MEASURED, жёлтые ESTIMATED. На ребре — число чанков, байты и префикс `context_identity`.

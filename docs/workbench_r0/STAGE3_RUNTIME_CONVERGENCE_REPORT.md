# STAGE3_RUNTIME_CONVERGENCE_REPORT

**Дата:** 2026-08-15 · repo `Stimurid/zarathustra-.git`, branch `main`, HEAD `a72ae99` · baseline тестов на входе: 419 passed / 1 skipped

---

## T1 — Реальная топология · CLOSED

Противоречие WB-015 разрешено по коду и трассе: **прав не был ни один из двух вариантов**. Полная таблица — в [RUNTIME_TOPOLOGY_TRUTH_v0.1.md](RUNTIME_TOPOLOGY_TRUTH_v0.1.md).

Главное: `retrieve_initial_context` объявлен в `pipeline.yaml` отдельным шагом, но **рантайм такого шага не исполняет** — `DEAD_DECLARATION`. Реальное извлечение per-turn (`pipeline.py:545`, `:561`), его потребитель — `persona_turn`, а не `analyze_situation`. `cultural_context` исполняется 5 раз за прогон и в декларации не упомянут вовсе.

Проекция получила слои `ACTUAL_RUNTIME` / `DECLARED_PIPELINE` / `TEST_HARNESS` и статусы `MATCH` / `DECLARATION_DRIFT` / `DEAD_DECLARATION`. Harness-ребро никогда не рисуется как production-ребро; цикл совета нарисован циклом.

## T2 — RAGProfile управляет продакшн-рантаймом · CLOSED

**Найден настоящий дефект:** Workbench менял `top_k` только в собственном обходном вызове, а `pipeline.py` нёс литерал `top_k=2` в пяти местах.

Исправление behaviour-preserving: введён шов `californian_id/runtime_bindings.py`. Без установленного резолвера каждый вызов возвращает дефолт вызывающего — поведение байт-в-байт прежнее (`test_seam_is_behaviour_preserving_without_a_resolver`). Сбойный резолвер не может сломать прогон. Второй реализации извлечения не создано.

Доказательство через **обычную публичную точку входа** `Pipeline.run`:

```
RUN1  entrypoint=californian_id.pipeline.Pipeline.run  status=COMPLETED  turns=5
      effective top_k(cultural_cards) = 2   source=rag.cultural_cards.baseline:retrieval  pinned=True
      effective top_k(persona_lexical) = 2

activate candidate (top_k=5)

RUN2  effective top_k(cultural_cards) = 5   profile=rag.cultural_cards.<candidate> v0.1.1
      effective top_k(persona_lexical) = 2  (профиль другого движка не тронут)
      snapshot_id ≠ snapshot_id(RUN1)
```

15 обращений резолвера за прогон, каждое записано с источником разрешения.

## T3 — Теневые пути · CLOSED

Регрессия `NO_SHADOW_RUNTIME_PATHS`:

- ядро не содержит собственной реализации BM25, токенизатора, чанкера, парсера, класса `Pipeline` или ретривера (regex-скан по исполняемому коду, не по docstring);
- адаптер обязан делегировать: `CulturalIndex.retrieve_cards`, `LexicalPersonaRetriever.retrieve`, `_json_from_text`, `z.analyze_situation`, `z.prompt`, `Pipeline.run` — все проверяются присутствием в исходнике;
- `start_production_run` не вызывает harness-хелперов (`run_retrieval`, `run_smoke`, `retrieval_test`, `compile`) — проверяется по AST;
- во всём Workbench существует ровно одна реализация retrieval — ноль функций `def retrieve*` в `workbench_core` и `workbench_adapters`.

**Собственный тест инварианта поймал нарушение:** `start_production_run` импортировал `californian_id.runtime_bindings` прямо в ядре. Установка резолвера вынесена в адаптер (`bind_runtime_resolver` / `unbind_runtime_resolver`) — ядро снова не знает ни одной ветки.

## T4 — Единый снимок конфигурации · CLOSED

`RunConfigurationSnapshot` объединяет pipeline, prompt, rag, model, algorithm, orchestration и contract привязки. Подробности — в [RUN_CONFIGURATION_SNAPSHOT_v0.1.md](RUN_CONFIGURATION_SNAPSHOT_v0.1.md). Инвариант «активация после старта не меняет прогон» доказан на закреплённом резолвере. `model_bindings` покрыты частично и честно помечены `resolved_at_call_time`.

## T5 — Словарь вердиктов · CLOSED

`NO_REGRESSION_ON_DECLARED_FIXTURE` удалён как слишком сильный. Введены структурные вердикты (`IDENTICAL`, `BASELINE_PREFIX_PRESERVED`, `BASELINE_SET_PRESERVED`, `SUPERSET`, `SUBSET`, `RANK_CHANGED`, `SOURCE_COVERAGE_CHANGED`, `CONTEXT_EXPANDED`, `CONTEXT_REDUCED`), downstream-вердикты и `QUALITY_*`.

`QUALITY_BETTER/WORSE` не выдаются никогда без объявленной истины. Для случая 2→5 честный набор:

```
BASELINE_PREFIX_PRESERVED · SUPERSET · CONTEXT_EXPANDED · QUALITY_UNKNOWN
```

## T6 — Сходимость телеметрии · CLOSED

Единая проекция `node_execution` + `edge_telemetry`, целиком из трассы продукта. Стоимость — `UNKNOWN`, поскольку ценовой таблицы нет. Модель — в [TELEMETRY_EVENT_MODEL_v0.1.md](TELEMETRY_EVENT_MODEL_v0.1.md).

## T7 — Stage 2 переподтверждён на реальной топологии · CLOSED

```
Pipeline.run (обычная точка входа)
  → analyze_situation                      (один раз)
  → цикл: route_next → cultural_context (top_k=5 из активного профиля)
                     → persona_turn (потребитель)
                     → assess_turn
  → RunConfigurationSnapshot зафиксирован на старте
  → RunTrace: node_executions + edge_telemetry
```

Прежнее доказательство Stage 2 перемаркировано как `HARNESS_VALIDATION`, новое — `PRODUCTION_RUNTIME_VALIDATION`. Это не обесценивает RAG-воркбенч: он работал, но проверялся не в порядке продукта.

```
STAGE_2 = ACCEPTED_CANDIDATE
```

## T8 — Гейт Сократа

См. раздел 7 итогового отчёта: материализацию подтвердить не удалось → **Branch B**.

## Тесты

Вход: 419 passed / 1 skipped. Выход: **456 passed / 1 skipped**, +37 новых, ноль регрессий. Новые файлы: `test_t2_production_binding.py` (12), `test_t6_t7_topology_and_telemetry.py` (11), `test_stage4b_whitecrow_projection.py` (14). Live-провайдер остаётся отдельным гейтом и не симулируется.

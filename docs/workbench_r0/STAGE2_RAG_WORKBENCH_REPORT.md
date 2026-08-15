# STAGE2_RAG_WORKBENCH_REPORT

**Дата:** 2026-08-15 · repo `Stimurid/zarathustra-.git`, branch `main`, HEAD `a72ae99`

Цель стадии: сделать извлечение таким же управляемым объектом, каким Stage 1 сделал генерацию — не смешивая семантику двух классов ткани.

---

## 1. Что создано

| Модуль | Назначение |
|---|---|
| `src/workbench_core/rag.py` | `RAGProfile`, `RAGParameter`, `MissingCapability`, `RetrievalEvent`, `RetrievalCandidate`, лента состояний RAG, `explain_candidate`, `compare_retrieval`, градации достоверности |
| `src/workbench_core/store.py` (+) | хранение профилей, привязок движков, `retrieval_events.jsonl`, `drift_waivers.json`, `rejections.jsonl` |
| `src/workbench_core/service.py` (+) | `bootstrap_rag`, `rag_view`, `clone_rag`, `update_rag`, `validate_rag`, `retrieval_test`, `compare_rag`, `explain_chunk`, `accept_rag`, `activate_rag`, `rollback_rag`, RAG в `start_run` |
| `src/workbench_adapters/zarathustra_adapter.py` (+) | перепись параметров двух движков, baseline-профили, фикстуры, инструментированный `run_retrieval` |
| `src/workbench_api/server.py` (+) | 9 RAG-эндпоинтов |
| `workbench_ui/src/components/RagPanel.tsx` | инспектор RAG: параметры, NOT_IMPLEMENTED, факты, «почему этот чанк», сравнение, жизненный цикл |
| `workbench_ui/src/components/PromptEditor.tsx` | CodeMirror 6 (C2) |
| `workbench_ui/qa/ui_smoke.mjs` | headless UI-приёмка (C5) |

Изменённые точки рантайма — только наблюдение и кеш: `CaptureClient.provider` (WB-010), `Zarathustra.invalidate_prompt_cache`. Семантика извлечения не тронута; регрессия `test_07` это фиксирует.

## 2. Инвариант зависимостей

```
workbench_core        ✗ californian_id.*  ✗ zarathustra.*  ✗ socrates.*
workbench_adapters.*  ✓ workbench_core    ✓ своя ветка
```

Проверяется AST-сканированием в `test_dependency_invariant.py` (14 тестов) и дополнительно для RAG-кода в `test_12_core_stays_branch_independent_including_rag`.

## 3. Два класса ткани не смешаны

| | Prompt / Generation | RAG / Retrieval |
|---|---|---|
| актив | `PromptAsset` + `PromptVariant` | `RAGProfile` |
| гейты | STATIC_VALIDATE → **COMPILE** → SMOKE | STATIC_VALIDATE → **RETRIEVAL_TEST** → DOWNSTREAM_SMOKE |
| идентичность | `source_hash` + `compiled_hash` | `source_hash` профиля + `context_identity` |
| защита | protected regions, intent-гейт | protected contracts, contract_version |
| редактор | CodeMirror с областями | типизированная конфигурация, без текстового редактора |
| provenance | `source_map`, 100 % покрытие | `RetrievalEvent` с градациями |

Узел `cultural_context` отдаёт RAG-инспектор и **не** отдаёт редактор промпта (`test_14`), детерминированный `assess_turn` не отдаёт ни того, ни другого (`test_13`).

## 4. Телеметрия на графе

Из последнего прогона, только измеренное или явно помеченное:

- **RAG-узлы:** `chunks returned/considered`, `ctx tokens` (ESTIMATED), `bytes` (MEASURED), `latency ms`, версия профиля.
- **MODEL-узлы:** `tokens in/out`, `latency`, провайдер, префикс `compiled_hash`.
- **Ребро RAG → MODEL:** число чанков, байты, префикс `context_identity`.

Пилюли раскрашены по градации: зелёные — MEASURED, жёлтые — ESTIMATED. Скриншот `15_telemetry_overlay.png`.

Фактические значения на снимке: `Культурные карты` — `chunks 2/37 · ctx 46t · 250B · 82ms · v 0.1.0`; `Извлечение контекста` — `chunks 0/0 · ctx 0t · 0B · 2ms` (пустые корпуса); `Чтение сцены` — `in/out 506/308 · 1ms · stub · hash be013758`.

## 5. Сквозная цепочка

```
RAGProfile rag.cultural_cards.74a80d24 (v0.1.1, top_k=5)
  └─ ACTIVE через ActivationBinding, revision N
     └─ start_run wbrun_ad3f7b589fe1 берёт снимок активации
        ├─ RAG: CulturalIndex.retrieve_cards(query="сцена спор истина", top_k=5)
        │    5 карт из 37 · ранги 1..5 · score 3.99 … 2.37
        │    chunk_hash 9339902e…, 7d93338f…, …
        │    context_identity = ctx:0c7dd7c57b16686dce0d2e85
        │    RetrievalEvent → retrieval_events.jsonl (run_id связан)
        └─ MODEL: analyze_situation под тем же снимком
             variant v_baseline_baseline_file, source_hash 9e17b536…
             compiled_hash sha256:be013758…, profile tinkuy.zarathustra.lazy
        └─ RunTrace: rag_snapshot + activation_snapshot + обе ноды
```

`test_16` сверяет состав и порядок чанков между событием и трассой; `test_17` пересчитывает `context_identity` независимо.

## 6. Тесты

| Файл | Тестов |
|---|---|
| `test_stage2_rag.py` | 25 |
| `test_c1_drift_fingerprint.py` | 15 |
| `test_c2_protected_regions.py` | 6 |
| `test_c3_smoke_levels.py` | 6 + 1 skip |
| `test_c4_activation_isolation.py` | 4 |
| `test_vertical_slice.py` | 31 |
| `test_prompt_extraction_golden.py` | 37 |
| `test_dependency_invariant.py` | 14 |

**Итого по проекту: 419 passed, 1 skipped.** Пропуск — `LIVE_ACCEPTANCE_SMOKE`, `EXTERNAL_BLOCKER` (нет ключей провайдера), PASS не симулируется.

## 7. Чего Stage 2 сознательно не делает

Не добавлены ре-ранкер, диверсификация, пороги схожести, бюджеты, переписывание запроса, эмбеддинги — они помечены `NOT_IMPLEMENTED` и не имеют фиктивных значений. Не начаты Google Docs, полевые проекции WhiteCrow, полный адаптер Сократа, переписывание фронтенда. Наполнение корпусов персон — продуктовое решение, а не задача Workbench.

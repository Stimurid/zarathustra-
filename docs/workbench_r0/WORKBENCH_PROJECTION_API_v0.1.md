# WORKBENCH_PROJECTION_API v0.1

**Дата:** 2026-08-15 · Только чтение. Дисциплина заимствована у `litops/web/visual_data.py`: «no mutation, no registry writes, no file writes».

Базовый префикс: `/api/workbench`. Аутентификация — существующая JWT-схема Тинкуя (`web_ui.py`, `jwt_auth.py`).

---

## 0. Инварианты

1. **Все эндпоинты этого документа — read-only.** Мутации (сохранение варианта, активация) вынесены в отдельный контракт и в R1 не специфицируются.
2. **Измеренное отделено от оценённого.** Любое число несёт `"measured": true|false`. Оценки помечаются `"estimated": true` и никогда не записываются обратно как конфигурация.
3. **Никакого домысливания графа.** Узлы и рёбра строятся только из `pipeline.yaml`, `PROMPT_DEPENDENCY_MAP.yaml` и фактических событий трассы. Если узел не исполнялся — он `state: "not_executed"`, а не отсутствует.
4. **Типы преобразований различимы.** `kind` обязателен и не может быть `prompt` по умолчанию.

---

## 1. Пайплайн и подграф

### `GET /api/workbench/pipelines`

```json
{"pipelines": [
  {"pipeline_id": "californian_id.inner_council", "version": "0.1.0",
   "status": "candidate", "branch": "tinkuy_core",
   "entrypoints": ["cli", "web"], "steps_count": 13}
]}
```

### `GET /api/workbench/pipeline/{pipeline_id}/graph`

Параметры: `?entrypoint=cli&input_mode=raw&runtime_layer=californian_id&run_id=<optional>`

Селекторы ветки (`input_mode`, `runtime_layer`) **меняют топологию**, а не подсвечивают её. Без `run_id` возвращается статический граф, с `run_id` — фактически исполненный.

```json
{
  "pipeline_id": "californian_id.inner_council",
  "resolved_for": {"input_mode": "raw", "runtime_layer": "californian_id"},
  "nodes": [
    {"node_id": "analyze_situation",
     "label": "Чтение сцены",
     "kind": "MODEL_CALL",
     "implementation": "zarathustra.analyze_situation",
     "source_ref": "src/californian_id/zarathustra.py:238",
     "prompt_asset_id": "zarathustra.03_scene_reading",
     "active_variant_id": "v_baseline_0_2_0",
     "rag_profile_id": null,
     "input_contract": null,
     "output_contract": "schemas.SituationAnalysis",
     "contract_status": "MISMATCH",
     "state": "executed",
     "params": [{"id": "CALIFORNIAN_ID_SITUATION_MAX_CHARS", "class": "E", "value": 100000}]
    },
    {"node_id": "assess_turn", "kind": "DETERMINISTIC",
     "implementation": "argumentation.assess_turn",
     "source_ref": "src/californian_id/argumentation.py:138",
     "prompt_asset_id": null,
     "output_contract": "data/argumentation/schemas/dispute_assessment.schema.json",
     "contract_status": "OK"},
    {"node_id": "retrieve_initial_context", "kind": "RAG",
     "rag_profile_id": "tinkuy.persona_scoped_bm25",
     "prompt_asset_id": null},
    {"node_id": "route_next", "kind": "ROUTER",
     "prompt_asset_id": "zarathustra.04_head_calling"},
    {"node_id": "checkpoint", "kind": "HUMAN_GATE",
     "implementation": "runtime_control.wait_if_paused"},
    {"node_id": "persist_trace", "kind": "STORE"},
    {"node_id": "select_initial_voice", "kind": "HYBRID",
     "note": "prompt-composed persona assets + deterministic routing overlap"}
  ],
  "edges": [
    {"edge_id": "analyze_situation→select_initial_voice",
     "from": "analyze_situation", "to": "select_initial_voice",
     "carries": "SituationAnalysis",
     "transform": null}
  ]
}
```

`kind` ∈ `PROMPT | MODEL_CALL | DETERMINISTIC | RAG | ROUTER | STORE | HUMAN_GATE | HYBRID`.

`contract_status` ∈ `OK | MISMATCH | UNDECLARED | INCOMPATIBLE`.

---

## 2. Инспектор узла и ребра

### `GET /api/workbench/node/{node_id}`

Прообраз — `visual_data.build_inspector()` + двенадцать `_inspect_*` резолверов WhiteCrow.

```json
{
  "node_id": "analyze_situation",
  "kind": "MODEL_CALL",
  "operation": "структурная реконструкция входа",
  "prompt": {
    "asset_id": "zarathustra.03_scene_reading",
    "active_variant_id": "v_baseline_0_2_0",
    "variants_count": 1,
    "compiled_hash": "sha256:…",
    "baseline_fallback_ref": "zarathustra._DEFAULT_SCENE_READING_PROMPT"
  },
  "rag_profile": null,
  "model_profile": {"role": "zarathustra_situation_reading", "preset": "fast", "model": "…"},
  "contracts": {
    "input_schema_ref": null,
    "output_schema_ref": "schemas.SituationAnalysis",
    "declared_fields": 9, "prompt_fields": 17, "consumed_fields": 7,
    "status": "MISMATCH",
    "detail": "10 полей запрошены промптом и не читаются потребителем"
  },
  "params": [
    {"id": "CALIFORNIAN_ID_SITUATION_MAX_CHARS", "class": "E",
     "value": 100000, "range": [1000, 200000], "authority": "env", "runtime_mutable": false}
  ],
  "protected_regions": [{"name": "output_json_contract", "reason": "потребитель парсит эти ключи"}],
  "recent_runs": [{"run_id": "run_…", "at": "…", "tokens_in": 4210, "tokens_out": 380,
                   "latency_ms": 2140, "measured": true}],
  "validation": {"static": "not_run", "contract": "MISMATCH", "smoke": "not_run"},
  "provenance": {"donor": null, "canon_refs": ["canon/…"], "version": "0.2.0"},
  "warnings": ["contract_mismatch", "no_variants_besides_baseline"]
}
```

### Гибриды — обязательная секция

Для узлов и контролов с несколькими эффектами инспектор **обязан** отдавать `effects[]`. Пустой `effects[]` при известном гибриде считается провалом приёмки.

```json
{
  "control": {"id": "critique_regime", "label": "Critique Regime", "value": "hard",
              "semantics": "единый пользовательский режим, не расщепляется"},
  "effects": [
    {"class": "PROMPT_BEHAVIOR", "target": "regimes.CritiqueRegime.directness_hint",
     "resolved_value": "Критикуй жёстко: …", "consumers": ["persona_turn"],
     "source_ref": "src/californian_id/regimes.py:32"},
    {"class": "DETERMINISTIC_ALGORITHM", "target": "regimes.CritiqueRegime.attack_bias",
     "resolved_value": 0.8, "consumers": ["router_scoring"],
     "source_ref": "src/californian_id/regimes.py:35"}
  ]
}
```

То же для `variation_regime` и для приёмочной фикстуры **V054**:

```json
{"asset_id": "persona.LENS_RATIONALIST.position_model",
 "effects": [
   {"class": "PROMPT_BEHAVIOR", "target": "persona turn composition",
    "consumers": ["persona_turn"]},
   {"class": "DETERMINISTIC_ALGORITHM", "target": "routing.topics/tensions overlap",
    "consumers": ["select_initial_voice", "zarathustra.cast"],
    "source_ref": "src/californian_id/zarathustra.py:294"}
 ]}
```

### `GET /api/workbench/edge/{edge_id}`

Та же структура, плюс `carries` (объект, пересекающий границу) и `transform` (ассет, если ребро несёт преобразование).

---

## 3. Промпт-ассет

- `GET /api/workbench/asset/{asset_id}` — карточка ассета по модели `WORKBENCH_ASSET_MODEL_v0.1`.
- `GET /api/workbench/asset/{asset_id}/variants` — список вариантов с `state`, `version`, `source_hash`, `usage`.
- `GET /api/workbench/asset/{asset_id}/variant/{variant_id}/source` — **SOURCE VIEW**: текст исходника + разметка `protected_regions` / `editable_regions`.
- `GET /api/workbench/asset/{asset_id}/variant/{variant_id}/compiled?profile_id=…` — **COMPILED VIEW**: `system_text`, `user_template`, `token_count`, `compiled_hash`, `source_map[]`.
- `GET /api/workbench/asset/{asset_id}/diff?base={vid}&candidate={vid}` — построчный diff исходника и diff скомпилированного вида.
- `GET /api/workbench/pack/{pack_id}` — `PromptPack` (для `prompt_stack` Заратустры).

---

## 4. Контракты

- `GET /api/workbench/contract/{schema_ref}` — JSON Schema.
- `GET /api/workbench/contract/check?asset_id=…&variant_id=…` — статический отчёт совместимости: объявленные поля, поля промпта, потребляемые поля, расхождения, затронутые соседи по `depends_on`.

---

## 5. Телеметрия

`GET /api/workbench/telemetry?scope=node|asset|variant|run&id=…&window=…`

```json
{"scope": "node", "id": "analyze_situation",
 "metrics": {
   "runs": {"value": 214, "measured": true},
   "tokens_in": {"value": 903_112, "measured": true},
   "tokens_out": {"value": 81_440, "measured": true},
   "cost_usd": {"value": 12.4, "measured": false, "estimated": true,
                "basis": "tokens × price_table@2026-08-01"},
   "latency_ms_p50": {"value": 2140, "measured": true},
   "errors": {"value": 3, "measured": true},
   "retries": {"value": 1, "measured": true},
   "bytes_in": {"value": 4_120_338, "measured": true}
 },
 "source": "runs/*/events.jsonl", "window": "30d"}
```

**Что придётся добавить в рантайм, чтобы это заработало** (append-only, без изменения поведения):

| Поле | Сейчас | Нужно |
|---|---|---|
| `tokens_in/out` на узел | нет | эмитить из `models.build_client` результата |
| `latency_ms` на узел | нет | обёртка вокруг `client.generate` |
| `compiled_hash` | нет | пишет компилятор |
| retrieval-события | нет | `score`, `locator`, `chunk_hash` уже вычисляются в `retrieval.py` / `cultural_rag.py` |

---

## 6. Трасса прогона

- `GET /api/workbench/run/{run_id}/trace` — существующий `events.jsonl`, нормализованный по узлам графа.
- `GET /api/workbench/run/{run_id}/node/{node_id}` — вход, выход, промпт-вариант, `compiled_hash`, извлечённые чанки, метрики.
- `GET /api/workbench/run/{run_id}/retrieval/{node_id}` — **объяснимость RAG**:

```json
{"query": "…", "profile_id": "tinkuy.persona_scoped_bm25",
 "returned": [
   {"locator": "CHUNK=nietzsche_zarathustra#42", "chunk_hash": "a1b2…",
    "score": 7.31, "rank": 1, "persona_scope": "LENS_RATIONALIST",
    "included_in_prompt": true, "chars_contributed": 800}
 ],
 "config_snapshot": {"top_k": 3, "chunk_size": 800, "overlap": 200, "k1": 1.5, "b": 0.75},
 "explanation_available": true}
```

- `GET /api/workbench/run/compare?base={run_id}&candidate={run_id}` — сравнение baseline и кандидата.

---

## 7. Минимальный набор для Stage 1

Из перечисленного для первого вертикального среза обязательны только шесть:

1. `GET /pipeline/{id}/graph`
2. `GET /node/{node_id}`
3. `GET /asset/{asset_id}` + `/variants`
4. `GET /asset/{id}/variant/{vid}/source` и `/compiled`
5. `GET /contract/check`
6. `GET /run/{run_id}/node/{node_id}`

Остальное — Stage 2 и далее.

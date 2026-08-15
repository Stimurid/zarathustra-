# WORKBENCH_ASSET_MODEL v0.1

**Дата:** 2026-08-15 · **Метод:** обобщение существующих моделей, а не проектирование с нуля.

Две работающие модели промпт-ассета уже существуют: WhiteCrow `prompt_bodies/registry.yaml` + `activation_policy.yaml` и Tinkuy `data/zarathustra/PROMPT_DEPENDENCY_MAP.yaml` + `manifest.yaml`. Модель Workbench — их обобщение плюс недостающее.

---

## 1. Кроссуок трёх моделей

Легенда: **KEEP** — сохранить имя и семантику · **RENAME** — та же семантика, другое имя · **GENERALIZE** — расширить область действия · **SPLIT** — разделить на несколько полей · **ADD** — нового не было нигде

### 1.1. Идентичность и расположение

| WhiteCrow | Tinkuy | Workbench | Действие | Обоснование |
|---|---|---|---|---|
| `prompt_id` | `id` (в dependency map) | `asset_id` | **RENAME** | `prompt_id` уже занят под конкретный файл; нужна стабильная идентичность ассета, переживающая переименование файла |
| `path` | путь в `prompt_stack` | `source_path` | KEEP | |
| `category` (00–09) | — | `category` | KEEP | WhiteCrow-категории обобщаются в свободный namespace |
| `organ_id` | `agent_id` (`HEAD_ZARATHUSTRA`) | `owner_id` | **GENERALIZE** | «орган» у WhiteCrow и «агент/голова» у Тинкуя — одна роль: владелец ассета |
| `template_family` | — | `template_family` | KEEP | |
| `operation_class` | `purpose` | **SPLIT** → `operation_class` + `purpose` | **SPLIT** | машинный класс операции и человеческое назначение — разные вещи; у WhiteCrow первое, у Тинкуя второе |
| — | `used_by_steps[]` | `used_by_steps[]` | **KEEP из Тинкуя** | обратная связь ассет→шаг пайплайна; у WhiteCrow этого нет, а для графа обязательно |

### 1.2. Контракт

| WhiteCrow | Tinkuy | Workbench | Действие |
|---|---|---|---|
| `transition: "A + B -> C"` | — | `transition` | **KEEP** — человекочитаемая формулировка преобразования, ценна как есть |
| `upstream_objects[]` | — | `upstream_objects[]` | KEEP |
| `output_object` | — | `output_object` | KEEP |
| — | `output_schema` (inline dict) | `output_schema_ref` | **RENAME + GENERALIZE** — ссылка на JSON Schema вместо инлайна; инлайн у Тинкуя уже разошёлся с реальностью (см. §3) |
| — | — | `input_schema_ref` | **ADD** |
| — | — | `required_variables[]` | **ADD** — плейсхолдеры, обязательные к подстановке |
| `runtime_block_policy: "RUNTIME_PROMPT_START/END only"` | — | `protected_regions[]` + `editable_regions[]` | **GENERALIZE** — от одной пары маркеров к списку именованных областей |
| — | `non_negotiable_identity[]` (в manifest) | `invariants[]` | **KEEP из Тинкуя, GENERALIZE** — 8 неотчуждаемых утверждений Заратустры становятся защищёнными инвариантами ассета |
| — | — | `contract_version` | **ADD** |
| — | — | `compat_range` | **ADD** — с какими версиями соседних контрактов совместим |

### 1.3. Композиция и зависимости

| WhiteCrow | Tinkuy | Workbench | Действие |
|---|---|---|---|
| `depends_on[]` | `depends_on[]` | `depends_on[]` | **KEEP** — совпадает в обеих моделях |
| `composition_allowed` | — | `composition_allowed` | KEEP |
| — | `prompt_stack[]` (manifest) | `PromptPack.members[]` | **RENAME** |
| — | `donor_ops_used[]` | `donor_ops_used[]` | KEEP из Тинкуя |
| — | `cultural_cards_used[]` | `modules_used[]` | **GENERALIZE** — карты Заратустры это частный случай PromptModule |
| — | `prompt_modules/` | `PromptModule` | KEEP |
| — | `policies{}` (manifest) | `policy_refs{}` | KEEP |

### 1.4. Рантайм и активация

| WhiteCrow | Tinkuy | Workbench | Действие |
|---|---|---|---|
| `runtime_allowed: true\|guarded` | — | `runtime_allowed` | **KEEP** — трёхзначное `true\|guarded\|false` |
| `activation_policy.server_manual` | — | `ActivationBinding.manual_server` | KEEP |
| `activation_policy.workpack_manual` | — | `ActivationBinding.manual_batch` | RENAME |
| `activation_policy.auto_run_allowed` | — | `ActivationBinding.auto_run_allowed` | KEEP |
| `activation_policy.review_required` | — | `ActivationBinding.review_required` | KEEP |
| `activation_policy.budget_risk` | — | `ActivationBinding.budget_risk` | KEEP |
| `activation_policy.allowed_scopes[]` | — | `ActivationBinding.allowed_scopes[]` | KEEP |
| `activation_policy.output_destination[]` | — | `ActivationBinding.output_destination[]` | KEEP |
| invocation manifest (`prompt_engine.py`) | — | `InvocationManifest` | **KEEP** — структура сохраняется |
| — | fallback на `_DEFAULT_*_PROMPT` | `baseline_fallback_ref` | **ADD** — механизм Тинкуя формализуется: константа в коде становится явным baseline-вариантом |

### 1.5. Версионирование — почти всё ADD

| WhiteCrow | Tinkuy | Workbench | Действие |
|---|---|---|---|
| `version: "0.1"` | `version: "0.2.0"` | `PromptVariant.version` | KEEP |
| `status: draft\|candidate` | `status: candidate` | `PromptVariant.state` | **GENERALIZE** → 10 состояний, см. `PROMPT_VARIANT_LIFECYCLE_v0.1` |
| `external_workspace_sync_status` | — | `external_sync{}` | **GENERALIZE** — обобщается на Google Docs, Яндекс.Диск и любой внешний редактор |
| — | — | `PromptVariant.variant_id` | **ADD** |
| — | — | `parent_variant_id` | **ADD** — lineage |
| — | — | `source_hash` | **ADD** — sha256 исходника |
| — | — | `author`, `created_at` | **ADD** |
| — | — | `deprecation_reason`, `rollback_of` | **ADD** |

### 1.6. Компиляция и телеметрия — целиком ADD

| Объект | Поля | Источник идеи |
|---|---|---|
| `PromptCompilerProfile` | `profile_id`, `model_id`, `context_window`, `supports_system_role`, `assembly_order[]`, `allow_superprompt`, `token_budget`, `cache_strategy` | `PROMPT_ORCHESTRATOR_SPEC.md` формула сборки |
| `CompiledPrompt` | `compiled_hash`, `system_text`, `user_text`, `token_count`, `source_map[]`, `profile_id`, `built_at` | ADD |
| `source_map[]` | `{span_start, span_end, asset_id, variant_id, region_name}` | ADD |
| `EvaluationRecord` | `variant_id`, `kind: static\|contract\|llm_review\|smoke`, `verdict`, `reasons[]`, `fixture_id`, `evaluated_at` | ADD |
| `UsageTelemetry` | `variant_id`, `runs`, `tokens_in`, `tokens_out`, `cost_usd`, `latency_p50`, `errors`, `retries`, `last_used_at` | ADD |

**Важно:** `allow_superprompt` обязателен как поле уровня ветки. `PROMPT_DEPENDENCY_MAP.yaml` Тинкуя прямо запрещает мега-промпт для Заратустры («Никакой мега-промпт. Каждый шаг подгружает ТОЛЬКО нужные модули»). Компилятор обязан уважать этот запрет, а не считать суперпромпт универсальным предельным случаем.

---

## 2. Итоговая модель

```yaml
PromptAsset:
  asset_id: str                    # стабильная идентичность
  branch: str                      # tinkuy_core | socrates | zarathustra | whitecrow
  owner_id: str                    # <- organ_id / agent_id
  category: str
  template_family: str
  operation_class: str             # машинный класс
  purpose: str                     # человеческое назначение
  used_by_steps: [str]
  transition: str                  # "A + B -> C"
  upstream_objects: [str]
  output_object: str
  input_schema_ref: str | null
  output_schema_ref: str | null
  required_variables: [str]
  protected_regions: [Region]      # <- RUNTIME_PROMPT_START/END обобщённые
  editable_regions: [Region]
  invariants: [str]                # <- non_negotiable_identity
  contract_version: str
  compat_range: str
  depends_on: [asset_id]
  composition_allowed: bool
  modules_used: [module_id]
  donor_ops_used: [str]
  policy_refs: {str: str}
  runtime_allowed: true | guarded | false
  baseline_fallback_ref: str | null   # ссылка на Python-константу, если есть
  active_variant_id: variant_id

PromptVariant:
  variant_id: str
  asset_id: str
  version: str
  state: <10 состояний>
  origin: baseline_file | baseline_code | user_edit | user_new | imported_gdoc | llm_proposed
  parent_variant_id: str | null
  source_path: str
  source_hash: str                 # sha256
  author: str
  created_at: iso8601
  external_sync: {provider, doc_id, revision_id, last_pull, last_push}
  evaluations: [EvaluationRecord]
  usage: UsageTelemetry
  deprecation_reason: str | null
  rollback_of: variant_id | null

Region:
  name: str
  kind: protected | editable
  start_marker: str
  end_marker: str
  reason: str                      # почему защищена

PromptModule:      # <- prompt_modules/ + cultural cards
  module_id, path, purpose, depends_on, version

PromptPack:        # <- prompt_stack
  pack_id, members: [asset_id | module_id], order, branch

ActivationBinding:
  asset_id, variant_id, scope, manual_server, manual_batch,
  auto_run_allowed, review_required, budget_risk,
  allowed_scopes, output_destination, activated_by, activated_at

RAGProfile:        # отдельный тип, не PromptAsset
  profile_id, corpus_refs, chunker{strategy,size,overlap,min,max},
  index{kind,params}, retriever{algo,k1,b,top_k}, reranker,
  filters, thresholds, diversity, budget, cache, saturation,
  query_rewrite_asset_id      # <- LLM-часть остаётся PromptAsset
```

---

## 3. Что этот кроссуок немедленно ловит

Применение модели к `03_scene_reading` вскрывает трёхуровневое расхождение контракта:

| Уровень | Полей | Где |
|---|---|---|
| Промпт требует от модели | 17 | `data/zarathustra/03_scene_reading.md` |
| `PROMPT_DEPENDENCY_MAP.output_schema` объявляет | 9 | `PROMPT_DEPENDENCY_MAP.yaml:26` |
| `analyze_situation` читает | 7 | `zarathustra.py:277–285` |
| `SituationAnalysis` хранит | 7 | `schemas.py` |

Десять полей генерируются моделью и молча выбрасываются. В модели Workbench это ошибка уровня `contract_mismatch`, обнаруживаемая статическим валидатором до любого прогона: `required_variables` промпта не совпадают с `output_schema_ref`.

**Это не чинится в R1.** Фиксируется как первый реальный дефект, который найдёт Workbench, и как критерий приёмки статического валидатора.

---

## 4. Правило переноса

1. Ничего не переименовывать без причины из таблиц §1.
2. Поля `transition`, `depends_on`, `runtime_allowed`, `composition_allowed`, `runtime_block_policy`, activation-политики и invocation manifest переносятся **с сохранением семантики**.
3. Реестры Тинкуя (`genres`, `protocols`, `method_packs`) получают ту же схему записи — сегодня они плоские (`id` + файл).
4. `PROMPT_DEPENDENCY_MAP.yaml` Заратустры становится первым живым экземпляром `PromptPack` + `PromptAsset`, а не переписывается.

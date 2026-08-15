# PROMPT_RAG_ASSET_INVENTORY

**Дата:** 2026-08-15 · Тинкуй `zarathustra-push@a72ae99`, пути от `CALIFORNIAN_ID/src/californian_id/` · WhiteCrow `conceptarticle@a140dca`

Легенда извлекаемости: **READY** — файл, загружается в рантайме, готов к версионированию · **NEEDS_EXTRACTION** — в коде · **NEEDS_CONTRACT** — файл есть, контракт I/O не формализован · **NEEDS_INSTRUMENTATION** — нет трассировки

---

## 1. Промпт-ассеты Тинкуя

### 1.1. Персоны — 7 ассетов × 4 файла

| Поле | Значение |
|---|---|
| Логическая идентичность | `LENS_ACCELERATIONIST`, `LENS_AI_SAFETY`, `LENS_EFFECTIVE_ALTRUIST`, `LENS_LIBERTARIAN`, `LENS_LONGTERMIST`, `LENS_RATIONALIST`, `LENS_TRANSHUMANIST` |
| Файлы | `data/personas/<ID>/system_prompt.md`, `values.yaml`, `argumentation.yaml`, `position_model.yaml`, `manifest.yaml`, `sources/source_manifest.yaml` |
| Хранение | файлы |
| Вызывающий | `persona_layer.py:29` (`yaml.safe_load(path.read_text())`), `:196` (чтение карточек построчно) |
| Контракт | `data/personas/persona.schema.json` — валидирует `manifest.yaml`. Контракт **самого промпта** не формализован |
| Привязка к модели | через пресет/`models.yaml`, не в ассете |
| Композиционные зависимости | `manifest.routing.topics/tensions` используются детерминированно в `select_initial_voice` (`pipeline.yaml:32`) |
| Версии | нет. Есть `_template/` для нового |
| Тесты | `validate_personas` шаг пайплайна отклоняет персоны с фатальными ошибками манифеста |
| Извлекаемость | **NEEDS_CONTRACT** — файлы готовы, но нет разделения на protected/editable |
| Protected blocks | нет |

### 1.2. Ткань — 12 ступеней

| Поле | Значение |
|---|---|
| Файлы | `data/fabric/00_fabric_parser_orchestrator.md` … `11_no_loss_validation.md` |
| Ступени | orchestrator · coarse_composition · multiscale_segmentation · semantic_move_extraction · block_assembly · relation_extraction · thread_induction · cross_scale_reconciliation · window_boundary_repair · scene_reconstruction · provenance_validation · no_loss_validation |
| Активны | только при `input_mode = raw+fabric` |
| Контракт | косвенно через `schemas.py` / `UnitPack` |
| Версии / тесты | нет |
| Извлекаемость | **NEEDS_CONTRACT** |

Это самая длинная чисто-промптовая цепочка в Тинкуе и лучший кандидат на демонстрацию графа: 12 узлов подряд, каждый — один файл.

### 1.3. Жанры закрытия

`data/rhetoric/genres/registry.yaml` + `academic_critique.md`, `forensic_argument.md`, `ironic_demolition.md`, `methodological_consultation.md` (+ прочие). Реестр уже есть, выведен через `GET /api/genres`. **READY** — ближайший кандидат на первое версионирование.

### 1.4. Диалог-протоколы

`data/dialogue_protocols/registry.yaml` + `clarifying.md`, `joint_inquiry.md`, `listening.md`, `problematising.md`, `socratic.md`. Выведен через `GET /api/protocols`. **READY**.

`socratic.md` — прямая точка входа для ветки Сократа.

### 1.5. Метод-паки

`data/method_packs/registry.yaml` + `argument_reconstruction.md`, `claim_and_logic_analysis.md`, `conceptual_analysis.md`, `ontological_reconstruction.md`, `problematisation.md`, `socratic_inquiry.md`. Загрузка: `method_packs.py:49` `prompt_path.read_text()`. Выведен через `GET /api/methods`. **READY**.

### 1.6. Аргументация

`data/argumentation/prompts/socratic_question_chain.md` + 7 YAML-политик (`attack_defence_operations`, `burden_rules`, `dispute_modes`, `fairness_policy`, `fallacies_and_tricks`, `refusal_and_stopping`, `thesis_tracking`) + `schemas/dispute_assessment.schema.json` + `manifest.yaml`.

**КОРРЕКЦИЯ v0.2 — предыдущее утверждение было неточным.** В первой редакции здесь стояло: «единственное место, где **промпт-узел** имеет формализованный выходной контракт, кандидат №1 на вертикальный срез». Проверка `argumentation.py` (235 строк) показала: **этот узел детерминированный, а не промпт-опосредованный.** Ни одного вызова LLM; `assess_turn`, `detect_thesis_substitution`, `detect_fallacy_or_trick`, `check_anti_slop` — чистые Python-эвристики (Jaccard, regex, счётчики операций). `dispute_assessment.schema.json` описывает выход **детерминированной функции**, а `prompts/socratic_question_chain.md` помечен в самом файле как *«Reference-only template»* и в рантайме не вызывается.

Правильная роль узла: **эталонный DETERMINISTIC-узел** для Workbench. На нём демонстрируется, что инспектор корректно отличает детерминированное преобразование от промптового и показывает схему выхода без редактора промпта. Кандидатом на промптовый вертикальный срез он **не является** — см. §1.11.

### 1.7. Карты Заратустры — ~30 YAML

`data/corpus/zarathustra/{operations,scenes,constraints,risks}/CARD_*.yaml`, схема `schemas/scene_operation_card.schema.json`, манифест `SOURCE_MANIFEST.yaml`, отчёт извлечения `extraction_reports/PASS_v0_4_0.{md,yaml}`.

Это **композиционные модули промпта** (PromptModule), а не самостоятельные PromptAsset. Имеют схему. Имеют provenance. **READY как модули**.

### 1.8. Политики взаимодействия

`data/interaction/{disclosure,interaction,manipulation,repetition,role_preservation}_policy.yaml` — 5 файлов. Класс F (контракт), не редактируются свободно.

### 1.9. Доноры

`data/donors/DONOR_REGISTRY.yaml`, `DONOR_TO_RUNTIME_MAP.yaml`, `DONOR_OPERATION_CARDS/*.yaml` (8 карт, в т.ч. `prompt_body_selection_and_assembly.yaml`, `role_wipe_guard.yaml`, `socratic_question_chain.yaml`, `anti_slop_synthesis_gate.yaml`).

`DONOR_TO_RUNTIME_MAP.yaml` — уже существующая карта «донор → рантайм-объект». Это прообраз provenance-связей Workbench.

### 1.11. Промпт-хребет Заратустры — **ПРОПУЩЕН в v0.1, главный ассет Тинкуя**

Первая редакция инвентаря не нашла `data/zarathustra/`. Это была самая существенная лакуна R0: здесь лежит уже работающая модель промпт-ассета Тинкуя, близкая к WhiteCrow.

| Артефакт | Содержание |
|---|---|
| `data/zarathustra/01…13_*.md` | 13 промпт-модулей: identity_and_laws · cave_ontology · scene_reading · head_calling · move_assignment · tension_regulation · position_testing · question_transformation · completion_form_selection · narrative_memory · defense_and_role_holding · rhetorical_presentation · closing_speech (2–5 KB каждый) |
| `data/zarathustra/manifest.yaml` | `agent_id: HEAD_ZARATHUSTRA`, `version: 0.2.0`, `status: candidate`, `head_layer` (spine_zone / head_zone), `canonical_alignment` (4 ссылки на канон), **`non_negotiable_identity`** — 8 инвариантов, `functions[]` (10), `prompt_stack[]` (12), `policies{}` (4) |
| `data/zarathustra/PROMPT_DEPENDENCY_MAP.yaml` | **`prompt_dependency_map_id`, `version: 0.4.0`, `status: candidate`, `rule_source`, и на каждый модуль: `id`, `purpose`, `used_by_steps[]`, `depends_on[]`, `output_schema` (inline), `version`, `donor_ops_used[]`, `cultural_cards_used[]`** |
| `data/zarathustra/{routing,dialogue,completion_forms,affect}_policy.yaml` | 4 политики |
| `data/zarathustra/prompt_modules/architectonic_turn_reconstruction.md` | композиционный подмодуль |

**Загрузка:** `zarathustra.py:150` — `Zarathustra.prompt(name)`, ленивое чтение с диска с кешем `_prompt_cache`, при отсутствии файла — fallback на Python-константы `_DEFAULT_SCENE_READING_PROMPT` / `_DEFAULT_ROUTE_PROMPT` / `_DEFAULT_CLOSING_SPEECH_PROMPT`.

**Три реальных LLM-вызова, управляемых файлами:**

| Модуль | Шаг | Точка вызова | Выход |
|---|---|---|---|
| `03_scene_reading.md` | `analyze_situation` | `zarathustra.py:260` | JSON → `SituationAnalysis` |
| `04_head_calling.md` | `route_next` | `zarathustra.py:390` | JSON → `RoutingDecision` |
| `13_closing_speech.md` | `closing_speech` | `zarathustra.py:857` | свободный текст |

**Принцип, зафиксированный в самой карте зависимостей:**

> «Никакой мега-промпт. Каждый шаг Заратустры подгружает ТОЛЬКО те prompt-modules, что ему нужны. Новые модули появляются через явный proposal и versioning.»

Это прямо **противоречит** формулировке «в предельном случае — компиляция в суперпромпт» из ранней спецификации Workbench. Для ветки Заратустры суперпромпт запрещён каноном. `PromptCompilerProfile` обязан поддерживать оба режима и уважать branch-level запрет.

**Обнаруженный дефект контракта (три уровня рассинхронизации):**

| Уровень | Полей | Источник |
|---|---|---|
| Промпт `03_scene_reading.md` требует от модели | **17** | topic, genre, stakes, horizons, concepts, tensions, uncertainties, dominant_frame, suppressed_frame, model_of_human, model_of_future, model_of_power, central_value, hidden_fear, potential_idol, absent_head, possible_transformation |
| `PROMPT_DEPENDENCY_MAP.yaml` объявляет | **9** | + dominant_frame, suppressed_frame |
| `analyze_situation` фактически читает | **7** | `zarathustra.py:277–285` |
| `SituationAnalysis` хранит | **7** | `schemas.py` |

**Десять полей, которые модель генерирует по инструкции, молча выбрасываются.** Это оплаченные токены без потребителя и одновременно идеальная демонстрация того, зачем нужен контрактный валидатор Workbench: он ловит такое расхождение на первом же проходе.

**Статус: IMPL как модель, READY как ассет, NEEDS_CONTRACT_VALIDATION.**

### 1.10. Захардкоженные — NEEDS_EXTRACTION

| Ассет | Расположение | Варианты | Приоритет |
|---|---|---|---|
| Assembly instruction | `web_ui.py:_assembly_instruction()` ~1419–1446 | synthesis, verdict, dissent_forward, diagnostic, projective, **roast** | **1** |
| Grounding instruction | `web_ui.py:_grounding_instruction()` ~1402 | strict_card, balanced, freer_synthesis | **2** |
| Critique directness_hint | `regimes.py:22–36` | gentle, balanced, hard | 3 |
| Variation prompt_hint | `regimes.py:41–58` | strict, normal, jazz | 3 |
| Persona-layer генерация хода/финала | `web_ui.py:_generate_persona_layer_utterance()` :1253, `_generate_persona_layer_final_answer()` :1329 | — | 4 — требует чтения перед извлечением |

Итого: **~5 промптовых поверхностей в Python**, из них две — с пользовательским переключателем в форме.

---

## 2. RAG-ассеты Тинкуя

### 2.1. Корпуса

| Корпус | Путь | Состояние |
|---|---|---|
| Zarathustra primary | `data/corpus/zarathustra/normalized/` | README есть; `cultural_rag.py` чанкует на лету |
| Zarathustra cards | `data/corpus/zarathustra/{operations,scenes,...}` | загружаются целиком (`_load_all_cards`) |
| RAG-каталог | `data/rag/zarathustra/README.md` | только README |
| Persona sources | `data/personas/LENS_*/sources/source_manifest.yaml` | манифесты источников на персону |
| Persona-scoped evidence | `retrieval.py` над `corpus_root` | `pipeline.yaml:30` — «persona-scoped lexical retrieval; no cross-persona bleed» |

### 2.2. Конфигурация извлечения — вся в коде

| Параметр | Значение | Файл |
|---|---|---|
| Чанкер evidence | 800 симв., overlap 200 | `retrieval.py:34` |
| Ранжирование | BM25, k1=1.5, b=0.75 | `retrieval.py:85` |
| top_k | 3 | `retrieval.py:58` |
| Чанкер культурного корпуса | 800 / 200 | `cultural_rag.py:91,106` |
| top_k карт | 3 | `cultural_rag.py:280` |
| Семантический чанкер | target 2000 / max 4000 / min 300 | `adapters/text_chunker.py:26–28` |
| tf-idf индекс | `persona_layer.py:364` — `json.loads(self.tfidf_path.read_text())` | предвычисленный индекс |

Отсутствуют как понятия: эмбеддинги (используется лексический поиск), ре-ранкер, порог схожести, диверсификация, временные/источниковые фильтры, бюджет извлечения, кэш, условия насыщения, требования к цитированию.

### 2.3. Что есть для объяснимости

`EvidenceChunk` (`retrieval.py:17`) содержит `score`. `cultural_rag.py` формирует `locator: CHUNK={stem}#{i}` и sha256-хэш чанка — то есть **provenance чанка уже есть**. Но эти данные не попадают в `events.jsonl` и не выводятся ни в один интерфейс.

**Статус: NEEDS_INSTRUMENTATION.** Требование «объяснить, почему извлеклись эти чанки» блокируется не UI, а отсутствием эмиссии retrieval-события в трассу. Это минимальная и дешёвая доработка рантайма, которую надо сделать до, а не после Workbench.

---

## 3. Промпт-ассеты WhiteCrow — эталонная модель

64 prompt-body в 10 категориях. Запись реестра (`prompt_bodies/registry.yaml`):

```yaml
prompt_id, version, status(draft|candidate), path
organ_id, template_family, operation_class
transition: "<входные объекты> -> <выходной объект>"
context_level, runtime_allowed(true|guarded), composition_allowed
category, depends_on[], upstream_objects[], output_object
runtime_block_policy: "RUNTIME_PROMPT_START/END only"
external_workspace_sync_status, notes
```

Что даёт эта модель поверх текущей тинкуевской:

| Свойство | Tinkuy | WhiteCrow |
|---|---|---|
| Явный контракт I/O в записи | нет | `upstream_objects` → `output_object` |
| Зависимости между промптами | нет | `depends_on[]` |
| Статус жизненного цикла | нет | `status: draft\|candidate` |
| Разрешение на рантайм | нет | `runtime_allowed: true\|guarded` |
| Разрешение на композицию | нет | `composition_allowed` |
| Защищённая область | нет | `RUNTIME_PROMPT_START/END`, проверяется валидатором |
| Политика активации | нет | `activation_policy.yaml`: `server_manual`, `workpack_manual`, `auto_run_allowed`, `review_required`, `budget_risk`, `allowed_scopes`, `output_destination` |
| Шаблон нового ассета | `personas/_template/` только для персон | `templates/organ_prompt_body_template_v0_1.md` |
| Статический валидатор | нет | `scripts/validate_prompt_bodies.py` |
| Anti-ingestion граница | нет | `.litopsignore` + запрет индексации prompt-bodies |

**Категория `06_field_whitecrow`** — прямые RAG/проекционные ассеты: `field_candidate_miner_v0_1` (24 KB), `field_text_projector_v0_1` (32 KB), `relation_tension_map_builder_v0_1` (28 KB), `document_role_resolver_v0_1` (41 KB), `whitecrow_export_builder_v0_1` (32 KB).

Пример контракта из реестра:

```
whitecrow_export_builder_v0_1
transition: FieldText + RelationTensionMap + FieldCandidates + ContextPack
            + Workset state + provenance -> WhiteCrowExportPackage
runtime_allowed: guarded
```

---

## 4. Сводная таблица извлекаемости

| Ассет | Кол-во | Хранение | Контракт | Версии | Тесты | Protected | Статус |
|---|---|---|---|---|---|---|---|
| Жанры закрытия | ~5 | файл + реестр | нет | нет | нет | нет | **READY** |
| Диалог-протоколы | 5 | файл + реестр | нет | нет | нет | нет | **READY** |
| Метод-паки | 6 | файл + реестр | нет | нет | нет | нет | **READY** |
| Аргументация | 1 + 7 политик | файл + манифест | **JSON Schema есть** | нет | нет | нет | **READY (лучший)** |
| Персоны | 7×4 | файл | schema только манифеста | нет | `validate_personas` | нет | NEEDS_CONTRACT |
| Ткань | 12 | файл | косвенно | нет | нет | нет | NEEDS_CONTRACT |
| Карты Заратустры | ~30 | файл | **schema есть** | нет | нет | нет | READY как модули |
| Assembly / Grounding / Regimes | ~4 | **Python** | нет | нет | нет | нет | **NEEDS_EXTRACTION** |
| RAG-конфиг Тинкуя | 10 параметров | **Python defaults** | нет | нет | нет | — | **NEEDS_INSTRUMENTATION** |
| WhiteCrow prompt bodies | 64 | файл + реестр + политика | `transition` + объекты | `version` + `status` | валидатор | **есть** | эталон |

---

## 5. Вывод

Тинкуй имеет **промпты**, но не имеет **промпт-ассетов**: нет контракта в записи, нет версий, нет статусов, нет защищённых областей, нет политики активации, нет валидатора. WhiteCrow имеет всё перечисленное в работающем виде.

Правильное действие — не проектировать модель ассета заново, а **перенести модель WhiteCrow в Тинкуй**, начав с четырёх READY-семейств (жанры, протоколы, метод-паки, аргументация), где уже есть реестры и где у аргументации есть настоящая выходная схема.

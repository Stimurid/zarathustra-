# UPDATED_READINESS_ESTIMATE

**Дата:** 2026-08-15 · Заменяет грубую оценку «~40 %» из прохода до R0.

Оценка ведётся по подсистемам. Столбец «Готово» отвечает на вопрос: сколько работы **не придётся делать**, потому что артефакт существует и проверен. Столбец «Где» — точный источник.

Статусы источника: **IMPL** реализовано · **PARTIAL** частично · **SPEC** только спецификация · **NONE** отсутствует

---

## 1. Таблица

| # | Подсистема | Готово | Что уже есть | Где | Статус |
|---|---|---|---|---|---|
| 1 | Pipeline introspection | **55 %** | `pipeline.yaml` (13 шагов, entrypoints, terminal_states, llm_calls, fail_closed), `state_model.yaml`, контракт PipelinePack в каноне; в WhiteCrow — работающий read-model `build_field_graph` + `build_inspector` | Tinkuy `data/pipeline/`; WhiteCrow `litops/web/visual_data.py` | PARTIAL |
| 2 | Variable typing | **75 %** | Перепись выполнена: 58 переменных, 7 классов + BRANCH_SELECTOR, 3 гибрида расщеплены, класс D проаудирован | `WORKBENCH_VARIABLE_CENSUS.csv` | IMPL (как документ), NONE в коде |
| 3 | Prompt asset storage | **50 %** | Tinkuy: 4 семейства с реестрами (жанры, протоколы, метод-паки, аргументация) + персоны + ткань + карты, всё файлами, читается в рантайме. WhiteCrow: полная модель записи с контрактом и зависимостями | Tinkuy `data/*/registry.yaml`; WhiteCrow `prompt_bodies/registry.yaml` | PARTIAL |
| 4 | Versioning | **20 %** | В Тинкуе нет ничего. В WhiteCrow — поля `version` + `status(draft\|candidate)` в реестре, но без истории версий и diff | WhiteCrow `prompt_bodies/registry.yaml` | PARTIAL (модель), NONE (история) |
| 5 | Activation binding | **60 %** | `activation_policy.yaml` со всеми полями (`server_manual`, `workpack_manual`, `auto_run_allowed`, `review_required`, `budget_risk`, `allowed_scopes`, `output_destination`) + проверка в `prompt_engine.py` | WhiteCrow | IMPL (в WhiteCrow), NONE (в Тинкуе) |
| 6 | Prompt compiler | **35 %** | Полная спецификация 5-слойной сборки, порядок over-агентов, стейдж-гейты, подстановка `{{...}}`. Реализация — внутри монолитного HTML, не модуль. В Тинкуе — сборка размазана по `persona_layer.py` и `web_ui.py` | WhiteCrow `docs/PROMPT_ORCHESTRATOR_SPEC.md` (348 стр.) | SPEC + PARTIAL |
| 7 | Compiled view + source map | **5 %** | Нигде не реализовано. Есть только требование | — | NONE |
| 8 | Graph UI | **60 %** | Quinta: `@xyflow/react` + `elkjs`, 9 типов узлов, кастомные рёбра, 3 оверлея, `SpindleLayout.ts`, `SpindleCanvas`, `AgentMapView`, `RunTraceStudio`. Требуется адаптация типов узлов под пайплайн | Quinta `src/components/pdf/`, `base/AgentMapView.tsx` | IMPL (подложка) |
| 9 | Inspector / drawer | **70 %** | Quinta `RightDock.tsx` — ресайз, 70 %, pinned/overlay, схлопывание, вкладки. WhiteCrow — 12 типизированных `_inspect_*` резолверов с provenance-цепочкой | Quinta + WhiteCrow | IMPL |
| 10 | Markdown editor | **10 %** | Ничего своего. Зрелые внешние компоненты (CodeMirror 6, Monaco) подключаются штатно | — | NONE (внешняя зависимость) |
| 11 | LLM copilot | **45 %** | Quinta `FieldCopilot.tsx`: контекст выбранного объекта, `LLMActionProposal` + `onApplyProposal`, контекстные быстрые кнопки, провайдерный слой (`anthropicProvider`, `openAICompatibleProvider`, `mockProvider`). Нет: контекст-брокер, INSERT SELECTION, DIFF | Quinta `src/components/FieldCopilot.tsx`, `src/llm/` | PARTIAL |
| 12 | Static validation | **55 %** | `validate_prompt_bodies.py`: обязательные метаполя, обязательные секции, соответствие id имени файла, соответствие H1, ровно один `RUNTIME_PROMPT_START` и один `RUNTIME_PROMPT_END`, запрет forbidden paths, проверка `.litopsignore` | WhiteCrow `scripts/` | IMPL (в WhiteCrow) |
| 13 | Protected blocks | **70 %** | Конвенция `RUNTIME_PROMPT_START/END` реализована и проверяется. Требуется перенос в Тинкуй и связка с JSON-схемами | WhiteCrow | IMPL (в WhiteCrow) |
| 14 | Contract validation | **40 %** | JSON-схемы существуют: `dispute_assessment.schema.json`, `scene_operation_card.schema.json`, `persona.schema.json`, схемы PipelinePack (`SEMANTIC_OBJECT`, `RELATION_ASSERTION`, `PROVENANCE_BUNDLE`, `RUN_TRACE` и др. в каноне). Шаг `validate_output` есть в пайплайне. Нет связи «промпт-ассет ↔ его схема» | Tinkuy `data/**/schemas/`, канон `12_пайплайны/**/schemas/` | PARTIAL |
| 15 | Smoke harness | **45 %** | Фикстуры готовы: `examples/valid/`, `examples/invalid/`, `tests/test_plan.yaml`, `tests/validate_run.py` в PipelinePack'ах канона; архив ранов `runs/`; 281 тест в рантайме Тинкуя | канон `12_пайплайны/**/tests/`, Tinkuy `runs/`, `CALIFORNIAN_ID/tests/` | PARTIAL |
| 16 | Baseline vs candidate compare | **25 %** | WhiteCrow `/extraction-compare` и `/extraction-runs/<id>` — сравнение прогонов извлечения, не промпт-вариантов. Paideia `api/dialogue_runtime/diff.py` + `lineage.py` | WhiteCrow, Paideia | PARTIAL |
| 17 | Candidate lifecycle | **40 %** | WhiteCrow: `POST /action/candidate-accept\|reject\|add\|promote-candidates/<id>`, статусы в реестре. Нет: цепочки EDIT→…→ACTIVATE→ROLLBACK для промптов | WhiteCrow `litops/web/app.py` | PARTIAL |
| 18 | RAG workbench | **10 %** | Извлечение работает (BM25, чанкер, top_k, provenance-локаторы `CHUNK={stem}#{i}` + sha256). Но: 10 параметров зашиты в Python-дефолты, ни один не выведен, retrieval-события не пишутся в трассу | Tinkuy `retrieval.py`, `cultural_rag.py`, `text_chunker.py` | PARTIAL (движок), NONE (управление) |
| 19 | Telemetry / RunTrace | **50 %** | `runs/<run_id>/events.jsonl` + `state.json`, экспорт `md\|json\|bundle`, WS/SSE события (`run_started`, `turn_completed`, `route_previewed`, `closing_speech_delta`, `run_completed`), аудит интервенций в SQLite. Нет: токены/стоимость/латентность per-node, retrieval-события, compiled-prompt hash | Tinkuy `runs/`, `ws_endpoint.py` | PARTIAL |
| 20 | Prompt API | **0 %** | Ни одного эндпоинта. Есть `/api/presets`, `/api/models`, `/api/genres`, `/api/protocols`, `/api/methods`, `/api/runs`, `/api/budgets`, `/api/workspaces`, `/api/auth/*`, `/api/narrative/*`, `/api/reflect/*` — и ничего вида `/api/prompts` | Tinkuy `web_ui.py` do_GET/do_POST | NONE |
| 21 | Hardcoded prompt debt | **0 %** | ~5 промптовых поверхностей в Python, включая `roast` («прожарка») и все три grounding-режима | Tinkuy `web_ui.py`, `regimes.py` | NONE (долг) |
| 22 | Google Docs projection | **30 %** | Форматы `fc5_bridge_v1`, `fc5_review_batch_v1`, `fc5_patch_v1`; экспортёры работают; алгоритм сопоставления комментария с блоком специфицирован; черновик Apps Script. Не сделано: `importReviewBatch` (заглушка), OAuth, серверный мост | WhiteCrow `docs/GOOGLEDOCS_BRIDGE_PREP.md` | PARTIAL |
| 23 | Branch adapters | **15 %** | Понятие есть в требовании; в WhiteCrow есть доказательство необходимости — 4 разные проекции одного корпуса (`FIELD_PROJECTION_ENGINE_SPEC.md`). Контракт адаптера не написан | — | SPEC |
| 24 | Zarathustra portability | **50 %** | Вторая ветка идентифицирована: `runtime_assets/personas/v0.2/personas/{C,EA,Ex,L,N8,R,S,T}/persona_constitution.md` (8 персон, отдельная от 7 LENS_*), ветка `codex/persona-layer-nemo8-integration`, документы `docs/PERSONA_LAYER_INTEGRATION.md`, `NEMO8_META_LAYER.md`, `PERSONA_PACKAGE_PROVENANCE.md` | Tinkuy `zarathustra-push` | PARTIAL |
| 25 | Socrates branch | **35 %** | **ИСПРАВЛЕНО v0.2.** Architectural/constitutional build существует и активно собирается: `07_SOCRATES_PIPELINE_PACK` (`10WHFJzLZYP6JblzmZJBk1X3_sdETU4A2`) развёрнут полным скелетом из 13 директорий; `steps/` и `prompts/` пусты. Build status `G-S19 COMPLETED_CANDIDATE`, next `G-S20`. Сократические ассеты в Тинкуе есть (`dialogue_protocols/socratic.md`, `method_packs/socratic_inquiry.md`, `argumentation/prompts/socratic_question_chain.md`, `CARD_ELENCHUS_PLATO.yaml`) | Drive `07/10/13_*` | PARTIAL (архитектура), NONE (executable) |
| 26 | **Zarathustra prompt spine** | **65 %** | **ПРОПУЩЕНО в v0.1.** `data/zarathustra/` — 13 промпт-файлов `01…13_*.md`, `manifest.yaml` с `prompt_stack`/`functions`/`policies`/`non_negotiable_identity`, **`PROMPT_DEPENDENCY_MAP.yaml`** с полями `id/purpose/used_by_steps/depends_on/output_schema/version/donor_ops_used/cultural_cards_used`, 4 policy-YAML, `prompt_modules/`. Ленивая загрузка с диска `Zarathustra.prompt(name)` + fallback на Python-константы | Tinkuy `data/zarathustra/`, `zarathustra.py:150` | **IMPL** |

---

## 2. Агрегат

| Слой | Средняя готовность | Комментарий |
|---|---|---|
| Данные и контракты | **50 %** | Промпты файлами, схемы есть, реестры есть, трассы есть |
| Модель промпт-ассета | **50 %** | Существует в WhiteCrow, отсутствует в Тинкуе. Перенос, а не разработка |
| UI-подложка | **55 %** | Граф, док, копилот, инспектор — всё есть в Quinta и WhiteCrow |
| Сервисный слой Workbench | **25 %** | Резолвер и валидатор есть, компилятор — спека, API промптов — ноль |
| RAG-контур | **10 %** | Движок есть, управления и объяснимости нет |
| Ветки | **20 %** | Заратустра идентифицирована, Сократ отсутствует |

**Интегральная оценка: 40 %.** Совпадает с прежней цифрой численно, но смысл принципиально другой.

Раньше 40 % означало «фундамент данных есть, весь воркбенч писать». Теперь 40 % означает: **воркбенч в значительной части уже написан, но в трёх разных проектах и в трёх стеках, и главная работа — не разработка, а консолидация**. Реально отсутствующего кода мало: API промптов, история версий, компилятор как модуль, редактор, RAG-управление и инструментирование извлечения.

---

## 3. Три настоящих блокера

1. ~~Сократ отсутствует~~ — **СНЯТО в v0.2.** Сократ существует как архитектурная сборка (`G-S19 COMPLETED_CANDIDATE`), исполняемый PipelinePack ещё не материализован. Это не блокер: первый срез строится на реальном исполняемом узле Tinkuy runtime, Сократ подключается BranchAdapter'ом по мере материализации.

2. **RAG не инструментирован.** Требование «объяснить, почему извлеклись эти чанки» невыполнимо, пока retrieval не пишет события в трассу. `EvidenceChunk.score` и `locator` уже вычисляются — их надо просто начать эмитить. Это малая доработка рантайма, но она предшествует любому RAG-воркбенчу.

3. **Захардкоженные промпты.** Пока `roast` и grounding-режимы живут в Python-литералах, редактор не может их показать, а «активировать вариант» физически невозможно без передеплоя. Извлечение — предусловие среза, а не его часть.

---

## 4. Что снялось как блокер

- **«WhiteCrow не имеет интерфейса»** — снято. Два UI-тела найдены.
- **«Нет модели версионирования промптов»** — снято частично: модель есть в WhiteCrow, включая protected blocks и политику активации.
- **«Нужно выбрать React или Svelte»** — снято: выбор определён фактами, см. `FRONTEND_STACK_EVIDENCE_NOTE.md`.
- **«Нужно спроектировать Google Docs мост»** — снято частично: форматы и алгоритм сопоставления комментариев уже написаны.

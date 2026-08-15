# WORKBENCH_REUSE_MAP

**Дата:** 2026-08-15 · **Фаза:** R0 · Все пути и коммиты проверены на диске. Донорские репозитории не изменялись.

---

## 0. Реестр репозиториев

| PROJECT | REPO (remote) | PATH | BRANCH | COMMIT | DATE |
|---|---|---|---|---|---|
| Tinkuy / Zarathustra runtime | `Stimurid/zarathustra-.git` | `C:\projects\zarathustra-push` | main | `a72ae99` | 2026-08-12 |
| WhiteCrow / Litops | `Stimurid/whitecrow.git` | `C:\projects\conceptarticle` | main | `a140dca` | 2026-08-12 |
| WhiteCrow (worktree) | тот же | `C:\projects\conceptarticle-prompt-bodies` | `feature/prompt-body-registry-v0-1` | `b49b4c9` | — |
| Quinta (TRIZ Bench) | `Stimurid/quinta.git` | `C:\projects\quinta` | main | `3963df4` | 2026-06-27 |
| Paideia | `Stimurid/paideia.git` | `C:\projects\paideia-app` | `m1-integrated-runtime` | `d2144ad` | 2026-08-13 |
| Daedalum | `Stimurid/dedalum.git` | `C:\projects\dedalum` | main | `6eb4c7e` | — |
| Agentum | `Stimurid/Agentum.git` | `C:\projects\protected-agent-kit` | main | `db7f59c` | — |
| Socrates | — | **не найден локально** | — | — | — |
| «whitecrow» (ложный) | нет remote | `C:\projects\whitecrow` | main | `12ae796` | — |

---

## 1. Карта переиспользования

Легенда REUSE_DECISION: **COPY** — перенести код · **EXTRACT** — вынести в общий пакет · **ADAPT** — переписать под наш стек, сохранив логику · **REFERENCE** — использовать как проектный образец · **REJECT** — не годится.

### 1.1. Quinta — `C:\projects\quinta` @ `3963df4`

Stack: React 19.2.5 + Vite + TypeScript. Зависимости рантайма всего четыре: `react`, `react-dom`, `@xyflow/react ^12.11.0`, `elkjs ^0.11.1`. Скрипты: `dev` (vite), `build` (`tsc -b && vite build`), `lint` (eslint). Тестов — 25 файлов (`src/tests/*.mjs` smoke + прочие).

| COMPONENT | PATH | GENERICITY | CONTRACTS | REUSE |
|---|---|---|---|---|
| `RightDock` | `src/components/RightDock.tsx` (164 стр.) | **высокая** — чистый layout-компонент, props-driven, никакой доменной привязки | `defaultWidth`, `minWidth`, `maxWidthPercent` (70), `collapsed`, `mode: pinned\|overlay`, `width`, `activeTab`, `tabs[]` + колбэки | **COPY** |
| `FieldCopilot` | `src/components/FieldCopilot.tsx` (310 стр.) | средняя — знает `Branch`, `SessionState`, `FieldAction`, но контракт применения предложений отделим | `provider: LLMProvider`, `onApplyAction`, `onApplyProposal(LLMActionProposal)`, `chatMessages`, `autoMessage` | **ADAPT** — забрать механику `LLMActionProposal → onApplyProposal`, переписать доменные quick-кнопки |
| Граф-подложка | `src/components/pdf/SpindleCanvas.tsx` (255 стр.), `SpindleLayout.ts` (459 стр.), `nodes/*` (9 типов), `edges/SemanticEdge.tsx` (134 стр.), `overlays/*` (3), `src/components/base/AgentMapView.tsx` (290 стр.) | **высокая** для каркаса, доменная для типов узлов и раскладки | `@xyflow/react`. **КОРРЕКЦИЯ v0.2: `elkjs` объявлен в `package.json`, но в коде не используется** — `AgentMapView.tsx:12` прямо пишет «Layout is deterministic column-based (no ELK for first cut)». Раскладка в обоих графах рукописная колоночная | **ADAPT каркас, ADAPT типы узлов, раскладку писать свою** |
| `RunTraceStudio` | `src/components/RunTraceStudio.tsx` (175 стр.) | средняя | стадии, статусы (`completed/pending/failed/waiting_user/blocked_by_evidence/sandboxed/skipped`), источник результата (`live_llm/deterministic/deterministic_fallback/mock/user_action/imported`) | **ADAPT** — модель «источник результата» переносится как есть |
| `AgentFoundryView` | `src/components/AgentFoundryView.tsx` (109 стр.) | средняя | статусы `active/draft/deprecated/needs_review`, уровни L0–L3, `getCompatibilitySummary()` → `{totalPairs, compatible, conflicts}` | **ADAPT** — модель статусов и проверки совместимости |
| `PromptImportView` + анализатор | `src/components/PromptImportView.tsx` (119 стр.), `src/promptImport/promptAnalyzer`, `promptRefactorMock`, `mockPromptSources` | средняя, **на моках** | `PromptSource → PromptCandidate[] → AgentSpec draft` | **ADAPT** — сценарий импорта из документа; мок-слой заменить реальным |
| `RunProfileEditor` | `src/components/spindle/RunProfileEditor.tsx` (189 стр.) | **высокая** как паттерн | `Depth`, `BudgetClass`, `Autonomy`, `EvidencePolicy`; жёсткое правило «Apply dispatches RUN_CONTROL_UPDATE only — no provider call» | **REFERENCE** — паттерн draft→apply без побочных вызовов |
| `PipelineBuilder` | `src/components/PipelineBuilder.tsx` (260 стр.) | низкая — TRIZ-пресеты зашиты | `RunProfile`, `RunPolicy`, `RunBudget` | **REFERENCE** |
| Метрики/бюджет | `src/components/MetricsDashboard.tsx`, `src/logic/agentBudget.ts`, `src/logic/eventLog.ts` | средняя | — | **ADAPT** |
| LLM-провайдеры | `src/llm/provider.ts`, `anthropicProvider.ts`, `openAICompatibleProvider.ts`, `mockProvider.ts`, `llmSettings.ts`, `types.ts` | **высокая** | `LLMProvider` интерфейс | **COPY** (если фронт на React) |

**Конфликт:** Quinta — React, живой UI Тинкуя — Svelte 5. Прямой `COPY` возможен только при решении в пользу отдельного React-приложения.

**Замечание о ценности:** `@xyflow/react` + `elkjs` с уже написанными кастомными узлами, рёбрами, оверлеями и ELK-раскладкой — это самый дорогой в разработке кусок графовой поверхности, и он готов.

### 1.2. WhiteCrow — `C:\projects\conceptarticle` @ `a140dca`

Stack: Python 3.13 + Flask + Jinja2 (web); vanilla JS + inline CSS (field kernels).

| COMPONENT | PATH | STATUS | GENERICITY | REUSE |
|---|---|---|---|---|
| Prompt body registry | `prompt_bodies/registry.yaml` (53 KB, ~64 записи) | IMPLEMENTED | **высокая как схема** | **EXTRACT** — модель записи переносится в Тинкуй |
| Activation policy | `prompt_bodies/activation_policy.yaml` (12 KB) | IMPLEMENTED | высокая | **EXTRACT** — прямой прообраз `ActivationBinding` |
| Prompt invocation engine | `litops/prompt_engine.py` (15 KB) | IMPLEMENTED | **высокая** — чистый Python, зависимости `yaml`, `litops.registry`, `litops.schema` | **ADAPT** — ближайший кандидат в ядро WorkbenchCore |
| Static validator | `scripts/validate_prompt_bodies.py` | IMPLEMENTED | высокая | **ADAPT** |
| Protected blocks | конвенция `RUNTIME_PROMPT_START/END` + проверка | IMPLEMENTED | **высокая** | **COPY конвенцию** |
| Prompt body template | `prompt_bodies/templates/organ_prompt_body_template_v0_1.md` | IMPLEMENTED | высокая | **COPY** — «создать пустой промпт по структурному шаблону» |
| Visual read-model | `litops/web/visual_data.py` (37 KB): `build_field_graph`, `build_line_lanes`, `build_next_actions`, `build_inspector` + 12 `_inspect_*` | WORKING | **высокая как дисциплина** | **REFERENCE + ADAPT** |
| Node inspector route | `litops/web/app.py` → `/visual/inspector/<path:node_id>` | WORKING | высокая | **REFERENCE** |
| Candidate lifecycle | `app.py` → `POST /action/candidate-accept\|reject\|add\|promote-candidates/<id>` | WORKING | средняя | **REFERENCE** |
| Variant comparison | `app.py` → `/extraction-compare`, `/extraction-runs/<id>` | WORKING | средняя | **REFERENCE** |
| Field Kernel v6.3.1 | `mvp/FIELD_KERNEL_v6_3_1.html` (225 KB) | WORKING | низкая — монолит | **REFERENCE** |
| Field Projection Engine | `docs/FIELD_PROJECTION_ENGINE_SPEC.md` + реализация в HTML | WORKING | средняя | **REFERENCE** — обоснование BranchAdapter |
| Prompt orchestrator | `docs/PROMPT_ORCHESTRATOR_SPEC.md` (348 стр.) | PARTIAL | **высокая как спека** | **EXTRACT спецификацию** |
| Agent/Mode registries | `mvp/data/agent_registry_v3.json` (55 KB, 43 агента), `mode_registry_v3.json` (25 KB, 36 режимов + 7 рецептов) | WORKING (данные) | средняя | **REFERENCE** |
| Google Docs bridge | `docs/GOOGLEDOCS_BRIDGE_PREP.md` (191 стр.) + `exportMsJson/exportMsMd/exportPatchQueue/exportProjectJson` в HTML | PARTIAL | **высокая** — форматы `fc5_bridge_v1`, `fc5_review_batch_v1`, `fc5_patch_v1` | **EXTRACT форматы**, реализацию писать заново |
| Shared GUI analysis | `docs/SHARED_GUI_EXTRACTION.md` (146 стр.) | WORKING (документ) | — | **REFERENCE — не переделывать** |
| Layout constitution | `docs/WHITECROW_LAYOUT_CONSTITUTION_V1.md` (342 стр.) | — | — | **REFERENCE** |
| Review workbench contract | `docs/agent_context/REVIEW_WORKBENCH_CONTRACT.md` (235 стр.) | — | — | **REFERENCE** |
| Quinta↔WhiteCrow LLM-мост | `docs/architecture/quinta_llm_provider_handoff.md` | — | — | **REFERENCE** |

### 1.3. Tinkuy runtime — `C:\projects\zarathustra-push` @ `a72ae99`

| COMPONENT | PATH (от `CALIFORNIAN_ID/`) | STATUS | REUSE |
|---|---|---|---|
| PipelinePack контракт | `src/californian_id/data/pipeline/pipeline.yaml`, `state_model.yaml` | WORKING | **основа графа** |
| Реестры вариантов | `data/rhetoric/genres/registry.yaml`, `data/dialogue_protocols/registry.yaml`, `data/method_packs/registry.yaml` | WORKING | **точка навешивания версий** |
| Загрузка промптов с диска | `src/californian_id/persona_layer.py:29,196`, `method_packs.py:49` | WORKING | **делает горячую подмену возможной** |
| Персоны | `data/personas/LENS_*/{system_prompt.md,values.yaml,argumentation.yaml,position_model.yaml,manifest.yaml}` + `persona.schema.json` + `_template/` | WORKING | PromptAsset-кандидаты |
| Ткань | `data/fabric/00…11_*.md` (12 ступеней) | WORKING | PromptAsset-кандидаты |
| Карты Заратустры | `data/corpus/zarathustra/{operations,scenes,constraints,risks}/*.yaml` + `schemas/scene_operation_card.schema.json` | WORKING | композиционные модули |
| Runtime control / HIL | `src/californian_id/runtime_control.py` | WORKING | интервенции + SQLite audit |
| Режимы | `src/californian_id/regimes.py` | WORKING | **источник гибридов** |
| Трассы | `runs/<run_id>/events.jsonl`, `state.json` | WORKING | телеметрия |
| Live UI | `frontend/src/App.svelte`, `components/*.svelte` (8), `wsClient.ts`, `stores.svelte.ts` | WORKING | Svelte 5 |
| Legacy UI | `src/californian_id/web_ui.py` (~2500 стр.) | WORKING | **источник переписи переменных**, содержит захардкоженные промпты |
| API | `web_ui.py` do_GET/do_POST, `ws_endpoint.py` | WORKING | нет `/api/prompts` |
| Persona assets v0.2 | `runtime_assets/personas/v0.2/personas/{C,EA,Ex,L,N8,R,S,T}/persona_constitution.md` | WORKING | **цель второй ветки** |

### 1.4. Paideia / Daedalum — `paideia-app@d2144ad`, `dedalum@6eb4c7e`

| COMPONENT | PATH | STATUS | REUSE |
|---|---|---|---|
| Плоский каталог промптов | `prompts/*.md` (35 файлов) + `api/agent.py:_load_prompt(name)` | WORKING | **REFERENCE** — простейшая модель |
| Реестр сценариев | `prompts/scenarios/_registry.yaml` (`id`, `name`, `family`, `icon`, `model_role`, `needs_case_param`, `description`) | WORKING | **ADAPT** — схема каталога вариантов |
| Серверные страницы прогонов | `templates/foundry.html`, `llm_runs.html`, `llm_run.html`, `agent_runs_list.html`, `agent_run.html`, `admin_stances.html` | WORKING | **REFERENCE** |
| Dialogue runtime | `api/dialogue_runtime/{orchestrator,router,state,lineage,diff,lab}.py` | WORKING | **REFERENCE** — есть `diff.py` и `lineage.py` |

### 1.5. Agentum — `C:\projects\protected-agent-kit` @ `db7f59c`

Статусы взяты из готового форензик-отчёта `C:\projects\agentum_archaeology_export_2026-08-11\AGENTUM_CODE_RUNTIME_ARCHAEOLOGY_HANDOFF_v0.1.md` (снимок 2026-08-11, HEAD на тот момент `e3261a7`).

| COMPONENT | STATUS (по отчёту) | REUSE |
|---|---|---|
| Cockpit | **PARTIAL** — PowerShell-генератор статического HTML + валидатор; нет демона, live-refresh, сервиса, записи | **REFERENCE** |
| Daemon / read model | DOCUMENTED_ONLY | REJECT как код |
| Project discovery | PARTIAL — хардкод-пробы внутри `scripts/build_cockpit_prototype.ps1` | REJECT |
| Prompt / LLM registry | **DOCUMENTED_ONLY** | REJECT как код, REFERENCE как онтология |
| Foundry projection | DOCUMENTED_ONLY | REFERENCE |
| Runs / run theatre | FIXTURE_ONLY | REJECT |
| Adapters / runners | FIXTURE_ONLY | REJECT |
| Profiles | IMPLEMENTED (`05_PROFILES`) | REFERENCE |
| Registries | IMPLEMENTED (`02_REGISTRIES`, `09_ECOSYSTEM`) | REFERENCE |
| Local probes | IMPLEMENTED (`Get-LiveLocalProbe`) | REFERENCE |

**Вердикт по Agentum:** как донор кода для Workbench не годится. Ценность — в онтологии (fleet/run/profile/budget/evidence/trace/risk) и в дисциплине статусов, которую этот отчёт задаёт. Утверждение handoff «Cockpit prototype / Prompt Inspector / RunProfileCore как код-донор» **не подтверждается**: RunProfileCore в Agentum не найден; реальный `RunProfileEditor` живёт в Quinta.

### 1.6. Отклонённые

| Кандидат | Причина |
|---|---|
| `C:\projects\whitecrow` | Не WhiteCrow. 3 python-модуля импорта litops-seed, без remote, без UI. **REJECT** |
| Socrates | Локально отсутствует. Drive-папки не перечисляются. **UNKNOWN** |

---

## 2. Конфликты, требующие решения

1. **React vs Svelte.** Quinta (React 19 + xyflow + elkjs) против Tinkuy live UI (Svelte 5). См. `FRONTEND_STACK_EVIDENCE_NOTE.md`.
2. **Два инспектора узла в разных стеках.** WhiteCrow `/visual/inspector/<id>` (Flask+Jinja, серверный) и Quinta `Inspector.tsx` + `RightDock` (React, клиентский). Требование handoff «не создавать второй Cockpit/RightDock/Canvas» означает: выбрать один и не писать третий.
3. **Две модели промпт-ассета.** WhiteCrow `prompt_bodies/registry.yaml` (богатая: контракт, зависимости, политика, protected blocks) против Tinkuy `registry.yaml` жанров/протоколов (плоская: id + файл). Слияние обязательно, иначе получим два несовместимых реестра.
4. **Два компилятора промпта.** WhiteCrow `PROMPT_ORCHESTRATOR_SPEC` (5 слоёв, браузерный) против Tinkuy сборки в `persona_layer.py`/`web_ui.py`. Нужен один `PromptCompilerProfile`.
5. **Дублирование графовых движков.** `@xyflow/react` в Quinta против самописного SVG в WhiteCrow FIELD_KERNEL. Для Workbench брать один.

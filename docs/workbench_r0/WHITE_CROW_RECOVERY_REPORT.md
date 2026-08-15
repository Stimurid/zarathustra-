# WHITE_CROW_RECOVERY_REPORT

**Дата:** 2026-08-15 · **Фаза:** R0 repository archaeology · **Статус гейта:** ЗАКРЫТ (визуальное тело найдено)

---

## 0. Итог одной строкой

Предыдущий вывод «WhiteCrow — маленькая Python-библиотека без интерфейса» **неверен**. Он был получен поиском по имени каталога. Реальный WhiteCrow — это репозиторий `C:\projects\conceptarticle` с remote `https://github.com/Stimurid/whitecrow.git`, и у него есть **два независимых визуальных тела**: линейка standalone HTML-ядер (FIELD_COCKPIT → FIELD_KERNEL, 12 файлов, 29–236 KB) и production Flask-воркбенч (`litops/web/`, 133 KB кода, 58 шаблонов, включая маршрут графа `/visual` и инспектор узла `/visual/inspector/<node_id>`).

Сверх того найден **работающий контроль-план промптов** — реестр, политика активации, движок разрешения и статический валидатор. Это перекрывает значительную часть того, что в требовании названо PromptAsset / ActivationBinding / static validator.

---

## 1. Почему предыдущий проход провалился

| Что было сделано | Почему это дало ложный результат |
|---|---|
| Поиск каталога с именем `whitecrow` | `C:\projects\whitecrow` существует, но это **не проект**. Это отдельный локальный git-репозиторий без remote, 3 python-модуля (`litops_import.py`, `first_workset.py`, `__init__.py`), 2 JSON-импорта, 1 тест. Это **потребитель seed-пакета**, а не WhiteCrow. |
| Не проверен `git remote` у соседних репозиториев | `conceptarticle`, `conceptarticle-prompt-bodies`, `conceptarticle__clean_recovery_20260721` — все три указывают на `github.com/Stimurid/whitecrow.git`. Имя каталога расходится с именем проекта. |
| Не выполнен content-first поиск | Поиск по сигнатурам `FIELD_KERNEL`, `FieldAtlas`, `attractor`, `field_projection` немедленно выводит на визуальное тело. |

**Вывод для процесса:** в этом рабочем пространстве имя каталога систематически не совпадает с именем проекта (`conceptarticle`→whitecrow, `protected-agent-kit`→Agentum, `quinta`→TRIZ Inventive Memory Bench, `zarathustra-push/CALIFORNIAN_ID`→Tinkuy runtime). Поиск по имени каталога здесь запрещён как метод.

---

## 2. Область поиска

### 2.1. Перечислено локальное пространство

`C:\projects` — 39 каталогов верхнего уровня. Из них 23 являются git-репозиториями. Собраны: путь, remote, ветка, HEAD, число веток.

Репозитории, релевантные задаче:

| REPO | PATH | REMOTE | BRANCH | HEAD | DATE |
|---|---|---|---|---|---|
| whitecrow | `C:\projects\conceptarticle` | `Stimurid/whitecrow.git` | main | `a140dca` | 2026-08-12 |
| whitecrow (wt) | `C:\projects\conceptarticle-prompt-bodies` | тот же | `feature/prompt-body-registry-v0-1` | `b49b4c9` | — |
| whitecrow (wt) | `C:\projects\conceptarticle__clean_recovery_20260721` | тот же | detached | `86fb282` | — |
| quinta | `C:\projects\quinta` | `Stimurid/quinta.git` | main | `3963df4` | 2026-06-27 |
| tinkuy runtime | `C:\projects\zarathustra-push` | `Stimurid/zarathustra-.git` | main | `a72ae99` | 2026-08-12 |
| paideia | `C:\projects\paideia-app` | `Stimurid/paideia.git` | m1-integrated-runtime | `d2144ad` | 2026-08-13 |
| dedalum | `C:\projects\dedalum` | `Stimurid/dedalum.git` | main | `6eb4c7e` | — |
| agentum | `C:\projects\protected-agent-kit` | `Stimurid/Agentum.git` | main | `db7f59c` | — |
| (не проект) | `C:\projects\whitecrow` | нет remote | main | `12ae796` | — |

Ветки WhiteCrow: `main`, `feature/prompt-body-registry-v0-1`, `integration/prompt-body-merge`, `spinout/litops-mvp`, `agentum/guard-only-runtime-slice`, `backup/agentum-guard-install-bom-crlf-038cc5e`. Три worktree. Донорские репозитории не изменялись.

### 2.2. Content-first сигнатуры (выполнено)

Искалось регистронезависимо по всему `C:\projects`: `whitecrow`, `white_crow`, `white-crow`, `FieldKernel`, `FIELD_KERNEL`, `FieldAtlas`, `SelectionWorkbench`, `FieldCanvas`, `field_projection`, `attractor`, `gradient`, `phase_boundary`, `wavelet`, `density field`, `manuscript trajectory`, `field_text`, `field_candidate`, `projection`, `spindle`, `canvas`, `workbench`, `Cockpit`, `PromptInspector`, `RunProfile`, `fleet`.

Первая группа дала 120+ файлов (лимит), вторая — 80+ (лимит). Совпадения сконцентрированы в `conceptarticle*` worktrees.

### 2.3. Drive

Проверены три якоря из handoff:

| Drive ID | Название | Результат |
|---|---|---|
| `1qNNDOgws645rOSoEekgaO-TvORH1YHYP7ZICCIPOugw` | SOCRATES_TINKUY_PROMPT_RAG_WORKBENCH_REQUIREMENTS_v0.1_candidate | **ДОСТУПЕН**, прочитан. Владелец `timurid@gmail.com`, создан 2026-08-15 11:26 UTC |
| `1xvaBNQFJ-uOw4c8HVdP9J96rRTDPsJtKAV0EQ9KDzes` | литраскоп — shared Litops · WhiteCrow · Kairoscope architecture | **НЕДОСТУПЕН** из аккаунта `dc@shchuk.in`: `Requested entity was not found` |
| `1d2734hLI-AiE5l-x5tm-2aZpXcXGkSbB42J6Ea0WI4M` | whitecrow_export_builder_v0_1 | **НЕДОСТУПЕН** по ID, но **восстановлен локально** — см. §4.5 |

Fulltext-поиск по Drive (`fullText contains 'WhiteCrow' or title contains 'литраскоп'`) вернул только несвязанные документы. Папки Сократа `1aG3RvdCuIqu5Rq3NUFvuF_k-Dgu2LwdL` (10_INTERFACE_AND_PRODUCT_SURFACES) и `1MKDBQIUE53OaYFDROYfDJDVR-Ckj5aYC` (13_RELEASES_HANDOFFS_AND_EXPORTS) существуют, владелец `timurid@gmail.com`, `canAddChildren: false`, **перечисление дочерних элементов возвращает пусто**.

**Вывод по Drive:** корпус WhiteCrow и сборка Сократа живут на аккаунте `timurid@gmail.com` и этому агенту недоступны. Это ограничение доступа, а не отсутствие материала. Локальные репозитории перекрывают потребность полностью.

---

## 3. Что найдено: визуальное тело WhiteCrow

### 3.1. Линейка standalone field-ядер — `C:\projects\conceptarticle\mvp\`

Полнофункциональные одностраничные HTML-приложения (весь STATE, рендер, LLM-оркестратор — внутри файла). Хронология развития очевидна из размеров и дат.

| Файл | KB | Дата | Роль |
|---|---|---|---|
| `FULL_PATH_FIELD.html` | 69 | 11.05 | ранний полный путь |
| `UNIVERSAL_INGEST_FIELD.html` | 98 | 11.05 | универсальный приём материала |
| `CONCEPT_PLAYGROUND.html` | 99 | 11.05 | песочница концептов |
| `ANCHOR_INSPECTION.html` | 33 | 11.05 | инспектор якорей |
| `CALIBRATION_INSPECTION.html` | 27 | 11.05 | инспектор калибровки |
| `FIELD_COCKPIT.html` … `_v5_1.html` | 85→172 | 11–12.05 | 6 итераций кокпита |
| `FIELD_KERNEL_v6.html` | 164 | 12.05 | ядро v6 + LLM |
| `FIELD_KERNEL_v6_1.html` | 184 | 13.05 | v6.1 LLM |
| `FIELD_KERNEL_v6_2.html` | 236 | 13.05 | v6.2 agent-layer, **самый крупный** |
| `FIELD_KERNEL_v6_3.html` | 182 | 15.05 | v6.3 |
| `FIELD_KERNEL_v6_3_1.html` | 225 | 18.05 | **последний** |
| `LITOPS_MVP_v0_1/v0_2.html` | 29/52 | 23.06 | отдельная линия litops MVP |

Сопровождающие данные: `mvp/data/agent_registry_v1..v3.json` (21/51/55 KB), `mvp/data/mode_registry_v1..v3.json` (11/31/25 KB), `mvp/data/demo_worksets_v2.json`.

Документация на каждую версию — тройками REPORT / RUNBOOK / VALIDATION в `docs/`: `FIELD_COCKPIT_V2..V5_1`, `FIELD_KERNEL_V6`, `V6_1_LLM`, `V6_2_AGENT`, плюс HANDOFF-документы `V6_2`, `V6_3`, `V6_3_1`, `V6_3_1_PASS2`, и концепт `FIELD_KERNEL_V6_CONCEPT.md`.

**Статус: WORKING** (самодостаточные HTML, запускаются через `.claude/launch.json` → конфигурация `whitecrow-static`, `python -m http.server 8765`).

### 3.2. Production web-воркбенч — `C:\projects\conceptarticle\litops\web\`

| Компонент | Размер | Что делает |
|---|---|---|
| `app.py` | 133 KB | Flask-приложение, ~120 маршрутов, auth-гейт, POST-действия |
| `visual_data.py` | 37 KB | **read-only проекционный адаптер**: `build_field_graph()`, `build_line_lanes()`, `build_next_actions()`, `build_inspector()` + 12 типизированных `_inspect_*` резолверов |
| `templates/` | 58 файлов | Jinja2, включая `visual.html` (23 KB), `weekly_review.html` (19 KB), `source_detail.html` (14 KB) |

Ключевые маршруты для нашей задачи:

- `GET /visual` — граф-поверхность (LEFT field graph / CENTER line lanes / BOTTOM action counters)
- `GET /visual/inspector/<path:node_id>` — **инспектор узла по id с цепочкой provenance**
- `GET /validation`, `/validation/<organ_run_id>` — статусы прогонов органов
- `GET /extraction-compare`, `/extraction-runs/<id>` — **сравнение вариантов извлечения**
- `POST /action/candidate-accept|reject|add|promote-candidates` — **жизненный цикл кандидатов accept/reject**
- `GET /dictionary-graph`, `/dictionary-graph/node/<id>` — типизированный граф + узел
- `GET /trace`, `/jobs`, `/attention`, `/needs-action`, `/integrity`

`visual_data.py` документирует контракт явно: «No mutation, no registry writes, no file writes», переиспользует существующие продюсер-операции дословно. Это ровно та дисциплина read-model, которую требует Workbench.

**Статус: WORKING** (`.claude/launch.json` → `litops-web-v1`, `python -m litops.web.app`, порт 8080; есть `docs/WHITECROW_PROD_DEPLOY.md`, `scripts/deploy_whitecrow_prod.ps1`).

### 3.3. Контроль-план промптов — `C:\projects\conceptarticle\prompt_bodies\` + `litops/prompt_engine.py`

Это самая важная находка после визуального тела.

| Артефакт | Размер | Содержание |
|---|---|---|
| `prompt_bodies/registry.yaml` | 53 KB | канонический реестр ~64 prompt-bodies |
| `prompt_bodies/activation_policy.yaml` | 12 KB | политика активации: `server_manual`, `workpack_manual`, `auto_run_allowed`, `review_required`, `budget_risk`, `allowed_scopes`, `output_destination` |
| `prompt_bodies/bodies/**` | 64 файла, 2–41 KB | тела промптов, 10 категорий (00_intake_corpus … 09_semantic_resolution) |
| `prompt_bodies/templates/organ_prompt_body_template_v0_1.md` | 2 KB | **структурный шаблон нового промпта** |
| `prompt_bodies/backlog.yaml` | 2 KB | ещё не написанные промпты |
| `prompt_bodies/generated/registry.generated.json` | 63 KB | сгенерированный каталог |
| `litops/prompt_engine.py` | 15 KB | «Prompt Invocation Core — L1 engine»: загрузка реестра и политики, резолв по `prompt_id`, проверка правил активации, сборка invocation manifest |
| `scripts/validate_prompt_bodies.py` | — | **статический валидатор** |
| `docs/PROMPT_ORCHESTRATOR_SPEC.md` | 348 строк | спецификация 5-слойной компиляции промпта |

Поля записи реестра (проверено по факту в `registry.yaml`):

```
prompt_id · version · status(draft|candidate) · path · organ_id · template_family
operation_class · transition · context_level · runtime_allowed · composition_allowed
category · depends_on[] · upstream_objects[] · output_object
runtime_block_policy · external_workspace_sync_status · notes
```

Это уже **PromptAsset с контрактом** (`upstream_objects` → `output_object`), **зависимостями** (`depends_on`), **статусом** и **политикой рантайма**.

Проверки валидатора (из `validate_prompt_bodies.py`): `REQUIRED_METADATA_FIELDS`, `REQUIRED_SECTIONS`, соответствие `prompt_id` имени файла, соответствие H1 имени файла, наличие ровно одного `RUNTIME_PROMPT_START` и одного `RUNTIME_PROMPT_END`, запрет размещения тел под запрещёнными путями, наличие `.litopsignore` с обязательными путями.

**`RUNTIME_PROMPT_START` / `RUNTIME_PROMPT_END` — это уже реализованный механизм protected blocks / editable regions.** В рантайм-вызов разрешено вставлять только блок между маркерами; остальной файл — метаданные, контракт, история, тесты, предназначенные для `PromptRegistryManager`, `PromptAssembler`, аудита и версионирования.

Отдельно зафиксирован **anti-ingestion boundary**: prompt-bodies никогда не индексируются в RAG, не попадают в Sources, не зеркалируются в RAW/INBOX. Это прямой ответ на риск «промпты попали в собственный корпус».

**Статус: IMPLEMENTED** (реестр + политика + движок + валидатор существуют и связаны).

### 3.4. Компилятор промпта — `docs/PROMPT_ORCHESTRATOR_SPEC.md`

Спецификация ровно того, что в требовании названо PromptCompiler:

```
final_system_prompt =
    base_mode_instruction(mode)
  + Σ active_canonical_inject[i]      // упорядочено по слоям F1→F6
  + Σ active_override_inject[j]       // over-agents всегда последними
  + constraint_block(active_constraints)
```

Control Plane v1: 43 агента, 8 семейств, 36 режимов, 7 рецептов. 13 типов целей (field · field_slice · relation_cluster · concept_center · visual_configuration · projection_block · field_text_block · manuscript_block · manuscript_section · source_fragment · branch · review_issue · artifact_path). 15 типов эффектов (inspect · reframe · synthesize · project · patch · fork · compile · ground · verify · adapt · translate · split · annotate · route_update · pressure_only). Уровни полномочий: observe · suggest · patch · apply_as_alternative · enforce · veto.

Подстановка переменных `{{...}}` из STATE с предупреждением в консоль для незаполненных. Стейдж-гейты для over-агентов enforced.

**Статус: SPEC_ONLY на уровне документа, PARTIAL в коде** — реализация живёт внутри `FIELD_KERNEL_v6_*.html` (браузерный оркестратор, «runs entirely in-browser, no backend»), а не как переиспользуемый модуль.

### 3.5. Google Docs bridge — `docs/GOOGLEDOCS_BRIDGE_PREP.md`

191 строка. Отображение сущностей Cockpit → GDocs, два экспортных пути (через `manuscript.md` + Pandoc и через `manuscript.bridge.json`), формат `fc5_bridge_v1`, формат обратного импорта `fc5_review_batch_v1` с алгоритмом сопоставления комментария с блоком по `anchor_text` (первые 60 символов, нормализация пробелов, lowercase), формат `patch_queue.json` (`fc5_patch_v1`, только реверсивные операции), черновик Apps Script адаптера `bridge/gdocs_adapter.gs`, заметка про CORS и необходимость серверного моста.

Раздел «What's Already Working in v5.1»: `exportMsJson`, `exportMsMd`, `exportPatchQueue`, `exportProjectJson`, `importProjectJson` — **✓ Working**. `importReviewBatch` — **stub**. GDocs API — не начато. Apps Script — только спецификация.

**Статус: PARTIAL** (экспорт работает, импорт комментариев — заглушка, OAuth не начат).

### 3.6. Field Projection Engine — `docs/FIELD_PROJECTION_ENGINE_SPEC.md`

58 строк. Четыре режима проекции одного корпуса абзацев: **Mosaic** (CSS-грид плиток), **Cross** (крест 4 квадранта + центр), **Radial** (SVG, до 8 узлов по окружности, лучи цвета активной связи), **Linearized** (полный текст, сортировка field→node→synthesis).

Это прямое подтверждение тезиса требования: **не всё есть node-edge граф**. Одни и те же объекты проецируются четырьмя разными способами, и переключение проекции — операция интерфейса.

**Статус: WORKING** (реализовано в `FIELD_KERNEL_v6*.html`, специфицированы CSS-классы и функции `getFPEItems`, `selectFPETile`, `promptToMs`, `confirmToMs`).

### 3.7. Прочие спецификации визуального слоя (все PRESENT в main worktree)

| Файл | Строк | Что даёт |
|---|---|---|
| `docs/WHITECROW_LAYOUT_CONSTITUTION_V1.md` | 342 | конституция раскладки |
| `docs/LITOPS_WEB_WORKBENCH_v0_1.md` | 328 | спецификация web-воркбенча |
| `docs/agent_context/REVIEW_WORKBENCH_CONTRACT.md` | 235 | контракт review-воркбенча |
| `docs/agent_context/UI_CAPABILITY_MATRIX.md` | 59 | матрица возможностей UI |
| `docs/SHARED_GUI_EXTRACTION.md` | 146 | **уже выполненный анализ общих GUI-паттернов между WhiteCrow и Quinta** — S1…S7 |
| `docs/GUI_ARCHITECTURE_CONCEPTARTICLE_v1.md` | — | архитектура GUI |
| `docs/CANONICAL_LAYOUT_PROPOSAL.md` | — | каноническая раскладка |
| `docs/POLYFIELD_KERNEL_PROPOSAL.md` | — | полиполевое ядро |
| `docs/architecture/quinta_llm_provider_handoff.md` | — | **мост WhiteCrow ↔ Quinta по LLM-провайдеру** |
| `docs/agent_context/UI_ROUTE_MIGRATION_MAP.md`, `UI_2A_PLAN.md`, `UI_2B_PLAN.md`, `CLAUDE_UI_IMPLEMENTATION_PLAN.md` | — | планы и карта миграции маршрутов UI |

`SHARED_GUI_EXTRACTION.md` особенно важен: он уже зафиксировал семь общих паттернов (S1 Object Inspector, S2 append-only timeline, S3 seed input, S4 artifact panel, S5 agent status, S6 copilot/suggested moves, S7 export) и явно снял блокер «TRIZ GUI unknown → RESOLVED». То есть работа по извлечению общей оболочки уже начиналась.

---

## 4. Классификация найденного

| Компонент | Путь (repo `whitecrow`, worktree `C:\projects\conceptarticle`, `main@a140dca`) | Статус |
|---|---|---|
| Field Kernel HTML (v6–v6.3.1) | `mvp/FIELD_KERNEL_v6*.html` | WORKING |
| Field Cockpit HTML (v1–v5.1) | `mvp/FIELD_COCKPIT*.html` | WORKING (superseded) |
| Field Projection Engine (4 проекции) | внутри `FIELD_KERNEL_v6*.html` + `docs/FIELD_PROJECTION_ENGINE_SPEC.md` | WORKING |
| Prompt Orchestrator (5-слойная сборка) | внутри HTML + `docs/PROMPT_ORCHESTRATOR_SPEC.md` | PARTIAL (в браузере, не модуль) |
| Agent/Mode registries v3 | `mvp/data/agent_registry_v3.json`, `mode_registry_v3.json` | WORKING (данные) |
| Web workbench Flask | `litops/web/app.py` | WORKING |
| Visual projection adapter | `litops/web/visual_data.py` | WORKING |
| Node inspector | `/visual/inspector/<node_id>` + `_inspect_*` | WORKING |
| Prompt body registry | `prompt_bodies/registry.yaml` | IMPLEMENTED |
| Activation policy | `prompt_bodies/activation_policy.yaml` | IMPLEMENTED |
| Prompt invocation engine | `litops/prompt_engine.py` | IMPLEMENTED |
| Static validator | `scripts/validate_prompt_bodies.py` | IMPLEMENTED |
| Protected blocks (RUNTIME_PROMPT_START/END) | конвенция + проверка валидатором | IMPLEMENTED |
| Prompt body template | `prompt_bodies/templates/organ_prompt_body_template_v0_1.md` | IMPLEMENTED |
| Candidate lifecycle accept/reject | `POST /action/candidate-*` в `app.py` | WORKING |
| Variant comparison | `/extraction-compare` | PARTIAL (сравнение прогонов извлечения, не промптов) |
| Google Docs bridge | `docs/GOOGLEDOCS_BRIDGE_PREP.md` + экспортёры в HTML | PARTIAL |
| Field Atlas / Selection Workbench | упомянуты в `whitecrow_export_builder_v0_1.md` как downstream-поверхности | SPEC_ONLY |
| Relief / gradients / attractors / wavelet / density fields | сигнатуры встречаются в prompt-bodies и docs; отдельного рендерера не найдено | SPEC_ONLY |

### 4.5. Восстановление Drive-якоря B локально

Документ `whitecrow_export_builder_v0_1` (Drive ID `1d2734hLI-…`, недоступен по ID) **найден локально** как `prompt_bodies/bodies/06_field_whitecrow/whitecrow_export_builder_v0_1.md` (32 KB) и присутствует в реестре как `prompt_id: whitecrow_export_builder_v0_1`, `organ_id: whitecrow_bridge_organ`, `template_family: field_projection`, `runtime_allowed: guarded`.

Из его содержания подтверждаются названные в handoff downstream-поверхности и, дополнительно, имена подсистем-потребителей: `PromptRegistryManager`, `PromptAssembler`, `ClaudeCodeDeveloper`, `WhiteCrow Bridge subsystem`, `Field Kernel subsystem`, `Audit/Verifier subsystem`, `Vault/Obsidian subsystem`.

Смежные тела той же категории `06_field_whitecrow`: `field_text_projector_v0_1.md` (32 KB), `field_candidate_miner_v0_1.md` (24 KB), `relation_tension_map_builder_v0_1.md` (28 KB), `document_role_resolver_v0_1.md` (41 KB).

---

## 5. Что осталось нерешённым

1. **Drive-корпус WhiteCrow недоступен** этому агенту (аккаунт `dc@shchuk.in` против владельца `timurid@gmail.com`). Якоря A и B по ID не открываются. Требуется либо расшаривание, либо работа только по локальным репозиториям.
2. ~~Папки сборки Сократа пусты при перечислении~~ — **ИСПРАВЛЕНО, см. §8.**
3. **Field Atlas и Selection Workbench как исполняемые поверхности не найдены** — только упоминания в prompt-bodies. Возможно, они существуют только на уровне спецификации.
4. **Рендереров рельефа, градиентов, аттракторов, вейвлет-срезов и плотностных полей в коде нет.** Найдены четыре проекции FPE (Mosaic/Cross/Radial/Linearized) — это меньше, чем декларирует полевая онтология. Разрыв между декларируемой онтологией и реализацией зафиксирован как открытый.
5. **История git по удалённым UI-пакетам не разбиралась подробно** — ветки перечислены, но поиск по `git log`/деревьям удалённых компонентов не проводился, поскольку визуальное тело нашлось в рабочем дереве и необходимость отпала.

---

## 6. Прямые кандидаты на переиспользование

| Кандидат | Почему |
|---|---|
| `prompt_bodies/` модель целиком (реестр + политика + шаблон + маркеры + валидатор) | Готовая, работающая модель PromptAsset с контрактом, зависимостями, статусом и protected blocks. Переносится в Тинкуй как схема, а не как код. |
| `litops/prompt_engine.py` | Python, без UI-зависимостей. Резолв + проверка активации + сборка invocation manifest. Ближайший к WorkbenchCore код из всего найденного. |
| `litops/web/visual_data.py` | Образец строгого read-model адаптера графа и инспектора с provenance. Дисциплина «no mutation» — то, что нужно для телеметрии Workbench. |
| `docs/PROMPT_ORCHESTRATOR_SPEC.md` | Готовая формула компиляции. Переносится как спецификация PromptCompiler. |
| `docs/GOOGLEDOCS_BRIDGE_PREP.md` + форматы `fc5_*` | Готовые форматы моста и алгоритм сопоставления комментариев. Экономит проектирование раздела 13 требований. |
| `docs/SHARED_GUI_EXTRACTION.md` | Уже выполненный анализ пересечения с Quinta. Не повторять. |
| `FIELD_PROJECTION_ENGINE_SPEC.md` | Доказательство необходимости BranchAdapter с несколькими проекциями. |

---

## 7. Ответ на вопрос гейта

**Гейт закрыт по варианту A.** Визуальное тело WhiteCrow локализовано, инвентаризировано, классифицировано по статусам, снабжено точными путями и коммитом. Негативное доказательство требуется только для Drive-слоя и для Field Atlas / Selection Workbench как исполняемых поверхностей — оно приведено в §5 с указанием, где именно искалось.

---

## 8. КОРРЕКЦИЯ v0.2 (2026-08-15) — состояние Сократа

Формулировка «папки Сократа пусты» в §5.2 первой редакции была **неверна** и повторяла ту же методологическую ошибку, что и с WhiteCrow: отсутствие доступа выдано за отсутствие объекта.

Технически произошло следующее. Запрос `parentId = '<folder_id>'` вернул `{}` для обеих папок. Из пустого перечисления был сделан вывод «папка пуста». Правильный вывод: **перечисление дочерних элементов не работает для этих папок из моего аккаунта** — они принадлежат `timurid@gmail.com` и имеют `canAddChildren: false`. Прямой доступ по идентификатору файла при этом работает.

Проверено прямыми запросами метаданных после получения корректных ID:

| Объект | Drive ID | Проверено |
|---|---|---|
| `07_SOCRATES_PIPELINE_PACK` | `10WHFJzLZYP6JblzmZJBk1X3_sdETU4A2` | **СУЩЕСТВУЕТ**, папка, создана 2026-08-14 23:10, владелец `timurid@gmail.com` |
| `10_INTERFACE_AND_PRODUCT_SURFACES` | `1aG3RvdCuIqu5Rq3NUFvuF_k-Dgu2LwdL` | **СУЩЕСТВУЕТ**, папка, создана 2026-08-14 23:10 |
| `13_RELEASES_HANDOFFS_AND_EXPORTS` | `1MKDBQIUE53OaYFDROYfDJDVR-Ckj5aYC` | **СУЩЕСТВУЕТ**, папка |
| `SOCRATES_…REQUIREMENTS_v0.1_candidate` | `1qNNDOgws645rOSoEekgaO-TvORH1YHYP7ZICCIPOugw` | **ЧИТАЕТСЯ**, документ, 9947 байт |
| `SOCRATES_…CLAUDE RESEARCH HANDOFF v0.1 candidate` | `1tDvFaSZBS-_tAauXnt4X4RJo7ONt6jHhRAFpP24g6Xw` | **СУЩЕСТВУЕТ**, документ, 19090 байт, создан 2026-08-15 11:41 |

**Правильный статус Сократа:**

> Architectural / constitutional build **существует и активно собирается**. Executable PipelinePack **ещё не материализован**: скелет `07_SOCRATES_PIPELINE_PACK` развёрнут полностью (`steps/`, `prompts/`, `schemas/`, `contracts/`, `policies/`, `state_and_memory/`, `runtime_profiles/`, `examples/`, `tests/`, `evaluators/`, `traces/`, `reference_harness/`, `host_bindings/`), но `steps/` и `prompts/` пока пусты.
> Последний подтверждённый build status: **`G-S19 COMPLETED_CANDIDATE`**, следующий — `G-S20 HUMAN OPERATION, OWNERSHIP, COMMITMENT AND DEVELOPMENT`.

**Следствие для Workbench:** ожидание материализации Сократа не является блокером. Сократ становится **первым приоритетным BranchAdapter** по мере материализации PipelinePack. Первый вертикальный срез строится на реальном исполняемом узле Tinkuy runtime, Заратустра остаётся тестом переносимости на вторую ветку.

Требование «выбери Заратустру вместо Сократа» из первой редакции **снято**.

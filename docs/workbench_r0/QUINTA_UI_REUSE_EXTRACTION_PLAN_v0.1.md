# QUINTA_UI_REUSE_EXTRACTION_PLAN v0.1

**Дата:** 2026-08-15 · Источник: `C:\projects\quinta` @ `3963df4` (2026-06-27), ветка `main`, рабочее дерево чистое.
Стек: React 19.2.5 + Vite + TypeScript. Зависимости рантайма: `react`, `react-dom`, `@xyflow/react ^12.11.0`, `elkjs ^0.11.1` (объявлен, **не используется**).
Скрипты: `dev` (vite), `build` (`tsc -b && vite build`), `lint` (eslint). Тестов: 25 файлов.

**Правило: донорский репозиторий не изменяется. Извлечение — копирование в новый проект.**

---

## 1. `RightDock.tsx` — прямое переиспользование

| Параметр | Значение |
|---|---|
| Путь | `src/components/RightDock.tsx` |
| Объём | 164 строки |
| Импорты | **только `react`** — `useState, useCallback, useRef, useEffect, type ReactNode`. Ноль доменных импортов |
| Доменная привязка | отсутствует, кроме типа `DockTab = 'inspector'\|'copilot'\|'agents'\|'runs'\|'debug'` |
| Владение состоянием | гибридное: `width` и `activeTab` контролируемые (через props) либо внутренние |
| Ожидания от API | нет — чистый layout |
| CSS | **23 правила `.right-dock*` в `src/styles.css`, начиная со строки 5518** |

**Что копируется:** файл целиком + 23 CSS-правила.

**Единственный шов адаптации:** расширить `DockTab` под вкладки воркбенча:

```ts
export type DockTab = 'inspector' | 'editor' | 'copilot' | 'contract' | 'runs' | 'compiled';
```

**Поведение подтверждено чтением кода:** перетаскивание за ручку с зажимом `Math.max(minWidth, Math.min(w, window.innerWidth * maxWidthPercent / 100))`; `maxWidthPercent` по умолчанию 70; схлопывание в 40 px с вертикальной полосой иконок; режим `overlay` переводит в `position: absolute; z-index: 100`. Требование «треть по умолчанию, до двух третей, сворачивается» выполняется параметрами `defaultWidth` и `maxWidthPercent` без правки кода.

**Решение: COPY. Оценка работы — часы, не дни.**

---

## 2. Графовая подложка — адаптация

### 2.1. Что есть

| Файл | Строк | Импорты | Оценка |
|---|---|---|---|
| `components/base/AgentMapView.tsx` | 290 | `@xyflow/react`: `ReactFlow, ReactFlowProvider, Background, Controls, MiniMap, Position` + доменные реестры агентов | **лучший образец generic-оболочки графа** |
| `components/pdf/SpindleCanvas.tsx` | 255 | xyflow + `ProblemDynamicsField`, `SpindleAction`, 10 компонентов узлов, `PDFInspector`, 3 оверлея, `viewportDiagBus` | сильная доменная связанность |
| `components/pdf/SpindleLayout.ts` | 459 | `Node, Edge` из xyflow + `ProblemDynamicsField, SolutionFamily` | раскладка доменная, колоночная, рукописная |
| `components/pdf/edges/SemanticEdge.tsx` | 134 | `BaseEdge, EdgeLabelRenderer, getBezierPath` + один доменный тип `PDFEdgeKind` | **почти generic** |
| `components/pdf/nodes/*` | 9 файлов | доменные | образцы формы |
| `components/pdf/overlays/*` | 3 файла | доменные | не нужны в первом срезе |

### 2.2. Честная оценка

`elkjs` в зависимостях есть, но в коде не вызывается ни разу — `AgentMapView.tsx:12` прямо говорит «Layout is deterministic column-based (no ELK for first cut)». Значит **автораскладки пайплайна в наследство не достаётся**. Для линейного пайплайна из 13 шагов это не проблема: колоночная детерминированная раскладка даже предпочтительнее, потому что порядок шагов задан `pipeline.yaml` и не должен «плавать».

### 2.3. План извлечения

| Действие | Что |
|---|---|
| **COPY** | шаблон оболочки из `AgentMapView.tsx`: `ReactFlowProvider` + `ReactFlow` + `Background` + `Controls` + `MiniMap`, обработчики выделения узла |
| **COPY с заменой одного типа** | `SemanticEdge.tsx` — заменить `PDFEdgeKind` на `WorkbenchEdgeKind` |
| **ADAPT** | один узловой компонент `PipelineNodeComponent` вместо девяти доменных; форма и стилистика берутся с `MechanismNodeComponent` |
| **NEW** | `PipelineLayout.ts` — колоночная раскладка из `pipeline.yaml` с развилками по `input_mode` |
| **SKIP** | `SpindleCanvas.tsx`, `overlays/*`, восемь остальных типов узлов, `viewportDiagBus` |

**Оценка: дни, не недели.** Дорогая часть — интеграция xyflow — уже отработана и видна в рабочем коде.

---

## 3. `FieldCopilot.tsx` — адаптация

| Параметр | Значение |
|---|---|
| Путь | `src/components/FieldCopilot.tsx`, 310 строк |
| Импорты | `../types`: `LLMMessage, Branch, FieldAction, SessionState` · `../llm/types`: `LLMProvider, LLMActionProposal` · `../llm/actionRegistry` · `../llm/debugLog` |

**Что переиспользуется без изменений — механика применяемого предложения:**

```ts
provider: LLMProvider
onApplyProposal?: (proposal: LLMActionProposal) => void
onApplyAction: (action: FieldAction) => void
```

Генерация возвращается не текстом, а объектом-предложением, которое применяется явным действием. Это и есть требуемые INSERT ALL / INSERT SELECTION / APPLY DIFF — предложение никогда не переписывает источник молча.

**Швы адаптации:**

| Что заменить | На что |
|---|---|
| `Branch`, `SessionState`, `FieldAction` | `WorkbenchContext` = `{asset, variant, node, selection_in_editor, selection_in_output, edit_history, contracts, recent_runs}` |
| `getSmartQuickButtons(branch)` | контекстные кнопки воркбенча: «объясни этот блок», «что зависит от него», «почему извлеклись эти чанки», «переформулируй выделенное», «сравни с baseline» |
| `getActionRegistry()` | реестр действий воркбенча: `insert_all`, `insert_selection`, `apply_diff`, `copy_all` |
| `pushDebugEntry` | оставить как есть |

**Что копируется целиком:** `src/llm/provider.ts`, `types.ts`, `anthropicProvider.ts`, `openAICompatibleProvider.ts`, `mockProvider.ts`, `llmSettings.ts`, `debugLog.ts`.

**Решение: ADAPT компонент, COPY провайдерный слой.**

---

## 4. `AgentFoundryView.tsx` — модель, не код

109 строк. Ценность — не в разметке, а в трёх решениях:

1. Статусы `active / draft / deprecated / needs_review` с цветовой кодировкой.
2. Уровни `L0–L3` как фильтр списка.
3. `getCompatibilitySummary()` → `{totalPairs, compatible, conflicts}` — сводка совместимости пар агентов.

Третье — прямой прообраз `contract_check` из `WORKBENCH_PROJECTION_API_v0.1`: проверка стыкуемости входов и выходов соседних ассетов.

**Решение: REFERENCE. Разметку не копировать, модель статусов и сводку совместимости — воспроизвести.**

---

## 5. `RunProfileEditor.tsx` — обязательный паттерн

189 строк. В шапке файла зафиксировано правило, которое обязано перейти в воркбенч дословно:

> «Apply dispatches `RUN_CONTROL_UPDATE` only — no provider call, no Auto-to-N, no draft verification.»

То есть: **редактирование и применение никогда не вызывают провайдера как побочный эффект.** Проверки запускаются только явными кнопками. Для воркбенча это критично: сохранение варианта не должно тратить токены.

Плюс паттерн `draft` → `useEffect(() => setDraft(current), [source])` → `apply()`.

**Решение: REFERENCE как инвариант поведения.**

---

## 6. Что не берём

| Компонент | Причина |
|---|---|
| `PipelineBuilder.tsx` | TRIZ-пресеты зашиты в константы, к пайплайну Тинкуя отношения не имеют |
| `PromptImportView.tsx` | работает на `mockPromptSources`; сценарий импорта нужен, но не в первом срезе |
| `RunTraceStudio.tsx` | понадобится на стадии телеметрии, не сейчас |
| `overlays/*`, `MetricsDashboard` | стадия телеметрии |
| `Board.tsx`, `BranchCard.tsx`, `CommandPalette` и прочая доменная TRIZ-поверхность | вне задачи |

---

## 7. Порядок извлечения

1. Создать проект воркбенча: Vite + React 19 + TS, зависимости `react`, `react-dom`, `@xyflow/react`. `elkjs` **не тянуть** — он не используется и в Quinta.
2. Скопировать `RightDock.tsx` + 23 CSS-правила. Расширить `DockTab`. Проверить ресайз и схлопывание.
3. Скопировать провайдерный слой `src/llm/*`.
4. Собрать оболочку графа по образцу `AgentMapView.tsx`, один тип узла, `SemanticEdge` с заменённым типом.
5. Написать `PipelineLayout.ts` под линейный пайплайн с развилками.
6. Адаптировать `FieldCopilot` под `WorkbenchContext`.
7. Подключить CodeMirror 6 как редактор — своего в Quinta нет.

**Что придётся написать с нуля:** редактор с областями protected/editable, SOURCE/COMPILED переключатель с `source_map`, панель контрактов, лента жизненного цикла варианта.

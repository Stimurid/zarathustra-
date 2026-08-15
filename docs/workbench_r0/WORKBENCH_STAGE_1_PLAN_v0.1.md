# WORKBENCH_STAGE_1_PLAN v0.1

**Дата:** 2026-08-15 · Пишется после A–F и опирается на них. Реализация не начата.

---

## Stage 0 — поведение-сохраняющая подготовка

Правило стадии: **ни одно изменение не меняет наблюдаемое поведение рантайма.** Каждый пункт либо только добавляет, либо доказан эквивалентностью.

### 0.1. Золотые фикстуры эквивалентности для захардкоженных промптов

Цель: вынести промптовые строки из Python в `PromptAsset`, не изменив ни одного символа того, что уходит в модель.

**Затронутые функции**

| Функция | Файл | Вариантов |
|---|---|---|
| `_assembly_instruction(mode)` | `web_ui.py` ~1419–1446 | 6: synthesis, verdict, dissent_forward, diagnostic, projective, **roast** |
| `_grounding_instruction(mode)` | `web_ui.py` ~1402 | 3: strict_card, balanced, freer_synthesis |
| `CRITIQUE_REGIMES[*].directness_hint` | `regimes.py:22–36` | 3 |
| `VARIATION_REGIMES[*].prompt_hint` | `regimes.py:41–58` | 3 |
| `_DEFAULT_SCENE_READING_PROMPT` | `zarathustra.py` ~992 | 1 |
| `_DEFAULT_ROUTE_PROMPT` | `zarathustra.py` ~979 | 1 |
| `_DEFAULT_CLOSING_SPEECH_PROMPT` | `zarathustra.py` ~985 | 1 |

Итого **18 строковых значений**.

**Процедура на каждое значение**

```
1. ЗАПИСЬ ЭТАЛОНА
   old_output = <функция>(<аргумент>)
   сохранить в tests/gold/workbench/prompt_extraction/<id>.golden.txt
   побайтово, без нормализации, включая переводы строк и неразрывные пробелы

2. СОЗДАНИЕ АССЕТА
   data/prompt_assets/<family>/<id>.md
   содержимое между маркерами RUNTIME_PROMPT_START/END = old_output дословно
   метаданные и контракт — вне маркеров

3. ПОДКЛЮЧЕНИЕ ЧЕРЕЗ РЕЗОЛВЕР
   new_output = resolve_prompt_asset("<id>").runtime_block

4. ТЕСТ ЭКВИВАЛЕНТНОСТИ
   assert new_output == old_output          # побайтово
   assert sha256(new_output) == sha256(golden)

5. ПЕРЕКЛЮЧЕНИЕ
   старая функция сохраняется и начинает делегировать резолверу
   тело функции НЕ удаляется до PASS всех 18 тестов

6. УДАЛЕНИЕ
   только после зелёного прогона полного набора (281 существующий тест + 18 новых)
```

**Особый случай — `roast`.** «Прожарка» — пользовательски заметный режим. Помимо побайтовой эквивалентности строки, требуется прогон на фикстуре с `assembly_mode=roast` и сравнение итогового текста речи с baseline по: длине в токенах (±10 %), наличию обязательных структурных признаков режима, отсутствию новых предупреждений валидатора.

**Особый случай — `_DEFAULT_*` константы Заратустры.** Они срабатывают только когда файл отсутствует. Тест обязан покрывать оба пути: файл есть → используется файл; файл убран → используется константа. Оба варианта регистрируются как `BASELINE`: `origin: baseline_file` и `origin: baseline_code`.

**Место хранения:** `CALIFORNIAN_ID/tests/gold/workbench/prompt_extraction/`. Директория `tests/gold/` уже существует (`test_regression.py`).

### 0.2. Инвариант сохранения меньшинства

При извлечении `_assembly_instruction` фрагмент, обеспечивающий `synthesis_erases_all_minority_voices` (инвариант из `pipeline.yaml:54–59` и `runtime.yaml:11,17`), помещается в `protected_region`, а не в редактируемую область. Это закрывает единственный оставшийся открытым пункт гейта R0.

### 0.3. Гибриды — представление без рефакторинга

`Critique Regime` и `Variation Regime` **не расщепляются**. Добавляется декларативное описание эффектов:

```yaml
# data/controls/critique_regime.yaml
control:
  id: critique_regime
  label: "Critique Regime"
  values: [gentle, balanced, hard]
  default: balanced
  semantics: "единый пользовательский режим; не расщепляется в UI"
effects:
  - class: PROMPT_BEHAVIOR
    target: regimes.CritiqueRegime.directness_hint
    consumers: [persona_turn]
    source_ref: src/californian_id/regimes.py:24,29,34
  - class: DETERMINISTIC_ALGORITHM
    target: regimes.CritiqueRegime.attack_bias
    value_map: {gentle: -0.4, balanced: 0.0, hard: 0.8}
    consumers: [router_scoring]
    source_ref: src/californian_id/regimes.py:26,31,36
```

`regimes.py` **не изменяется**. Файл описания — источник для инспектора. То же для `variation_regime` и для ассетного гибрида V054.

### 0.4. Телеметрия — append-only

| Что добавить | Где | Условие |
|---|---|---|
| `tokens_in`, `tokens_out`, `latency_ms` на каждый LLM-вызов | обёртка `client.generate` | ranking/поведение не трогать |
| retrieval-события: `score`, `locator`, `chunk_hash`, `rank`, `included_in_prompt` | `retrieval.py`, `cultural_rag.py` | значения **уже вычисляются**, только эмиссия |
| `compiled_hash`, `sources[]` | пишет компилятор | появляется вместе с компилятором |

Ranking, top_k, размеры чанков, пороги — **не менять**. Любое изменение результатов извлечения означает провал стадии.

### 0.5. Инвалидация кеша промптов

`Zarathustra._prompt_cache` (`zarathustra.py:145`) не имеет сброса. Добавляется метод `invalidate(name=None)`. Поведение при неизменных файлах идентично. Без этого активация варианта не подействует до перезапуска процесса.

### 0.6. Реестр ассетов и read-only проекция

Создаются `data/prompt_assets/registry.yaml` и `activation_policy.yaml` по модели из `WORKBENCH_ASSET_MODEL_v0.1`. `PROMPT_DEPENDENCY_MAP.yaml` Заратустры **импортируется как есть**, не переписывается. Поднимаются шесть read-only эндпоинтов из §7 `WORKBENCH_PROJECTION_API_v0.1`.

### Критерий выхода из Stage 0

- 18 из 18 тестов эквивалентности зелёные
- 281 существующий тест зелёный
- прогон на `fx_scene_reading_001` до и после даёт одинаковый выход при одинаковом seed/модели
- эндпоинты отвечают, ни один не пишет на диск

---

## Stage 1 — вертикальный срез

**Один узел, один кандидат, полная лента.** Узел — `analyze_situation` / `zarathustra.03_scene_reading`. Контрольный — `assess_turn` (детерминированный). Приёмочный гибрид — V054.

### Порядок работ

| # | Работа | Опирается на |
|---|---|---|
| 1 | `AssetRegistry` + `PromptResolver` — адаптация `litops/prompt_engine.py` | A |
| 2 | `StaticValidator` — адаптация `validate_prompt_bodies.py` + 6 новых проверок | C §4 |
| 3 | `PromptCompiler` + `CompiledPrompt` + `source_map` | D |
| 4 | `GraphReadModel` из `pipeline.yaml` + `PROMPT_DEPENDENCY_MAP.yaml` | B §1 |
| 5 | `NodeInspector` с обязательным `effects[]` | B §2 |
| 6 | Проект фронта, `RightDock` + CSS | F §1 |
| 7 | Оболочка графа + `PipelineLayout.ts` + один тип узла | F §2 |
| 8 | CodeMirror 6 с областями protected/editable | — |
| 9 | SOURCE / COMPILED переключатель на `source_map` | D §6 |
| 10 | `VariantStore` + лента состояний | C |
| 11 | `SmokeHarness` на `fx_scene_reading_001` | E |
| 12 | Сравнение baseline и кандидата | E §7 |
| 13 | Активация + инвалидация кеша + запись `compiled_hash` в `RunTrace` | D §5 |
| 14 | Копилот на адаптированном `FieldCopilot` | F §3 |

### Критерии приёмки Stage 1

1. Граф пайплайна отрисован из `pipeline.yaml`; типы узлов различимы; `input_mode` меняет топологию, а не подсветку.
2. Клик по `analyze_situation` открывает док на треть, тянется до двух третей, сворачивается.
3. Инспектор показывает: `MODEL_CALL`, активный вариант, контракт, **и `contract_status: MISMATCH` с перечислением 10 непотребляемых полей**.
4. Клик по `assess_turn` показывает `DETERMINISTIC`, схему выхода, пороги — **и не даёт открыть редактор промпта**.
5. `socratic_question_chain.md` показан как `reference_only, not wired to runtime`.
6. Инспектор на V054 показывает **оба** эффекта и всех потребителей.
7. Инспектор на `critique_regime` показывает один контрол с двумя эффектами; контрол **не расщеплён**.
8. Редактор блокирует четыре `protected_region` файла `03_scene_reading.md`.
9. Клонирование → правка `signal_definitions` → сохранение даёт `CANDIDATE_UNCHECKED`.
10. Статическая валидация проходит; попытка изменить защищённую область даёт `INCOMPATIBLE`.
11. COMPILED VIEW показывает точный payload и число токенов; клик по фрагменту ведёт в область SOURCE.
12. Смок на `fx_scene_reading_001` даёт `SMOKE_TESTED` с записанными `compiled_hash`, `fixture_id`, результатом схемной проверки.
13. Сравнение с baseline показывает оба выхода и дельту метрик.
14. Активация переводит кандидата в `ACTIVE`, baseline в `DEPRECATED`, кеш сброшен, следующий прогон использует новый промпт.
15. `RunTrace` содержит `variant_id`, `source_hash`, `compiled_hash`, `profile_id`.
16. Любое из семи условий отката (E §7) возвращает baseline без пересмока.
17. Ни редактирование, ни сохранение, ни активация не вызывают провайдера как побочный эффект.

### Вне Stage 1

RAG-воркбенч, телеметрические оверлеи на графе, BranchAdapter, Google Docs, полевые проекции WhiteCrow, редактирование детерминированной конфигурации, система пользователей.

**Google Docs исключён обоснованно:** в WhiteCrow готовы форматы `fc5_bridge_v1` / `fc5_review_batch_v1` / `fc5_patch_v1` и алгоритм сопоставления комментариев, но `importReviewBatch` — заглушка, OAuth не начат, серверный мост не написан. «Почти готового адаптера», который сделал бы включение бесплатным, нет.

---

## Дальнейший порядок, диктуемый доказательствами

| Стадия | Содержание | Почему в этом порядке |
|---|---|---|
| 2 | `RAGProfile`: конфиг из кода в типизированный профиль, объяснение извлечения на трассе Stage 0 | телеметрия уже собрана |
| 3 | Телеметрические оверлеи на графе | нужен объём данных |
| 4 | BranchAdapter + Заратустра как тест переносимости; **Сократ подключается по мере материализации PipelinePack** | ядро доказано на одной ветке |
| 5 | Google Docs: экспорт варианта, импорт как кандидата, правка через комментарии | нужен зрелый жизненный цикл вариантов |
| 6 | Полевые проекции WhiteCrow как branch-specific | ядро должно отдавать типизированные объекты, а не готовый граф |

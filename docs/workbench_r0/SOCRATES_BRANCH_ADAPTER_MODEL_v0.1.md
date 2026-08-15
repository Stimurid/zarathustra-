# SOCRATES BRANCH ADAPTER MODEL v0.1

**Статус:** durable output Stage 4A
**Код:** `CALIFORNIAN_ID/src/workbench_adapters/socrates_adapter.py`
**Тесты:** `CALIFORNIAN_ID/tests/workbench/test_stage4a_socrates_adapter.py` (33)

---

## 1. Что доказывает эта ветка

Zarathustra доказала, что Workbench управляет **живым** рантаймом.
WhiteCrow доказала, что ядро не навязывает представление «узлы и рёбра».
Socrates доказывает третье и самое неудобное: **один и тот же WorkbenchCore
открывает ветку, у которой рантайма ещё нет**, — и при этом ничего не
изображает.

Ключевой отрицательный результат: в `workbench_core` не появилось ни одного
Socrates-специфичного импорта, идентификатора или строки. Это проверяется
AST-тестами (`test_core_does_not_import_socrates`,
`test_core_has_no_socrates_specific_identifier`), а не обещанием.

## 2. Форма адаптера

```python
class SocratesBranchAdapter:
    branch_id = "socrates"
    generation = "G-S24"
    owner = "LOCAL_SOCRATES"
    PRODUCTION_ENTRYPOINT = None                       # отсутствие объявлено
    LIVE_RUNTIME_STATUS = "WAITING_FOR_G-S26_RUNTIME_BINDING"
```

`PRODUCTION_ENTRYPOINT = None` — не заглушка, а утверждение. `WorkbenchService.
start_production_run("socrates", …)` возбуждает ошибку; тест это фиксирует.

### 2.1 Поверхность

| Метод | Что возвращает | Откуда |
|---|---|---|
| `describe_pipeline()` | 18 узлов (11 шагов + 7 терминалов), 19 рёбер | `pipeline.yaml` (BYTE_EXACT) |
| `state_projection()` | 21 состояние, 69 переходов | `state_model.yaml` |
| `branch_invariants()` | 18 (10 authority + 8 global guards) | `README.md`, `pipeline.yaml` |
| `contract_bindings()` | 12 | `manifest.yaml`, схемы |
| `runtime_profiles()` | 6 | `pipeline.yaml`, `README.md` |
| `branch_readiness()` | матрица готовности | все источники |
| `declarative_snapshot()` | `decl_323b8e9da8e32c69` | те же |
| `prompt_body(binding)` | тело промпта, `editable: False` | зеркало |
| `list_assets()` | **`[]`** | — |
| `build_invocation()` | `NotImplementedError` | — |

## 3. Три решения, которые определили модель

### 3.1 Вид узла выводится из спецификации, а не из имени

Соблазн: «S8 называется `intervention_selection`, значит это MODEL_CALL».
Пакет говорит другое, и мы следуем пакету:

| Шаг | Вид | На каком основании |
|---|---|---|
| S6 | `HUMAN_GATE` | `state_model`: переход в `PAUSED_AWAITING_HUMAN_INPUT`, компонентная привязка `OWNERSHIP_SLICE_ONLY` |
| S8 | `ROUTER` | S9 условен от `InterventionSelection.execution_status == EXECUTE` — S8 решает маршрут, включая «не исполнять вовсе» |
| S9 | `OTHER` | привязка `TINKUY_EXECUTION_ADAPTER`, хост отложен до G-S26 — вид исполнения **ещё не решаем** |
| S10 | `STORE` | `CONTRACT_DRIVEN_PROVENANCE_AND_WRITE_GATE` |
| S7 | `HYBRID` | `optional: true`, совет/арбитраж по ссылке на G-S23 |
| S0–S5 | `HYBRID` | контрактные оркестрационные композиты, отдельного вызова модели не объявлено |

`S9 = OTHER` — самая честная строка таблицы. `MODEL_CALL` было бы догадкой,
`DETERMINISTIC` — тоже. Неопределённый вид записан как неопределённый.

**Объявленная привязка промпта не делает шаг MODEL_CALL.** У S7 есть привязка и
теперь есть тело — вид остался `HYBRID`.

### 3.2 Условность сохранена, конвейер не выпрямлен

Плоская линия S0→S10 была бы ложью о ветке, у которой пять из семи терминалов
достижимы **без единого исполнения**. В проекции сохранены:

* `S6 → S8` — прямой обход совета (стабильная SYSTEM-работа);
* `S6 → PAUSED_AWAITING_HUMAN_INPUT` — человеческий шлюз как терминал;
* `S8 → S10` — обход S9, когда `execution_status != EXECUTE`;
* `S10 → {RETURN_OPERATION, PRESERVE_APORIA, REFUSED, …}`.

`NodeProjection.optional` и `conditional_on` — нейтральные поля ядра; они
описывают условность, не зная слова «Сократ».

### 3.3 Никаких выдуманных промптов

`list_assets()` возвращает `[]`. Ни один узел не получил `asset_id`.
Объявленная привязка без тела показывается через **готовность узла**, а не как
поддельный ассет с пустым текстом. Разница не косметическая: поддельный ассет
получил бы жизненный цикл (clone → validate → activate), которого не может быть.

## 4. Модель готовности

Уровни — нейтральные для ядра (`workbench_core.branch.Readiness`):

```
DECLARATIVE_READY → CONTRACT_READY → PROMPT_BINDING_READY
                  → PROMPT_BODY_READY → RUNTIME_BINDING_READY → LIVE_VALIDATED
NOT_READY
```

Текущее состояние ветки после A14-перепроверки:

| Шаг | Готовность | Ждёт |
|---|---|---|
| S0–S6, S10 | `CONTRACT_READY` | G-S25 |
| S7, S8 | `PROMPT_BODY_READY` | G-S26 |
| S9 | `CONTRACT_READY` | G-S26 |

Матрица ветки:

```
pipeline_structure   DECLARATIVE_READY
state_model          DECLARATIVE_READY
step_declarations    DECLARATIVE_READY
runtime_profiles     DECLARATIVE_READY
trace_schema         CONTRACT_READY
prompt_hierarchy     PROMPT_BINDING_READY (partial)
prompt_bodies        PROMPT_BODY_READY (S7-S8 only, read-only)
live_runtime         NOT_READY
```

Квалификатор `(S7-S8 only, read-only)` обязателен: одно тело из четырёх
привязок. `PROMPT_BODY_READY` без него завысило бы готовность втрое.

## 5. Читать можно, переписывать — нет

A14-перепроверка Drive нашла тело `MODE_AND_REFLEXIVITY_GOVERNOR_PROMPT_PACK`.
Оно втянуто и показывается в инспекторе — это прямо отвечает постоянному
требованию «Сократ должен иметь интерфейс объяснения промптов».

Интерфейса **переписывания** нет, и это не недоделка:

1. файл принадлежит LOCAL_SOCRATES — граница записи;
2. его никто не исполняет — нечем проверить правку;
3. редактор поверх текста, который ничего не меняет, обучал бы оператора
   ложной причинности.

`prompt_body()` возвращает `editable: False` вместе с причиной, а UI показывает
причину рядом с текстом.

## 6. Инварианты ветки хранятся, а не толкуются

18 инвариантов (`Truth is never decided by vote`, `Arbitration cannot create
HUMAN binding`, `Persona default is NO_PERSONA`, `NO_COUNCIL_THEATRE`, …)
приходят из данных ветки с provenance. Ядро их **отображает**, но не применяет
и не интерпретирует: инвариант чужой ветки, зашитый в ядро, стал бы
предположением ядра обо всех ветках.

## 7. Модель состояний — отдельная проекция

`StateProjection` намеренно не слит с топологией шагов. У Socrates 21 состояние
против 11 шагов; `RETRY_PENDING` и `ESCALATION_PENDING` — диспетчерские,
они **не** являются шагами. Слияние потеряло бы ровно то различие, которое эта
ветка проводит явно: повтор возвращается в тот же самый шаг (бюджет 1, для
S9 — 2), а эскалация — не повтор и ведёт в другое место.

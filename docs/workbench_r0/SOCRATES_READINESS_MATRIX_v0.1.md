# SOCRATES READINESS MATRIX v0.1

**Статус:** durable output Stage 4A
**Источник:** `SocratesBranchAdapter.branch_readiness()` / `.describe_pipeline()`
**Проверка:** `test_stage4a_socrates_adapter.py::test_branch_readiness_matrix_is_honest`

Эта матрица существует, чтобы **ограничивать** то, что Workbench разрешает
делать. Она не витрина: каждый уровень отключает конкретные действия в UI.

---

## 1. Шкала

| Уровень | Что уже есть | Что ещё нельзя |
|---|---|---|
| `DECLARATIVE_READY` | объект объявлен в пакете | ничего исполнить нельзя |
| `CONTRACT_READY` | объявлен контракт входа/выхода | тело промпта отсутствует |
| `PROMPT_BINDING_READY` | привязка промпта объявлена | тела нет |
| `PROMPT_BODY_READY` | тело втянуто и читаемо | исполнять и переписывать нельзя |
| `RUNTIME_BINDING_READY` | связан с хостом | живой прогон не подтверждён |
| `LIVE_VALIDATED` | подтверждено прогоном | — |
| `NOT_READY` | не готово | — |

## 2. Матрица ветки

| Измерение | Уровень | Свидетельство |
|---|---|---|
| `pipeline_structure` | `DECLARATIVE_READY` | `pipeline.yaml`, BYTE_EXACT, sha256 совпал с манифестом владельца |
| `state_model` | `DECLARATIVE_READY` | `state_model.yaml` v0.3.0 |
| `step_declarations` | `DECLARATIVE_READY` | 11 шагов объявлены; **тела контрактов не втянуты** |
| `runtime_profiles` | `DECLARATIVE_READY` | 6 профилей |
| `trace_schema` | `CONTRACT_READY` | `pipeline_trace.schema.json` — единственная схема в манифесте владельца |
| `prompt_hierarchy` | `PROMPT_BINDING_READY (partial)` | 4 привязки объявлены |
| `prompt_bodies` | `PROMPT_BODY_READY (S7-S8 only, read-only)` | 1 тело из 4 |
| `live_runtime` | `NOT_READY` | `WAITING_FOR_G-S26_RUNTIME_BINDING` |

`canonical_claim: false` — ветка **не** объявлена канонической.

## 3. По шагам

| Шаг | Вид | Готовность | Ждёт | Привязка промпта |
|---|---|---|---|---|
| S0 Приём и юрисдикция контекста | HYBRID | CONTRACT_READY | G-S25 | `CONTRACT_DRIVEN_EXECUTION` |
| S1 Сцена и телос | HYBRID | CONTRACT_READY | G-S25 | `CONTRACT_DRIVEN_EXECUTION` |
| S2 Проверка захвата давлением/ролью | HYBRID | CONTRACT_READY | G-S25 | `CONTRACT_DRIVEN_EXECUTION` |
| S3 Происхождение, статус, полномочия | HYBRID | CONTRACT_READY | G-S25 | `CONTRACT_DRIVEN_EXECUTION` |
| S4 Объявление операции и применимость | HYBRID | CONTRACT_READY | G-S25 | `CONTRACT_DRIVEN_EXECUTION` |
| S5 Конфигурация внимания/памяти/воображения | HYBRID | CONTRACT_READY | G-S25 | `CONTRACT_DRIVEN_EXECUTION` |
| S6 Человеческая операция и владение | **HUMAN_GATE** | CONTRACT_READY | G-S25 | `CONTRACT_DRIVEN_EXECUTION` |
| S7 Рефлексивный отход / совет *(условный)* | HYBRID | **PROMPT_BODY_READY** | G-S26 | `MODE_AND_REFLEXIVITY_GOVERNOR_PROMPT_PACK` |
| S8 Выбор вмешательства | **ROUTER** | **PROMPT_BODY_READY** | G-S26 | тот же пак |
| S9 Исполнение через Тинкуй *(условный)* | **OTHER** | CONTRACT_READY | G-S26 | `TINKUY_EXECUTION_ADAPTER` |
| S10 Контраст, provenance, запись | **STORE** | CONTRACT_READY | G-S25 | `CONTRACT_DRIVEN_PROVENANCE_AND_WRITE_GATE` |

## 4. Что готовность запрещает в интерфейсе

| Уровень | Разрешено | Заблокировано и почему |
|---|---|---|
| `DECLARATIVE_READY` / `CONTRACT_READY` | inspect, compare, clone_candidate, validate_declaratively | активация профиля — `WAITING_FOR_G-S26_RUNTIME_BINDING` |
| `PROMPT_BODY_READY` | + чтение тела промпта | редактор промпта — файл принадлежит LOCAL_SOCRATES, и ничто его не исполняет |
| вся ветка | — | `start_production_run` возбуждает ошибку: точки входа нет |

Это проверено в UI, а не только в API: все шесть кнопок `activate`
отрендерены `disabled` с причиной в `title`; редакторов CodeMirror на узлах
Socrates — ноль (`stage4a_socrates_smoke.mjs`, шаги 06–07, 12).

## 5. Что переведёт строки вверх

| Поколение | Что должно появиться | Строки, которые изменятся |
|---|---|---|
| **G-S25** | тела контрактов шагов; иерархия промптов S0–S6, S10 | `step_declarations` → CONTRACT_READY по телам; `prompt_bodies` → без квалификатора |
| **G-S26** | привязка исполнительного хоста | `live_runtime` → RUNTIME_BINDING_READY; после прогона — LIVE_VALIDATED; активация профилей включается |

Контракт снимка (`declarative_snapshot()`) специально имеет ту же форму, что и
`RunConfigurationSnapshot` живого прогона, чтобы свидетельства G-S26 принимались
без новой модели данных (тест `test_snapshot_is_declarative_not_executed`).

## 6. Итог A14

Перепроверка Drive в конце прохода:

* **выходов G-S25 не найдено** — `SOCRATES_PROMPT_DEEP_INTEGRATION = WAITING_FOR_G-S25`;
* найдено одно **тело промпта G-S23**, объявленное привязками G-S24 → S7/S8
  подняты до `PROMPT_BODY_READY`.

Важная оговорка: перечисление папок для этого аккаунта возвращает пустой
результат, поэтому «G-S25 не найден» означает **не найден по прямым id и
поиску**, а не «не существует».

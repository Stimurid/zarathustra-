# SOCRATES STRUCTURAL PROJECTION REPORT

**Статус:** durable output Stage 4A
**Что проецируется:** реальный G-S24 PipelinePack, прочитанный из зеркала
**Скриншоты:** `CALIFORNIAN_ID/workbench_ui/qa/screenshots/s4a_*.png`

---

## 1. Цифры

| Проекция | Объём |
|---|---|
| Узлы конвейера | **18** (11 шагов S0–S10 + 7 типизированных терминалов) |
| Рёбра конвейера | **19** (включая два обходных) |
| Состояния | **21** (11 рабочих + 2 диспетчерских + 7 терминальных + `RECEIVED`) |
| Переходы состояний | **69** |
| Инварианты ветки | **18** (10 authority + 8 global guards) |
| Контракты | **12** (9 схем + 3 компонентные привязки) |
| Runtime-профили | **6** |
| Декларативный снимок | `decl_323b8e9da8e32c69` |
| Промпт-ассеты Workbench | **0** |

## 2. Конвейер: условность сохранена

```
S0 → S1 → S2 → S3 → S4 → S5 → S6 ─┬─→ S7 ─→ S8 ─┬─→ S9 ─→ S10 → {7 терминалов}
                                  │             │
                                  ├─→ S8        └─→ S10          (обход S9)
                                  │  (обход совета)
                                  └─→ PAUSED_AWAITING_HUMAN_INPUT
```

Три условности, которые выпрямление уничтожило бы:

1. **`S6 → S8`** — стабильная SYSTEM-работа обходит совет. S7 объявлен
   `optional: true`; совет не ритуал.
2. **`S8 → S10`** — если `InterventionSelection.execution_status != EXECUTE`,
   исполнения не будет вовсе.
3. **`S6 → PAUSED_AWAITING_HUMAN_INPUT`** — человеческий шлюз завершает прогон.

Следствие, проверенное тестом
`test_non_execution_terminals_reachable_without_s9`: терминалы
`RETURN_OPERATION`, `PRESERVE_APORIA`, `REFUSED` (а также `COMPLETED` и
`PROVISIONAL_COMPLETED` при DO_NOT_EXECUTE) достижимы **без единого
исполнения**. Ветка, у которой отказ и апория — типизированные исходы, а не
ошибки, не может быть нарисована прямой линией.

## 3. Семь типизированных терминалов

`COMPLETED`, `PROVISIONAL_COMPLETED`, `PAUSED_AWAITING_HUMAN_INPUT`,
`RETURN_OPERATION`, `PRESERVE_APORIA`, `REFUSED`, `FAILED_EXPLICIT`.

Они спроецированы как узлы первого класса, а не как метки. `PRESERVE_APORIA`
рядом с `COMPLETED` в одном ряду — это и есть содержательное утверждение ветки:
нерешённость сохраняется, а не маскируется под ответ.

## 4. Модель состояний — вторая проекция, не второй граф

21 состояние против 11 шагов. Разница — не косметическая:

* **`RETRY_PENDING`** (диспетчерское) — «никогда не продвигает вперёд»:
  возвращает **в тот же самый шаг**, 11 обратных переходов, все с guard.
  Бюджет: `default: 1`, `S9_TINKUY_EXECUTION: 2`.
* **`ESCALATION_PENDING`** (диспетчерское) — **не повтор**. Ведёт в
  `S7_REFLEXIVE_RETREAT_COUNCIL_IF_NEEDED`, `RETURN_OPERATION` или
  `FAILED_EXPLICIT`, но никогда не «обратно в тот же шаг».

5 запрещённых переходов спроецированы явно, среди них:

* `PAUSED_AWAITING_HUMAN_INPUT -> S9_TINKUY_EXECUTION` — нельзя исполнять,
  пока ждём человека;
* `ArbitrationRecord -> HUMAN binding` — арбитраж не создаёт человеческого
  обязательства;
* запись состояния при незакрытом ontology gap.

Слияние двух проекций в одну потеряло бы ровно это.

## 5. Классификация узлов: от спецификации, не от имени

| Шаг | Вид | Свидетельство в проекции (`note`) |
|---|---|---|
| S6 | `HUMAN_GATE` | переход в `PAUSED_AWAITING_HUMAN_INPUT`; привязка `OWNERSHIP_SLICE_ONLY` |
| S8 | `ROUTER` | решает, будет ли S9 вообще |
| S9 | `OTHER` | хост отложен до G-S26 — вид исполнения не решаем |
| S10 | `STORE` | `CONTRACT_DRIVEN_PROVENANCE_AND_WRITE_GATE` |
| S7 | `HYBRID` | `optional: true`; совет/арбитраж по ссылке на G-S23 |
| S0–S5 | `HYBRID` | контрактные композиты без объявленного вызова модели |

Каждый узел несёт своё свидетельство в поле `note`, видимое в инспекторе.
`S9 = OTHER` — отказ угадывать: `MODEL_CALL` и `DETERMINISTIC` были бы одинаково
недоказуемы.

## 6. Контракты

12 привязок с provenance. В интерфейсе каждая помечена по принадлежности к
контрольному манифесту владельца:

* `pipeline_trace.schema.json` → `CONTRACT_READY`;
* остальные восемь схем → `CONTRACT_READY / NOT_IN_G-S24_MANIFEST` (красным).

Это визуализация дефекта **SD-001**, а не наша поправка к источнику.

Привязки к шагам: S6 → `human_operation`, `human_operation_return`,
`ownership_assessment_v0.2`, `competence_after_interaction`,
`development_risk`; S7 → `arbitration_record`, `council_recipe`;
S8 → `intervention_selection`; S10 → `pipeline_trace`.

## 7. Профили: осмотреть можно, включить нельзя

6 профилей (`DIRECT_ASSISTANCE` — по умолчанию, `DELIBERATE`, `DWELL`,
`RESEARCH`, `CONCEPT_GENESIS`, `PUBLIC_TWIN_DEMO`). У каждого четыре
разрешённых действия — `inspect`, `compare`, `clone_candidate`,
`validate_declaratively` — и заблокированная активация со статусом
`WAITING_FOR_G-S26_RUNTIME_BINDING` в подсказке кнопки.

Кнопка есть и она видимо отключена — это лучше, чем её отсутствие: оператор
видит, что операция существует и чего именно она ждёт.

## 8. Чего в проекции нет намеренно

* нет промпт-ассетов и жизненного цикла над ними;
* нет телеметрии — вместо пустых нулей ветка вообще не запрашивает прогоны
  (UI пропускает запрос `runs` для веток без живого рантайма);
* нет дрейфа контрактов — сравнивать не с чем;
* нет ни одного экрана, где активация выглядела бы доступной.

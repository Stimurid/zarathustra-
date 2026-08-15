# THREE-BRANCH PORTABILITY REPORT

**Статус:** durable output Stage 4A
**Тест-якорь:** `test_stage4a_socrates_adapter.py::test_one_core_three_branches`,
`::test_three_maturity_patterns_are_distinct`, `test_stage4b_whitecrow_projection.py`

---

## 1. Утверждение

Один `WorkbenchCore` обслуживает три ветки с **тремя разными паттернами
зрелости представления и рантайма**, и в ядре нет ни одного импорта, типа или
идентификатора, принадлежащего какой-либо ветке.

Это отрицательное утверждение, поэтому оно проверяется отрицательными тестами:
AST-обход всех модулей `workbench_core/` на импорты и на упоминания
(`test_core_does_not_import_socrates`, `test_dependency_invariant.py`,
`test_paying_the_debts_did_not_put_a_branch_into_the_core`,
`test_core_names_no_branch_specific_configuration`).

## 2. Три паттерна

| | **Zarathustra** | **WhiteCrow (проекция)** | **Socrates** |
|---|---|---|---|
| Что это | живой рантайм Tinkuy | альтернативное представление тех же объектов | декларативный пакет G-S24 |
| Точка входа | `californian_id.pipeline.Pipeline.run` | — (поверх Zarathustra) | **нет** |
| Слой узлов | `ACTUAL_RUNTIME` (+ DECLARED/HARNESS) | наследует | `DECLARED_PIPELINE` целиком |
| Топологический статус | MATCH / DECLARATION_DRIFT / DEAD_DECLARATION | наследует | `UNKNOWN` — не с чем сравнивать |
| Представление | направленный граф | радиальное поле | направленный граф + отдельная модель состояний |
| Промпт-ассеты | 18, редактируемые | те же | **0** |
| RAG-профили | да | да | нет |
| Телеметрия | измеренная из трасс | та же | нет — и не показывается пустой |
| Снимок конфигурации | `RunConfigurationSnapshot` (исполненный) | тот же | `DECLARATIVE_SNAPSHOT`, `is_executed_run: False` |
| Активация | реальная, влияет на прогон | реальная | **отключена**, `WAITING_FOR_G-S26_RUNTIME_BINDING` |

## 3. Что пришлось изменить в ядре, чтобы это стало возможно

Ничего специфичного для ветки — но кое-что **обобщить**. Каждое изменение
формулировалось как нейтральное понятие, а не как приспособление под Socrates:

| Добавлено в `workbench_core.branch` | Нейтральная формулировка | Кто этим пользуется |
|---|---|---|
| `Readiness` | «объект объявлен, но ещё не исполним» | Socrates; Zarathustra оставляет `None` |
| `BranchInvariant` | «правило, которое ветка объявляет о себе» | Socrates (18); Zarathustra пока 0 |
| `StateNode` / `StateTransition` / `StateProjection` | «рантайм-машина состояний ≠ топология шагов» | Socrates; применимо к любой ветке |
| `NodeProjection.optional` / `.conditional_on` | «шаг выполняется не всегда» | Socrates; Zarathustra — узлы в цикле |
| `NodeProjection.prompt_binding` / `.contract_refs` | «объявленная привязка без тела» | Socrates |
| `ProjectionKind = str` (было `Literal`) | перечисление видов проекций — онтология ветки | WhiteCrow |

Последняя строка — исправление дефекта Stage 4B: `Literal["graph","mosaic",
"cross","radial"]` затащил ontology WhiteCrow в ядро. Открытая строка честнее:
ядро не знает, какие проекции бывают.

## 4. Где проходит шов

Единственный канал, по которому специфика ветки достигает ядра, — протокол
`BranchAdapter`. Проверенные следствия:

* **Ядро не импортирует рантайм.** `service.start_production_run` не знает про
  `californian_id.runtime_bindings`; резолвер устанавливает адаптер через
  `bind_runtime_resolver`/`unbind_runtime_resolver`. Это исправление появилось
  потому, что наш собственный тест поймал нарушение инварианта.
* **Ядро не знает конфигурации ветки.** A15 убрал из `service.py` последние
  зашитые строки — `californian_id.inner_council`, `runtime.yaml`, `0.11.1`;
  теперь `orchestration_binding` берётся из `PipelineProjection.pipeline_id`,
  а `algorithm_bindings` поставляет адаптер.
* **Возможности объявляются, а не угадываются.** `branch_capabilities()`
  проверяет наличие метода на адаптере; UI не рисует «состояния» для ветки без
  `state_projection`.

## 5. Отрицательные результаты (что портируемость НЕ доказывает)

* Не доказано, что Socrates работает. Ветка не исполнялась ни разу; это
  зафиксировано в трёх местах (`PRODUCTION_ENTRYPOINT = None`,
  `is_executed_run: False`, `test_no_live_execution_claim_in_adapter_source`).
* Не доказано, что любая четвёртая ветка подойдёт без изменений ядра.
  Доказано более слабое и проверяемое: три ветки с разной зрелостью
  потребовали **нуля** ветко-специфичных понятий в ядре.
* Не доказано, что WhiteCrow — отдельная ветка. Это **проекция** поверх
  Zarathustra, и в таблице она названа так, а не «третьей веткой».

## 6. Как это увидеть

```bash
python -m workbench_api.server            # http://127.0.0.1:8790
node qa/stage4a_socrates_smoke.mjs        # 29/29, 0 ошибок консоли
```

Переключение `zarathustra → поле (WhiteCrow) → socrates` без перезагрузки —
шаги 17–18 сценария; скриншоты `s4a_07…09`.

# WHITECROW_PROJECTION_PROOF_REPORT — Stage 4B

**Дата:** 2026-08-15 · Ветка выбрана по факту: PipelinePack Сократа материализацию не подтвердил.

---

## 1. Почему Branch B

Проверка Drive после закрытия Stage 3:

| Объект | Результат |
|---|---|
| `07_SOCRATES_PIPELINE_PACK` (`10WHFJzLZYP…`) | папка существует, владелец `timurid@gmail.com`, `canAddChildren: false` |
| перечисление дочерних элементов | `{}` — недоступно из аккаунта `dc@shchuk.in` |
| `fullText contains 'SOCRATES' and modifiedTime > 2026-08-01` | единственный результат — мой собственный документ |
| поиск по `title contains 'S23' / 'G-S2' / 'PIPELINE_PACK'` | ни одного артефакта Сократа |

Наличия папки недостаточно: требуются реальные `steps/`, `prompts/`, порядок исполнения, контракты и тестовый маршрут. Подтвердить существование хотя бы одного из них не удалось. **Фиктивный адаптер Сократа не создавался.**

## 2. Что доказывается

`workbench_core` не навязывает node-edge представление. Те же типизированные объекты рендерятся и как граф Заратустры, и как полевая радиальная проекция WhiteCrow — **без форка модели данных**.

## 3. Что переиспользовано

Геометрия перенесена дословно из реального кода WhiteCrow — `conceptarticle/mvp/FIELD_KERNEL_v6_3_1.html`, функция `getFPERadial()`:

```
W=300  H=240  cx=150  cy=120  R=95
angle = (i / min(8, n)) · 2π − π/2
node r = 10, active r = 14, hub r = 16, центр подписан FIELD
```

Ролевой словарь взят из `docs/FIELD_PROJECTION_ENGINE_SPEC.md` §Radial: Поле · Институт · Куратор · Синтез · Феномен · Концепт · Напряжение · Источник. WhiteCrow не переписывался и не изменялся.

## 4. Реализация

`workbench_adapters/whitecrow_projection.py` — **презентационный** адаптер. Он:

- принимает готовые `NodeProjection` от `ZarathustraAdapter`;
- не владеет ни пайплайном, ни рантаймом (проверяется тестом: нет `describe_pipeline`, `run_retrieval`, `Pipeline(`, `production_entrypoint`);
- не импортирует `californian_id` вовсе — презентации рантайм не нужен;
- отдаёт `FieldProjection` из `FieldItem`, у которых `node_id`, `asset_id`, `rag_profile_id` — **те же значения**, что в графе.

В ядре появились только два нейтральных типа — `FieldItem` и `FieldProjection`. `ProjectionKind` намеренно сделан открытой строкой: перечисление `mosaic|cross|radial|linearized` в ядре означало бы протаскивание визуальной онтологии одной ветки в общую модель. Это поймал собственный тест — см. дефект WB-016.

## 5. Приёмка

| Требование | Как проверено |
|---|---|
| те же типизированные объекты | `test_same_typed_objects_feed_both_projections` — совпадают `kind`, `asset_id`, `rag_profile_id`, `label` |
| инспектор открывает тот же ассет | `test_inspector_opens_the_same_asset_from_either_projection` |
| RAG-семантика сохраняется | `test_rag_item_keeps_rag_semantics` — редактор промпта недоступен |
| детерминированный узел без редактора | `test_deterministic_item_still_has_no_editor` |
| проекция задаёт другой вопрос | `test_field_ordering_differs_from_call_order` — порядок по весу преобразования, не по порядку вызова |
| мёртвая декларация не полевой объект | `test_dead_declaration_is_not_a_field_object` |
| нет форка модели данных | `test_core_has_no_whitecrow_specific_type` (по исполняемому коду, без docstring) |
| зависимость односторонняя | `test_projection_adapter_imports_core_not_the_other_way` |

14 тестов, все зелёные.

## 6. Визуальное доказательство

`workbench_ui/qa/screenshots/s4b_*.png`, 5/5 шагов, 0 ошибок:

1. `01_graph_real_topology` — граф с исправленной топологией и слоями;
2. `02_radial_field` — та же 15-узловая проекция как радиальное поле с ролями;
3. `03_inspector_from_field` — клик по полевому объекту открывает инспектор с `zarathustra.03_scene_reading`, контрактом `17/9/7 MISMATCH` и «superprompt запрещён»;
4. `04_rag_from_field` — RAG-инспектор с эффективными параметрами, открытый из поля;
5. `05_back_to_graph` — возврат в граф.

## 7. Границы

Реализована одна проекция из четырёх — радиальная, как максимально непохожая на граф и полностью специфицированная. Mosaic, Cross и Linearized сознательно отклоняются (`test_unsupported_kind_is_refused`), а не заглушены. Это доказательство переносимости слоя представления, а не новый WhiteCrow.

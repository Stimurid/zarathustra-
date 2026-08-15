# NATIVE TINKUY RUNTIME INVENTORY — local executable code

**Проход:** `WORKING_SOCRATES / G-S26 local repository side`
**Ветка:** `socrates/gs26-runtime-integration` от `777b976`
**Вопрос:** есть ли у нас на диске исполняемые органы, до которых не дотянулась
Drive-сцена G-S26 — semantic fabric, argumentation, Working Memory?

Составлено **до** написания единой строки адаптера. Ничего не скачивалось;
локальный `socrates_mirror/` трактуется как `HISTORICAL_INTEGRATION_FIXTURE`
и в этой инвентаризации не является источником.

---

## 0. Осмотренные репозитории

| Путь | Тип | Идентичность | Вердикт |
|---|---|---|---|
| `C:/projects/zarathustra-push` | git | HEAD `777b976`, ветка `socrates/gs26-runtime-integration` | **единственный авторитетный исполняемый чекаут** |
| `C:/projects/tinkuy/CALIFORNIAN_ID` | не git | `fabric/store.py`, `fabric/schemas.py`, `argumentation.py`, `narrative_memory.py` — **побайтово идентичны** первому | рабочая копия, не отдельная реализация |
| `memory-workbench`, `abulafia`, `dedalum`, `kairoskopion` | git | — | по содержимому: ноль совпадений на `propose_write` / `commit_write` / `WorkingMemory` |

Вывода «CASE D — реализация в другом репозитории» нет: второй путь оказался
копией, а не другим движком.

---

## 1. SEMANTIC FABRIC — **классификация A**

### Требуемая семантика → что реально есть

| Канонический объект Тинкуя | Локальная реализация | Файл |
|---|---|---|
| `SemanticUnit` | `FabricUnit` | `fabric/schemas.py:130` |
| `SemanticBlock` | `FabricBlock` | `fabric/schemas.py:147` |
| `SemanticRelation` | `FabricRelation` | `fabric/schemas.py:163` |
| `SemanticThread` | `FabricThread` | `fabric/schemas.py:178` |
| `SemanticSnapshot` | `FabricSnapshot` — докстрока прямо ссылается на канон **«021 SemanticSnapshot»** | `fabric/schemas.py:206` |
| `SourceSpan` | `FabricSourceSpan` | `fabric/schemas.py:101` |
| `EvidenceFragment` | `FabricEvidenceFragment` | `fabric/schemas.py:118` |
| `SceneState` / `OpenLoop` | `FabricSceneState.open_loops` — докстрока ссылается на канон **«022 SceneState»** | `fabric/schemas.py:189,200` |

Это не совпадение имён: сами докстроки реализации ссылаются на номера
канонических документов Тинкуя.

| Поле | Значение |
|---|---|
| **путь реализации** | `CALIFORNIAN_ID/src/californian_id/fabric/` (`__init__.py`, `schemas.py` 236 стр., `parser.py` 403 стр., `store.py` 312 стр.) |
| **точка входа (запись)** | `FabricParser.parse(text, source_id, parser_run_id) -> FabricSnapshot` — LLM-управляемый резчик |
| **точка входа (чтение)** | `FabricStore.load_snapshot(snapshot_id)`, `FabricStore.list_snapshots(source_id)`, `FabricStore.load_source_text(source_id, version)` |
| **персистентность** | SQLite, 8 таблиц: `source_artifact`, `source_version`, `source_span`, `evidence_fragment`, `fabric_unit`, `fabric_block`, `fabric_relation`, `fabric_thread`, `fabric_snapshot` + 5 индексов |
| **существующие вызывающие** | `pipeline.py:861` (`run_from_raw_text` — сохраняет snapshot), `cli.py:34` |
| **тесты** | `tests/unit/test_fabric.py` — `test_store_round_trip`, `test_converter_produces_unit_pack`, `test_fabric_parser_rejects_mock` |
| **классификация** | **A — настоящая исполняемая реализация с персистентностью** |
| **минимальное действие для привязки** | `fabric.query` как таковой отсутствует: есть `load_snapshot` / `list_snapshots`, но нет запроса по типам/нитям/отношениям. Нужен **тонкий read-only шов поверх существующего `FabricStore`** — без нового хранилища и без изменения `fabric/` |
| **риск теневой реализации** | **высокий, если писать свой запрос по своим таблицам.** Смягчение: шов обязан открывать существующее соединение `FabricStore` и возвращать существующие dataclass-ы, а не свои |

Важное ограничение честности: `FabricParser` **требует живую модель** и явно
отвергает mock (`test_fabric_parser_rejects_mock`). Поэтому детерминированно
доказуем именно **запрос по ткани**, а не её порождение.

---

## 2. ARGUMENTATION — **классификация A**

> **Поправка, внесённая по ходу инвентаризации.** Первая редакция этого раздела
> ставила **B** и утверждала, что «персистентного аргумент-графа и отдельных
> `Ground`/`Undercutter` нет, есть только проектор». Это было неверно: при
> проверке вызовов обнаружился `ArgumentMap` — **живой накопительный граф
> аргументации** на `RunState`, который сворачивается на каждом ходе совета.
> Класс поднят до **A**. Поправка оставлена в тексте намеренно: она показывает,
> что классификация выведена из вызовов, а не из первого впечатления от имён.

### Что есть

| Часть | Реализация | Файл |
|---|---|---|
| `Claim` | dataclass | `schemas.py:15` |
| `Attack` / `Support` | dataclass | `schemas.py:36,43` |
| Toulmin: claim / data / **warrant** / qualifier / **rebuttal** / counterclaim | `ToulminBundle` | `schemas.py:~405-420` |
| Оценка хода (детерминированная) | `assess_turn()` → `DisputeAssessment` | `argumentation.py:138` |
| Обнаружение подмены тезиса | `detect_thesis_substitution()` | `argumentation.py:58` |
| Обнаружение уловок | `detect_fallacy_or_trick()` | `argumentation.py:81` |
| Режим спора | `infer_dispute_mode()` | `argumentation.py:124` |
| **Проекция ткани → аргумент** | `_fabric_snapshot_to_unit_pack()`: `intention=claim → Toulmin.claim`, `intention=assumption → Toulmin.warrant`, `FabricRelation(contradicts\|avoids) → Toulmin.rebuttal` | `pipeline.py:1953-2010` |
| Toulmin из внешней разметки | `adapters/units_of_content_md/parser.py:168-176` | |

| Поле | Значение |
|---|---|
| **живой граф** | **`ArgumentMap`** (`schemas.py:112`): `claims`, `assumptions`, `values`, `supports`, `attacks`, `actions`, `questions`, `unresolved_conflicts` — поле `RunState.argument_map` |
| **кто его ведёт** | `pipeline._fold_turn_into_argument_map(turn, argument_map)` — вызывается **на каждом ходе совета** (`pipeline.py:596`, `pipeline.py:1278`); `_seed_argument_map_from_pack` (`pipeline.py:1071`) засевает его из UnitPack; `_inject_user_voice` (`pipeline.py:298`) добавляет human-claim |
| **кто его читает** | `assess_turn` (`pipeline.py:614`), синтез (`pipeline.py:716,734`), `check_anti_slop` (`pipeline.py:720`), закрывающая речь (`pipeline.py:760`), экспорт CLI (`cli.py:230`) |
| **точки входа** | `argumentation.assess_turn(turn, prior_turns, argument_map)` — публичная; `pipeline._fold_turn_into_argument_map`, `pipeline._fabric_snapshot_to_unit_pack` — приватные по имени, но исполняемые в проде |
| **персистентность** | **отдельного аргумент-хранилища нет.** Граф живёт на `RunState` и уходит в `RunTrace` (`dispute_assessment`, `architectonic_delta`) — это персистентность прогона, а не отдельная БД аргументов |
| **тесты** | `tests/unit/` покрывают `assess_turn`; `test_fabric.py::test_converter_produces_unit_pack` покрывает проекцию |
| **классификация** | **A — настоящая исполняемая реализация.** Есть и накопительный граф аргументации, и детерминированная оценка хода, и проекция ткани в Тулмина; всё это исполняется в каждом реальном прогоне |
| **минимальное действие** | ничего не писать заново: **опубликовать существующие вызовы как именованные швы** — `map_of`, `fold_turn`, `assess_turn`, `project` |
| **риск теневой реализации** | **очень высокий.** Соблазн написать «настоящий» аргумент-движок в Workbench. Запрещено: шов обязан вызывать `pipeline._fabric_snapshot_to_unit_pack` и возвращать его `ToulminBundle`, а не собственные |

Отдельно фиксирую различие, о котором предупреждал handoff:
`assess_turn` — это **оценка хода**, а не полный сервис аргументации. Его наличие
само по себе не закрывает `argumentation.project`; проекцию закрывает проектор
ткани, а граф — `ArgumentMap`. Три разных вызова, три разных шва.

**Что действительно отсутствует** (и не выдумывается): отдельное персистентное
хранилище аргументов и первоклассные `Ground` / `Undercutter`. Основания
представлены как Тулминовское `data`; подрезающих возражений (undercutter) в
онтологии нет вовсе.

---

## 3. WORKING MEMORY — **классификация B (субстрат A, шлюз D)**

### Требуемая семантика

```
READ · PROPOSE_WRITE · REJECT_WRITE · COMMIT_WRITE
инвариант: порождение информации ≠ полномочие её сохранить
```

### Что есть на диске

| Кандидат | Что это на самом деле | Годится? |
|---|---|---|
| `ConversationMemory` (`memory.py`, 35 стр.) | **в-прогонная**, без персистентности, без шлюза | нет — это то самое «conversation summary», от которого handoff предостерегает |
| `RunState` (`state.py`) | состояние одного прогона | нет |
| `RunStore` (`workspaces.py:109`) | метаданные прогонов | нет |
| **`NarrativeStore`** (`narrative_memory.py:59`) | **персистентный SQLite на workspace**, типизированные заметки между прогонами: `observation`, `distinction`, `recurring_pattern`, `contradiction`, `hypothesis`; API `add` / `get` / `list` / `by_related_run` | **да — это ближайший настоящий durable state store** |
| **`FabricStore.save_snapshot/load_snapshot`** | durable `SemanticSnapshot` + `SceneState.open_loops` | **да — это durable SharedState/OpenLoop** |

| Поле | Значение |
|---|---|
| **пути** | `narrative_memory.py:59` (`NarrativeStore`), `fabric/store.py:126` (`FabricStore`), `workspaces.py:51` (`fabric_store_path`), `narrative_memory.py:55` (`_store_path`) |
| **точки входа** | `NarrativeStore.for_workspace(ws)`, `.add(note)`, `.get(id)`, `.list(kind, limit)`, `.by_related_run(run_id)`; `FabricStore.save_snapshot/load_snapshot` |
| **персистентность** | SQLite: `<workspace>/narrative.sqlite3`, `<workspace>/fabric.sqlite3` |
| **существующие вызывающие** | `narrative_memory.auto_record_observation`, `reflect_over_window`; `pipeline.run_from_raw_text` |
| **тесты** | покрытие есть в `tests/unit/` |
| **классификация** | **B.** Субстрат хранения — **A** (реальный, durable, с нужными объектами). Шлюз полномочий — **D**: `NarrativeStore.add()` пишет **напрямую**, никакого `propose/reject/commit` в репозитории нет (проверено по содержимому: ноль совпадений на `propose_write`/`commit_write` во всех локальных репозиториях) |
| **минимальное действие** | Реализовать **шлюз как политику поверх существующих store**, а не как базу. Это ровно то, что разрешает handoff: «Socrates-specific objects are views, policies or candidate artifacts over Tinkuy substrate», и ровно то, что запрещает `create_new_memory_store: false` |
| **риск теневой реализации** | **критический.** Любая новая таблица/файл БД под именем `SocratesMemoryDB` нарушает замороженную store-policy. Смягчение: шлюз **не владеет** хранилищем; `COMMIT_WRITE` обязан делегировать в `NarrativeStore.add`, а отклонённое предложение не оставляет следа в БД вообще |

---

## 4. Сводка перед решением

| Орган | Класс | Субстрат | Шов, которого не хватает |
|---|---|---|---|
| semantic fabric | **A** | `FabricStore` + 8 таблиц | типизированный запрос `fabric.query` поверх существующего store |
| argumentation | **A** | `ArgumentMap` (живой граф) + проектор + `assess_turn` | публикация существующих вызовов как именованных швов |
| Working Memory | **B** | `NarrativeStore` (durable) — субстрат **A** | шлюз `propose → reject/commit` как политика, **без новой БД** |

### Решение гейта

**CASE A** по ткани и аргументации: реализации существуют и исполняются в
каждом реальном прогоне; недоставало только названных, тестируемых вызовов.

**CASE B** по Working Memory: субстрат хранения настоящий и durable, но шлюза
полномочий в репозитории нет ни в каком виде. Строим **политику поверх
существующего store**, а не второе хранилище.

Ни одного «CASE C — только схемы» здесь нет: во всех трёх случаях за схемами
стоит исполняемый код и настоящая персистентность. «CASE D» тоже нет: второй
локальный путь оказался побайтовой копией первого.

### Направление зависимости, которое будет соблюдаться

```
Socrates / Workbench
        ↓ (адаптер)
californian_id.fabric.FabricStore
californian_id.pipeline._fabric_snapshot_to_unit_pack
californian_id.narrative_memory.NarrativeStore
```

Обратной зависимости нет: ни один файл в `californian_id/` не будет знать о
Workbench или о Сократе.

# ARGUMENTATION_VERTICAL_SLICE_FIXTURE v0.1

**Дата:** 2026-08-15

---

## 0. Коррекция выбора узла

Директива R1 предписывала строить срез на «argumentation node с существующей выходной схемой `dispute_assessment.schema.json`». Это опиралось на мою же формулировку из R0, которая была неточной. Проверка исходников показала:

> `src/californian_id/argumentation.py` — **235 строк детерминированного Python**. Ни одного вызова LLM. `assess_turn`, `detect_thesis_substitution`, `detect_fallacy_or_trick`, `check_anti_slop` — Jaccard-сходство, regex, счётчики операций. `dispute_assessment.schema.json` описывает выход детерминированной функции. Файл `prompts/socratic_question_chain.md` помечен внутри себя как *«Reference-only template»* и рантаймом не вызывается.

Промпт-опосредованного узла в пакете argumentation **нет**. Строить на нём срез редактирования промптов невозможно.

**Решение: срез содержит два узла.**

| Роль в срезе | Узел | Тип |
|---|---|---|
| **Основной, промпт-управляемый** | `analyze_situation` / `zarathustra.03_scene_reading` | `MODEL_CALL` |
| **Контрольный, детерминированный** | `assess_turn` / `argumentation.dispute_assessment` | `DETERMINISTIC` |

Контрольный узел нужен, чтобы доказать главное требование инспектора: **UI не притворяется, будто всякое преобразование — промпт**. На детерминированном узле редактор промпта не открывается, а показывается типизированная конфигурация и схема выхода.

---

## 1. Основной узел

| Поле | Значение |
|---|---|
| `node_id` | `analyze_situation` |
| Шаг пайплайна | `pipeline.yaml:24` — `zarathustra.analyze_situation -> topic/genre/stakes/tensions` |
| Реализация | `src/californian_id/zarathustra.py:238–287` |
| Точка вызова промпта | `zarathustra.py:260` — `self.prompt("03_scene_reading.md") or _DEFAULT_SCENE_READING_PROMPT` |
| `asset_id` | `zarathustra.03_scene_reading` |
| Исходник | `src/californian_id/data/zarathustra/03_scene_reading.md` (48 строк) |
| Baseline-fallback | `zarathustra._DEFAULT_SCENE_READING_PROMPT` (константа, ~строка 992) |
| Объявленный контракт | `PROMPT_DEPENDENCY_MAP.yaml:22–27` — `output_schema: {topic, genre, stakes, horizons, concepts, tensions, uncertainties, dominant_frame, suppressed_frame}`, `version: 0.2.0`, `used_by_steps: [analyze_situation]`, `depends_on: [01_identity_and_laws]` |
| Фактический потребитель | `SituationAnalysis` (`schemas.py`), 7 полей |
| Вызовов модели | **ровно один**, без цикла повторов (комментарий в коде: «single call, no fallback loop») |
| Параметр | `CALIFORNIAN_ID_SITUATION_MAX_CHARS`, default 100000, clamp [1000, 200000] |

**Почему именно он:**

1. Реально исполняется в каждом прогоне — это первый LLM-шаг пайплайна.
2. Один вызов, ограниченная стоимость — идеален для смока.
3. Промпт уже лежит файлом и загружается с диска → механизм горячей подмены существует.
4. Есть baseline в виде Python-константы → сразу проверяется семантика `BASELINE`-варианта.
5. Есть объявленный контракт в машиночитаемом виде.
6. **Уже содержит настоящий дефект контракта** — см. §3. Срез начнётся с находки, а не с демонстрации на пустом месте.
7. Узел общий для веток: чтение сцены понадобится и Сократу, что делает его хорошей проверкой BranchAdapter.

---

## 2. Входная фикстура

```
fixture_id: fx_scene_reading_001
kind: bounded_smoke
input_type: raw text
```

Содержимое фикстуры — короткий нормативный вопрос на русском (200–400 символов), покрывающий все требуемые промптом признаки: доминирующая рамка, вытесненная рамка, скрытый страх, потенциальный идол.

Хранение: `CALIFORNIAN_ID/tests/fixtures/workbench/fx_scene_reading_001.md` (рядом с существующими `tests/fixtures/units_md/`).

Дополнительные фикстуры второй очереди: `fx_scene_reading_002` (транскрипт, длинный вход, проверка `MAX_CHARS`), `fx_scene_reading_003` (вход без ставок — проверка запрета домысливания).

---

## 3. Выходной контракт и обнаруженный дефект

| Уровень | Полей | Источник |
|---|---|---|
| Промпт требует от модели | **17** | `03_scene_reading.md:6–24` |
| `PROMPT_DEPENDENCY_MAP` объявляет | **9** | `PROMPT_DEPENDENCY_MAP.yaml:26` |
| `analyze_situation` читает | **7** | `zarathustra.py:277–285` |
| `SituationAnalysis` хранит | **7** | `schemas.py` |

Поля, генерируемые по инструкции и молча выбрасываемые: `dominant_frame`, `suppressed_frame`, `model_of_human`, `model_of_future`, `model_of_power`, `central_value`, `hidden_fear`, `potential_idol`, `absent_head`, `possible_transformation` — **десять**.

**Это дефект, а не задача среза.** Срез обязан его *обнаружить и показать*, а не чинить. Ожидаемый вердикт статического валидатора при первом запуске:

```
contract_check: MISMATCH
  prompt_requires: 17 fields
  declared_output_schema: 9 fields
  consumer_reads: 7 fields
  unconsumed: [dominant_frame, suppressed_frame, model_of_human, model_of_future,
               model_of_power, central_value, hidden_fear, potential_idol,
               absent_head, possible_transformation]
  undeclared_in_map: [model_of_human, model_of_future, model_of_power,
                      central_value, hidden_fear, potential_idol,
                      absent_head, possible_transformation]
```

Если валидатор этого не выдаёт — приёмка среза не пройдена.

---

## 4. Baseline

| Что | Значение |
|---|---|
| `variant_id` | `v_baseline_0_2_0` |
| `origin` | `baseline_file` |
| `source_path` | `data/zarathustra/03_scene_reading.md` |
| `source_hash` | вычисляется при первом индексировании |
| `state` | `BASELINE`, всегда активен до первой активации кандидата |
| Второй baseline | `v_baseline_code` — `_DEFAULT_SCENE_READING_PROMPT`, `origin: baseline_code`, активируется только при отсутствии файла |

Базовый прогон на `fx_scene_reading_001` фиксирует: выход модели, число заполненных полей, `tokens_in/out`, латентность, `compiled_hash`. Этот прогон — точка сравнения для всех кандидатов.

---

## 5. Защищённые области `03_scene_reading.md`

| Область | Строки | Вид | Причина |
|---|---|---|---|
| `output_json_contract` | 5–25 (блок с JSON) | **protected** | потребитель парсит эти ключи; изменение ломает `SituationAnalysis` |
| `anti_speculation_rules` | 27–28 | **protected** | «Не приписывай пользователю позицию… Пустые поля — null, не заполняй домыслом» — эпистемический инвариант |
| `signal_definitions` | 30–39 | editable | определения признаков — содержательная часть, переписывается свободно |
| `prohibitions` | 41–47 | **protected** | «Только из реестра persona-линз», «не больше одного варианта преображения» — правила, на которые опираются соседние шаги |

Плюс наследуемые инварианты из `data/zarathustra/manifest.yaml` → `non_negotiable_identity` (8 утверждений), применимые ко всем ассетам Заратустры.

Редактируемой остаётся примерно **четверть файла** — секция признаков. Это честное отражение того, что промпт с контрактом нельзя переписывать целиком.

---

## 6. Кандидат для демонстрации

Минимальное осмысленное изменение в `signal_definitions`: уточнить формулировку «скрытого страха» так, чтобы модель различала тревогу автора текста и тревогу, приписываемую предмету. Изменение затрагивает только `editable_region`, контракт не трогает, эффект на выходе измерим.

Ожидаемая лента: `CANDIDATE_UNCHECKED → STATIC_VALID → COMPILED → SMOKE_TESTED → ACCEPTED → ACTIVE`.

---

## 7. Условие отката

Кандидат откатывается автоматически, если на фикстуре `fx_scene_reading_001` выполняется хотя бы одно:

1. Выход не парсится как JSON (`_json_from_text` бросает исключение).
2. Отсутствует любое из семи потребляемых полей (`topic`, `genre`, `stakes`, `horizons`, `concepts`, `tensions`, `uncertainties`).
3. `topic` пуст или длиннее 280 символов после нормализации.
4. `genre` вне множества `{question, statement, normative, long_form, transcript}`.
5. Нарушен инвариант анти-домысливания: непустые `stakes` при их отсутствии в baseline-выходе на том же входе.
6. `tokens_out` превышает baseline более чем в 2 раза.
7. Изменена хотя бы одна `protected_region`.

Откат = `ACTIVE → DEPRECATED` для кандидата и повторная активация `v_baseline_0_2_0` без пересмока (`source_hash` и `compiled_hash` совпадают с ранее принятыми).

---

## 8. Контрольный детерминированный узел

| Поле | Значение |
|---|---|
| `node_id` | `assess_turn` |
| Реализация | `src/californian_id/argumentation.py:138–195` |
| `kind` | `DETERMINISTIC` |
| Выходная схема | `data/argumentation/schemas/dispute_assessment.schema.json` (29 строк, 4 обязательных поля) |
| `prompt_asset_id` | **null** |
| Что показывает инспектор | тип операции, схему выхода, типизированные пороги (`_jaccard` 0.05 и 0.75, окно `same_persona_prior[-3:]`, множество `high_severity`), потребителей — и **не открывает редактор промпта** |
| Критерий приёмки | попытка открыть редактор промпта на этом узле должна быть невозможна в UI |

Дополнительно на этом узле проверяется отображение `reference_only`-ассета: `data/argumentation/prompts/socratic_question_chain.md` должен быть показан со статусом `reference_only, not wired to runtime` — иначе Workbench будет создавать ложное впечатление, что редактирование этого файла на что-то влияет.

---

## 9. Приёмочная фикстура гибрида V054

Третья обязательная проверка среза, вне обоих узлов. Инспектор открывается на ассете `persona.LENS_*.position_model` и обязан показать оба эффекта:

| Эффект | Класс | Потребитель | Точка |
|---|---|---|---|
| композиция промпта персоны | PROMPT_BEHAVIOR | `persona_turn` | `persona_layer.py` |
| ранжирование при кастинге | DETERMINISTIC_ALGORITHM | `select_initial_voice`, `Zarathustra.cast` | `zarathustra.py:294+`, `pipeline.yaml:32` |

Показ только первого = провал приёмки.

Аналогично для контрола `critique_regime`: один семантический контрол, два эффекта, оба видимы, контрол в UI **не расщеплён**.

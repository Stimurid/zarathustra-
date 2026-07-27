# CLAUDE CODE — CONTINUATION HANDOFF
## CALIFORNIAN_ID v0.3.0 → корпус Заратустры, машина спора и donor pass

Ты продолжаешь существующую рабочую сборку `CALIFORNIAN_ID`.

Предыдущий проход уже завершил:

- `CompletionOutcome` и 10 форм завершения;
- отказ от автоматического synthesis;
- `BodyProjection`;
- функциональный кастинг семи голов;
- Заратустру как восьмую голову при разделении HEAD / SPINE;
- chorus mode;
- `AffectBook`;
- 39/39 зелёных тестов;
- версию проекта `v0.3.0`.

Не повторяй Пики 1–3 и не переписывай рабочее ядро без доказанного дефекта.

Текущий проход открывает ранее отложенные задачи:

- **G — Cultural corpus scaffolding and integration**;
- **J — Nietzschean and cultural core acquisition/extraction**;
- **K — argumentation/dispute donor integration**;
- **L — architectonic reconstruction donor integration**;
- **M — hybrid RAG and runtime grounding**.

Работай до результата или реального блокера.

---

# 1. ЛОКАЛЬНЫЙ КОРЕНЬ

В корне рабочей папки сейчас находятся как минимум:

```text
CALIFORNIAN_ID/
tinkuy canon/
промпты доноры/
CLAUDE_CODE_HANDOFF_CALIFORNIAN_ID*
TINKUY_PROMPT_RUNTIME_ARCHITECTURE_V1*
TINKUY_STANDALONE_MVP_ARCHITECTURE_V1.1*
Тинкуй Арх1*
ZARATHUSTRA_SOURCE_ACQUISITION_FINAL*
```

Также пользователь положил в корень книги и материалы, среди которых визуально видны:

- две версии/издания `Тысячи плато` Делёза и Гваттари;
- `bakhtin_poetika_dostoevsky`;
- Бахтин — `Проблемы творчества Достоевского`;
- Бахтин — `К философии поступка`;
- К. Г. Юнг — `The Red Book — Liber Novus`;
- К. Г. Юнг — `Красная книга — Liber Novus`;
- Бруно Латур — `Политики природы`;
- Вахштайн — `Социология вещей`;
- Гурджиев — `Взгляды из реального мира`;
- Поварнин — `Искусство спора. О теории и практике спора`;
- другие файлы и папки, которые нужно установить рекурсивной инвентаризацией.

Названия могут быть обрезаны интерфейсом, содержать кириллицу, пробелы, версии, PDF/EPUB/HTML/TXT/DOCX и дубликаты. Не полагайся на этот список как на точные пути.

---

# 2. СНАЧАЛА — ПОЛНЫЙ INVENTORY

Рекурсивно проиндексируй весь корень, кроме технических кешей и виртуальных окружений.

Для каждого файла установи:

- абсолютный и относительный путь;
- имя;
- размер;
- расширение и фактический MIME/type;
- SHA-256;
- язык;
- автор;
- заглавие;
- издание/перевод, если доступны;
- доступность полного текста;
- является ли это:
  - первичным источником;
  - вторичным исследованием;
  - донорским промптом;
  - архитектурным документом;
  - runtime-кодом;
  - повтором;
  - производным файлом;
  - повреждённым/нечитаемым файлом;
- связь с другими версиями того же текста.

Создай:

```text
CALIFORNIAN_ID/_work/ROOT_SOURCE_INVENTORY.yaml
CALIFORNIAN_ID/_work/DUPLICATE_AND_VERSION_MAP.yaml
CALIFORNIAN_ID/_work/SOURCE_GAPS.md
```

Не перемещай, не переименовывай и не перезаписывай исходные файлы в корне.

Если для работы нужен локальный нормализованный вариант, создавай производный файл внутри `CALIFORNIAN_ID/corpus/`, сохраняя:

- исходный путь;
- hash исходника;
- операцию преобразования;
- hash производного текста;
- точный provenance.

---

# 3. СТАТУС ИСТОЧНИКОВ

Разделяй:

```text
PRIMARY_SOURCE
SECONDARY_SCHOLARSHIP
DONOR_PROMPT
TINKUY_CONTRACT
PROJECT_ARCHITECTURE
INTERPRETIVE_NOTE
DERIVED_EXTRACTION
TEST_FIXTURE
```

Не подменяй первичный текст пересказом или исследовательской статьёй.

Не объединяй молча:

- разные переводы;
- разные редакции;
- `Проблемы творчества Достоевского` и `Проблемы поэтики Достоевского`;
- русский и английский `Liber Novus`;
- французское/английское и русское издания `Тысячи плато`.

Различия версий могут быть содержательно значимыми и должны сохраняться.

---

# 4. КАК ИСПОЛЬЗОВАТЬ КОНКРЕТНЫЕ ИСТОЧНИКИ

## 4.1. Бахтин

Используй:

- `Проблемы поэтики Достоевского`;
- `Проблемы творчества Достоевского`;
- `К философии поступка`.

Извлекай:

- полифонию;
- самостоятельность и незавершимость голоса;
- запрет авторского поглощения героя;
- диалогическое событие;
- слово с оглядкой на чужое слово;
- ответственность и поступок;
- архитектонику `я-для-себя / другой-для-меня / я-для-другого`;
- границы права Заратустры говорить от имени голов;
- критерии ложного синтеза.

Бахтин не должен превращаться в стилистическое украшение. Он задаёт конституционные ограничения оркестратора.

## 4.2. Юнг — Liber Novus

Сопоставь русский и английский тексты.

Извлекай:

- автономные внутренние фигуры;
- активное воображение;
- встречу с фигурой без её мгновенной рационализации;
- преобразование самого субъекта диалога;
- различие между вызванным образом и произвольной фантазией;
- опасность захвата одной фигурой;
- способы возвращения из сцены;
- нарративную память встреч.

Не делай из Юнга доказательство истинности любой внутренней фигуры. Используй его как источник сцен, операций и рисков.

## 4.3. Делёз и Гваттари — `Тысяча плато`

Сопоставь имеющиеся версии.

Извлекай:

- множественность;
- сборку;
- ризому;
- территориализацию / детерриториализацию / ретерриториализацию;
- план консистенции;
- линии ускользания;
- различие дерева и ризомы;
- безорганное тело как ограниченный архитектурный донор;
- механизмы захвата;
- недопустимость сведения сборки к единому центру.

Не превращай `Тысячу плато` в обязательную онтологию всего проекта. Это донор операций и диагностики сборки.

## 4.4. Латур + Вахштайн

Латур — первичная теоретическая опора. Вахштайн — вторичная и интерпретативная.

Извлекай:

- представительство отсутствующих;
- нечеловеческих акторов;
- вещи как участников конфликта;
- сборку вокруг matters of concern;
- составление парламента затронутых;
- проверку: кто не представлен;
- материальные последствия позиции;
- риск подмены участника говорящим от его имени.

## 4.5. Гурджиев

Извлекай:

- множественность `я`;
- отсутствие постоянного хозяина;
- механичность;
- наблюдение;
- формирование центра;
- различение голоса, состояния и субъекта;
- опасность ложного управляющего центра.

Используй ограниченно. Гурджиев не должен становиться скрытой догматической метафизикой Заратустры.

## 4.6. Поварнин — `Искусство спора`

Это основной донор **протокола спора**, но не единственный источник аргументативной логики.

Извлекай:

- виды и цели спора;
- спор ради истины / убеждения / победы;
- условия допустимости спора;
- точность и удержание тезиса;
- подмену тезиса;
- бремя аргумента;
- способы доказательства и опровержения;
- логические и психологические уловки;
- недобросовестные ходы;
- правила отказа и остановки;
- поведение при манипуляции;
- различие сильного возражения и риторического захвата.

Создай исполняемый слой, а не summary книги.

## 4.7. Архитектурные документы Тинкуя

`TINKUY_PROMPT_RUNTIME_ARCHITECTURE_V1`, `TINKUY_STANDALONE_MVP_ARCHITECTURE_V1.1`, `Тинкуй Арх1` и документы в `tinkuy canon/` используются как:

- контракты;
- ограничения;
- схемы;
- архитектурный baseline;
- provenance решений.

Не считай файл каноническим только по тому, что он лежит в `canon/`. Читай статус внутри документа.

Исходный canon не изменяй.

---

# 5. DONOR PASS ПО `промпты доноры/`

Полностью проиндексируй папку `промпты доноры/` по содержанию.

Особенно найди:

- концептуально-архитектонический мастер-промпт v1.2.1;
- варианты объединённого промпта анализа/визуализации;
- `резчик — аналитик — сборщик транскриптов`;
- промпты аргументации;
- Сократику;
- риторику;
- нарративные сборщики;
- оркестраторы;
- анализ многоголосия;
- карты и графы;
- защиту роли;
- провенанс и проверку оснований.

Не вставляй ни один большой донорский промпт целиком в Заратустру.

Для каждого релевантного донора создай карточку:

```yaml
donor_id:
source_path:
title:
version:
status:
usable_operations:
  - operation_id:
    purpose:
    input_contract:
    output_contract:
    invariant:
    extracted_prompt_fragment:
    failure_modes:
    adaptation_required:
target_modules:
provenance:
```

Создай:

```text
CALIFORNIAN_ID/donors/DONOR_REGISTRY.yaml
CALIFORNIAN_ID/donors/DONOR_OPERATION_CARDS/
CALIFORNIAN_ID/donors/DONOR_TO_RUNTIME_MAP.yaml
```

---

# 6. АРХИТЕКТОНИЧЕСКИЙ МАСТЕР-ПРОМПТ

Это главный донор реконструкции общего тела Змея.

Не запускай его целиком после каждого хода.

Извлеки инкрементальный модуль:

```text
CALIFORNIAN_ID/zarathustra/prompt_modules/architectonic_turn_reconstruction.md
```

Он должен принимать:

```yaml
current_body:
previous_turn:
new_turn:
source_context:
```

И возвращать:

```yaml
new_claims:
revised_claims:
withdrawn_claims:
attacked_claims:
new_supports:
new_attacks:
assumptions_exposed:
concepts_introduced:
concept_meanings_changed:
values_activated:
ontology_shifts:
position_changes:
risks:
projects:
futures:
unresolved_questions:
breaks:
loops:
returns:
false_closures:
state_delta:
provenance:
```

Перенеси из донора:

- атомизацию тезиса;
- типизированные связи;
- текстовые якоря;
- различение основания и утверждения;
- дефекты, вопросы и гипотезы;
- обрывы, тупики, циклы, возвраты и повторы;
- запрет ложной совместимости;
- сохранение продуктивного противоречия;
- provenance.

Удали из runtime-версии:

- полный peer-review;
- поабзацную редактуру статьи;
- длинный отчёт;
- требования выдавать готовую редакцию каждого абзаца;
- всё, что не нужно для изменения `BodyProjection` одним ходом.

---

# 7. МАШИНА СПОРА

Создай отдельный пакет:

```text
CALIFORNIAN_ID/argumentation/
├── README.md
├── manifest.yaml
├── dispute_modes.yaml
├── thesis_tracking.yaml
├── attack_defence_operations.yaml
├── burden_rules.yaml
├── fallacies_and_tricks.yaml
├── fairness_policy.yaml
├── refusal_and_stopping.yaml
├── schemas/
├── prompts/
└── tests/
```

Поварнин задаёт культуру и протокол спора.

Дополнительно используй уже существующие в canon/донорах:

- аргументативную ткань Тинкуя;
- Toulmin;
- Walton argumentation schemes;
- pragma-dialectics;
- Socratic elenchus;
- Rapoport `fight / game / debate`.

Не создавай энциклопедию теории аргументации. Реализуй минимальный исполняемый слой, нужный внутреннему совету.

Каждый ход после architectonic reconstruction должен получить dispute assessment:

```yaml
dispute_mode:
thesis_preserved:
burden_state:
valid_attack:
valid_defence:
fallacies_or_tricks:
fairness_events:
required_response_type:
continue_or_stop:
confidence:
```

---

# 8. SCENE / OPERATION CARDS

Создай schema:

```text
CALIFORNIAN_ID/corpus/zarathustra/schemas/scene_operation_card.schema.json
```

Минимальный контракт:

```yaml
card_id:
card_type: scene|operation|constraint|risk|completion_pattern
title:
primary_sources:
  - source_id:
    locator:
    translation_or_edition:
secondary_sources: []
figures: []
situation:
conflicts: []
operation:
activation_conditions: []
contraindications: []
expected_body_delta:
affect:
completion_implications: []
orchestrator_directive_template:
failure_modes: []
provenance_status:
confidence:
```

Создай первые candidate-карточки по реально прочитанным фрагментам.

Не выдумывай равномерное число карточек на источник.

Минимальный первый пакет должен содержать содержательно проверяемые карты для:

- полифонии и незавершимости голоса;
- автор/герой;
- ответственный поступок;
- автономная внутренняя фигура;
- активное воображение;
- множественная сборка;
- детерриториализация;
- парламент отсутствующих;
- множественные `я`;
- удержание тезиса;
- подмена тезиса;
- уловка;
- прекращение бесплодного спора;
- архитектоническая реконструкция хода;
- ложный синтез;
- сохранение dissent;
- смена формы завершения.

---

# 9. СТРУКТУРА КОРПУСА

Создай:

```text
CALIFORNIAN_ID/corpus/zarathustra/
├── README.md
├── SOURCE_MANIFEST.yaml
├── sources/
│   ├── primary/
│   ├── secondary/
│   └── external_references/
├── normalized/
├── section_indexes/
├── scenes/
├── operations/
├── constraints/
├── risks/
├── schemas/
└── extraction_reports/
```

Исходники в корне остаются immutable.

В `SOURCE_MANIFEST.yaml` должны быть:

- source_id;
- title;
- author;
- path;
- hash;
- language;
- edition;
- translation;
- primary/secondary;
- rights/status;
- parse status;
- normalization status;
- extraction coverage;
- known gaps.

---

# 10. RAG

Сейчас нужен **управляемый гибридный retrieval**, не agentic RAG.

Создай три пространства:

```text
zarathustra_scenes
zarathustra_operations
zarathustra_primary_fragments
```

Маршрут:

```text
BodyProjection + текущее напряжение
→ требуемая функция вмешательства
→ metadata filter
→ hybrid lexical/vector retrieval
→ rerank
→ 1–3 карты
→ при необходимости 1–3 первичных фрагмента
→ prompt stack Заратустры
```

Обязательно:

- metadata filtering;
- exact provenance;
- source/translation identity;
- duplicate suppression;
- lexical fallback;
- тест без внешней vector DB;
- trace каждого retrieval event.

Не передавай в контекст целые книги.

Не позволяй similarity search самостоятельно определять действие без routing function.

---

# 11. ИНТЕГРАЦИЯ С ЗАРАТУСТРОЙ

Сохраняй **один runtime-модуль Заратустры**, как уже принято.

Не создавай новых скрытых агентов:

- отдельного судью;
- отдельного суммаризатора;
- отдельного начальника голосов.

Можно создавать чистые функции, data classes и prompt modules.

Добавь в ход Заратустры:

1. чтение `BodyProjection`;
2. architectonic reconstruction последнего хода;
3. dispute assessment;
4. определение дефицита сцены;
5. retrieval культурной операции;
6. назначение следующей голове:
   - функции;
   - операции;
   - объекта воздействия;
   - запретов;
   - критерия нового вклада;
7. обновление общего тела;
8. проверку формы завершения.

Не превращай культурный RAG в стилизацию под Ницше.

---

# 12. PROMPT STACK

Сохрани существующую нумерацию 12 файлов.

Допускается:

- обновить содержание;
- добавить импортируемые prompt modules;
- ввести manifest зависимостей.

Не допускается:

- один гигантский prompt;
- копирование Поварнина или мастер-промпта целиком;
- смешивание identity, retrieval, dispute assessment и completion в одном блоке.

Создай:

```text
CALIFORNIAN_ID/zarathustra/PROMPT_DEPENDENCY_MAP.yaml
```

Для каждого prompt:

- назначение;
- входы;
- зависимости;
- используемые donor operations;
- используемые cultural cards;
- output schema;
- version.

---

# 13. ТЕСТЫ

Существующие 39 тестов не должны регрессировать.

Добавь минимум:

1. source inventory test;
2. duplicate version preservation;
3. primary/secondary separation;
4. donor prompt extraction test;
5. architectonic turn delta;
6. claim atomization;
7. thesis substitution detection;
8. fallacy/trick detection;
9. dispute stopping;
10. polyphony preservation;
11. authorial absorption rejection;
12. retrieval metadata filtering;
13. translation/version provenance;
14. no false quotation;
15. RAG lexical fallback;
16. retrieval trace;
17. cultural card activation;
18. cultural card contraindication;
19. source-grounded completion-form choice;
20. end-to-end council with corpus retrieval.

Mock tests должны работать без внешнего API.

При наличии модели выполни live case:

```text
«Следует ли ради безопасности централизовать управление развитием сильного ИИ?»
```

Проверяй:

- не свёл ли Заратустра спор к голосованию;
- представлен ли отсутствующий/нечеловеческий участник;
- сохранён ли конфликт свободы и безопасности;
- не подменён ли тезис;
- использована ли культурная операция по функции;
- не создана ли ложная цитата;
- почему выбрана конкретная форма завершения.

---

# 14. ПРОДУКТЫ ПРОХОДА

Обязательные результаты:

```text
CALIFORNIAN_ID/_work/ROOT_SOURCE_INVENTORY.yaml
CALIFORNIAN_ID/_work/DUPLICATE_AND_VERSION_MAP.yaml
CALIFORNIAN_ID/_work/SOURCE_GAPS.md

CALIFORNIAN_ID/donors/DONOR_REGISTRY.yaml
CALIFORNIAN_ID/donors/DONOR_OPERATION_CARDS/
CALIFORNIAN_ID/donors/DONOR_TO_RUNTIME_MAP.yaml

CALIFORNIAN_ID/corpus/zarathustra/SOURCE_MANIFEST.yaml
CALIFORNIAN_ID/corpus/zarathustra/schemas/scene_operation_card.schema.json
CALIFORNIAN_ID/corpus/zarathustra/scenes/
CALIFORNIAN_ID/corpus/zarathustra/operations/
CALIFORNIAN_ID/corpus/zarathustra/extraction_reports/

CALIFORNIAN_ID/argumentation/

CALIFORNIAN_ID/zarathustra/prompt_modules/architectonic_turn_reconstruction.md
CALIFORNIAN_ID/zarathustra/PROMPT_DEPENDENCY_MAP.yaml

CALIFORNIAN_ID/rag/zarathustra/
CALIFORNIAN_ID/tests/
CALIFORNIAN_ID/examples/demo_runs/

CALIFORNIAN_ID/_work/CORPUS_AND_DONOR_COMPLETION_REPORT.md
CALIFORNIAN_ID/HANDOFF.md
CALIFORNIAN_ID/CHANGELOG.md
```

Версию подними только после прохождения тестов. Рекомендуемый статус:

```yaml
version: 0.4.0
status: candidate
```

---

# 15. DEFINITION OF DONE

Проход завершён, когда:

- все файлы корня проинвентаризированы;
- источники не изменены;
- версии и дубликаты разведены;
- первичные и вторичные источники различены;
- релевантные донорские промпты прочитаны полностью;
- операции из доноров извлечены;
- architectonic reconstruction работает инкрементально;
- машина спора интегрирована;
- созданы проверяемые cultural cards;
- RAG индексирует карты и фрагменты раздельно;
- retrieval имеет provenance и trace;
- Заратустра получает культурную операцию по функции;
- форма завершения остаётся множественной, synthesis не возвращён как default;
- старые 39 тестов проходят;
- новые тесты проходят;
- есть end-to-end demo;
- completion report честно перечисляет coverage и source gaps.

Папка с книгами сама по себе не является корпусом.
Summary книги не является извлечённой операцией.
Большой системный prompt не является архитектурой.
Векторный индекс без provenance не является приемлемым RAG.

Начинай с inventory корня и полного donor pass. Не спрашивай пользователя, где лежит файл, пока рекурсивный поиск не доказал его отсутствие.

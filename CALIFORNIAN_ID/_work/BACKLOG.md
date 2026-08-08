# BACKLOG — CALIFORNIAN_ID

## КАРТА ПИКОВ (roadmap стендалон-Тинкуя)

По каноническому `TINKUY_STANDALONE_MVP_ARCHITECTURE_V1.1` (226 док-номеров).
Пиков 1-4 закрыты (совет, персоны, корпус карт, аргументативный слой, RAG).
Оценка покрытия канона на 2026-08-08 ≈ **30-35%**. Ниже — как закрыть остальное.

### ⏳ Пик 5 — СВОЯ ФАБРИКА ТКАНИ (в работе, крит-блокер стендалона)
Без своего резчика мы не сервис, а обёртка над LLM. Сейчас принимаем только
готовые md-units и делаем плоский pre-pass.
- 5.1 Schemas (JSON Schema + dataclasses): SemanticUnit / Block / Relation /
  Thread / Snapshot / SourceSpan / EvidenceFragment / SceneState.
  Канон 015-024, 035-044.
- 5.2 Prompts `data/fabric/*.md` (11 модулей, канон 045-056):
  FabricParserOrchestrator, CoarseComposition, MultiscaleSegmentation,
  SemanticMoveExtraction, BlockAssembly, RelationExtraction, ThreadInduction,
  CrossScaleReconciliation, WindowBoundaryRepair, FabricProvenanceValidator,
  FabricNoLossValidator.
- 5.3 `fabric/parser.py` — исполнитель orchestrator: source_map →
  coarse_composition → moves → blocks → relations → threads → reconciliation.
- 5.4 `fabric/store.py` — SQLite (JSON1) хранилище ткани: таблицы
  source_artifact, source_version, source_span, evidence_fragment,
  semantic_unit, semantic_block, semantic_relation, semantic_thread,
  semantic_snapshot.
- 5.5 `Pipeline.run_from_raw_text(text) → SemanticSnapshot → CouncilResult`:
  парсит ткань → сохраняет snapshot → seed'ит argument_map/BodyProjection
  из ткани → зовёт inner council по обычной схеме.
- 5.6 CLI: `python -m californian_id fabric parse --file X.txt`,
  `fabric snapshot <run_id>`, `fabric export <run_id> --format md|json`.
- 5.7 Web UI: новый Input Mode "raw + fabric" который для длинных текстов
  автоматически запускает fabric parser перед советом.
- 5.8 Валидаторы: NoSilentOverwriteGuard, FabricNoLossValidator,
  FabricProvenanceValidator, SourceCoverageValidator (канон 2.19-2.21, 055-056).
- 5.9 Тесты: unit — round-trip snapshot; integration — fabric+council на
  реальном транскрипте 5-10 стр.
- **Приёмка (§9 канона):** испытание A (сократическая линия), B (атака →
  защита → карта применимости), C (полный текст → 5-7 связанных вмешательств).
- **Оценка:** 3-5 дней. **Deliverable:** пользователь вставляет транскрипт
  100 страниц, получает ткань + связный совет по ткани.

### 🔜 Пик 6 — REALTIME + WORKSPACE + MULTI-USER
Сейчас: sync HTTP, per-run, single-user, тишина 90-180s.
- 6.1 SSE streaming — turn-by-turn прогресс в UI (persona → operation →
  utterance).  Endpoint `GET /api/run/{id}/stream`.
- 6.2 TinkuyWorkspace (канон 2.1) — контейнер исследования: сессия + история
  run'ов + snapshot ткани, привязанные к user_id. SQLite таблица workspace.
- 6.3 Async job queue — POST /api/run → 202 {run_id}; GET /api/run/{id} →
  status; GET /api/run/{id}/result → payload. Пользователь может закрыть
  браузер и вернуться.
- 6.4 Auth: basic → JWT + user table. `/etc/tinkuy/users.yaml` или SQLite.
  Per-user quotas.
- 6.5 История в UI: список run'ов пользователя, повторный прогон,
  cross-run reflection ("покажи все run'ы про X").
- **Оценка:** 2-3 дня. **Deliverable:** сервис-как-сервис, не local demo.

### 🔜 Пик 7 — MethodPacks + Dialogue + Rhetoric (глубина)
По канону 090-150. У нас закрыт argumentation (Toulmin+Поварнин).
- 7.1 6 универсальных MethodPack'ов: ClaimAndLogicAnalysis,
  ArgumentReconstruction, ConceptualAnalysis, OntologicalReconstruction,
  Problematisation, SocraticInquiry.
- 7.2 RhetoricalTransformer + 5-7 жанров (academic critique, socratic
  questions, methodological consultation, ironic demolition, supportive
  reframing, forensic argument, short intervention).
- 7.3 PositionModelPack'и для 8 персон по каноническому шаблону 194-200
  (сейчас только persona_constitution.md — недостаточно структурно).
- 7.4 5 Dialogue protocols: Listening, Clarifying, Socratic, Joint Inquiry,
  Problematising (канон 106-111).
- **Оценка:** ~1 неделя. **Deliverable:** совет умеет 6 методов, 7 жанров
  предъявления, 5 диалоговых протоколов.

### 🔜 Пик 8 — Export + Cross-run + Publish
- 8.1 ExportService (канон 2.55): Markdown / DOCX / JSON / trace bundle.
  Кнопка «скачать» в UI. Voice + closing + ткань + trace в одном bundle.
- 8.2 Cross-run reflection: «покажи все run'ы про свободу», «сравни этот
  совет с прошлым». Требует Пик 5 (ткань) + Пик 6 (workspace).
- 8.3 Полировка `/v1/*` OpenAI-compatible endpoint: per-API-key auth +
  rate limit + billing metrics.
- 8.4 Public docs + пример «Тинкуй как LLM для чужой системы».
- **Оценка:** 2-3 дня.

### 🔜 Пик 9 — Полировка + Corpus expansion
- 9.1 Persistent narrative memory Заратустры (SQLite store).
- 9.2 Cost budgets enforcement (soft → hard, per-user).
- 9.3 CI/CD — `.github/workflows/tests.yml` на push/PR.
- 9.4 PyPI publish (сейчас только `pip install git+…`).
- 9.5 Cultural corpus expansion: 18 карт → 200+ по Ницше книга IV, Платон,
  Достоевский, Бахтин, Иов, Гита, Гурджиев, Латур.
- 9.6 Gold Test Corpus + regression suite (канон 4.11, 212-223).
- **Оценка:** ~1 неделя.

---

## Правила чтения этой карты для следующей сессии
- Пики закрываются последовательно. Пик N+1 требует Пика N.
- Внутри одного Пика подзадачи (5.1, 5.2, …) можно делать параллельно
  в разных worktree/агентах, но `_work/DECISIONS.md` пусть удерживает
  единый контракт.
- После закрытия Пика — обновить эту карту (переставить ⏳ → ✅), в
  `CHANGELOG.md` добавить raздел «vX.Y.0: Пик N закрыт», написать
  испытания по канону §9.

---

## Раздел 5. Multi-orchestrator + human-in-the-loop + shared corpus

Направление от пользователя (2026-08-08). Требует отдельного проектирования.

### B-5.1. Второй проход: Сократ-оркестратор + новые персоны (Мавринский корпус)
- **Задача:** сделать вторую многоголовую конструкцию по образу Заратустры,
  но с оркестратором **Сократ** и другим набором субличностей (расшифровки
  Мавринского). Инфа хранится у пользователя в ГПТ — нужно **запросить у
  него** и загрузить.
- Каждый оркестратор (Заратустра/Ассуна/Сократ/…) имеет свой prompt-стек,
  свою логику routing и свои формы завершения. Персоны частично
  пересекаются, частично уникальны.
- **Зависимости:** дождаться от пользователя расшифровок Мавринского;
  реализовать B-5.4 (multi-orchestrator в pipeline).

### B-5.2. Ассуна + расширенный Бахтинский корпус
- Добавить Ассуну как отдельного оркестратора / персону.
- Расширить существующий Бахтинский слой (сейчас 2-3 карты) до полноценного
  корпуса — все доступные тексты Бахтина, размеченные scenes/operations.

### B-5.3. Cross-provider persona routing
- **Задача:** каждая персона может ехать на своей модели. Gemini-персона
  общается с GPT-персоной, обе слушают Opus-Заратустру.
- **Схема:** `persona.manifest.yaml` получает поле `preferred_model` (или
  `preferred_provider`), которое переопределяет provider для этой персоны
  на этот ход. Оркестратор — свой отдельный провайдер.
- **Ценность:** снимает «моно-модельность». Реальная полифония стилей и
  reasoning-путей.
- **Совместимо с:** уже существующим 302.ai + fallback chain +
  model_override в UI. Расширение: model_override становится
  per-persona, не глобальный.

### B-5.4. Форматы советов: Переслегинские реакторы и коллайдеры
- **Задача:** сейчас есть только один формат — sequential inner council
  с 10 формами завершения. Добавить как отдельные `AssemblyProtocol`:
  - `reactor` (Переслегин) — контролируемая цепная реакция, стадии
    разгона/удержания/гашения
  - `collider` (Переслегин) — направленное столкновение двух рамок с
    измерением энерговыделения
  - `dialectical_assembly` (уже в каноне 163)
  - `parallel_lens` (уже в каноне 162)
  - другие сценированные дискуссии
- Каждый формат — отдельный `orchestrator_prompt` + `workflow_yaml`, вызов
  из UI через новый dropdown «Формат совета».

### B-5.5. Human-in-the-loop внутри совета (НЕ post-hoc review)
- **Ключевой сдвиг:** пользователь не бросает текст → ждёт result. Он
  **внутри** беседы: видит идущий совет в реальном времени, может:
  1. **Направлять поток** — «пусть эту линию продолжит Сингуляритарианец,
     а не Cost_seer»
  2. **Менять приоритеты** — усилить/ослабить голос **бегунком**
  3. **Усилить голос напрямую** — своим аргументом (текстовый вклад
     пользователя становится частью тела Змея)
  4. **Прикрепить файл** — файл усиливает какого-то голоса
  5. **Погружаться в чужие субветки** — интерфейс показывает не только
     финальную речь, но и внутреннюю драму (у нас trace уже есть, надо
     превратить в UI)
- **Требования:** streaming (SSE/WebSocket), pause/resume run, live
  edit-in-place body, реактивный UI (React/Vue?). См. B-1.5 realtime
  intervention.

### B-5.6. Shared corpus (кэш эмбеддингов через common vocabulary)
- **Проблема:** библиотека уже гигабайты. Персоны и оркестраторы
  пересекаются в источниках (Бахтин у Заратустры и Сократа; Ницше у
  Заратустры и Ассуны; и т.д.).
- **Плохое решение:** отдельный embedding per persona = дорого × N.
- **Альтернативное решение (мы обсуждали, надо вспомнить):**
  - **Гипотеза 1:** shared embedding backbone (один индекс) + per-persona
    **фильтр provenance + rerank prompt-based**. Один embed(source), но
    какая персона это увидит — решается на этапе retrieval.
  - **Гипотеза 2:** shared card layer поверх source layer. Cards
    (SceneOperationCard) — общие; embedding строится по картам, а не по
    сырому тексту. Тогда card × persona_activation_condition — routing.
  - **Гипотеза 3:** «linden» / matryoshka embeddings — один общий индекс,
    несколько projection heads (по одному на персону) — дообучаемо, если
    у нас есть feedback loop.
- **Действие:** пользователь просит вспомнить, что мы обсуждали. **Уточнить
  у пользователя (или через ГПТ-историю).** Записано как открытый вопрос.

---


Записи для следующих сессий. Читай в начале сессии, чтобы не переоткрывать
уже понятое. Не переносить в CHANGELOG, пока не сделано.

---

## Раздел 1. Работа с большими входами и с пакетами юнитов

### B-1.1. Focus mode для run_from_units
- **Задача:** `Pipeline.run_from_units(pack, focus_on=["U3","U7","U12"])`.
  Совет обсуждает подмножество юнитов, остальные попадают в chorus как
  фон/контекст, но не как предмет.
- **Зачем:** сейчас, если в пакете 100 юнитов, совет всё равно обсуждает
  один `seminar_title` — нельзя точечно поговорить об одном юните из ста.
- **Оценка:** ~½ дня.
- **Файлы:** `pipeline.py::run_from_units` (аргумент focus_on),
  `_situation_from_pack` (topic = title focus'а, если один юнит),
  `_seed_argument_map_from_pack` (seed'ит только focus подмножество,
  остальное — в chorus как «фон»).
- **Тесты:** synthetic pack на 5 юнитов, `focus_on=["U2"]` — argument_map
  должен содержать только U2-теги; форма завершения основана на U2.

### B-1.2. Per-unit mode
- **Задача:** `Pipeline.run_from_units(pack, mode="per_unit")`.
  Мини-совет на каждый юнит независимо (или пачками по 3–5), потом
  мета-совет над мета-выходами. Форма выхода:
  `{unit_id: CompletionOutcome, ...} + meta_completion`.
- **Зачем:** покрывает сценарий «дай мне разбор каждого юнита из
  пакета по-отдельности + свод сверху».
- **Оценка:** ~1 день.
- **Файлы:** новый `pipeline.py::_run_per_unit(pack, mode)`, новая
  структура выхода `PerUnitPipelineResult(unit_results: dict[str, PipelineResult],
  meta: PipelineResult)`.
- **Зависимости:** `run_from_units` уже готов, per-unit просто зовёт его
  N раз с `focus_on=[Ui]` (нужен B-1.1 сначала).

### B-1.3. Long text chunker
- **Задача:** разбиение сырого текста по параграфам/секциям, каждый
  chunk идёт как отдельный «псевдо-юнит» через `run_from_units`.
- **Зачем:** сейчас `text[:20000]` в LLM path — хвост игнорируется
  на 100-страничных входах. Chunker снимает потолок.
- **Оценка:** ~½ дня.
- **Файлы:** новый `adapters/text_chunker/` с regex-разбивалкой по
  заголовкам/пустым строкам/длине. Компромисс: это встраивание
  простейшего резчика внутрь pipeline — не полноценная ткань Тинкуя.
- **Ограничение:** результат хуже, чем внешний резчик. Работа на
  случай отсутствия резчика.

### B-1.4. Увеличить text cap в LLM path
- **Задача:** сейчас `text[:20000]` в `_llm_situation`. Anthropic Claude
  держит 200K, OpenAI GPT-4o 128K. Поднять до 100K с warning в config.
- **Зачем:** тексты до ~25 страниц пойдут в модель целиком без chunking.
- **Оценка:** 15 минут кода + документация про cost.
- **Файлы:** `zarathustra.py::_llm_situation` (`text[:CAP]`), `config/models.yaml`
  добавить `situation_reading_max_input_chars`, README про cost.

---

## Раздел 2. Универсальный LLM-определитель формата пакета

### B-2.1. UnitPack adapter registry + LLM format detector
- **Задача:** вместо одного жёсткого `units_of_content_md` — реестр
  адаптеров, LLM смотрит начало файла и решает, какой adapter вызвать
  (или сгенерировать fallback JSON adapter на лету).
- **Зачем:** сейчас каждый новый формат резчика требует отдельного
  Python-adapter'а. LLM-определитель снимает необходимость писать код
  под каждую вариацию.
- **Оценка:** 2–3 дня. Большая архитектура.
- **Зависимости:** нужна стабильная схема `UnitPack` (готова) и
  промпт `adapter_format_detection.md` (новый).

---

## Раздел 3. Real-LLM полировка (после первого live-запуска у пользователя)

### B-3.1. JSON parsing resilience
- **Задача:** после первого прогона на Anthropic/OpenAI — вероятно
  вылезут случаи, когда модель возвращает JSON с лишними полями,
  чуть иным именованием или обёртками. Уточнить schema retry в
  `_json_from_text` и добавить fuzzy field mapping.
- **Зачем:** пока код только на mock. Первый живой прогон почти
  гарантированно найдёт мелочи.

### B-3.2. Prompt tuning под конкретный live-провайдер
- **Задача:** после первого прогона может понадобиться уточнить
  `03_scene_reading.md`, `04_head_calling.md`, `09_completion_form_selection.md`
  под особенности выбранного провайдера.
- **Оценка:** ½–1 день после первого live-прогона.

---

## Раздел 3-bis. Persona-layer заточка (v0.4.3 candidate)

### B-3bis.1. Вынести ROUTING_KEYWORDS из Python в persona manifest
- **Задача:** удалить `ROUTING_KEYWORDS` dict из `src/californian_id/persona_layer.py`.
  Переехать в `runtime_assets/personas/v0.2/personas/<ID>/manifest.yaml`
  под `routing.topics` (уже есть в schema). Добавить `routing.topics_ru`
  для русских корней.
- **Зачем:** сейчас keyword-таблица захардкожена в Python-модуле. Чужие
  персоны не смогут переопределить без правки кода библиотеки. Русский
  ввод не матчится вообще (English-only).
- **Оценка:** ~2 часа. Тесты: routing на RU-input даёт non-random cast.

### B-3bis.2. Вынести FULL_COUNCIL_KEYWORDS в policy YAML
- **Задача:** переехать в `runtime_assets/personas/v0.2/registry/policies.yaml`
  под `full_council_triggers` с multi-lingual поддержкой.
- **Зачем:** сейчас триггер полного совета вшивает governance-домен
  (charter/century/constitutional/civilizational). Ядро становится
  domain-specific — это ровно то, от чего v0.4.2 избавляло.

### B-3bis.3. Вынести NEMO8_TRIGGER_KEYWORDS в N8 rag_policy
- **Задача:** переехать в `runtime_assets/personas/v0.2/personas/N8/rag_policy.yaml`
  под `activation_triggers`. N8 сам решает, когда включаться.
- **Зачем:** NEMO-8 сейчас триггерится по governance/parrhesia словарю.
  Домен снова вшит.

### B-3bis.4. Опциональный LLM-matching для routing
- **Задача:** при live провайдере — использовать concepts, выданные
  `_llm_situation`, как дополнительный сигнал для persona-layer cast.
  Русский текст и любой домен получают семантический matching, а не
  keyword-only.
- **Зависимости:** B-3bis.1 сделан (persona.routing.topics — источник
  истины). Без него — двойное место истины.

## Раздел 4. Не в scope библиотеки (но пользователи спросят)

### B-4.1. PyPI publish
- Сейчас `pip install git+https://github.com/Stimurid/zarathustra-.git`
- PyPI-релиз позже, когда стабилизируется API.

### B-4.2. GitHub Actions CI
- Auto-run 76 тестов на push/PR. ~20 минут работы. `.github/workflows/tests.yml`.

### B-4.3. Persistent narrative memory
- Сейчас per-run. Для conversation continuity нужен SQLite или Redis
  адаптер. Контракт `narrative_memory` промпт уже описывает.
- ~½ дня работы.

### B-4.4. Telegram/Feynman thin adapters
- Контракты в `adapters/*/README.md`. Кода нет. Пользователь оборачивает
  сам.

---

## Правила для будущих сессий

1. Читай этот файл первым.
2. Не переоткрывай уже принятые решения (см. `DECISIONS.md`).
3. Не переизвлекай corpus (см. `SOURCE_MANIFEST.yaml`).
4. Не восстанавливай заточку словаря — она снята сознательно в v0.4.2.
5. Не пиши мок как «умную» модель — mock детерминистичен и для тестов.
6. При добавлении пунктов сюда — оставляй **задачу**, **зачем**,
   **оценку**, **файлы**, **зависимости**.

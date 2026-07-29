# BACKLOG — CALIFORNIAN_ID

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

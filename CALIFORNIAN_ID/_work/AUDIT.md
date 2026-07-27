# AUDIT — CI-G01

## Что было в рабочем каталоге

- `tinkuy canon/` — полный локальный экспорт Canon Тинкуя (20 слоёв, 00–20).
- `промпты доноры/` — 5 подпапок донорских промптов (агентные архитектуры,
  онтологические режимы, креативные движки, аналитические операторы, стилизация).
- Три дополнительных файла архитектурного уровня:
  - `TINKUY_PROMPT_RUNTIME_ARCHITECTURE_V1 — архитектура интеллектуальной машины и реестр корпуса.docx`
  - `TINKUY_STANDALONE_MVP_ARCHITECTURE_V1.1 — техническое ядро, ткань, RAG и полный корпус документов.docx`
  - `Тинкуй Арх1.docx`
- `ChatGPT - тинкуй.html` (экспорт беседы) и её `_files/` — не использовались.
- `CLAUDE_CODE_HANDOFF_CALIFORNIAN_ID.md` — задача этой сборки (1400 строк).

Реального Python skeleton («бот Сапольского») в трёх дополнительных
файлах не оказалось: они архитектурные спецификации, не код. Поэтому
runtime был поднят с нуля на минимальном Python-стеке (Python 3.11+,
PyYAML, pytest), но полностью в согласии с каноническими контрактами.

## Что переиспользуется из canon (найденные gold-файлы)

- `12_пайплайны_и_оркестраторы/digital_personality_runtime/` — рабочий
  референс-скелет пайплайна persona-runtime (S01–S10 + fail_closed +
  prompts P00–P06). Использован как **прототип** для нашего pipeline.yaml,
  state_model.yaml и prompt stack Заратустры.
- `12_пайплайны_и_оркестраторы/world_value_position_narrative_to_group_soul/`
  — архетип синтезирующего оркестратора (`assemble_shared_nucleus`,
  `preserve_dissent`, `review_gate`). Использован как модель для
  Zarathustra synthesis policy.
- `09_культурные_персоны/G-U06_cultural_persona_lenses/`
  `CULTURAL_PERSONA_LENS_LIBRARY.yaml` + `CULTURAL_PERSONA_LENS_CONTRACT.md`
  — семь готовых линз с полем `assignment_prohibited: true` и запретом
  профилирования/имитации. Использован как **обязательный шаблон
  дисциплины** для наших семи fixture-персон и как императив для
  реальных семи персон, которые придут позже.
- `14_Group_Soul/G-U07_Group_Soul/GROUP_SOUL_MINORITY_RETENTION_LAW.md`
  — единственный корректный закон компрессии итогов. Полностью встроен в
  `zarathustra.synthesize` + `_derive_minority_positions`.
- `12_.../digital_personality_runtime/communication/jailbreak_and_manipulation_policy.yaml`
  — jailbreak ladder (levels 0–4), anti_sycophancy, forbidden_responses.
  Адаптирован в `interaction/manipulation_policy.yaml` и `interaction.py`.
- `02_схемы_данных_и_контракты_выходов/` — 30+ JSON Schemas. Наши
  dataclass-схемы `schemas.py` — совместимая проекция; полноценный
  jsonschema-валидатор может быть подключён позже без изменений runtime.
- `11_агенты_карты_и_колоды/G-U21_DP-01_agent_pack/` — эталон structure
  persona-пакета (identity_core, values, style_pack, rhetorical_operations,
  action_model, interaction_policy). Наш `persona.schema.json` соответствует.

## Что переиспользуется из донорских промптов

- `02_агентные_архитектуры/Orc_agent_met.docx` — общий паттерн
  многоагентного оркестратора («пять/семь режимов — части одного тела»).
  Использован как концептуальный референс для Zarathustra
  `identity_and_laws.md`.
- `02_агентные_архитектуры/Agent 0/A/B/C.docx` — паттерн
  последовательного handoff. Совместим с нашим sequential loop.
- `02_агентные_архитектуры/промпты бобера.docx` — claim taxonomy
  (`source_fact / inference / hypothesis / conflict / gap / question`),
  «не сглаживай противоречия ради красивого отчёта». Встроено в
  synthesis policy.
- `01_онтологические_режимы/antiGPT_SP.docx` — принцип защиты от свода
  роли к generic assistant. Встроено в `zarathustra/interaction_defense.md`.
- `05_стилизация/SYSTEM ROLE anti-slop.docx` — принцип quality gate
  синтеза. Встроено в `zarathustra/synthesis.md`.

## Решения аудита

1. **Не форкать `digital_personality_runtime` файлами.** Слишком
   специфичен под DP-01. Взяли структурные паттерны, реализовали заново.
2. **Персоны — линзы, не люди.** Явное каноническое требование. Все семь
   fixture-персон помечены `assignment_prohibited: true`. Реальные семь,
   которые придут позже, обязаны проходить тот же контракт.
3. **Runtime собран на mock-модели.** Так работает end-to-end без ключей.
   Anthropic/OpenAI подключаются одним флагом.
4. **RAG — lexical BM25-fallback.** Векторный store в этом MVP не
   собирали (нет корпусов у fixture-персон); интерфейс подготовлен.
5. **Feynman API — только контракт, не реализация.** Endpoints нигде не
   найдены; писать mock, выглядящий как реальный, было бы вредно.
6. **Telegram — только backlog.** Реального skeleton в трёх файлах нет.
   Ядро от Telegram не зависит; связка тривиальна, но требует Telegram
   token — вне scope этого прохода.

## Что не читалось из canon (сознательно отложено)

- `06_методы_мышления_и_TRIZ` — не требуется для этого MVP.
- `18_экспериментальные_версии` — не canonical.
- `19_экспорты_и_релизы` — вне scope.
- Полные тексты 226 документов из `TINKUY_STANDALONE_MVP_ARCHITECTURE_V1.1`
  — читались только релевантные схемы; контрактам «Калифорнийского Ида»
  этого достаточно.

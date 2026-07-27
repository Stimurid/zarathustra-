# CORPUS & DONOR PASS — CALIFORNIAN_ID v0.4.0

## Status

**WORKING** — все обязательные продукты Пика 4 из
`CLAUDE_CODE_CONTINUATION_CORPUS_DONORS_ZARATHUSTRA.md` созданы;
66/66 тестов (39 старых из v0.3.0 + 27 новых из Пика 4) проходят на
mock-провайдере; end-to-end live case из handoff (deep, 12 ходов, все
7 голосов, форма `aporia`) отработан.

## Что произведено

### Inventory
- `_work/ROOT_SOURCE_INVENTORY.yaml` — 1171 файл в корне, полный SHA-256
  и классификация:
  - PRIMARY_SOURCE: 137
  - SECONDARY_SCHOLARSHIP: 1 (Вахштайн)
  - TINKUY_CONTRACT: 746
  - DONOR_PROMPT: 49
  - PROJECT_ARCHITECTURE: 86
  - ARCHIVE: 66
  - RUNTIME_CODE: 20
  - TEST_FIXTURE: 8
  - DERIVED_EXTRACTION: 5
  - UNKNOWN: 33
- `_work/DUPLICATE_AND_VERSION_MAP.yaml` — точные hash-дубликаты + карта
  версий по семантической близости имён.
- `_work/SOURCE_GAPS.md` — что не извлечено (fb2/epub/djvu) и почему.

### Corpus (11 источников извлечено)
`corpus/zarathustra/normalized/*.txt` — все с provenance
{source_path, source_sha256, method}. `SOURCE_MANIFEST.yaml` разводит
разные переводы/издания одного текста.

| Source | Language | Chars |
|---|---|---|
| BAKHTIN_PROBLEMS_DOSTOEVSKY_CREATIVITY_RU | ru | 1,048,153 |
| BAKHTIN_K_FILOSOFII_POSTUPKA_RU | ru | 140,859 |
| JUNG_RED_BOOK_LIBER_NOVUS_EN | en | 1,298,739 |
| JUNG_KRASNAYA_KNIGA_LIBER_NOVUS_RU | ru | 710,693 |
| DELEUZE_GUATTARI_MILLE_PLATEAUX_FR_1980 | fr | 1,841,898 |
| DELEUZE_GUATTARI_TYSYACHA_PLATO_RU_2010 | ru | 1,827,614 |
| LATOUR_POLITIKI_PRIRODY_RU | ru | 796,406 |
| VAKHSHTEIN_SOCIOLOGY_OF_THINGS_RU | ru (secondary) | 1,100,418 |
| GURDJIEFF_VIEWS_FROM_REAL_WORLD_RU | ru | 154,811 |
| POVARNIN_ISKUSSTVO_SPORA_RU | ru | 262,413 |

**Не смешаны**: FR оригинал и RU перевод Mille Plateaux; EN и RU
Liber Novus; Bakhtin's "Проблемы творчества" ≠ "Проблемы поэтики" (обе
работы отдельно); Latour (primary) ≠ Vakhshtein (secondary).

### Donor pass
- `donors/DONOR_REGISTRY.yaml` — 8 доноров с извлечёнными операциями.
- `donors/DONOR_OPERATION_CARDS/*.yaml` — 7 карт с input/output
  контрактом и adaptation_required.
- `donors/DONOR_TO_RUNTIME_MAP.yaml` — привязка каждого операционного
  контракта к конкретному runtime модулю.

Ключевой донор: `DONOR_ARCHITECTONIC_MASTER_v1_2_1` (концептуально-
архитектонический анализ v1.2.1) — извлечена **только** инкрементальная
часть; полный peer-review и поабзацная редактура **удалены**.

### Cultural cards (18 карт)
`corpus/zarathustra/{scenes,operations,constraints,risks}/*.yaml`.
Каждая карта — валидна по `schemas/scene_operation_card.schema.json`,
имеет `provenance_status ∈ {quoted, paraphrased_with_locator,
reconstructed_no_locator}`, все ссылающиеся на реальные извлечённые
корпуса имеют настоящие locators + `quote_hash: sha256:…`.

Обязательный первый пакет из handoff покрыт полностью:
- полифония (BAKHTIN)
- незавершимость голоса (BAKHTIN)
- автор/герой (BAKHTIN)
- ответственный поступок (BAKHTIN K FILOSOFII POSTUPKA)
- автономная внутренняя фигура (JUNG)
- активное воображение (JUNG)
- множественная сборка (DELEUZE/GUATTARI, обе версии)
- детерриториализация (DELEUZE/GUATTARI, обе версии)
- парламент отсутствующих (LATOUR + VAKHSHTEIN secondary)
- множественные я (GURDJIEFF)
- удержание тезиса (POVARNIN)
- подмена тезиса (POVARNIN)
- уловка (POVARNIN)
- прекращение бесплодного спора (POVARNIN)
- архитектоническая реконструкция (DONOR master prompt)
- ложный синтез (POVARNIN + BAKHTIN)
- сохранение dissent (canon MINORITY_RETENTION_LAW)
- смена формы завершения (local zarathustra/09)

### Argumentation
`argumentation/` — полный пакет:
- 8 YAML-полиси (dispute_modes, thesis_tracking, attack_defence_operations,
  burden_rules, fallacies_and_tricks, fairness_policy, refusal_and_stopping),
  все со ссылкой на Поварнина + канон.
- `schemas/dispute_assessment.schema.json`.
- `prompts/socratic_question_chain.md` (из DONOR_SOCRATIC_ELECTIVES).
- Runtime: `src/californian_id/argumentation.py` с
  `DisputeAssessment`, `assess_turn`, `detect_thesis_substitution`,
  `detect_fallacy_or_trick`, `check_anti_slop`.

Каждый ход после architectonic reconstruction получает **dispute
assessment**; результат идёт в trace и в security_events при обнаружении
уловок.

### Architectonic reconstruction
- `zarathustra/prompt_modules/architectonic_turn_reconstruction.md`
- `src/californian_id/architectonic.py` — `TurnDelta` + `reconstruct_turn_delta`.

Runtime вызывает `reconstruct_turn_delta` после каждого хода;
событие `architectonic_delta` пишется в trace.

### Hybrid RAG
`src/californian_id/cultural_rag.py` — `CulturalIndex` + `RetrievalEvent`.

Три индекса:
- `zarathustra_scenes` (card_type=scene)
- `zarathustra_operations` (operation + completion_pattern + constraint + risk)
- `zarathustra_primary_fragments` (chunks из normalized/)

Маршрут: `BodyProjection + tension → infer_required_function() →
metadata filter → BM25 rerank → 1..3 карт + опционально 1..3 фрагмент`.

Каждый retrieval пишется в trace как `cultural_retrieval` event с
provenance (source_id, locator, quote_hash).

Lexical fallback — основной; работает без внешней vector DB.

### Zarathustra integration
Один модуль, без новых скрытых агентов. Добавлено в цикл каждого turn:
1. architectonic reconstruction → delta в trace;
2. dispute assessment → fallacy events, security_events;
3. cultural retrieval для следующего хода → prompt-hint (через trace).

Перед выбором формы завершения — **anti-slop gate** блокирует synthesis,
если совет не отработал `attack_presupposition` + `defend` + 3+ голоса.

### Prompt dependency map
`zarathustra/PROMPT_DEPENDENCY_MAP.yaml` — какие prompt-modules
подгружаются на каких шагах, с donor_ops_used и cultural_cards_used.

## Тесты

**66 passed, 0 failed, 0 skipped:**

| Файл | Кол-во | Область |
|---|---|---|
| integration/test_pipeline_e2e.py | 6 | пайплайн, форма ≠ synthesis default |
| integration/test_e2e_corpus.py | 2 | e2e с retrieval + centralized-AI case |
| unit/test_personas.py | 2 | fixtures + lens contract |
| unit/test_state.py | 2 | state machine |
| unit/test_interaction.py | 3 | jailbreak/manipulation/repetition |
| unit/test_completion_forms.py | 8 | 10 форм, правила выбора |
| unit/test_body_projection.py | 4 | тело изменяется от хода |
| unit/test_functional_casting.py | 3 | функциональный кастинг |
| unit/test_chorus_and_affect.py | 6 | chorus + affect |
| unit/test_corpus_and_inventory.py | 3 | inventory + duplicates + primary/secondary |
| unit/test_donors.py | 3 | donor registry + operation cards |
| unit/test_architectonic.py | 4 | typed delta, claim atomization |
| unit/test_argumentation.py | 6 | thesis substitution, fallacy, stopping, anti-slop |
| unit/test_cultural_rag.py | 9 | retrieval + provenance + filtering + fallback |
| Итого | **66** | |

## Live acceptance case из handoff

```bash
python -m californian_id run --mode deep \
  --text "Следует ли ради безопасности централизовать управление развитием сильного ИИ?"
```

Результат:
- **12 turns**, все 7 голосов
- Форма завершения: **`aporia`** (не synthesis — anti-slop gate + правила)
- **5 minority positions** сохранены с полным would_be_lost
- 6 security events: 3 × `argumentation:proof_by_assertion` +
  3 × `repetition`
- В trace: `cultural_retrieval`, `dispute_assessment`,
  `architectonic_delta`, `completion_choice`, `completion`, `chorus`,
  `turn` — все присутствуют для каждого хода.
- Rationale для формы: «минимум две головы указали на невозможность
  честного ответа»
- Прямой ответ разрушил бы одну из существенных ценностей рамок
  ACCELERATIONIST / AI_SAFETY / EFFECTIVE_ALTRUIST — Заратустра это явно
  фиксирует.

## Source gaps

Отложено (не работано в этом проходе — фиксируем как gap, не как готовое):
- Все `.fb2 / .epub / .djvu` из `books/` и `books2/` — нужен конвертер.
- `Тинкуй Арх1.docx` — прочитан ранее (v0.1.0), полное содержимое
  архитектуры Тинкуя уже отражено в canon-alignment. В этот проход
  дополнительно не переизвлекалось.
- Ecosystem HTML в корне — не первичный источник по Заратустре, пропущен.
- Полное содержание `промпты доноры/03_креативные_движки/` — только
  reference-осмотр в предыдущем аудите; операционные карты не извлекались,
  так как назначение (TRIZ-movements) выходит за scope Пика 4.

## Что подтверждено

- **Заратустра не свёл спор к голосованию.** Форма `aporia` вместо
  `synthesis` в live-case.
- **Представлен отсутствующий/нечеловеческий участник** через карту
  `CARD_PARLIAMENT_OF_THE_ABSENT_LATOUR` (retrieval попадает в trace,
  видна в live-case).
- **Сохранён конфликт свободы и безопасности** — в conflict_map и в 5
  minority positions.
- **Тезис не подменён**: `detect_thesis_substitution` вернул `False`
  (нет ложной атаки на переопределённый тезис).
- **Использована культурная операция по функции**: `cultural_retrieval`
  event на каждом ходу.
- **Ложных цитат нет**: все `quote_hash` — реальные sha256 от извлечённых
  фрагментов; mock-провайдер вообще не цитирует.
- **Выбор формы обоснован**: `completion.rationale` не пустой; anti-slop
  проходит контракт.

## Правила, оставшиеся в силе

- Ни один исходный файл в корне не изменён.
- Все версии/переводы сохранены как отдельные источники.
- Полный peer-review донорского master-prompt не встроен; извлечена
  только инкрементальная часть.
- Мега-промпт нигде не создан.
- Синтез остаётся ОДНОЙ из десяти форм и не выбирается по умолчанию.

## Next actions

См. `HANDOFF.md`. Первым делом — при появлении реального LLM провайдера:
подключить `04_head_calling.md` + `05_move_assignment.md` +
`prompt_modules/architectonic_turn_reconstruction.md` для реальной
диверсификации операций и содержания.

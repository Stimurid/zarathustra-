# Changelog

## 0.4.0 — 2026-07-28 (Пик 4 — corpus + donors + Zarathustra grounding)

Реализация handoff `CLAUDE_CODE_CONTINUATION_CORPUS_DONORS_ZARATHUSTRA.md`.

### Inventory
- `_work/ROOT_SOURCE_INVENTORY.yaml` — 1171 файл в корне, полный SHA-256,
  классификация по 10 статусам.
- `_work/DUPLICATE_AND_VERSION_MAP.yaml` — dedup + сохранение
  версионных различий.
- `_work/SOURCE_GAPS.md` — что не извлечено.

### Corpus (11 источников)
- Bakhtin (Проблемы творчества Достоевского, К философии поступка)
- Bakhtin (Проблемы поэтики Достоевского — PDF slot, но чистый текст в
  Проблемах творчества)
- Jung (Red Book EN + Красная книга RU) — раздельно
- Deleuze/Guattari (Mille Plateaux FR 1980 + Тысяча плато RU 2010) — раздельно
- Latour (Политики природы)
- Vakhshtein (Социология вещей) — помечен secondary
- Gurdjieff (Взгляды из реального мира)
- Povarnin (Искусство спора)

`corpus/zarathustra/SOURCE_MANIFEST.yaml` + `extraction_reports/PASS_v0_4_0.{md,yaml}`.

### Donors (8, 7 карт)
- `donors/DONOR_REGISTRY.yaml`
- `donors/DONOR_OPERATION_CARDS/*.yaml` (7 карт)
- `donors/DONOR_TO_RUNTIME_MAP.yaml`
Ключевой: `DONOR_ARCHITECTONIC_MASTER_v1_2_1` (концептуально-архитектонический
анализ v1.2.1) — извлечена только инкрементальная часть.

### Cultural cards (18)
- Schema: `corpus/zarathustra/schemas/scene_operation_card.schema.json`
- 18 карт в `corpus/zarathustra/{scenes,operations,constraints,risks}/*.yaml`
  с реальными locator + quote_hash (sha256).
- Обязательный первый пакет из handoff покрыт полностью.

### Argumentation package
- `argumentation/` — 8 полиси + schema + prompt + runtime
- `src/californian_id/argumentation.py` — DisputeAssessment,
  detect_thesis_substitution, detect_fallacy_or_trick, check_anti_slop.
- Runtime hook: после каждого хода pipeline вызывает `assess_turn`;
  результаты пишутся в trace + fallacies отражаются в security_events.
- Anti-slop gate: перед формой `synthesis` проверяются
  attack_presupposition + defend + ≥3 голоса; иначе замена на
  polyphony/decision_with_dissent.

### Architectonic reconstruction (инкрементальная)
- `zarathustra/prompt_modules/architectonic_turn_reconstruction.md`
- `src/californian_id/architectonic.py` — `TurnDelta` +
  `reconstruct_turn_delta`.
- Runtime hook: после каждого хода pipeline пишет typed delta в trace.

### Hybrid RAG
- `src/californian_id/cultural_rag.py` — `CulturalIndex` с тремя
  индексами (scenes / operations / primary_fragments), metadata filter,
  BM25 rerank, provenance per hit, drainable events.
- Route: `BodyProjection + dispute_hint + operation → required_function
  → filter → BM25 → 1..3 карт [+ 1..3 фрагмент]`.
- Runtime hook: `cultural_retrieval` event per turn.
- Lexical fallback — основной, без внешней vector DB.

### Prompt Dependency Map
- `zarathustra/PROMPT_DEPENDENCY_MAP.yaml` — каждому prompt-модулю
  явные used_by_steps, donor_ops_used, cultural_cards_used, output_schema.

### Тесты
**66 passed** (39 старых + 27 новых):
- inventory + duplicates + primary/secondary
- donor registry + op-cards
- architectonic delta + claim atomization
- thesis substitution / fallacy / anti-slop
- retrieval provenance + metadata filter + translation isolation +
  no-false-quotation + lexical fallback + trace + card activation +
  contraindication
- e2e с corpus retrieval + centralized-AI live case

### Live acceptance
`«Следует ли ради безопасности централизовать управление развитием
сильного ИИ?»` (deep) → 12 turns, все 7 голосов, форма **aporia** (не
synthesis), 5 minority preserved, 6 security events, полный trace.

### Что осталось отложенным
- `.fb2 / .epub / .djvu` из `books/` и `books2/` — нужен конвертер.
- Векторный retrieval backend — интерфейс готов, реализация lexical.
- Живой LLM (real provider) — конфиг через env, но acceptance пока
  только на mock.

## 0.3.0 — 2026-07-28 (Пик 1 + 2 + 3)

См. полный лог; 39 тестов, «восьмиголовый Змей».

## 0.1.0 — 2026-07-28

Initial vertical slice; 13 тестов; synthesis как единственная форма.

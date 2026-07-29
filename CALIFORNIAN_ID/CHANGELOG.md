# Changelog

## 0.4.4 — 2026-07-29 (302.ai default + prod deployment + fallback chain)

### LLM provider
- **Primary:** 302.ai (OpenAI-compatible aggregator) через `base_url=https://api.302.ai/v1`.
- **Fallback chain** (проверенные на ключе рабочие модели):
  1. `302ai/claude-opus-4-1-20250805` — топовая для аргументации и длинного контекста
  2. `302ai/gpt-5`
  3. `302ai/claude-sonnet-4-20250514`
  4. `302ai/deepseek-reasoner`
  5. `direct-anthropic/claude-opus-4-1` (если `ANTHROPIC_API_KEY` есть)
  6. `direct-openai/gpt-5` (если `OPENAI_API_KEY` есть)
- Новый `FallbackClient` пробует steps по порядку, ловит exception, идёт дальше.
- `openai_client.py` — принимает `base_url` + `provider_label`, покрывает
  любые OpenAI-compatible endpoints (302.ai, DeepSeek, Together, Groq и т.п.).
- Новый `kind: 302ai` и `kind: openai_compatible` в фабрике.

### Prod deployment (tinkuy.mindkampf.ru)
Развёрнут на `deploy@81.26.176.248` (`moderbober-prod-01`):
- `/opt/tinkuy/app/{CALIFORNIAN_ID, runtime_assets, docs}` (editable pip install в venv)
- `/etc/tinkuy/tinkuy.env` (chmod 600, `CALIFORNIAN_ID_PROVIDER=302ai` + `API_302AI_KEY`)
- systemd `tinkuy-web.service` (порт 8085, host=0.0.0.0)
- Caddy reverse proxy: `tinkuy.mindkampf.ru → host.docker.internal:8085`
- UFW: `allow tcp from 172.18.0.0/16 to 8085` (docker→host bridge)
- Регрессия: соседи (dedalum/paideia/litops/kairoskop/mindfield/whitecrow) не задеты.

### Fix schema
- `Attack.target` и `Support.target` — теперь с дефолтом `"previous_turn"`,
  `text` с дефолтом `""`. Live LLM (Claude Opus 4.1) эмитит `attacks`
  без `target`; mock всегда возвращал. Fix предотвращает
  `Attack.__init__() missing 1 required positional argument: 'target'`
  при парсинге ответа реальной модели.

### Deploy artefacts (`deploy/`)
- `tinkuy.service` (systemd unit, `--host 0.0.0.0`)
- `tinkuy.env.template` (302.ai по умолчанию)
- `install_on_vm.sh` (идемпотентно, force `systemctl restart`)
- `caddy_snippet.txt` (для `/opt/moderbober/Caddyfile`)

### Docs
- **`_work/DEPLOYMENT_RUNBOOK.md`** — полный runbook продакшна (сервер,
  раскладка, systemd, UFW, Caddy, обновление, LLM провайдеры,
  basic_auth, troubleshooting, история инцидентов). Достаточен для
  чистой сессии агента.
- `_work/BACKLOG.md` дополнен разделами B-3bis (persona-layer заточка),
  B-4 (Codex merge follow-ups).

### Tests
- **111 passed, 3 skipped** (все прежние + новые от Codex + fallback).
- Live smoke: Claude Opus 4.1 через 302.ai ответил осмысленно на
  вопрос про диалогичность у Бахтина.

## 0.4.3 — 2026-07-29 (persona-layer routing — снять заточку словаря)

- Удалены Python-константы `ROUTING_KEYWORDS` / `FULL_COUNCIL_KEYWORDS`
  / `NEMO8_TRIGGER_KEYWORDS` из `persona_layer.py` — были English-only,
  вшитый TESCREAL/governance домен.
- Заменены на data: per-persona `manifest.yaml::routing.topics.{en,ru}`
  для 8 персон + `registry/routing_policy.yaml` для cross-cutting триггеров.
- `RoutingPolicy` dataclass, `load_routing_policy()`.
- Bilingual matching: русские stem'ы через substring (`будущ` → все формы).
- Live-проверка: русские запросы («долгосрочная траектория цивилизации»,
  «обязательный устав управления ИИ», «байесовская модель») получают
  осмысленный cast; раньше — все нули.
- Тесты: 111 passed.

## 0.4.2 — 2026-07-29 (снять заточку словаря в ядре)

- Удалены `_concept_hints` / `_stakes_guess` / `_horizon_guess` из
  `zarathustra.analyze_situation` — были regex-словари по AGI/moratorium/human.
- `_topic_guess` → `_first_meaningful_sentence`: первое осмысленное
  предложение >=30 chars, пропуская markdown-заголовки.
- `_genre_guess` оставлен только на структурных модальных словах.
- Новая LLM-ветка `_llm_situation` через `03_scene_reading.md` при
  live-провайдере. Работает на любой теме — от Канта до борща.
- Тесты: 76 passed.

## 0.4.1 — 2026-07-28 (md-units adapter + run_from_units + pip-install restructure)

- `adapters/units_of_content_md/` — парсер формата резчика Тимура
  (Units of Content) → `UnitPack`, `SemanticUnit`, `SourceAudit`.
- `Pipeline.run_from_units(pack, ...)` — новая точка входа, seed'ит
  `argument_map` и `BodyProjection` из готовой ткани.
- CLI: `--units-file`.
- Restructure для `pip install`: data-папки переехали в
  `src/californian_id/data/`. Env override `CALIFORNIAN_ID_DATA_DIR`.

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

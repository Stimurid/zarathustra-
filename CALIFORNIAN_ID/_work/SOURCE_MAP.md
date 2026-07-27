# SOURCE_MAP — конкретные адаптации canon → CALIFORNIAN_ID

Формат: `canon-source  →  target-in-this-pack  →  что взято / что изменено`.

## Персоны и контракты

- `tinkuy canon/09_культурные_персоны/G-U06_cultural_persona_lenses/CULTURAL_PERSONA_LENS_LIBRARY.yaml`
  → `personas/*/manifest.yaml`
  → **взято:** обязательные поля `assignment_prohibited: true`,
    `forbidden_uses: [participant profiling, identity attribution,
    style imitation, authority claim]`. Каждая наша fixture-персона
    несёт эти же поля.

- `tinkuy canon/09_культурные_персоны/G-U06_cultural_persona_lenses/CULTURAL_PERSONA_LENS_CONTRACT.md`
  → `personas/README.md`
  → **взято:** запрет имитации живого человека; проверяется тестом
    `test_no_persona_impersonates_a_real_person`.

- `tinkuy canon/11_агенты_карты_и_колоды/G-U21_DP-01_agent_pack/identity_core.yaml`
  + `values.yaml` + `style_pack.yaml` + `rhetorical_operations.yaml`
  + `action_model.yaml`
  → `personas/persona.schema.json`
  → **взято:** структура полей `persona_id`, `status`, `role_summary`,
    `system_prompt_ref`, `values_ref`, `argumentation_ref`, `routing`.
    Наша схема — минимально достаточная проекция; canon-контракт богаче
    и может быть добавлен без миграции ядра.

## Pipeline и state model

- `tinkuy canon/12_пайплайны_и_оркестраторы/digital_personality_runtime/pipeline.yaml`
  → `pipeline/pipeline.yaml`
  → **взято:** структурная модель `entrypoints / steps / fail_closed /
    llm_calls / terminal_states`. Названия шагов переработаны под
    сценарий «внутренний совет» (intake → analyze → cast → run_inner_council
    → synthesize → persist_trace → render).

- `tinkuy canon/12_пайплайны_и_оркестраторы/digital_personality_runtime/`
  (state machine, вытекает из pipeline и `communication/dialogue_state_model.yaml`)
  → `pipeline/state_model.yaml` + `src/californian_id/state.py`
  → **изменено:** 10 состояний с явными переходами и invariants;
    illegal transitions выбрасывают `InvalidTransition`.

- `tinkuy canon/12_пайплайны_и_оркестраторы/world_value_position_narrative_to_group_soul/`
  pipeline (шаги `assemble_shared_nucleus`, `preserve_dissent`, `review_gate`)
  → `src/californian_id/zarathustra.py::synthesize`
    + `zarathustra/synthesis_policy.yaml`
  → **взято:** архитектура «собрать общее ядро + сохранить dissent +
    review». `preserve_dissent` реализован через
    `_derive_minority_positions` (см. Minority Retention Law ниже).

## Zarathustra prompt stack

- `tinkuy canon/12_.../digital_personality_runtime/prompts/P00_system_identity.md`
  → `zarathustra/identity_and_laws.md`
  → **взято:** тон «не соглашаться ради гладкости», «признавать ошибки»,
    «отказ должен быть конкретен», «affect модулирует, но не отменяет
    доказательства». Переоформлено под роль оркестратора (не персоны).

- `tinkuy canon/12_.../digital_personality_runtime/prompts/P03_response_planner.md`
  → `zarathustra/routing.md` + `zarathustra/routing_policy.yaml`
  → **изменено:** от «планировщик ответа» к «планировщик следующего
    голоса и операции».

- `tinkuy canon/12_.../digital_personality_runtime/prompts/P05_memory_and_self_commit.md`
  → `zarathustra/state_update.md`
  → **взято:** различение новизны и перифраза, запрет молчаливого
    обновления принятого состояния.

- `promt donors/05_стилизация/SYSTEM ROLE anti-slop.docx`
  → `zarathustra/synthesis.md`
  → **взято:** императив «риторическая гладкость — режим ошибки».

## Group Soul и синтез

- `tinkuy canon/14_Group_Soul/G-U07_Group_Soul/GROUP_SOUL_MINORITY_RETENTION_LAW.md`
  → `zarathustra/synthesis_policy.yaml` + `src/californian_id/schemas.py::MinorityPosition`
    + `src/californian_id/zarathustra.py::_derive_minority_positions`
  → **взято:** deletion требует review + tombstone + preserved
    provenance; compression может укоротить, но не удалить distinct
    claim/value/world/objection. Каждая `MinorityPosition` несёт поля
    `reason_for_retention` и `would_be_lost`.

- `tinkuy canon/14_Group_Soul/G-U07_Group_Soul/GROUP_SOUL_CONFLICT_AND_OPEN_QUESTION_MODEL.yaml`
  → `src/californian_id/schemas.py::ConflictItem` + `_derive_conflict_map`
  → **взято:** конфликты имеют `status: unresolved|narrowed|reframed|compromised`.

## Interaction policy

- `tinkuy canon/12_.../digital_personality_runtime/communication/jailbreak_and_manipulation_policy.yaml`
  → `interaction/manipulation_policy.yaml`
    + `interaction/role_preservation_policy.yaml`
    + `interaction/repetition_policy.yaml`
    + `interaction/disclosure_policy.yaml`
    + `src/californian_id/interaction.py`
  → **взято:** jailbreak_ladder (levels 0–4), anti_sycophancy,
    manipulation_response, forbidden_responses. Регэкспы адаптированы
    под русский/английский ввод. Реализован детектор повторов
    (Jaccard по нормализованным токенам).

- `promt donors/01_онтологические_режимы/antiGPT_SP.docx`
  → `zarathustra/interaction_defense.md`
  → **взято:** запрет сведения к generic assistant; «не читай лекцию о
    безопасности вместо работы».

## Модельный слой

- `tinkuy canon/12_.../digital_personality_runtime/host_bindings/openai_compatible.yaml`
  → `src/californian_id/models/factory.py` + `openai_client.py`
    + `anthropic_client.py`
  → **изменено:** унифицированный `ModelClient` protocol; провайдеры
    лениво импортируются, чтобы mock работал без установленных SDK.

## Схемы данных

- `tinkuy canon/02_схемы_данных_и_контракты_выходов/DISSENT_RECORD.schema.json`,
  `MINORITY_RETENTION_ASSESSMENT.schema.json`, `POSITION_CANDIDATE.schema.json`,
  `RUN_TRACE.schema.json`, `SCENE_STATE.schema.json`
  → `src/californian_id/schemas.py`
  → **взято:** имена полей и их семантика. Реализация — dataclasses для
    минимальной зависимости; jsonschema-строгий валидатор — задача
    следующего прохода (см. `HANDOFF.md`).

## Что НЕ адаптировано (сознательно, вне scope MVP)

- Полная семантическая ткань (`03_семантическая_ткань`) — MVP имеет
  минимальную проекцию (concept/claim/assumption/attack/support).
- Многомасштабный парсер (B04, B05, B06 из V1) — не требуется для
  сценария «текст → совет».
- Полный tool-use слой (H01–H50) — не требуется.
- Vector RAG backend — интерфейс есть, реализация lexical.

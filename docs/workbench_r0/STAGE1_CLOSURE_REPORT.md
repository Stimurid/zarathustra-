# STAGE_1_CLOSURE_REPORT

**Дата:** 2026-08-15 · repo `Stimurid/zarathustra-.git`, branch `main`, HEAD `a72ae99` (не сдвинут)

---

## Статусная коррекция Stage 0/1

Предыдущий отчёт перечислял retrieval-телеметрию среди сделанного в Stage 0. Это было неверно: на момент закрытия Stage 0 инструментирования извлечения не существовало. Исправлено:

```
PROMPT_EXTRACTION       = PASS
GOLDEN_EQUIVALENCE      = PASS   (усилено до invocation-уровня, см. C3)
WORKBENCH_CORE          = PASS
PROMPT_VERTICAL_SLICE   = PASS
RETRIEVAL_TELEMETRY     = выполнено в Stage 2, а не в Stage 0
STAGE_1                 = ACCEPTED_CANDIDATE
```

---

## C1 — STRUCTURAL DRIFT FINGERPRINT · PASS

Скалярное сравнение `18 ≤ 18` удалено. Введён `DriftFingerprint` (`workbench_core/models.py`) с закрытым набором из шести категорий: `prompt_fields_not_declared`, `declared_fields_not_consumed`, `prompt_fields_not_consumed`, `required_fields_missing`, `schema_type_mismatches`, `dangling_asset_refs`.

Сравниваются множества пар `(категория, элемент)`, а не количества. Амнистия только при `candidate ⊆ baseline`. Классы: `NONE` · `KNOWN_BASELINE_DRIFT` · `WAIVED_CANDIDATE_DRIFT` · `NEW_CANDIDATE_DRIFT` (фатально).

Waiver требует `reason` **и** `adr_ref`, привязан к `asset_id`, отклоняется при неизвестной категории. Хранится в `workbench_state/drift_waivers.json`.

Отпечаток реальной фикстуры `03_scene_reading`: `17/9/7`, 10 непотребляемых, 8 необъявленных, 0 отсутствующих, 0 висячих ссылок.

**Тесты — 15 в `test_c1_drift_fingerprint.py`:**

| Сценарий | Ожидание | Тест |
|---|---|---|
| 1. те же дефекты | PASS | `test_1_same_exact_defects_pass` |
| 2. подмножество | PASS | `test_2_subset_of_baseline_defects_pass` |
| 3. **то же число, один дефект подменён** | **FAIL** | `test_3_same_count_one_defect_replaced_fails` |
| 4. надмножество | FAIL | `test_4_superset_fails` |
| 5. новая категория (type mismatch) | FAIL | `test_5_new_defect_category_fails` |
| 6. явный waiver с provenance | controlled PASS | `test_6_explicit_waiver_gives_controlled_pass` |

Тест 3 явно проверяет равенство суммарных счётчиков перед проверкой вердикта — то есть ловит ровно тот случай, который скалярное сравнение пропускало.

---

## C2 — REAL EDITOR + SERVER-SIDE ENFORCEMENT · PASS

**Редактор.** `textarea` заменён на CodeMirror 6 (`workbench_ui/src/components/PromptEditor.tsx`): курсор и выделение, INSERT ALL, INSERT SELECTION, APPLY DIFF, undo/redo, подсветка provenance-спанов из `source_map`, подсветка protected/editable областей, маркеры валидации волнистым подчёркиванием, навигация по областям.

**Защита не зависит от фронтенда.** `WorkbenchService.update_source` сравнивает каждую защищённую область с baseline **до** записи. Расхождение → отказ, ничего не пишется, событие уходит в `rejections.jsonl`.

**Коллизия C1↔C2 и её разрешение.** Изменение полей контракта физически лежит внутри защищённой области `output_json_contract`. Введено явное намерение правки: `intent="content"` (по умолчанию, области неприкосновенны) и `intent="contract_revision"` (единственный способ тронуть контракт; кандидат помечается `contract_revision=True` и попадает под полную силу C1, где любой новый дефект требует waiver). Это усиление, а не послабление.

**Негативный интеграционный тест** — 6 тестов в `test_c2_protected_regions.py`, все через сырой HTTP:

```
POST /asset/.../variant/.../source  { "source_text": <topic → headline> }
→ 400, "output_json_contract"
→ candidate source unchanged
→ active binding unchanged        (variant_id и revision прежние)
→ baseline unchanged              (source_hash прежний)
→ rejection recorded              (code=protected_region_mutation, actor сохранён)
```

Отдельно покрыто: удаление области, правка BASELINE, приём легальной правки редактируемой области, аудит `contract_revision_accepted`, отказ на неизвестном intent.

---

## C3 — REAL RUNTIME SMOKE PATH · PASS (live — EXTERNAL_BLOCKER)

Три уровня, 6 тестов + 1 пропуск в `test_c3_smoke_levels.py`.

**UNIT_SMOKE** — `StubModel`, детерминированный, контракт-осведомлённый.

**INTEGRATION_SMOKE** — `WorkbenchService.run_integration_smoke` + `ZarathustraAdapter.integration_run`. Цепочка исполняется целиком:

```
ACTIVE variant → ActivationBinding → PromptResolver → PromptCompiler
→ immutable activation snapshot → Zarathustra(prompt_dir=<materialised variant>)
→ z.prompt("03_scene_reading.md")  [assert: runtime прочитал именно вариант]
→ analyze_situation() → Message-сборка → client.generate()  ← capture boundary
→ _json_from_text() (настоящий парсер) → SituationAnalysis
→ contract validation → EvaluationRecord → RunTrace
```

Трасса фиксирует `emitted_payload_matches_compiled: true` — то есть отправленное совпало со скомпилированным.

**Дефект, найденный именно этим уровнем (WB-010).** `zarathustra.py:197` маршрутизирует клиентов с `provider == "mock"` в детерминированный фолбэк, никогда не доходя до модели. `CaptureClient` без атрибута `provider` попадал под это правило, и интеграционный смок был бы молча пустым. Исправлено: `CaptureClient.provider = "capture"`. Заглушечный уровень такой дефект увидеть не мог.

**Golden equivalence — на уровне payload, не текста.**

```python
old = adapter.legacy_invocation(fixture)                      # Python-константа
new = adapter.build_invocation(ASSET, code_variant.source, f) # PromptAsset
assert canonical(old) == canonical(new)
assert sha256(canonical(old)) == sha256(canonical(new))
assert CaptureClient-payload-hash(old) == CaptureClient-payload-hash(new)
```

Плюс `test_semantic_output_similarity_is_not_used_as_equivalence_proof` — страховка от регресса к сравнению прозы.

**LIVE_ACCEPTANCE_SMOKE = EXTERNAL_BLOCKER.** Ни `ANTHROPIC_API_KEY`, ни `OPENAI_API_KEY`, ни `CALIFORNIAN_ID_API_KEY` не сконфигурированы. Тест помечен `skipif` с этой причиной и **не симулирует PASS**. Stage 2 не блокируется, поскольку integration smoke пройден.

---

## C4 — ACTIVATION / CACHE / RUN SNAPSHOT · PASS

4 теста в `test_c4_activation_isolation.py`, `RecordingProvider` подтверждает фактически отправленный payload.

```
activate A → R1: variant A, source_hash A, compiled_hash A, revision N
             payload содержит [A]
while R1 alive: activate B → revision N+1
R1 persisted trace: по-прежнему A, тот же compiled_hash, та же revision N
R2: variant B, другой compiled_hash, revision N+1, payload содержит [B], не [A]
```

`test_cache_identity_changes_with_every_dimension` проверяет все измерения ключа: профиль компилятора, variant_id, source_hash, activation_revision. `test_rollback_affects_only_the_next_run` — откат не переписывает уже записанную трассу.

Внешний инвариант доказан независимо от внутреннего механизма: императивная инвалидация оставлена вторым рубежом, корректность держится на версионной идентичности ключа и на неизменяемом снимке.

---

## C5 — UI ACCEPTANCE / VISUAL QA · PASS

Headless Chromium через Playwright, `workbench_ui/qa/ui_smoke.mjs`, только selector-based взаимодействия.

**Результат: 15/15 шагов, 14 скриншотов, 0 ошибок консоли, 0 ответов HTTP ≥ 400.** Пятнадцатый шаг — DOM-утверждение `deterministic_has_no_editor` (кнопки клонирования нет в дереве), оно не порождает снимок.

| # | Скриншот | Что доказывает |
|---|---|---|
| 01 | `pipeline_graph` | 13 узлов, 7 типов, бейдж `17/9/7` |
| 02 | `inspector_prompt_node` | MODEL_CALL, контракт, редактор доступен |
| 03 | `source_editor` | CodeMirror, области protected/editable |
| 04 | `diff` | unified diff кандидата |
| 05 | `validation` | вердикт + класс дрейфа |
| 06 | `compiled_provenance` | COMPILED, provenance 100 % |
| 08 | `inspector_deterministic` | DETERMINISTIC без редактора промпта |
| 09 | `effects_v054` | один контрол — оба класса эффектов |
| 10 | `rag_inspector` | RAG-профиль, эффективные параметры, NOT_IMPLEMENTED |
| 11 | `rag_retrieval_facts` | ранжированные чанки со score/locator/hash |
| 12 | `rag_why_this_chunk` | факты и интерпретация разделены |
| 13 | `rag_comparison` | baseline ↔ candidate |
| 14 | `run_trace` | variant/source/compiled/snapshot |
| 15 | `telemetry_overlay` | measured/estimated на узлах |

Артефакты: `workbench_ui/qa/screenshots/*.png` + машиночитаемый `report.json`.

Ограничение среды из прошлого прохода (`Browser pane is not displayed`) обойдено: Playwright управляет собственным Chromium и композитит кадры сам. `VISUAL_QA = PASS` с визуальным доказательством.

**Два дефекта найдены именно UI-смоком:** WB-009 (readOnly не переключался) и WB-011 (`innerText` возвращает CSS-`text-transform`, из-за чего текстовые ассерты ловили не то). Оба исправлены.

---

## Итог

```
C1 = PASS    C2 = PASS    C3 = PASS (live = EXTERNAL_BLOCKER)
C4 = PASS    C5 = PASS
STAGE_1 = ACCEPTED_CANDIDATE
```

Тесты на момент закрытия: **419 passed, 1 skipped**, из них закрывающие C1–C5 — 66.

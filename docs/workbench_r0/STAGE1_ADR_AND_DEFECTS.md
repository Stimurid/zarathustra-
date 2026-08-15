# Stage 0 / Stage 1 — ADR и журнал дефектов

**Дата:** 2026-08-15 · repo `Stimurid/zarathustra-.git`, branch `main`, HEAD `a72ae99`

---

## ADR-01. Ветка-адаптер введена с первого среза

**Решение.** `workbench_core` не содержит ни одного импорта `californian_id.*`. Всё, что знает про Заратустру, живёт в `workbench_adapters/zarathustra_adapter.py`. Контракт — `workbench_core/branch.py`: `BranchAdapter` + `PipelineProjection` / `NodeProjection` / `EdgeProjection` / `SemanticControl` / `ControlEffect` / `Invocation` / `Fixture`.

**Обеспечение.** `tests/workbench/test_dependency_invariant.py` разбирает AST каждого модуля ядра и падает при любом импорте с головой `californian_id` или `zarathustra`, а также при рантайм-обращении к этим именам. Адаптер отдельно проверяется на соответствие протоколу.

**Следствие.** `socrates_adapter` подключается тем же способом без единой правки ядра.

---

## ADR-02. Золотая эквивалентность — на уровне invocation payload

**Решение.** Схожесть живого вывода модели доказательством не считается. Доказывается байтовое равенство того, что уходит провайдеру.

**Реализация.** `scripts/workbench_extract_prompts.py` читает 18 значений из живого кода и порождает и ассеты, и золотые копии — ручного перенабора нет, равенство гарантировано конструктивно. `tests/workbench/test_prompt_extraction_golden.py` содержит:

- 18 параметризованных проверок «резолвер == золотая копия» побайтово;
- 15 проверок на уровне публичных функций (`_assembly_instruction`, `_grounding_instruction`, `CRITIQUE_REGIMES`, `VARIATION_REGIMES`);
- `test_scene_reading_invocation_payload_identical_old_vs_new` — канонический payload `analyze_situation` для OLD (Python-константа) и NEW (ассет) совпадает;
- `CaptureClient` в `workbench_core/smoke.py` — фиксирует messages + settings и даёт `payload_hash()`.

Живой смок остаётся дополнительным семантическим сигналом, не доказательством.

---

## ADR-03. Кеш версионно-осведомлённый, run фиксирует снимок активации

**Решение.** Идентичность кеша — `CacheKey(asset_id, variant_id, source_hash, profile_id, activation_revision)`. Императивная инвалидация оставлена как второй рубеж (`Zarathustra.invalidate_prompt_cache`, `WorkbenchService._compiled_cache.clear()`), но корректность на неё не опирается.

Каждый run в начале берёт `ActivationSnapshot` (frozen dataclass) и работает под ним до конца. Переключение активного варианта не меняет уже начатый run.

**Тесты.** `test_16b_activation_snapshot_is_immutable_for_started_run`, `test_16c_cache_identity_includes_activation_revision`.

---

## ADR-04. Исторический дрейф контракта амнистирован

**Решение.** Дрейф `17/9/7` в `03_scene_reading` — известный дефект baseline, а не повод блокировать существующий baseline.

**Реализация.** `StaticValidator` различает:

| Класс | Условие | Вердикт |
|---|---|---|
| `NONE` | дрейфа нет | pass |
| `KNOWN_BASELINE_DRIFT` | вариант — baseline, либо дрейф ≤ дрейфа baseline | pass (info-issue) |
| `NEW_CANDIDATE_DRIFT` | дрейф кандидата > дрейфа baseline | **fail** |

Потребляемое поле, отсутствующее в промпте (`missing_from_prompt`), фатально всегда — ему амнистия не положена.

**Тесты.** `test_09b_baseline_drift_is_grandfathered_not_blocking`, `test_09c_new_candidate_drift_is_fatal`.

---

## ADR-05. Provenance скомпилированного промпта — 100 %

**Решение.** Каждый символ `system_text` и `user_template` покрыт ровно одним `SourceSpan`. Допустимы два вида: `source_module` (asset_id + variant_id + region_name + region_kind) и `compiler_generated` (rule_id + compiler_profile). Непокрытый диапазон — исключение `ProvenanceError`, а не предупреждение.

**Реализация.** `CompiledPrompt.coverage_gaps()` вычисляет разрывы; `PromptCompiler.compile` бросает при непустом списке. Правила генерации именованы: `system_scaffold`, `user_payload_passthrough`, `fixture_payload`.

**Тест.** `test_10_11_compile_has_full_provenance`.

---

## ADR-06. Гибриды представлены, а не расщеплены

**Решение.** `regimes.py` не рефакторился: числовые половины (`attack_bias`, `repeat_penalty`, `class_repeat_penalty`) остались там же и с теми же значениями. Один семантический контрол отдаётся как `SemanticControl` с несколькими `ControlEffect`, у каждого свой класс, цель, потребители и точка в коде.

**Тесты.** `test_prompt_extraction_golden.test_regime_numeric_halves_untouched`, `test_04b_consumers_visible_for_hybrids`, `test_19_v054_shows_prompt_and_deterministic_effects`.

---

## ADR-07. Редактор — textarea, не CodeMirror

**Факт, обнаруженный при реализации.** CodeMirror 6 добавляет ~6 пакетов и заметный вес бандла ради подсветки, тогда как критерии Stage 1 требуют от редактора только открыть SOURCE, изменить, сохранить и увидеть разметку защищённых областей.

**Решение.** В Stage 1 — `textarea` плюс легенда областей (🔒 protected / ✎ editable) и серверная проверка неизменности защищённых областей. BASELINE отдаётся `readOnly`.

**Обратимость.** Замена на CodeMirror затрагивает один компонент и не меняет ни одного контракта API. Отложено до стадии RAG-воркбенча.

---

## ADR-08. Смок по умолчанию идёт на контракт-осведомлённой заглушке

**Решение.** `StubModel` отвечает ровно теми ключами JSON, которые запрашивает промпт, заполняя их детерминированно из фикстуры. Поэтому сравнение baseline↔candidate осмысленно без расхода токенов, а кандидат, изменивший набор запрашиваемых полей, видимо меняет выход.

Живой провайдер подключается подменой `SmokeHarness.model`. В `RunTrace` пишутся `provider` и `model`, так что происхождение результата всегда видно (`stub/workbench-stub-1`).

---

## Журнал дефектов

### WB-000 · Дрейф контракта `03_scene_reading` — 17/9/7 · OPEN, амнистирован

Промпт требует 17 полей, `PROMPT_DEPENDENCY_MAP.yaml` объявляет 9, `analyze_situation` читает 7. Десять полей генерируются моделью и выбрасываются: `dominant_frame`, `suppressed_frame`, `model_of_human`, `model_of_future`, `model_of_power`, `central_value`, `hidden_fear`, `potential_idol`, `absent_head`, `possible_transformation`.

Не чинится в Stage 1 намеренно: приведение уровней в согласие меняет поведение. Виден в UI как бейдж `17/9/7` на узле и как `KNOWN_BASELINE_DRIFT` в валидации.

### WB-001 · Висячие ссылки на ассеты · FIXED

Узлы `route_next` и `synthesize` несли `asset_id`, которых `list_assets()` не регистрировал → проекционный API отдавал 404 по собственным ссылкам. Обнаружено браузерным смоком (две 404 в network log).

**Исправление:** `zarathustra.04_head_calling` и `zarathustra.13_closing_speech` зарегистрированы как полноценные ассеты с baseline из файла и из кода. **Регрессия:** `test_02c_no_dangling_asset_references`.

### WB-002 · Клон подменялся baseline · FIXED

`loadAsset` выводил целевой вариант из `workingId`, захваченного в `useCallback`. После клонирования колбэк видел старое значение и возвращал выбор на активный baseline — редактор открывался в режиме `readOnly`.

**Исправление:** предпочтительный вариант передаётся аргументом, зависимости колбэка пусты. Обнаружено браузерным смоком (`readOnly: true` после клонирования).

### WB-003 · Ложный бейдж дрейфа `0/0/0` · FIXED

Ассеты без объявленного контракта показывали бейдж `0/0/0`. Теперь бейдж рисуется только если промпт реально объявляет поля.

### WB-004 · BASELINE переводился в DEPRECATED · FIXED

Активация кандидата помечала baseline `DEPRECATED`, что противоречит правилу «BASELINE неудаляем и всегда доступен для отката». Теперь состояние BASELINE не меняется никогда; «какой вариант живой» выражается привязкой, а не мутацией состояния.

### WB-005 · Порядок baseline-вариантов · FIXED

`bootstrap()` выбирал первый BASELINE по алфавиту файлов, из-за чего активным становился `baseline_code`, а не `baseline_file`. Теперь используется `baseline()` с явным приоритетом файла над кодом.

### WB-006 · Инвалидация кеша промптов отсутствовала · FIXED

`Zarathustra._prompt_cache` не имел сброса. Добавлен `invalidate_prompt_cache(name=None)`. Поведение при неизменных файлах идентично.

### WB-007 · PowerShell повреждает UTF-8 исходники · PROCESS

Правка `.tsx` через `Get-Content -Raw` / `Set-Content` в PowerShell 5.1 перекодировала кириллицу в мохибейк (чтение без BOM трактуется как ANSI). Файл восстановлен полной перезаписью. **Правило:** текстовые правки UTF-8 исходников делаются только файловыми инструментами, не PowerShell.

### WB-008 · Скриншоты недоступны · ENVIRONMENT

Browser pane в этой среде не композитит кадры (`Screenshot timed out: the Browser pane is not displayed`), поэтому визуальных скриншотов нет. Браузерный смок выполнен по DOM: `read_page`, `get_page_text`, `read_network_requests`, синтетические события. Физический клик по координатам также не попадал в узел по той же причине — это ограничение среды, а не дефект приложения.

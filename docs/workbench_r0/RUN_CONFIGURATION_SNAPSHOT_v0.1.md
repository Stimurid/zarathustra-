# RUN_CONFIGURATION_SNAPSHOT v0.1

Реализация: `workbench_core/models.py::RunConfigurationSnapshot` · сборка: `WorkbenchService.build_run_configuration` · закрепление: `WorkbenchConfigResolver.pinned()`

---

## 1. Зачем

До Stage 3 существовали два независимых снимка — активации промптов и активации RAG. Единый снимок делает воспроизводимым весь прогон целиком: любая рантайм-операция внутри прогона разрешает свою конфигурацию **из снимка**, а не из изменяемой текущей активации.

## 2. Схема

```yaml
run_configuration_snapshot:
  snapshot_id: cfg_<sha256[:16] от ревизии и всех секций>
  created_at:
  activation_revision:

  pipeline:            {pipeline_id, version, hash}
  prompt_bindings:     [{asset_id, variant_id, source_hash, version,
                         compiler_profile, compiled_hash}]
  rag_bindings:        [{engine_id, rag_profile_id, version, profile_hash,
                         index_version, corpus_versions}]
  model_bindings:      [{model_profile_id, provider, model, effective_parameters}]
  algorithm_bindings:  [{config_id, version, hash}]
  orchestration_binding: {profile_id, version}
  contract_bindings:   [{contract_id, version, hash}]
```

`snapshot_id` детерминирован: одинаковая конфигурация даёт одинаковый идентификатор (`test_snapshot_id_is_deterministic_for_identical_configuration`).

## 3. Инвариант

```
активация, произошедшая после старта прогона,
НЕ МОЖЕТ изменить ни одну привязку внутри этого прогона
```

Механизм — не только императивный: резолвер разрешает значения по цепочке приоритетов **закреплённый снимок → текущая активация → дефолт вызывающего**, и на время прогона закреплён контекст-менеджером `pinned()` (thread-local). Кеш-ключ дополнительно включает `activation_revision`.

Проверка `test_snapshot_pins_the_run_against_mid_flight_activation`:

```python
snap = svc.build_run_configuration("zarathustra")   # top_k = 2
svc.activate_rag(candidate_with_top_k_7)            # активация меняется

with resolver.pinned(snap.as_resolver_view()):
    assert resolver.retrieval_param(CARDS, "top_k", 2) == 2      # внутри прогона
assert resolver.retrieval_param(CARDS, "top_k", 2) == 7          # снаружи
```

## 4. Что покрыто и что нет

| Семейство | Покрытие |
|---|---|
| `PromptVariant` | полное — asset_id, variant_id, source_hash, профиль компилятора |
| `RAGProfile` | полное — profile_id, version, profile_hash, index/corpus |
| `algorithm_bindings` | `runtime.yaml` целиком, с хешем |
| `contract_bindings` | выходные объекты промпт-ассетов + `protected_contracts` RAG-профилей |
| `orchestration_binding` | пайплайн-профиль и версия |
| `model_bindings` | **частично**: провайдер и модель разрешаются в момент вызова через `models.yaml`/пресеты и пока не версионируются. Поле присутствует и честно помечено `resolved_at_call_time` |
| гибридные контролы | `critique_regime` / `variation_regime` в снимок пока не входят: они передаются аргументами `Pipeline.run` и не имеют активационной привязки |

Legacy-рантайм целиком не мигрирован — это и не требовалось. Воспроизводимость гарантируется для прогона, запущенного через Workbench.

## 5. Реальный пример

```
snapshot_id           cfg_… (детерминирован)
activation_revision   N
pipeline              californian_id.inner_council v0.1.0
prompt_bindings       zarathustra.03_scene_reading → v_baseline_baseline_file (9e17b536…)
                      zarathustra.04_head_calling, 05_move_assignment, 13_closing_speech
rag_bindings          zarathustra.cultural_cards_bm25 → rag.cultural_cards.baseline v0.1.0
                      tinkuy.persona_lexical_bm25   → rag.persona_lexical.baseline v0.1.0
contract_bindings     SituationAnalysis, RoutingDecision, TurnRecord, ClosingSpeech,
                      RetrievedCard, provenance.primary_sources,
                      EvidenceChunk, persona_scoped_isolation, provenance_required
```

После активации кандидата с `top_k=5` меняются `rag_bindings[cultural_cards].rag_profile_id`, `version`, `profile_hash` и `activation_revision` — а с ними и `snapshot_id`.

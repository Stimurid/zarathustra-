# RAG_PROFILE_SCHEMA v0.1

Реализация: `CALIFORNIAN_ID/src/workbench_core/rag.py`

---

## 1. Схема

```yaml
rag_profile:
  profile_id: str                # rag.<engine>.<baseline|hex>
  engine_id: str                 # какой движок конфигурируется
  version: str                   # 0.1.0, инкремент последнего сегмента при клоне
  state: BASELINE | CANDIDATE_UNCHECKED | STATIC_VALID | TESTED
       | ACCEPTED | ACTIVE | DEPRECATED | REJECTED | INCOMPATIBLE
  parent_profile_id: str | null
  parent_version: str | null
  title: str
  author: str
  created_at: iso8601

  source_bindings: {}            # корпус, namespace, типы файлов, изоляция
  chunking: {}                   # стратегия и её параметры
  retrieval: {}                  # top_k, источник запроса
  scoring: {}                    # алгоритм и его константы
  filtering: {}                  # пороги, фильтры, поведение при пустом результате
  caching: {}                    # что кешируется, что NOT_IMPLEMENTED
  runtime_binding: {}            # node_id + точка вызова в коде

  contract_version: str
  protected_contracts: [str]     # поверхности, которые правка параметра не двигает
  missing_capabilities: [MissingCapability]

  # производные, не хранятся как вход
  source_hash: sha256(engine_id + tunable + contract_version)
  tunable: {}                    # плоская проекция шести секций
```

`MissingCapability`: `{capability_id, label, status: NOT_IMPLEMENTED, note}`.

**Правило:** `NOT_IMPLEMENTED` — не значение с дефолтом, а отсутствие возможности. Такой параметр нельзя установить, провалидировать или активировать; `update_rag` отклоняет попытку с записью в `rejections.jsonl`.

---

## 2. Жизненный цикл

Отличается от `PromptVariant` намеренно: RAG-профиль не компилируется.

```
PromptVariant : STATIC_VALIDATE → COMPILE          → SMOKE
RAGProfile    : STATIC_VALIDATE → RETRIEVAL_TEST   → DOWNSTREAM_SMOKE
```

```
BASELINE ──clone──▶ CANDIDATE_UNCHECKED ──validate──▶ STATIC_VALID
                              │                            │
                              ▼                            ▼ retrieval test
                        INCOMPATIBLE                     TESTED
                                                           │ accept
                                                           ▼
                                                       ACCEPTED ──activate──▶ ACTIVE
                                                                                │
                                                                                ▼
                                                                          DEPRECATED
```

Состояние `COMPILED` в `RAG_ALLOWED` отсутствует физически — это проверяется тестом `test_rag_profile_has_no_compile_gate`. Прямая активация запрещена так же, как у промптов.

---

## 3. Baseline-профили (реконструированы из кода)

### `rag.persona_lexical.baseline` → `tinkuy.persona_lexical_bm25`

```yaml
source_bindings: {corpus_root: data/personas/<persona_id>/corpus,
                  file_types: [.md, .txt], persona_scoped: true,
                  corpora_present: false}
chunking:  {strategy: char_window, chunk_size: 800, overlap: 200,
            normalise_whitespace: true}
retrieval: {top_k: 2, query_source: state.situation.topic}
scoring:   {algorithm: bm25, k1: 1.5, b: 0.75, score_kind: bm25}
filtering: {min_token_len: 3, min_score: 0.0}
caching:   {result_cache: NOT_IMPLEMENTED}
runtime_binding: {node_id: retrieve_initial_context,
                  call_site: pipeline.py:544,1223}
protected_contracts: [EvidenceChunk, persona_scoped_isolation, provenance_required]
```

**`corpora_present: false` — установленный факт:** ни у одной из семи персон нет каталога `corpus/`, поэтому узел в поставке возвращает 0 чанков. Это состояние данных, а не поломка; показывается в UI отдельным предупреждением.

### `rag.cultural_cards.baseline` → `zarathustra.cultural_cards_bm25`

```yaml
source_bindings: {namespace: zarathustra_scenes+operations+constraints+risks,
                  corpus_root: data/corpus/zarathustra, corpora_present: true}
chunking:  {strategy: whole_card}          # карты не режутся
retrieval: {top_k: 2, query_source: topic + operation + persona_id}
scoring:   {algorithm: bm25, score_kind: bm25}
filtering: {required_function: any, min_score: 0.0,
            fallback_when_empty: drop_card_type_filter}
caching:   {index_cache: process_local, result_cache: NOT_IMPLEMENTED}
runtime_binding: {node_id: cultural_context,
                  call_site: pipeline.py:555,630,1230}
protected_contracts: [RetrievedCard, provenance.primary_sources]
```

---

## 4. Перепись параметров

Каждый параметр несёт `current_default` (литерал в коде) и `effective_value` (что пайплайн реально передаёт). Расхождение помечается флагом.

| parameter_id | в коде | эффективно | изменяем | источник |
|---|---|---|---|---|
| `chunking.chunk_size` | 800 | 800 | нет | `retrieval.py:34` |
| `chunking.overlap` | 200 | 200 | нет | `retrieval.py:34` |
| `retrieval.top_k` (persona) | **3** | **2** | **да** | `retrieval.py:58` → `pipeline.py:544,1223` |
| `scoring.bm25_k1` | 1.5 | 1.5 | нет | `retrieval.py:85` |
| `scoring.bm25_b` | 0.75 | 0.75 | нет | `retrieval.py:85` |
| `filtering.min_token_len` | 3 | 3 | нет | `retrieval.py:31` |
| `filtering.min_score` | 0.0 | 0.0 | нет | `retrieval.py:100` — жёсткий `score > 0` |
| `source_bindings.file_types` | `[.md,.txt]` | то же | нет | `retrieval.py:65` |
| `source_bindings.persona_scoped` | true | true | нет | `retrieval.py:60`, `pipeline.yaml:30` |
| `retrieval.top_k` (cards) | **3** | **2** | **да** | `cultural_rag.py:280` → `pipeline.py:555,630,1230` |
| `filtering.required_function` | `any` | `any` | да | `cultural_rag.py:283` |
| `filtering.min_score` (cards) | 0.0 | 0.0 | нет | `cultural_rag.py:299` |
| `source_bindings.namespace` | 4 каталога карт | то же | нет | `CARDS_DIRS` |
| `scoring.algorithm` | bm25 | bm25 | нет | `cultural_rag.py:168` |

**Главная находка переписи:** дефолт `top_k=3` не используется нигде — все четыре живых вызова передают 2.

### Отсутствующие возможности — `NOT_IMPLEMENTED`

`similarity_threshold` (есть только жёсткий `score > 0`, это не порог) · `reranker` · `diversity_control` · `saturation_criterion` · `retrieval_budget` · `query_rewriting` (запрос собирается конкатенацией в `pipeline.py`, LLM-перезаписи нет) · `source_weighting` · `embeddings` (лексический BM25) · `cache` результатов (кешируются только индексы, в пределах процесса).

---

## 5. Защищённые контракты (S2.9)

`validate_rag` отклоняет кандидата, если он снял хотя бы одну поверхность из `protected_contracts` baseline либо изменил `contract_version`. Смена контракта — отдельная миграция, а не побочный эффект правки параметра. Тесты: `test_protected_contract_cannot_be_dropped_by_a_parameter_edit`, `test_contract_version_change_requires_migration`.

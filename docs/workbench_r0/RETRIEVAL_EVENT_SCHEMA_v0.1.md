# RETRIEVAL_EVENT_SCHEMA v0.1

Реализация: `workbench_core/rag.py` · эмиссия: `ZarathustraAdapter.run_retrieval` · хранение: `workbench_state/retrieval_events.jsonl` (append-only)

---

## 1. Принцип

Событие — **наблюдение**, а не вмешательство. Инструментирование не считает ничего, чего движок не посчитал сам, и ничего не возвращает обратно в ранжирование. Регрессия `test_07_instrumentation_does_not_change_results` фиксирует, что прямой вызов движка до и после серии наблюдений даёт идентичные `(card_id, score)`.

## 2. Градация достоверности

Каждое поле несёт градацию, и они не смешиваются:

| Градация | Смысл |
|---|---|
| `MEASURED` | движок вернул это значение или оно снято таймером |
| `DERIVED` | вычислено из выходов движка его же функциями (например, пересечение токенов запроса с `_card_search_text`) |
| `ESTIMATED` | оценка (число токенов считается как `len/3.5`, токенизатора нет) |
| `LLM_EXPLANATION` | текст компаньона, никогда не факт |
| `UNKNOWN` | движок этого не экспонирует — поле остаётся пустым с явной пометкой |

`matched_features` всегда `UNKNOWN`: ни один из двух движков не выдаёт признакового вклада.

## 3. Схема

```yaml
retrieval_event:
  run_id:                 # связь с RunTrace
  node_id:                # cultural_context | retrieve_initial_context
  timestamp:

  query:
    query_hash:           # sha256[:16]
    query_text:           # MEASURED
    rewrite_applied:      # всегда false — query_rewriting NOT_IMPLEMENTED

  profile:
    rag_profile_id:
    rag_profile_version:
    rag_profile_hash:     # sha256 конфигурации
    index_id:
    index_version:
    corpus_ids: []

  candidates:             # по одному на каждый возвращённый чанк
    - chunk_id:
      chunk_hash:
      source_id:
      locator:
      rank:               # MEASURED
      score:              # MEASURED
      score_kind:         # bm25
      matched_terms: []   # DERIVED из searchable-текста движка
      matched_features: []# UNKNOWN
      filters_applied: []
      included_in_context:
      context_order:
      token_count:        # ESTIMATED
      byte_count:         # MEASURED
      grades: {}

  runtime:
    latency_ms:           # MEASURED
    cache_state:          # index_process_cache | cold
    considered_count:     # MEASURED
    returned_count:       # MEASURED
```

## 4. Реальный пример

Профиль `rag.cultural_cards.baseline`, фикстура `fx_rag_cards_001` («сцена спор истина»):

```json
{
  "run_id": "ragtest_442a1fb1a6",
  "node_id": "cultural_context",
  "query_hash": "355e6c3a69dd4e8f",
  "query_text": "сцена спор истина",
  "rewrite_applied": false,
  "rag_profile_id": "rag.cultural_cards.baseline",
  "rag_profile_version": "0.1.0",
  "rag_profile_hash": "30f5e0647870c262…",
  "index_id": "zarathustra.cultural_cards_bm25",
  "corpus_ids": ["zarathustra_scenes+operations+constraints+risks"],
  "considered_count": 37,
  "returned_count": 2,
  "latency_ms": 82,
  "cache_state": "index_process_cache",
  "candidates": [
    {
      "chunk_id": "CARD_GREAT_INQUISITOR_DOSTOEVSKY",
      "chunk_hash": "9339902e2432c04e",
      "source_id": "scenes\\CARD_GREAT_INQUISITOR_DOSTOEVSKY.yaml",
      "locator": "scene/CARD_GREAT_INQUISITOR_DOSTOEVSKY",
      "rank": 1, "score": 3.9941048864518365, "score_kind": "bm25",
      "matched_terms": ["истина", "спор"],
      "matched_features": [],
      "filters_applied": ["card_type_in=[…5 типов…]", "required_function=any"],
      "included_in_context": true, "context_order": 1,
      "token_count": 23, "byte_count": 126,
      "grades": {"score": "MEASURED", "rank": "MEASURED",
                 "matched_terms": "DERIVED", "token_count": "ESTIMATED",
                 "matched_features": "UNKNOWN"}
    },
    {
      "chunk_id": "CARD_OVERMAN_INVOCATION_NIETZSCHE",
      "rank": 2, "score": 3.930462653046879,
      "matched_terms": ["спор", "сцена"], "…": "…"
    }
  ]
}
```

## 5. «Почему этот чанк?»

`explain_candidate()` возвращает только факты, каждый со своей градацией:

```
MEASURED  query               = сцена спор истина
MEASURED  score               = 3.9941048864518365
MEASURED  score_kind          = bm25
MEASURED  rank                = 1
MEASURED  top_k_boundary      = top_k=2
MEASURED  source_id           = scenes\CARD_GREAT_INQUISITOR_DOSTOEVSKY.yaml
MEASURED  locator             = scene/CARD_GREAT_INQUISITOR_DOSTOEVSKY
MEASURED  chunk_hash          = 9339902e2432c04e
MEASURED  corpus_membership   = [zarathustra_scenes+operations+constraints+risks]
MEASURED  included_in_context = True
MEASURED  cache_state         = index_process_cache
DERIVED   matched_terms       = [истина, спор]
MEASURED  filters_applied     = [card_type_in=…, required_function=any]
```

`llm_interpretation` по умолчанию `null`. Дисклеймер: «Причинность за пределами перечисленных фактов движком не измеряется и не может утверждаться». В UI блоки `RETRIEVAL FACTS` и `LLM INTERPRETATION` разделены визуально (второй — пунктирной рамкой) и никогда не сливаются.

## 6. Связь с RunTrace

Каждый `start_run` берёт один снимок активации и под ним выполняет и промпт-узел, и все привязанные RAG-движки, записывая в `rag_nodes`:

```yaml
node_id, kind: RAG
rag_profile_id / rag_profile_version / rag_profile_hash
index_id / index_version / corpus_ids
retrieved: [{chunk_id, chunk_hash, rank, score, locator, included_in_context}]
context_identity: "ctx:<sha256[:24] от упорядоченных chunk_id:chunk_hash>"
context_tokens (ESTIMATED) / context_bytes (MEASURED)
considered_count / returned_count / latency_ms / cache_state
```

`context_identity` — точная идентичность контекста, ушедшего дальше по цепочке. Тест `test_17_downstream_receives_exactly_the_recorded_context` пересчитывает её из событий и сверяет с трассой; `test_16_event_to_runtrace_linkage` проверяет совпадение состава и порядка чанков и равенство `rag_profile_hash`.

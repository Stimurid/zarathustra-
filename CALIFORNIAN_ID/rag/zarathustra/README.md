# Cultural RAG for Zarathustra — v0.4.0

Реализация в `src/californian_id/cultural_rag.py`. Управляемый гибридный
retrieval, не agentic. Не позволяет similarity search самостоятельно
определять действие без routing function.

## Три пространства

- `zarathustra_scenes` — карты типа `scene`
- `zarathustra_operations` — `operation` + `completion_pattern` + `constraint` + `risk`
- `zarathustra_primary_fragments` — chunks из `corpus/zarathustra/normalized/`

## Маршрут

```
BodyProjection + tension
        │
        ▼
infer_required_function()      ← детерминистичная функция
        │
        ▼
metadata filter (card_type ∈ ...)
        │
        ▼
hybrid lexical retrieval       ← BM25 в Python, без внешней vector DB
        │
        ▼
rerank + provenance attach
        │
        ▼
1..3 cards [+ 1..3 primary fragments]
        │
        ▼
Zarathustra prompt stack
```

## Обязательные инварианты

- Ни один retrieval event не может произойти без `required_function`.
- Provenance каждого возврата: `card_id` + `card_type` + `primary_sources`
  либо `source_id + locator + quote_hash`.
- Trace каждого retrieval через `CulturalIndex.drain_events()` и запись
  в `runs/<run_id>/events.jsonl`.
- Никогда не передавать в контекст всю книгу.
- Никогда не передавать больше 3 карт и 3 фрагментов за один шаг.
- Lexical fallback обязателен (сейчас основной).

## Rules-based rerank (в этом MVP)

- karta с `contraindications` не отсекается автоматически, но помечается
  в metadata; Zarathustra должен читать `contraindications` перед
  использованием.
- fragment с той же source_id, что и уже используемая карта, поднимается
  на +5% score.

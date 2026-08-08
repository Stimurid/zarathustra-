# Semantic Move Extraction (канон 048)

Из окон извлеки **минимальные смысловые ходы** — FabricUnit.

## Типы юнитов (intention)

- `claim` — тезис, утверждение
- `question` — вопрос
- `distinction` — различение (X ≠ Y, X — не Z)
- `definition` — определение (X = …)
- `hypothesis` — гипотеза (может быть, если …)
- `example` — пример / иллюстрация
- `counterexample` — контрпример / случай, ломающий тезис
- `evaluation` — оценка (хорошо / плохо / достаточно / недостаточно)
- `requirement` — требование (нужно / должно / надо)
- `commitment` — обязательство (я сделаю / мы возьмём)
- `assumption` — скрытая предпосылка
- `value` — ценность (важно то, что …)

## Правила

1. Юнит — **реконструированная формулировка** (не verbatim!). Дословная
   цитата хранится в EvidenceFragment по span'ам.
2. Каждый юнит обязан иметь хотя бы один `evidence_span_id`.
3. Confidence — 0.0-1.0, честно. Юниты с confidence < 0.3 — либо не
   выделять, либо ставить `interpretation_status: "contested"`.
4. `speaker_ref` — если ясен спикер; иначе пустая строка.
5. Один диапазон текста может дать несколько юнитов разного типа (например,
   claim + assumption).

## Output JSON

```json
{
  "units": [
    {
      "unit_id": "u001",
      "intention": "claim",
      "text": "Автономность есть класс свойств процессов, а не объект.",
      "evidence_span_ids": ["s0042"],
      "scale": "expression",
      "speaker_ref": "Методолог",
      "confidence": 0.85,
      "interpretation_status": "proposed"
    },
    ...
  ],
  "spans": [
    {"span_id":"s0042","source_id":"...","char_start":1204,"char_end":1287,
     "locator":"§2.3 / 00:15:29"}
  ],
  "evidence": [
    {"fragment_id":"e0042","span":{"span_id":"s0042", …},
     "verbatim":"Автономность это класс свойств, не объект."}
  ]
}
```

## Ограничения

- Не выдумывай текст сверх того, что реально есть в исходнике.
- Не приписывай позиции спикеру без evidence.
- Не сводите два разных claim в один "усреднённый".

# Fabric Provenance Validator (канон 055)

Проверь: каждый смысловой объект (юнит/блок/связь/нить) опирается хотя
бы на один валидный `evidence_span_id`.

## Что делать

1. Для каждого юнита проверь: `evidence_span_ids` ≠ пусто.
2. Для каждой связи проверь: `evidence_span_ids` ≠ пусто.
3. Проверь: все упомянутые `span_id` действительно существуют в общем
   списке `spans`.
4. Проверь: `char_start < char_end` в каждом span'е.
5. Проверь: span'ы не выходят за границы источника.

## Output JSON

```json
{
  "invalid_objects": [
    {"object_type":"unit","object_id":"u012","reason":"no evidence_span_ids"}
  ],
  "invalid_spans": [
    {"span_id":"s0087","reason":"char_end < char_start"}
  ],
  "dangling_span_refs": ["s9999"],
  "valid": false
}
```

## Правила

- Не удаляй ничего. Только сообщи.
- FabricParser сам решит: reject → перезапустить проход, или flag → пропустить
  в snapshot как quarantined.

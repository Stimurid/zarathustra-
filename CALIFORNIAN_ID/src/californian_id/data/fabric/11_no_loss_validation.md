# Fabric No-Loss Validator (канон 056)

Проверь: **весь исходник покрыт** ткашью. Не должно быть длинных
неотмеченных диапазонов.

## Что делать

1. Собери все `char_start`/`char_end` из всех spans.
2. Найди в исходнике диапазоны, **не покрытые** ни одним span'ом.
3. Игнорируй пустые строки, чисто пробельные фрагменты.
4. Игнорируй coarse_blocks типа `gap`.
5. Всё остальное — потенциальная потеря.

## Output JSON

```json
{
  "total_chars": 15420,
  "covered_chars": 13411,
  "coverage_pct": 0.87,
  "uncovered_ranges": [
    {"char_start":8420,"char_end":8892,"preview":"…фрагмент около 500 знаков…",
     "hint":"похоже на пропущенный диалог"}
  ],
  "acceptable": true,
  "threshold_pct": 0.85
}
```

## Правила

- Threshold по умолчанию 85%. Ниже — FabricParser поднимает warning.
- Ниже 60% — блокирует commit snapshot.
- Uncovered ранги логгируются; следующая итерация может назначить им
  coarse_block `gap` или заново прогнать `03_semantic_move_extraction`
  на этих окнах.

# CLI adapter

Реализован в `src/californian_id/cli.py`. Реальный работающий host —
запускается напрямую:

```bash
python -m californian_id validate
python -m californian_id personas list
python -m californian_id run --text "Стоит ли ускорять развитие AGI?"
python -m californian_id run --file examples/inputs/agi_acceleration.txt --mode deep --debug
```

Вход: text или файл; выход: `pretty` (человекочитаемо) или `json`.
Секреты и скрытые prompt stack по умолчанию скрыты; `--debug` раскрывает
внутреннюю трассу.

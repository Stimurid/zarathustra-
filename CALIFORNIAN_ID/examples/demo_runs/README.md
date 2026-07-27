# Demo runs

Каждый прогон сохраняет свою трассу в `runs/<run_id>/`. Три канонических
демо-сценария:

```bash
python -m californian_id run --file examples/inputs/agi_acceleration.txt
python -m californian_id run --file examples/inputs/life_extension.txt --mode deep
python -m californian_id run --file examples/inputs/jailbreak_transcript.txt --debug
```

Все три идут на mock-модели без внешних API. Ожидаемые свойства выходов:

1. **Разные голоса** — минимум 2 идеологических линзы в каждом ходе.
2. **Сохранённые конфликты** — `conflict_map` не пустой; `status: unresolved`
   для несогласованных рамок.
3. **Меньшинственные позиции сохранены** — `minority_positions` не пустой.
4. **Security события** — jailbreak-сценарий помечает 2+ прикладных
   попытки перехвата без раскрытия системных промптов.
5. **Trace** — `events.jsonl` содержит все ходы, security-события,
   маршрутизацию и синтез.

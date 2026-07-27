# Personas

Каждая персона — отдельный пакет `personas/<persona_id>/` с обязательными
файлами. Схема пакета: `persona.schema.json`. Шаблон нового пакета:
`_template/`.

## Важное каноническое ограничение

Персоны — это **идеологические/функциональные линзы**, а не имитации
конкретных живых людей. Это прямое требование канона Тинкуя
(`tinkuy canon/09_культурные_персоны/G-U06_cultural_persona_lenses/
CULTURAL_PERSONA_LENS_CONTRACT.md`). В manifest.yaml каждой fixture
установлены:

```yaml
assignment_prohibited: true
forbidden_uses:
  - participant profiling
  - identity attribution
  - style imitation
  - authority claim
```

Семь готовых персон, которые придут позднее от заказчика, должны быть
приведены к тому же контракту — либо через `import/normalization layer`,
либо через явное переоформление в соответствии со схемой.

## Что сейчас в этой папке

Семь **fixture-персон** — минимальные идеологические линзы, помечены
`is_fixture: true` и `status: test_fixture`. Они позволяют runtime
запускать сквозной сценарий без внешних данных. Реальные персоны
приходят отдельным drop-in-пакетом.

## Как заменить fixture на реальную персону

1. Скопируйте `_template/`.
2. Заполните `manifest.yaml`, `system_prompt.md`, `values.yaml`,
   `ontology.yaml`, `argumentation.yaml`.
3. По желанию — положите тексты в `corpus/` и заполните
   `sources/source_manifest.yaml`.
4. Уберите `is_fixture: true` в manifest.
5. `python -m californian_id validate`.

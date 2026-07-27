# units_of_content_md — adapter

Принимает markdown-выход внешнего семантического резчика (формат
«единицы содержания»), возвращает `UnitPack` для `Pipeline.run_from_units`.

## Поддерживаемые формы

1. **Плоская.** Только список `### Un — Title` с паспортом на каждую единицу
   (Заголовок / Намерение / Объект / Участники / Позиция / Тема-Рема /
   Тулмин / Вмешательства / Провенанс / Абстракт).
2. **Обогащённая.** Плоская + преамбула с аудитом источника:
   инвентарь speaker-меток и ролей, дефекты диаризации, повреждения
   распознавания. Аудит становится `SourceAudit` и попадает в первую
   `chorus_reflection` совета как сигнал ненадёжности атрибуции.

## Что делает

- Парсит `Un — Title` секции regex'ом (без LLM).
- Извлекает Toulmin-структуру (Claim / Data / Warrant / Backing /
  Qualifier / Rebuttal / Counterclaim).
- Собирает Тема-Рема с locator'ами.
- Восстанавливает провенанс (speaker-label + name + locator) как есть, без
  доуверенности.
- Сохраняет аудит источника отдельным объектом; не смешивает его с
  содержательной тканью.

## Что НЕ делает

- Не додумывает Toulmin, если резчик его не проставил.
- Не выравнивает разные написания имён (`«Даша Грит» / «Даша Гриц»` — оба
  сохраняются как есть).
- Не восстанавливает повреждения распознавания.
- Не понимает форматы, отличные от `### Un — Title`. Для новых форматов —
  свой adapter.

## Использование

```python
from californian_id.adapters.units_of_content_md import parse_md_units_file
from californian_id.pipeline import Pipeline

pack = parse_md_units_file("path/to/units.md")
result = Pipeline().run_from_units(pack, mode="fast")
```

Или через CLI:

```bash
python -m californian_id run --units-file path/to/units.md --mode deep
```

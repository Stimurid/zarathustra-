# SOCRATES G-S24 — SOURCE MANIFEST (read-only mirror)

**Статус:** durable output Stage 4A
**Владелец источника:** LOCAL_SOCRATES
**Наш статус по отношению к нему:** READ-ONLY. Ни один файл пакета не изменён,
ни один дефект внутри пакета не исправлен.
**Машиночитаемая версия:** `CALIFORNIAN_ID/socrates_mirror/source_manifest.yaml`

---

## 1. Что такое зеркало и чем оно не является

`CALIFORNIAN_ID/socrates_mirror/` — это **фикстура проекции**, а не авторитет.
Источник истины — Google Drive, папка `07_SOCRATES_PIPELINE_PACK`
(`10WHFJzLZYP6JblzmZJBk1X3_sdETU4A2`). Зеркало существует только для того,
чтобы адаптер мог читать пакет детерминированно и чтобы у каждого прочитанного
байта была прослеживаемая провенанс-запись.

Правило, которое здесь соблюдается буквально: **отсутствие доступа ≠ отсутствие
объекта**. Перечисление содержимого папок для этого аккаунта возвращает пустой
результат; прямой доступ по id работает. Поэтому «папка пуста» нигде не
записано — записано `EMPTY_FOR_THIS_ACCOUNT`.

## 2. Классы достоверности

| Класс | Что означает |
|---|---|
| `BYTE_EXACT` | декодировано из бинарного содержимого Drive; sha256 совпал с собственным манифестом владельца `G-S24_SHA256SUMS` |
| `BYTE_EXACT_UNVERIFIED` | декодировано из бинарного содержимого и сверено по размеру с метаданными Drive, но файла нет в контрольном манифесте владельца — сверять хеш не с чем |
| `TEXT_EXTRACTION` | получено через текстовое представление коннектора; смысл сохранён, побайтовая идентичность **не заявляется** |
| `NOT_FETCHED` | присутствует в манифесте владельца, но прямой id не был предоставлен, а перечисление недоступно |

Разделение на `BYTE_EXACT` и `BYTE_EXACT_UNVERIFIED` появилось не из
педантизма: заявление о побайтовой идентичности без авторитета, с которым её
можно сверить, — это не проверка, а самоуверенность.

## 3. Что втянуто

| Файл | Drive id | Достоверность | Проверен по манифесту владельца |
|---|---|---|---|
| `pipeline.yaml` | `1cNyy952FrOL0shWm2J26DVeaFN7l5Tzm` | **BYTE_EXACT** | **да** — sha256 `9857ff19…4eb7783` |
| `manifest.yaml` | `1no6O2N05RpHlOeYMAdmfqaDZTYasnZjA` | TEXT_EXTRACTION | нет |
| `state_model.yaml` | `1kAHBbL6oQl4yeBvo-8DfrX3aR5qAzJYL` | TEXT_EXTRACTION | нет |
| `README.md` | `1FiepAVg0IuRe9ztYY6qbU6X3iuPZFnjR` | TEXT_EXTRACTION | нет |
| `prompts/prompt_bindings_v0.3.yaml` | `1d7AUn8-HDZ1DviUyAGyAUYqLZwl4VYOo` | TEXT_EXTRACTION | нет |
| `prompts/MODE_AND_REFLEXIVITY_GOVERNOR_PROMPT_PACK.md` | `1FRmTQfj2Vxwmgde_C_u2zX1fbGISGLUL` | BYTE_EXACT_UNVERIFIED | нет — файла нет в `G-S24_SHA256SUMS` (SD-002) |
| `G-S24_SHA256SUMS` | `1p-a9C5kiRsYQRrGurK6_GhaDrmBbed_y` | 37 записей | — (сам является манифестом) |

Единственный файл, который адаптер **парсит**, — `pipeline.yaml`, и именно он
подтверждён побайтово. Всё остальное используется как текстовые факты и
помечено соответственно.

### 3.1 Инцидент побайтовой верности (зафиксирован намеренно)

Тело промпт-пака переносилось через base64-полезную нагрузку, и первая попытка
**молча изменила одно слово** (`when` → постороннее слово в разделе P3).
Это поймала не проверка смысла, а проверка размера: 1845 ≠ 1844.

Отсюда постоянные меры в `scripts/socrates_mirror_add_prompt_pack.py`:
* утверждение о размере против метаданных Drive;
* четыре содержательных якоря, которые сверяются с двумя независимыми
  чтениями Drive;
* класс `BYTE_EXACT_UNVERIFIED` вместо `BYTE_EXACT`.

## 4. Точные пробелы источника

Это **не** «неизвестно» — это перечисленные, адресуемые пробелы.

* **Тела контрактов шагов** (`steps/S0…S10.yaml`, 11 файлов).
  Имена и sha256 владельца известны из `G-S24_SHA256SUMS`; содержимое —
  `NOT_FETCHED`. Папка `1nlNWyA3wkdq54qwBRB9GPd13P07-lttU`,
  `enumeration_status: EMPTY_FOR_THIS_ACCOUNT`.
  Ничего из них не реконструировано.
* **Схемы:** предоставлено 9 id, но в контрольном манифесте владельца
  присутствует только `pipeline_trace.schema.json` → дефект **SD-001**.
* **Промпт-пак** отсутствует в контрольном манифесте → дефект **SD-002**.
* `CHANGELOG.md`, `contracts/reference_registry.yaml` — в манифесте владельца
  есть, прямых id нет, не втянуты.

## 5. Граница записи

* Ни один файл G-S24/G-S25 в Drive не создан, не изменён и не удалён.
* Ни один дефект внутри пакета не «исправлен» — все переданы владельцу через
  [SOCRATES_WORKBENCH_SOURCE_DEFECT_HANDOFF.md](SOCRATES_WORKBENCH_SOURCE_DEFECT_HANDOFF.md).
* Всё новое создано только в implementation-репозитории Workbench.

## 6. Воспроизведение

```bash
python scripts/socrates_mirror_build.py            # pipeline.yaml, BYTE_EXACT
python scripts/socrates_mirror_add_prompt_pack.py  # промпт-пак, размер + якоря
```

# PROMPT_VARIANT_LIFECYCLE v0.1

**Дата:** 2026-08-15

---

## 1. Состояния

| Состояние | Смысл | Может быть активным |
|---|---|---|
| `BASELINE` | исходный вариант системы: файл на диске или Python-константа. Неудаляем | **да** |
| `CANDIDATE_UNCHECKED` | сохранён пользователем, ни одна проверка не пройдена | нет |
| `STATIC_VALID` | пройдена статическая валидация | нет |
| `COMPILED` | успешно скомпилирован хотя бы под один `PromptCompilerProfile` | нет |
| `SMOKE_TESTED` | пройден ограниченный смок на фиксированной фикстуре | нет |
| `ACCEPTED` | прошёл всю ленту проверок, готов к активации | нет |
| `ACTIVE` | связан `ActivationBinding` и реально используется рантаймом | **да** |
| `DEPRECATED` | вытеснен, сохраняется для истории и отката | нет |
| `REJECTED` | отклонён проверкой или человеком, с причиной | нет |
| `INCOMPATIBLE` | нарушает контракт или несовместим с соседями по `depends_on` | нет |

Дополнительные состояния из WhiteCrow (`draft`, `candidate`) отображаются как `CANDIDATE_UNCHECKED` и `ACCEPTED` соответственно при импорте реестра.

---

## 2. Граф переходов

```
                    ┌──────────┐
                    │ BASELINE │◄─────────── (создаётся системой, не человеком)
                    └────┬─────┘
                 clone   │
                         ▼
              ┌──────────────────────┐
   edit ─────►│ CANDIDATE_UNCHECKED  │
              └──────┬───────────────┘
                     │ static_validate
           ┌─────────┴─────────┐
           ▼                   ▼
    ┌─────────────┐     ┌──────────────┐
    │ STATIC_VALID│     │   REJECTED   │◄── human reject (в любой момент)
    └──────┬──────┘     └──────────────┘
           │ compile
           ├────────────────────► INCOMPATIBLE  (contract_check failed)
           ▼
     ┌───────────┐
     │ COMPILED  │
     └─────┬─────┘
           │ smoke_run(fixture)
           ├────────────────────► REJECTED  (smoke failed)
           ▼
   ┌────────────────┐
   │  SMOKE_TESTED  │
   └───────┬────────┘
           │ compare_with_baseline + human accept
           ▼
     ┌────────────┐   activate    ┌──────────┐
     │  ACCEPTED  │──────────────►│  ACTIVE  │
     └────────────┘               └────┬─────┘
                                       │ rollback / superseded
                                       ▼
                                 ┌─────────────┐
                                 │ DEPRECATED  │
                                 └─────────────┘
```

---

## 3. Правила переходов

| Переход | Условие | Побочные эффекты |
|---|---|---|
| `BASELINE → CANDIDATE_UNCHECKED` | клонирование; `parent_variant_id = baseline` | новый `variant_id`, `source_hash` пересчитан |
| `* → CANDIDATE_UNCHECKED` | любое редактирование сбрасывает проверки | все `EvaluationRecord` помечаются `stale` |
| `CANDIDATE_UNCHECKED → STATIC_VALID` | пройдены все проверки §4 | `EvaluationRecord(kind=static, verdict=pass)` |
| `CANDIDATE_UNCHECKED → INCOMPATIBLE` | нарушен контракт или защищённая область | причина обязательна |
| `STATIC_VALID → COMPILED` | компиляция под целевой профиль без ошибок | появляется `CompiledPrompt` с `compiled_hash` и `source_map` |
| `COMPILED → SMOKE_TESTED` | смок на фикстуре: выход валиден по схеме, инварианты держатся | `EvaluationRecord(kind=smoke)` с `fixture_id` |
| `SMOKE_TESTED → ACCEPTED` | сравнение с baseline проведено **и** человек подтвердил | фиксируется `accepted_by` |
| `ACCEPTED → ACTIVE` | создан `ActivationBinding`; предыдущий `ACTIVE` уходит в `DEPRECATED` | инвалидация кеша `Zarathustra._prompt_cache` **обязательна** |
| `ACTIVE → DEPRECATED` | вытеснение или откат | `rollback_of` заполняется при откате |
| `DEPRECATED → ACTIVE` | повторная активация ранее принятого варианта | без повторного смока, если `source_hash` и `compiled_hash` совпадают |
| `* → REJECTED` | человек или проверка | `deprecation_reason` обязателен |

**Жёсткие запреты:**

1. Прямой переход `CANDIDATE_UNCHECKED → ACTIVE` невозможен ни при каких флагах.
2. `BASELINE` нельзя удалить и нельзя перевести в `REJECTED`.
3. Активация без записи `compiled_hash` в `RunTrace` считается ошибкой рантайма.
4. Изменение `protected_regions` или `invariants` переводит вариант в `INCOMPATIBLE`, а не в `STATIC_VALID`.
5. Импорт из Google Docs всегда создаёт новый `CANDIDATE_UNCHECKED`, никогда не правит `ACTIVE`.

---

## 4. Что проверяет статическая валидация

Список наследует `scripts/validate_prompt_bodies.py` WhiteCrow и расширяет его.

| Проверка | Источник | Наследовано |
|---|---|---|
| обязательные метаполя присутствуют | `REQUIRED_METADATA_FIELDS` | ✓ WhiteCrow |
| обязательные секции присутствуют | `REQUIRED_SECTIONS` | ✓ WhiteCrow |
| `asset_id` соответствует имени файла | — | ✓ WhiteCrow |
| H1 соответствует имени файла | — | ✓ WhiteCrow |
| ровно один открывающий и один закрывающий маркер защищённой области | `RUNTIME_PROMPT_START/END` | ✓ WhiteCrow |
| файл не лежит под запрещённым путём | forbidden paths | ✓ WhiteCrow |
| ассет не попал в RAG-индекс | `.litopsignore` | ✓ WhiteCrow |
| **защищённые области не изменены относительно baseline** | — | **новое** |
| **инварианты (`non_negotiable_identity`) присутствуют дословно** | Tinkuy manifest | **новое** |
| **все `required_variables` подставляемы из контекста** | — | **новое** |
| **`depends_on` разрешаются в существующие ассеты** | — | **новое** |
| **поля, требуемые промптом, совпадают с `output_schema_ref`** | — | **новое, ловит дефект `03_scene_reading`** |
| **компиляция под целевой профиль завершается без ошибок** | — | **новое** |

---

## 5. Смок-валидация

Минимальный исполняемый срез: **один узел, одна фикстура, один вызов модели**.

Обязательно фиксируется в `EvaluationRecord`:

- `variant_id` и `source_hash` исходника;
- `compiled_hash` и `profile_id` скомпилированного payload;
- `fixture_id` и хэш входа;
- модель, провайдер, настройки вызова;
- выход, результат валидации по схеме, проверка инвариантов;
- `tokens_in/out`, `latency_ms`, стоимость (помеченная как оценка);
- сравнение с baseline: те же поля для `BASELINE`-варианта на той же фикстуре.

Смок **не считается пройденным**, если отсутствует хотя бы одно из: `compiled_hash`, `fixture_id`, результат схемной валидации.

---

## 6. Отсутствие пользователей

Пока системы пользователей нет, все варианты со статусом `ACCEPTED` и `ACTIVE` видимы и выбираемы всем входящим на портал. `author` заполняется, если известен (`jwt_auth` уже даёт `username`), но не даёт приватности. Это фиксируется явно, чтобы позже добавление тенантов не потребовало миграции семантики.

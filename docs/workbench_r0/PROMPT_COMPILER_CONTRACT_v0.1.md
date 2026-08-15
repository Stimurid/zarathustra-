# PROMPT_COMPILER_CONTRACT v0.1

**Дата:** 2026-08-15 · База: `PROMPT_ORCHESTRATOR_SPEC.md` (WhiteCrow, 348 строк) + `PROMPT_DEPENDENCY_MAP.yaml` (Tinkuy).

---

## 0. Ключевое ограничение, найденное в R0

`PROMPT_DEPENDENCY_MAP.yaml` Тинкуя постановляет:

> «Никакой мега-промпт. Каждый шаг Заратустры подгружает ТОЛЬКО те prompt-modules, что ему нужны. Новые модули появляются через явный proposal и versioning.»

Ранняя спецификация Workbench называла суперпромпт «предельным случаем» компиляции. Для ветки Заратустры это **запрещено каноном**. Поэтому:

**`allow_superprompt` — обязательное поле профиля компилятора, значение по умолчанию `false`, и оно может быть переопределено только на уровне ветки, а не отдельного ассета.**

---

## 1. Сигнатура

```
compile(
  pack: PromptPack | asset_id,
  variant_selection: {asset_id: variant_id},
  profile: PromptCompilerProfile,
  context: RuntimeContext
) -> CompiledPrompt
```

Компиляция **детерминирована**: одинаковые вход, выбор вариантов, профиль и контекст дают побитово одинаковый `CompiledPrompt` и одинаковый `compiled_hash`.

---

## 2. PromptCompilerProfile

```yaml
profile_id: str
branch: str
model_id: str
provider: str
context_window: int
supports_system_role: bool
max_system_chars: int | null
assembly_order: [str]        # порядок слоёв, см. §3
allow_superprompt: bool      # default false; для zarathustra — принудительно false
module_loading: lazy | eager # lazy = только used_by_steps текущего шага
token_budget: {system: int, user: int, total: int}
cache_strategy: none | prefix | full
variable_policy: strict | warn   # strict = незаполненный {{var}} → ошибка компиляции
truncation_policy: forbid | tail | middle
```

---

## 3. Порядок сборки

Наследуется из `PROMPT_ORCHESTRATOR_SPEC.md`, обобщён:

```
system_text =
    layer_constitution        # 01_identity_and_laws, invariants — ВСЕГДА первый, никогда не усекается
  + layer_ontology            # 02_cave_ontology и подобное, если used_by_steps совпал
  + layer_operation           # промпт-ассет текущего шага (03/04/13 …)
  + Σ layer_modules           # prompt_modules + cultural cards, порядок по depends_on
  + Σ layer_overrides         # over-agents / guards, всегда после канонических
  + layer_constraints         # constraint-блок, всегда последний

user_text =
    context_payload           # данные шага
  + command                   # запрос
```

Правила:

1. `layer_constitution` и `invariants` **никогда не усекаются**. Если бюджет не позволяет — компиляция падает, а не режет конституцию.
2. Модули упорядочиваются топологически по `depends_on`; при равенстве — по `asset_id` лексикографически. Порядок обязан быть воспроизводим.
3. `module_loading: lazy` подтягивает только модули, у которых текущий шаг есть в `used_by_steps`. Это машинное выражение принципа «никакого мега-промпта».
4. При `supports_system_role: false` `system_text` сливается в начало `user_text` — и это отражается в `source_map`.
5. `variable_policy: strict` — незаполненный `{{placeholder}}` останавливает компиляцию. WhiteCrow сейчас подставляет `'[unset]'` с предупреждением в консоль; для Workbench это ослабленный режим `warn`.

---

## 4. CompiledPrompt

```yaml
compiled_hash: str            # sha256 по канонизированному представлению
profile_id: str
built_at: iso8601
branch: str
step_id: str
system_text: str
user_template: str
token_count: {system: int, user: int, total: int, method: "tokenizer|estimate"}
sources: [{asset_id, variant_id, version, source_hash}]
source_map: [SourceSpan]
warnings: [str]
truncated: bool
```

### SourceSpan

```yaml
span_start: int        # индекс символа в system_text или user_template
span_end: int
target: system | user
asset_id: str
variant_id: str
region_name: str       # какая именованная область исходника сюда попала
region_kind: protected | editable
```

`source_map` покрывает **100 % символов** обоих текстов. Непокрытый диапазон — ошибка компилятора, а не предупреждение. Это то, что делает COMPILED VIEW кликабельным: клик по фрагменту скомпилированного промпта ведёт в конкретную область конкретного варианта.

### Канонизация для хэша

`compiled_hash` считается по конкатенации: `profile_id`, `branch`, `step_id`, нормализованный `system_text` (LF, без хвостовых пробелов), нормализованный `user_template`, отсортированный список `sources` (`asset_id:variant_id:source_hash`). Время сборки в хэш **не входит**.

---

## 5. Обязанности перед рантаймом

1. `compiled_hash` записывается в `RunTrace` **каждого** LLM-вызова. Без него прогон невоспроизводим.
2. Вместе с хэшем пишутся `sources[]` — точные версии исходников. «Промпт v4» без `compiled_hash` и `source_hash` считается недействительной записью.
3. При активации нового варианта кеш промптов инвалидируется. Сегодня `Zarathustra._prompt_cache` (`zarathustra.py:145`) **не имеет инвалидации** — это конкретный дефект, который надо закрыть до первой активации.
4. Компилятор ничего не пишет на диск. Он чистая функция.

---

## 6. Режимы SOURCE VIEW / COMPILED VIEW

| Вид | Что показывает | Редактируем |
|---|---|---|
| SOURCE | исходники модулей с разметкой protected/editable | да, только `editable_regions` |
| COMPILED | ровно то, что получит модель, с подсветкой границ модулей и счётчиком токенов | нет, только чтение |

Переключение видов не меняет состояние варианта. Клик по фрагменту COMPILED переводит фокус на соответствующую область SOURCE через `source_map`.

---

## 7. Профили первого среза

| profile_id | Назначение |
|---|---|
| `tinkuy.zarathustra.lazy` | `allow_superprompt: false`, `module_loading: lazy`, `variable_policy: strict` — рабочий профиль ветки Заратустры |
| `tinkuy.debug.eager` | `module_loading: eager` — диагностический, показывает максимальный возможный контекст, в рантайм не подаётся |

Профиль с `allow_superprompt: true` в первом срезе **не создаётся**. Он появится только если конкретная ветка (не Заратустра) потребует эффекта семантической суперпозиции и это будет зафиксировано в её каноне.

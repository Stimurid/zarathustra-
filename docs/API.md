# Tinkuy API

Публичный HTTP API. Все примеры относятся к прод-инстансу
`https://tinkuy.mindkampf.ru` (за Caddy basic-auth) или локальному
`http://127.0.0.1:8085` (dev).

## Аутентификация

Три режима, проверяются по порядку:

1. **JWT** (Пик 6.4) — `Bearer <jwt-token>`. Токен выдаёт `POST /api/auth/login`
   или CLI `python -m californian_id users token <username>`. Пользователи
   хранятся в SQLite (`RUNS_DIR/users.sqlite3`), pbkdf2_hmac password hash.
2. **Multi-key** (Пик 8.3) — env `CALIFORNIAN_ID_API_KEYS=k1:alice,k2:bob`.
   Каждый ключ имеет label; label используется в rate-limit и billing.
3. **Legacy single-key** — env `TINKUY_COMPAT_API_KEY=<key>`. `Bearer <key>`.

Отключить auth для dev: `CALIFORNIAN_ID_AUTH_DISABLED=1`.

Rate limit: 30 запросов/минуту per-label по умолчанию. Override:
`CALIFORNIAN_ID_RATE_LIMIT_PER_MIN=100`.

### JWT flow

```bash
# создать пользователя (админская команда)
python -m californian_id users add alice --roles user,admin

# войти → получить токен
curl -sS -X POST https://tinkuy.mindkampf.ru/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"..."}'
# → {"token":"eyJ...","token_type":"Bearer","expires_in":86400,"user":{...}}

# использовать в последующих запросах
curl -sS https://tinkuy.mindkampf.ru/api/auth/me \
  -H "Authorization: Bearer eyJ..."
# → {"username":"alice","roles":["user","admin"],"expires_at":...}
```

JWT: HS256, secret из env `CALIFORNIAN_ID_JWT_SECRET` или автогенерируется
в `RUNS_DIR/jwt.secret` (chmod 600). TTL default 24h.

## Endpoint reference

### Совет (Council)

#### `POST /api/run` — синхронный запуск
Ответ: 200 с полным payload через 60–180 сек.

```bash
curl -sS -X POST https://tinkuy.mindkampf.ru/api/run \
  -H "Content-Type: application/json" \
  -u user:pass \
  -d '{
    "text": "Является ли материальное автономным?",
    "runtime_layer": "californian_id",
    "input_mode": "raw",
    "mode": "fast",
    "workspace_id": "default",
    "closing_genre": "methodological_consultation",
    "dialogue_protocol": "joint_inquiry"
  }'
```

#### `POST /api/run/async` (Пик 6.3) — асинхронный
Ответ: 202 `{run_id, poll_status, poll_result}`. Результат в фоне.

#### `POST /api/run/stream` (Пик 6.B) — SSE стриминг
Ответ: `text/event-stream`. Events: `run_started`, `situation_reading_done`,
`cast_selected`, `turn_completed`, `closing_speech_delta`,
`closing_speech_complete`, `run_completed`, `final_payload`.

```bash
curl -N -X POST http://127.0.0.1:8085/api/run/stream \
  -H "Content-Type: application/json" \
  -d '{"text":"...", "runtime_layer":"californian_id"}'
```

### Раны

- `GET /api/runs?workspace=<id>&limit=50` — история ранов workspace.
- `GET /api/run/<run_id>/status?workspace=<id>` — метаданные (RUNNING|COMPLETED|ERROR).
- `GET /api/run/<run_id>/result?workspace=<id>` — полный payload (200 или 202).

### Экспорт (Пик 8.1)

- `GET /api/run/<run_id>/export?workspace=<id>&format=md|json|bundle`
  - `md` — читаемая markdown-версия совета.
  - `json` — сырой payload (то же что `/result`).
  - `bundle` — `tar.gz` со всем: result.json, closing.md, metadata.json,
    trace_dir/*.

```bash
curl -sS -u user:pass \
  "https://tinkuy.mindkampf.ru/api/run/${RID}/export?format=bundle&workspace=default" \
  -o run.tar.gz
```

### Cross-run reflection (Пик 8.2)

- `GET /api/runs/search?workspace=<id>&q=<text>&limit=20` — lexical search
  по input_summary + completion_form + voices.
- `POST /api/reflect/cross_run` — LLM-driven сравнение двух ранов.
  Тело: `{"workspace_id":"...", "run_a":"...", "run_b":"..."}`.
  Ответ: `{shared_ground, key_differences, what_A_saw_that_B_missed,
  what_B_saw_that_A_missed, position_evolution, recommended_next_move}`.

### Workspaces (Пик 6.A)

- `GET /api/workspaces` — все workspaces на диске + статистика.

### Ткань (Пик 5)

Через CLI (SQLite JSON1 store per-workspace):

```bash
python -m californian_id fabric parse --file transcript.txt --workspace default
python -m californian_id fabric list --workspace default
python -m californian_id fabric export <snapshot_id> --format md
```

Через web-ui: input mode `raw+fabric` — парсит ткань, сохраняет snapshot,
делегирует в совет.

### Каталоги (Пик 7)

- `GET /api/methods` — 6 MethodPack'ов.
- `GET /api/genres` — 7 риторических жанров закрытия.
- `GET /api/protocols` — 5 диалоговых протоколов.

### Billing (Пик 8.3)

- `GET /api/billing?workspace=<id>` — rate-limit snapshot + агрегаты
  ранов (по label ключа, если задан).

### OpenAI-compat (`/v1/*`)

- `GET /v1/models` — список моделей (Bearer required).
- `POST /v1/chat/completions` — совет как chat-completion endpoint.
  Совместим с любым OpenAI-клиентом (LangChain, LlamaIndex, curl).

## Tinkuy как LLM для чужой системы

Тинкуй экспонирует `/v1/*` как **drop-in OpenAI-compatible endpoint**.
Любой инструмент, умеющий OpenAI:

```python
from openai import OpenAI
client = OpenAI(
    base_url="https://tinkuy.mindkampf.ru/v1",
    api_key="<your-tinkuy-key>",
)
resp = client.chat.completions.create(
    model="tinkuy-council",
    messages=[{"role":"user","content":"Что такое свобода?"}],
)
print(resp.choices[0].message.content)
```

Отличия от обычной LLM:
- Ответ — не один голос, а результат работы 4–7 персон совета плюс
  закрывающая речь Заратустры.
- Задержка 60–180 сек в sync-режиме (используй `/api/run/async` для
  фоновой обработки).
- Формы завершения: synthesis, aporia, decision_with_dissent, world_fork,
  polyphony, delegation, alliance, refusal_to_close, transformed_question,
  unresolvable_conflict.

## Формы завершения

| Форма | Когда возникает |
|---|---|
| `synthesis` | Совет пришёл к общей конструкции. |
| `decision_with_dissent` | Решение принято, dissenting голоса удержаны. |
| `aporia` | Честный отказ: любой прямой ответ разрушит существенную ценность. |
| `transformed_question` | Исходный вопрос содержал скрытую нормативность; переформулирован. |
| `world_fork` | Позиции описывают разные миры; выбор — за юзером. |
| `unresolvable_conflict` | Картины мира несовместимы; полифония side-by-side. |
| `delegation` | Одна линза говорит от совета, остальные — в conflict_map. |
| `polyphony` | Несколько голосов без сведения. |
| `alliance` | Партнёры договорились о конкретном действии при разных основаниях. |
| `refusal_to_close` | Совет отказывается закрыть — закрытие разрушит предмет. |

## Каноническая спецификация

Всё это следует `TINKUY_STANDALONE_MVP_ARCHITECTURE_V1.1` (226 канонических
номеров), карта покрытия — в `_work/BACKLOG.md`.

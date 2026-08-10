# B-5.5 Human-in-the-loop внутри совета — Design v1.0

Дата: 2026-08-11
Статус: план утверждён, реализация не начата.

## Принятые решения

- **Transport**: WebSocket duplex, библиотека `websockets` (pure Python, stdlib-like).
  SSE endpoint /api/run/stream остаётся для legacy/curl.
- **Frontend**: Svelte 5 + Vite. Первый build step в проекте.
- **Permissions**: любой авторизованный JWT-юзер может интервенить.
  intervention.author = username из токена; per-workspace ACL — отдельная 6.4.5.
- **Legacy UI**: `/` остаётся vanilla, `/live` — новый Svelte.
- **Pause model**: cooperative checkpoint между ходами.
- **FabricParser внутри рана**: MVP — inline text без парсинга; FabricParser boost — веха 5+.

## Границы

**В scope**:
- HIL-1..HIL-7 (наблюдение, steer, sliders, user voice, attach file, subtree, pause/resume/cancel).
- Duplex WebSocket с auth JWT.
- Cooperative pause через `Pipeline._checkpoint()`.
- Intervention persistence + audit.
- Новый Svelte UI на `/live` без замены `/`.

**Не в scope**:
- Правка формы завершения после assemble.
- Re-run прошлого рана с изменениями (задача Пик 6.5+).
- Preemptive cancel посреди LLM-вызова.
- Per-workspace ACL интервенций (задача 6.4.5).
- PDF/DOCX extraction в attach (MVP: MD/TXT/JSON only).

## 7 пользовательских сценариев (HIL-1 .. HIL-7)

**HIL-1. Наблюдать ход**
Расширяет 6.B: per-turn utterance + token stream закрытия + architectonic delta stream + retrieved evidence.

**HIL-2. Направить следующий ход**
Между ходами Zarathustra шлёт `route_previewed {persona_id, operation}`, юзер может override, skip или let-decide. Deadline: 2 сек.

**HIL-3. Бегунки приоритета голосов**
Панель N слайдеров [0..2] per LENS. `Zarathustra.route_next` умножает scoring на `persona_weights`. Slider = 0 = временное exclusion.

**HIL-4. Юзер вставляет свой аргумент**
Textarea → optional attach-persona → добавляется в `state.turns` с `persona_id="USER_VOICE"`, `author=<username>`, `human_source=true`. Zarathustra видит в prior_turns.

**HIL-5. Прикрепить файл к голосу**
File upload + persona picker + TTL turns. Extracted text (MD/TXT в MVP) добавляется в RAG scope выбранной персоны на N следующих ходов.

**HIL-6. Погружение в субветки**
Каждый TurnCard collapsible: route decision, cultural cards, retrieved evidence, anti-slop, architectonic delta. Данные уже пишутся в trace_dir.

**HIL-7. Pause / Resume / Cancel**
Кнопки на panel. Pause → wait between turns. Resume → продолжает. Cancel → thread stop + финализация того что успело.

## Data model

Новая таблица `intervention` per-workspace (в новом `interventions.sqlite3`):

```sql
CREATE TABLE intervention (
    intervention_id  TEXT PRIMARY KEY,       -- iv_<sha1(12)>
    run_id           TEXT NOT NULL,
    workspace_id     TEXT NOT NULL,
    kind             TEXT NOT NULL,           -- steer|slider|user_voice|attach_file|pause|resume|cancel
    at_turn_index    INTEGER,                 -- перед каким turn'ом применяется
    author           TEXT NOT NULL,           -- username из JWT
    payload_json     TEXT,                    -- kind-specific payload
    applied          INTEGER DEFAULT 0,
    applied_at       TEXT,
    created_at       TEXT
);
CREATE INDEX idx_intervention_run ON intervention(run_id);
CREATE INDEX idx_intervention_author ON intervention(author);
```

Payload по kind:
- `steer`:       {persona_id, operation?, reason?}
- `slider`:      {weights: {LENS_A: 1.2, ...}}
- `user_voice`:  {utterance, attach_to_persona?, as_operation?}
- `attach_file`: {filename, extracted_text, boost_for_persona, ttl_turns}
- `pause`/`resume`/`cancel`: {}

Также: `runs/<run_id>/interventions.jsonl` — audit trace, попадает в bundle export.
На turn.applied_interventions[] — обратная ссылка.

## Backend изменения

### 1. `runtime_control.py` (новый модуль)
- `RunControl`: in-memory registry `{run_id: control_state}` + persist в intervention table.
- API: `register(run_id, workspace_id)`, `signal(run_id, kind, author, payload)`,
  `poll_pending(run_id) → list[Intervention]`, `set_state(run_id, RUNNING|PAUSED|CANCELLED)`,
  `sliders_for(run_id) → dict[persona_id, float]`,
  `pending_steer(run_id) → Optional[SteerDecision]`,
  `pending_user_voice(run_id) → list[UserVoice]`.

### 2. `Pipeline._checkpoint(state, before_turn_index)` (новый метод)
- Между turn'ами вызывается перед `route_next`.
- Читает `run_control.poll_pending(run_id)`.
- Применяет: обновляет sliders, инжектит user_voice как turn (persona_id=USER_VOICE),
  применяет steer_override к решению route_next.
- Если PAUSED → блокируется на `threading.Event.wait(timeout=60)` до resume/cancel.
- Emits `checkpoint_reached` в event_sink.

### 3. `Zarathustra.route_next` — apply weights
Signature: `route_next(..., persona_weights: dict[str,float] | None)`.
При наличии — multiply scoring per persona. Bound [0.1, 3.0].
При weight ≤ 0.05 → persona excluded from cast для этого turn'а.

### 4. `Pipeline.event_sink` — новые events
- `route_previewed {run_id, next_persona, operation, reason, deadline_ms}` — перед реальным route (dwait 2s на override).
- `slider_updated {weights, applied_at}` — эхо после apply.
- `user_voice_injected {turn_index, author, utterance}`.
- `paused {reason, at_turn_index}` / `resumed`.
- `cancelled {reason}`.
- `checkpoint_reached {turn_index, sliders_snapshot}`.

### 5. WebSocket endpoint (новый `ws_endpoint.py`)
- Библиотека `websockets` (добавить в deps).
- Server: `ws://.../ws/run/<run_id>`.
- Auth: JWT в query param `?token=...` (или в первом Frame `{"cmd":"auth","token":"..."}`).
- Client → Server frames:
  - `{cmd:"steer", persona_id, operation?, reason?}`
  - `{cmd:"slider", weights: {...}}`
  - `{cmd:"user_voice", utterance, attach_to_persona?}`
  - `{cmd:"attach", ref: <upload_id>}` (файл заранее через POST /api/run/<id>/attach)
  - `{cmd:"pause"}` / `{cmd:"resume"}` / `{cmd:"cancel"}`
  - `{cmd:"ping"}` → server отвечает `{type:"pong",ts}`
- Server → Client frames: все events из event_sink + `hello` / `state_snapshot` (на connect).
- Heartbeat: ping/pong каждые 15s; disconnect при 3 missed pongs.
- Reconnect: client шлёт `{cmd:"resume_stream", from_event_seq: N}`, сервер шлёт `state_snapshot` + missed events.

### 6. File attachment endpoint
- `POST /api/run/<id>/attach` — multipart file + form `boost_for_persona=<pid>&ttl_turns=3`.
- MVP: MD/TXT/JSON inline extract → `attach_boost` in-memory registry.
- Возвращает `{upload_id}` для последующей ссылки в WS-фрейме.

### 7. Deployment
- Caddyfile: `handle_path /ws/*` + `reverse_proxy` с `header_up Upgrade websocket`.
- Systemd unit: без изменений (тот же python процесс).
- Firewall: WS идёт через тот же 443 → 8085, дополнительно ничего.

## Frontend изменения (Svelte 5 + Vite)

### 1. Проект structure
```
CALIFORNIAN_ID/frontend/
  package.json              # Vite 5 + Svelte 5 + typescript
  vite.config.ts
  svelte.config.js
  tsconfig.json
  index.html
  src/
    main.ts                 # entry
    App.svelte              # root
    stores/
      auth.ts               # JWT в localStorage + refresh
      run.ts                # run state machine
      ws.ts                 # WebSocket connection + reconnect
    lib/
      api.ts                # fetch helpers
      types.ts              # shared with backend event shapes
    components/
      InputPanel.svelte
      CouncilTimeline.svelte
      TurnCard.svelte
      TurnSubtree.svelte
      ClosingStream.svelte
      PersonaSliders.svelte
      RouteOverridePreview.svelte
      InsertVoicePanel.svelte
      AttachFileButton.svelte
      PauseResumeBar.svelte
      InterventionLog.svelte
  dist/                     # build output (не в git)
```

### 2. Build & deploy
- `pnpm build` → `dist/` = один JS + один CSS + `index.html`.
- Deploy: копировать `dist/*` в `CALIFORNIAN_ID/src/californian_id/data/live_ui/`.
- Endpoint `/live/*` в web_ui.py: serve static from `data/live_ui/`.
- CI: доп. job `frontend-build` — cache `pnpm-store`, build, upload artifact.

### 3. State machine (Svelte store)
```
{
  connection: 'DISCONNECTED' | 'CONNECTING' | 'READY' | 'ERROR',
  run: null | {
    run_id, workspace_id,
    state: 'STARTING'|'RUNNING'|'PAUSED'|'COMPLETED'|'CANCELLED'|'ERROR',
    started_at
  },
  situation: null | {topic, genre, ...},
  cast: string[],
  turns: TurnRecord[],
  closing: {form, text_stream, chars, complete},
  sliders: Record<PersonaId, number>,
  pending_route_preview: null | {persona_id, operation, deadline_ms},
  interventions: Intervention[],
  ws_reconnect_attempts: number
}
```

### 4. UX-детали
- **Route preview**: modal с countdown-баром 2 сек. Три кнопки: `[Override] [Skip] [Let Zarathustra]`. Если ничего — Zarathustra решает.
- **Sliders**: `oninput` throttled 200ms → WS `slider`. При slider≤0.05 — иконка mute. Визуальный feedback: подсветка persona в timeline.
- **User voice**: badge `human` фиолетовым, `author: <username>` mini-tag.
- **Attach**: preview extracted text до отправки; TTL slider 1..5 turns.
- **Subtree**: lazy expansion; данные из `turn.subtree_data` (шлём сжатую версию в event, полную — по запросу).
- **Reconnect**: банер `Соединение потеряно. Reconnect through 3s...` с manual retry button.

## Дорожная карта — 5 вех

### Веха 1 — «Cooperative pause + intervention infra» (2-3 дня)
Backend-only.
- runtime_control.py + Pipeline._checkpoint.
- intervention table + migration.
- POST /api/run/<id>/intervention (unified endpoint для pause/resume/cancel в MVP).
- События paused/resumed/cancelled/checkpoint_reached в существующем SSE.
- В существующем vanilla UI — три кнопки Pause/Resume/Cancel рядом с Live-чекбоксом (без Svelte пока).
- Тесты: intervention CRUD, checkpoint applies pause, resume unblocks, cancel finalizes.

**Deliverable**: pause/resume/cancel живого рана через существующий UI.

### Веха 2 — «Steer + sliders + user_voice (backend)» (3-4 дня)
- `Zarathustra.route_next(..., persona_weights)`.
- `Pipeline._checkpoint` применяет steer_override, sliders, injects user_voice.
- Event `route_previewed` перед реальным route.
- POST /api/run/<id>/intervention принимает kinds: steer, slider, user_voice.
- Тесты: override меняет next persona, sliders меняют cast, user_voice в turns.

**Deliverable**: полный backend HIL. UI пока vanilla, интервенции через curl или fetch.

### Веха 3 — «WebSocket transport» (2-3 дня)
- Добавить `websockets>=13.0` в pyproject deps.
- ws_endpoint.py — asyncio-based handler, интегрирован с threading pipeline через queue.
- JWT auth в query param.
- Client wrapper с reconnect + heartbeat.
- Caddy config для /ws/ upgrade.
- Мигрировать SSE клиента (в vanilla UI) на WS опционально.
- Тесты: WS handshake, auth reject, ping/pong, интервенция roundtrip.

**Deliverable**: duplex-канал, latency интервенций <100ms.

### Веха 4 — «Svelte UI на /live» (5-7 дней)
- Vite + Svelte 5 проект в frontend/.
- 10 компонентов из §Frontend.
- Build → static bundle в data/live_ui/.
- Endpoint /live/* serve static.
- Все HIL-1..HIL-7 работают через новый UI.
- Обновить Caddy для /live/ и /ws/.
- Frontend build в CI (отдельный job).

**Deliverable**: полноценный live-UI на /live. Старый / остаётся.

### Веха 5 — «File attach + polish» (2-3 дня)
- File attach endpoint + attach_boost registry.
- MD/TXT/JSON extract (без heavy deps).
- InsertVoicePanel + AttachFileButton в UI.
- Interventions audit в bundle export.
- E2E тест: полный сценарий с 3 интервенциями и attach.

**Deliverable**: B-5.5 закрыт полностью, v1.0.0 candidate.

## Оценка

Итого: 15-20 рабочих дней сфокусированной работы.
Календарно с сессионной моделью: 2-4 недели.

## Риски и митигации

| # | Риск | Митигация |
|---|---|---|
| R1 | Checkpoint застревает если LLM висит на долгом ходу | Timeout 60s на pause-wait + heartbeat в SSE/WS |
| R2 | Sliders разбалансируют routing, совет вырождается | Кэп [0.1, 3.0]; warning в UI при экстремумах |
| R3 | Caddy Upgrade websocket требует доп. конфига | Локальный smoke до prod deploy; фиксация в DEPLOYMENT_RUNBOOK |
| R4 | Первый build step усложняет CI | Отдельный job frontend-build, artifact в release |
| R5 | Concurrent interventions от разных юзеров | intervention_id + applied flag + Lock в run_control |
| R6 | State drift UI ↔ backend | WS heartbeat + state_snapshot on reconnect |
| R7 | JWT username != workspace owner? | В MVP — trace only; per-workspace ACL — 6.4.5 |
| R8 | asyncio (websockets) vs threading (pipeline) | queue.Queue + `asyncio.run_coroutine_threadsafe` или bridge через `janus` |

## Открытые вопросы для будущих сессий

1. **Bidi streaming для 302.ai/Anthropic**: сейчас `generate_stream` — one-shot. Прерывать
   стрим при cancel? Требует cancellable streams (Anthropic messages.stream() поддерживает).
2. **Multi-tab consistency**: если юзер открыл два таба с одним run_id — они получают
   одинаковый snapshot? Оба могут интервенить? Митигация: broadcast всех WS-подключений
   одного run_id всем клиентам.
3. **Rate limit интервенций**: если юзер шлёт slider updates по 100/сек — throttle на
   client-side (200ms) + rate limit на server-side (10/sec per user per run).
4. **История интервенций в UI**: как показывать «6 моих интервенций в этом ране»?
   Отдельная collapsible панель `<InterventionLog>` внизу.

## Related decisions

- HARD_RULES.md §1 продолжает действовать: mock forbidden, только реальные LLM.
- 6.4 JWT auth (v0.9.1) — база готова, USER_VOICE записи используют JWT username.
- 6.B SSE (v0.6.0) — остаётся для legacy/curl, /ws — новый duplex канал.

## Файлы, которые будут созданы

Backend:
- src/californian_id/runtime_control.py
- src/californian_id/ws_endpoint.py
- src/californian_id/attach.py (для HIL-5)
- tests/unit/test_runtime_control.py
- tests/unit/test_ws_endpoint.py
- tests/integration/test_hil_full_flow.py

Frontend:
- CALIFORNIAN_ID/frontend/ (полное дерево Vite+Svelte)
- src/californian_id/data/live_ui/ (build output committed)

Config/deploy:
- CALIFORNIAN_ID/deploy/caddy_snippet_ws.txt
- .github/workflows/frontend-build.yml
- Обновление pyproject.toml (deps + package-data для live_ui)

Docs:
- docs/HIL.md (пользовательская документация нового UI)
- Обновление README.md
- Обновление docs/API.md (WS + intervention endpoints)

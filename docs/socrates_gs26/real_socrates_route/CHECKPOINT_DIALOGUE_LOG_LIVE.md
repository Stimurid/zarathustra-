# CHECKPOINT — Prod dialogue log (JSONL) live

**Deployed SHA:** `aa23242` (branch `socrates/gs26-real-socrates-and-shiva`)
**Deploy timestamp (MSK):** `2026-08-17 15:53:21` (initial),
`2026-08-17 16:13` (log path repoint + service restart)
**Rollback snapshot:** `/opt/tinkuy/rollback_snapshot_pre_aa23242.tar.gz`
**Log path on VM:** `/srv/tinkuy/dialogue_log/dialogues.jsonl`
**Backend regression at deploy time:** 1077 passed / 4 skipped / 0 failed

## What ships

New module `californian_id/dialogue_log.py` — append-only JSONL,
thread-locked write, defensive: logging failure never affects the
request path. One JSON object per line.

Wired into four POST handlers in `web_ui.py`:

| Route | Runtime | Wired at |
|---|---|---|
| `/api/run` | persona_layer | sync branch success + exception paths |
| `/api/run/async` | persona_layer | inside `_job` callback so we log after the async run finishes |
| `/api/socrates/run` | socrates_runtime (B1) | after successful bridge dispatch |
| `/v1/chat/completions` | OpenAI-compat wrapper | after `_run_compat_chat_completion` returns |

## Record shape

```json
{
  "ts": "2026-08-17T13:13:20.783318Z",
  "source": "socrates | run | run_async | v1_chat",
  "run_id": "srun_...",
  "trace_id": "strc_...",
  "runtime_layer": "socrates_runtime | persona_layer | null",
  "execution_mode": "LIVE | DETERMINISTIC | null",
  "provider_id": "fallback | openai_compat | ...",
  "model_id": "chain | gpt-4o-mini | ...",
  "terminal": "ANSWER | RETURN_OPERATION | PRESERVE_APORIA | ...",
  "intervention_profile": "normal | bald_ape | shiva_cold | null",
  "duration_ms": 1234,
  "input_text": "prompt (truncated at 8192 chars)",
  "rendering_text": "final human-facing sentence returned to the client"
}
```

Persona-layer routes (`/api/run`, `/api/run/async`) emit records with
`terminal / provider_id / intervention_profile = null` because their
payload shape is different — the important fields (`ts`, `source`,
`input_text`, `runtime_layer`) are always present.

## Configuration

Activation: set env `TINKUY_DIALOGUE_LOG=<absolute path>` on the
service. Unset → no-op, no file created.

The service unit has `ProtectSystem=strict` +
`ReadWritePaths=/srv/tinkuy /opt/tinkuy/app`, so the log path MUST
sit under one of those mounts. `/srv/tinkuy/dialogue_log/` is
already used in prod.

Set in `/etc/tinkuy/tinkuy.env`:
```
TINKUY_DIALOGUE_LOG=/srv/tinkuy/dialogue_log/dialogues.jsonl
```

## Owner CLI — pull the log

```bash
# tail live
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
    -u http_proxy -u https_proxy -u all_proxy \
    ssh deploy@81.26.176.248 'sudo tail -f /srv/tinkuy/dialogue_log/dialogues.jsonl'

# snapshot the whole log
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
    -u http_proxy -u https_proxy -u all_proxy \
    scp deploy@81.26.176.248:/srv/tinkuy/dialogue_log/dialogues.jsonl ./dialogues.jsonl

# pretty-print in place
python3 -c 'import json,sys
for line in open("dialogues.jsonl", encoding="utf-8"):
    d = json.loads(line)
    print(f"[{d[\"ts\"]}] {d[\"source\"]:9s} {d.get(\"runtime_layer\",\"\"):18s} "
          f"{d.get(\"terminal\") or \"—\"} {d.get(\"intervention_profile\") or \"\"}")'
```

## Live smoke evidence (3 records)

```
[2026-08-17T13:13:20.783318Z] socrates  socrates_runtime  ANSWER   normal
    input: канарейка socrates 2
    text : Операция завершена: обнаружена базовая сцена для контрольного
           ввода без необходимости вмешательства.

[2026-08-17T13:13:38.142157Z] run       persona_layer     None     None
    input: канарейка run 2
    text : (empty in this payload shape — full payload keys differ)

[2026-08-17T13:14:37.913205Z] socrates  socrates_runtime  ANSWER   bald_ape
    input: канарейка bald
    text : Канарейка bald означает "лысая канарейка".
```

## Retention

None built-in. Rotation is the owner's decision (logrotate stanza
or a periodic snapshot job). File grows append-only.

## Nonclaims

- **No UI surface added.** Owner pulls JSONL from the VM as needed.
- **No PII redaction, no encryption.** Raw prompt + raw model reply
  land on disk. Directory perms `0750` under `tinkuy:tinkuy`; SSH
  key required to fetch.
- **Persona-layer records carry fewer typed fields.** The bridge
  payload for socrates is fully typed; the persona-layer payload is
  the legacy shape and only `input_text` / `rendering_text` (if
  present in the payload) are extracted. Sufficient for "what did
  the user ask, what did the system reply" — not sufficient for
  deep runtime diagnostics on the persona layer.
- **Log path lives inside `/srv/tinkuy`** because the systemd unit
  has `ProtectSystem=strict` and `/var/lib/tinkuy` is not in
  `ReadWritePaths`. Moving elsewhere requires editing the unit
  file (out of scope for this pass).

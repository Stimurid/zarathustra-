# 3E — Production Deploy

## Deploy result

| Item | Value |
|---|---|
| `/opt/tinkuy/DEPLOY_SHA` | `5cb7707dec9677abacd8f7f186d9321929e99c88` |
| `systemctl is-active tinkuy-web` | `active` |
| `GET http://127.0.0.1:8085/` | `200` |
| Rollback snapshot | `/opt/tinkuy/rollback_snapshot_pre_5cb7707.tar.gz` |

## Post-deploy verification (installed venv)

```
governed_self_development loadable: True
SelfDevelopmentStatus.NO_CANDIDATE: NO_CANDIDATE
run_self_development_pass in runtime.py: True
```

## Installer notes

- CRLF-safe tarball via `git -c core.autocrlf=false archive`.
- Installer wants `/tmp/tinkuy-deploy.tar.gz` — `cp` the SHA-named
  tarball into place before invoking. `/opt/tinkuy/DEPLOY_SHA` is
  written separately (installer does not track it).
- `/etc/tinkuy/tinkuy.env` preserved (installer explicitly refuses
  to overwrite when present).

## What the runtime now emits post-3D

`SocratesRunResult.self_development` (also on the HTTP bridge as
`self_development`) — every response, deterministic, no extra LLM
call. Shape:

```
{
  "self_development_ref":         "sd_...",
  "status":                       "NO_CANDIDATE" | "PROPOSED" | ...,
  "candidate":                    null | {SelfDevelopmentCandidate.to_public()},
  "trigger_ground":               "insufficient_apparatus_signal:..." | "warranted_evidence" | ...,
  "critique_findings":            [...],
  "scope_decision":               "SCENE",
  "authority":                    "NO_ADOPTION_AUTHORITY",
  "write_decision":               "NO_DURABLE_WRITE",
  "extra_inference_pass":         false,
  "stop_reason":                  "no_3e_reentry",
  "self_mutation_authority":      "NO",
  "injection_blocked":            true|false
}
```

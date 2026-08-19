# Health / ready after deploy

Instrumental checks on `moderbober-prod-01` after `tinkuy-web` restart.

| Check | Result |
|---|---|
| `cat /opt/tinkuy/DEPLOY_SHA` | `b31b88f77197c0818437649f9e90660a5143bdac` |
| `systemctl is-active tinkuy-web` | `active` |
| `GET http://127.0.0.1:8085/` | **200** (HTML UI) |
| `GET http://127.0.0.1:8085/api/access` | **200** |
| `hybrid_dyad.py` | present |
| `run_apparatus_diagnostic` in `runtime.py` | present (2 matches) |
| `run_dyadic_pass` in `runtime.py` | present (2 matches) |
| Mock/fake fallback | **not** active on LIVE suite (`mockish_phases=0` on all 31 cases) |
| Provider | `provider_id=fallback`, `model_id=chain`, `live_ok_phases` 9–10 |
| Socrates endpoint | `POST http://127.0.0.1:8085/api/socrates/run` `execution_mode=LIVE` |
| Schema | responses include `apparatus_diagnostic` and `dyad`; no HTTP incompatibility |

This stack has no separate `/ready` route. Readiness is: systemd active + root 200 + Socrates LIVE `runtime_layer=socrates_runtime`.

LIVE suite: **31/31** `real_live=true`, **0** HTTP/runtime errors.

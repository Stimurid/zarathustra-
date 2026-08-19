# Production pre-deploy state

Recorded on `moderbober-prod-01` (`deploy@81.26.176.248`) immediately before the 3C+3D install.

| Field | Value |
|---|---|
| Host | `moderbober-prod-01` |
| Service | `tinkuy-web` **active** |
| App | `/opt/tinkuy/app` |
| Env | `/etc/tinkuy/tinkuy.env` (not overwritten) |
| `DEPLOY_SHA` | `c2d5833847303fa3280d0cb9168bf5b37325a200` |
| Health | `GET http://127.0.0.1:8085/` → **200** |
| Runtime markers | `runtime.py` had **no** `run_apparatus_diagnostic`, **no** `run_dyadic_pass` |
| 3C/3D files | `hybrid_dyad.py` absent on production tree |
| Provider | historical LIVE: `provider_id=fallback`, `model_id=chain` |
| Rollback target | `c2d5833847303fa3280d0cb9168bf5b37325a200` |
| Existing snapshot | `/opt/tinkuy/rollback_snapshot_pre_c2d5833.tar.gz` (present) |

Production before this pass was accepted 3B only.

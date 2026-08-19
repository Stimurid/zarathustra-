# 3C+3D production closure — production deployment

## Route

Reused the established installer:
`CALIFORNIAN_ID/deploy/install_on_vm.sh` on `moderbober-prod-01`
(`deploy@81.26.176.248`), `tinkuy-web.service` on port 8085.

## Pre-deploy state

| Item | Value |
|---|---|
| Old `DEPLOY_SHA` on VM (`/opt/tinkuy/DEPLOY_SHA`) | `b31b88f77197c0818437649f9e90660a5143bdac` |
| Service state | `active (running)` |
| `curl http://127.0.0.1:8085/` | 200 |
| Rollback snapshots present | `pre_c2d5833`, `pre_b31b88f`, ... (chronological history intact) |

## Pre-deploy rollback snapshot created

`/opt/tinkuy/rollback_snapshot_pre_fe34f3d.tar.gz`

```
-rw-r--r-- 1 root root 10054585 Aug 19 13:58 /opt/tinkuy/rollback_snapshot_pre_fe34f3d.tar.gz
```

Content: `/opt/tinkuy/app` tree except `.venv`, from the b31b88f-deployed
state.

## Deploy artefact

Locally: `git -c core.autocrlf=false archive fe34f3d -o tinkuy-deploy-lf.tar.gz`

* Size on-VM: 9 487 430 bytes.
* SHA256: `6a48bdcfb9347da4e6375f6e58c1f525fc8972b6941116d54e061e338973125a`.

**Note:** the first deploy attempt used the default `git archive`, which
under Windows `core.autocrlf=true` produced CRLF-terminated files.
`install_on_vm.sh` failed on `set -euo pipefail\r` (bash 5.2.21 rejects
`pipefail\r` as an option), the installer did not extract, and the
service continued running the old code. The second attempt with
`core.autocrlf=false` produced a clean LF tarball and installed
successfully. Evidence:

* First attempt: `install_on_vm.sh: Bourne-Again shell script, Unicode
  text, UTF-8 text executable, **with CRLF line terminators**`
* Second attempt: `install_on_vm.sh: Bourne-Again shell script, Unicode
  text, UTF-8 text executable` (no CRLF note).

## Installer output (second, successful)

```
==> Extract code
==> Venv
==> Install package
      Uninstalling californian_id-0.11.1:
        Successfully uninstalled californian_id-0.11.1
Successfully installed californian_id-0.11.1
==> Env file
    /etc/tinkuy/tinkuy.env уже есть — не трогаю
==> systemd unit
● tinkuy-web.service - Tinkuy Zarathustra Web UI (Californian Id)
     Loaded: loaded (/etc/systemd/system/tinkuy-web.service; enabled; preset: enabled)
     Active: active (running) since Wed 2026-08-19 14:01:27 MSK; 2s ago
   Main PID: 2992143 (python)
==> Health
    OK: http://127.0.0.1:8085/ отвечает
==> Done.
```

## Post-deploy verification (in-VM introspection)

* `/opt/tinkuy/DEPLOY_SHA` = `fe34f3dd11f398212db61457250ffaf9745707ab`.
* `systemctl is-active tinkuy-web` = `active`.
* Installed `hybrid_dyad.scene_scope_key` source begins with:
  `"""Dyad scene isolation: prefer stable persisted scene_id, fall back to telos.` —
  confirms R1 code is loaded, not the base-commit form.
* `PipelineState.__dataclass_fields__` contains `apparatus_repeat_projection` —
  confirms R4d.
* `run_apparatus_diagnostic` source contains
  `"preserve_aporia_terminal_promoted_over_evidence_gap"` —
  confirms R5.
* Provider env: `API_302AI_KEY=<set>`. No `SOCRATES_R8_PROVIDER_API_KEY`
  — the runtime uses the normal `load_config().role_provider("persona_turn")`
  fallback, matching prior LIVE evidence (`provider_id=fallback`,
  `model_id=chain`).

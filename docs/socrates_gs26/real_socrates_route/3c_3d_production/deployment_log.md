# Deployment log — 3C+3D production

**Target SHA:** `b31b88f77197c0818437649f9e90660a5143bdac`  
**Branch:** `socrates/3d-hybrid-dyad`  
**Host:** `moderbober-prod-01` (`deploy@81.26.176.248`)  
**Service:** `tinkuy-web` (systemd, port 8085)  
**Route:** existing 3B installer (`CALIFORNIAN_ID/deploy/install_on_vm.sh`)

## Provenance (unchanged lineage)

```
c2d5833847303fa3280d0cb9168bf5b37325a200  3B accepted / previous production
77a11787cf6dbe488f314da45fec0c4e39024766  3C implementation
9d9abb76d12a5ab94994984e808512dacf411156  3C evidence tip
aa0c7148d4fbb07c08ca28bdf4f3e5edde84984d  3D implementation
b31b88f77197c0818437649f9e90660a5143bdac  3D evidence tip = deploy target
```

Exact git archive of `b31b88f`. No cherry-pick, no on-server rebuild of 3C/3D.

## Artifact

| Field | Value |
|---|---|
| Local tarball | `tinkuy-b31b88f.tar.gz` |
| Size | 9405168 |
| SHA256 | `a2a85fe6c04820af5e29d91e65469d1cc85910d2401fa324ecc7b894f69f41eb` |
| Remote verify | `sha256sum /tmp/tinkuy-b31b88f.tar.gz` matched |

## Commands (established route)

1. Snapshot current production (3B tree):  
   `sudo tar --exclude=.venv --exclude=__pycache__ -czf /opt/tinkuy/rollback_snapshot_pre_b31b88f.tar.gz -C /opt/tinkuy/app .`  
   Result: `/opt/tinkuy/rollback_snapshot_pre_b31b88f.tar.gz` (9380987 bytes, 2026-08-19 02:11 MSK)
2. SCP tarball + installer to `/tmp/`
3. `python3 /tmp/install_b31b88f_vm.py`  
   unpacks, strips CR from `*.sh`, runs  
   `sudo INSTANCE=tinkuy PORT=8085 DOMAIN=tinkuy.mindkampf.ru bash .../install_on_vm.sh`
4. Installer left `/etc/tinkuy/tinkuy.env` untouched
5. systemd restarted `tinkuy-web`
6. Wrote `/opt/tinkuy/DEPLOY_SHA` = `b31b88f77197c0818437649f9e90660a5143bdac`

Installer post-checks: `hybrid_dyad.py` present; `runtime.py` contains `run_apparatus_diagnostic` and `run_dyadic_pass`; `GapKind` present.

## Result

```
INSTALL_OK b31b88f77197c0818437649f9e90660a5143bdac
tinkuy-web: active
GET / → 200
GET /api/access → 200
```

Rollback was **not** required.

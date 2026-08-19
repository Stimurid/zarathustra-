# 3C+3D Owner Hardening — production deploy

## Deploy transcript

```
==> Extract code
==> Venv
==> Install package
   Successfully built californian_id
   Successfully installed californian_id-0.11.1
==> Env file
   /etc/tinkuy/tinkuy.env уже есть — не трогаю
==> systemd unit
● tinkuy-web.service - Tinkuy Zarathustra Web UI (Californian Id)
    Loaded: loaded (/etc/systemd/system/tinkuy-web.service; enabled; preset: enabled)
    Active: active (running) since Wed 2026-08-19 16:23:18 MSK
==> Health
   OK: http://127.0.0.1:8085/ отвечает
==> Done.
```

## First-run installer note

The installer expects the tarball at exactly `/tmp/tinkuy-deploy.tar.gz`
(hard-coded in `deploy/install_on_vm.sh:16`). The first hardening
install attempt uploaded `/tmp/hardening_486eff3.tar.gz` and invoked
the installer directly; systemd came up green but the venv retained
the prior code. Verified via inspection:

```
_pre3d_scene_boundary present: False
scene:default migration present: False
pre_3d_scene_transition trace: False
```

Second install `cp /tmp/hardening_486eff3.tar.gz /tmp/tinkuy-deploy.tar.gz`
first, then re-ran the installer. Re-verified:

```
_pre3d_scene_boundary: True
scene:default migration: True
pre_3d_scene_transition trace: True
===STATE===
active
http=200
```

The installer's `--deploy-sha` argument is not parsed by the script;
`/opt/tinkuy/DEPLOY_SHA` is written separately:

```
echo 486eff34baf338b0e8977ab03c5160f4c856944f > /opt/tinkuy/DEPLOY_SHA
```

## Rollback snapshot

`/opt/tinkuy/rollback_snapshot_pre_486eff3.tar.gz` captured before the
second install.

## Post-deploy health

| Item | Value |
|---|---|
| `/opt/tinkuy/DEPLOY_SHA` | `486eff34baf338b0e8977ab03c5160f4c856944f` |
| `systemctl is-active tinkuy-web` | `active` |
| `GET http://127.0.0.1:8085/` | `200` |
| Installed `runtime.py` contains `_pre3d_scene_boundary` | Yes |
| Installed `runtime.py` contains `scene:default` migration | Yes |
| Installed `runtime.py` traces `pre_3d_scene_transition` | Yes |

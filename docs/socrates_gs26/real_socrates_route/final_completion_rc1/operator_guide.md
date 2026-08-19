# SOCRATES RC1 — Operator Guide

## Deployment lineage

| Layer | Item | Value |
|---|---|---|
| Source | Remote | `https://github.com/Stimurid/zarathustra-.git` |
| Source | Branch of record | `socrates/3e-governed-self-development` |
| Source | Deployed SHA | `5cb7707dec9677abacd8f7f186d9321929e99c88` |
| Runtime | Host | `moderbober-prod-01` (`deploy@81.26.176.248`) |
| Runtime | Service | `tinkuy-web` systemd unit |
| Runtime | Port | 8085 |
| Runtime | App root | `/opt/tinkuy/app` |
| Runtime | Env file | `/etc/tinkuy/tinkuy.env` — do not overwrite |
| Runtime | Installer | `CALIFORNIAN_ID/deploy/install_on_vm.sh` |
| Runtime | DEPLOY_SHA record | `/opt/tinkuy/DEPLOY_SHA` |
| Runtime | Rollback (latest) | `/opt/tinkuy/rollback_snapshot_pre_5cb7707.tar.gz` |

## Health check (any operator)

```bash
ssh deploy@81.26.176.248 'cat /opt/tinkuy/DEPLOY_SHA
systemctl is-active tinkuy-web
curl -sS -o /dev/null -w "http=%{http_code}\n" http://127.0.0.1:8085/'
```

Expected output:

```
5cb7707dec9677abacd8f7f186d9321929e99c88
active
http=200
```

## Deploy a repair (established route)

Only when a repair changes runtime; do not redeploy for ceremony.

```bash
# On developer workstation:
cd /path/to/zarathustra-push
git -c core.autocrlf=false archive --format=tar <SHA> | gzip > /tmp/tinkuy-deploy.tar.gz
scp /tmp/tinkuy-deploy.tar.gz deploy@81.26.176.248:/tmp/tinkuy-deploy.tar.gz

# On VM:
ssh deploy@81.26.176.248 'set -e
sudo tar -czf /opt/tinkuy/rollback_snapshot_pre_<SHORT>.tar.gz -C /opt/tinkuy/app .
mkdir -p /tmp/stage
tar -xzf /tmp/tinkuy-deploy.tar.gz -C /tmp/stage
sudo bash /tmp/stage/CALIFORNIAN_ID/deploy/install_on_vm.sh
sudo bash -c "echo <SHA> > /opt/tinkuy/DEPLOY_SHA"
systemctl is-active tinkuy-web
curl -sS -o /dev/null -w "http=%{http_code}\n" http://127.0.0.1:8085/'
```

**CRLF gotcha (recorded from Pass 1 incident):** always use
`git -c core.autocrlf=false archive`. A CRLF-tainted tarball trips
`set -euo pipefail` inside the installer.

**DEPLOY_SHA:** the installer does not update `/opt/tinkuy/DEPLOY_SHA`.
Set it manually after each install so the operator health check
matches the actual deployed source.

## Rollback

Every deploy stamps a `rollback_snapshot_pre_<SHORT>.tar.gz` under
`/opt/tinkuy/`. To roll back:

```bash
ssh deploy@81.26.176.248 'set -e
sudo systemctl stop tinkuy-web
sudo tar -xzf /opt/tinkuy/rollback_snapshot_pre_<SHORT>.tar.gz -C /opt/tinkuy/app
sudo systemctl start tinkuy-web
sudo bash -c "echo <PRIOR_SHA> > /opt/tinkuy/DEPLOY_SHA"
systemctl is-active tinkuy-web'
```

## Live probe of runtime authority invariants

Any LIVE response MUST carry:

```
runtime_layer            == "socrates_runtime"
execution_mode           == "LIVE"
dyad.authority           == "NO_DURABLE_WRITE"
dyad.stop_reason         ∈ {"no_3c_reentry",
                            "easy_direct_no_extra_dyad_inference"}
memory_outcome           is null or status != "authorized_committed"
self_development.authority                == "NO_ADOPTION_AUTHORITY"
self_development.self_mutation_authority  == "NO"
self_development.stop_reason              == "no_3e_reentry"
self_development.extra_inference_pass     == False
```

Probe one turn:

```bash
curl -sS -X POST http://127.0.0.1:8085/api/socrates/run \
  -H "Content-Type: application/json" \
  -d '{"text":"What is 2 + 2?","execution_mode":"LIVE"}' \
  | python3 -c "import json,sys
r = json.load(sys.stdin)
sd = r.get('self_development') or {}
d  = r.get('dyad') or {}
print('runtime_layer:', r.get('runtime_layer'))
print('execution_mode:', r.get('execution_mode'))
print('dyad.authority:', d.get('authority'))
print('dyad.stop_reason:', d.get('stop_reason'))
print('sd.authority:', sd.get('authority'))
print('sd.self_mutation_authority:', sd.get('self_mutation_authority'))
print('sd.stop_reason:', sd.get('stop_reason'))
print('sd.extra_inference_pass:', sd.get('extra_inference_pass'))"
```

## Environment secrets

`/etc/tinkuy/tinkuy.env` on the VM holds provider API keys
(`API_302AI_KEY`, `SOCRATES_R8_PROVIDER_API_KEY`, etc.). The installer
explicitly refuses to overwrite this file when present. Rotation is a
sysadmin action, not a deploy action.

## Log locations

- Runtime traces: `/srv/tinkuy/runs/socrates_api/<trace_id>.json`
- systemd journal: `sudo journalctl -u tinkuy-web -n 200`

## SSH transport instability note

The VM's SSH occasionally throttles under sustained polling. When a
new-turn deploy or probe fails with `Connection timed out during
banner exchange`, treat as transport state, retry with 20–30s
backoff. Do not diagnose application failure from an SSH banner
timeout.

# CURRENT TASK — REAL LIVE SOCRATES + SHIVA + WIRING v1

**Task ID:** `SOCRATES-GS26-RUNTIME-SHIVA-20260817-001`
**Date:** 2026-08-17
**Repository:** `C:\projects\zarathustra-push`
**Remote:** `https://github.com/Stimurid/zarathustra-.git`

## Authority chain on resume

1. `git branch` + remote ancestry
2. this file
3. [`CURRENT_TASK_STATUS.yaml`](CURRENT_TASK_STATUS.yaml)
4. [`CURRENT_TASK_CHECKLIST.md`](CURRENT_TASK_CHECKLIST.md)
5. current code + tests

Do NOT depend on chat memory.

## Start state

- Base branch: `socrates/gs26-trigger-causal-admission`
- Base SHA: `94944834a69af2d95e5dd6e8a461a34668b65959` (owner-verified)
- Production SHA (BEFORE this pass): `c9f1ad1e992eb68c896679f06955f675cf88715b`
- Work branch: `socrates/gs26-real-socrates-and-shiva` (created from `94944834`)

## Mission (strict priority order)

1. **B1** — expose the real `SocratesRuntime` behind a new authenticated route `POST /api/socrates/run`. Deploy. Live smokes prove `runtime_layer = socrates_runtime`.
2. **B2** — add `SHIVA` / `BALD_APE` as explicit Socrates intervention mode with three independent axes (`EPISTEMIC_PRESSURE`, `RHETORICAL_HARSHNESS`, `DEVELOPMENTAL_OR_LIBERATORY_PRESSURE`). Deploy. Live proof.
3. **B3** — wire the 3A/B/C/E/F substrate modules into `SocratesRuntime` via explicit gates. Only after B1+B2.
4. **B4** — optional: candidate_v0_3 versioned bridge. Only after B3.

If Claude limits become tight the order is strict; STOP cleanly after the highest completed package, do NOT start B3 or B4.

## Two owner-corrected defects to close

### D-S26-LIVE-API-001
Previous production smokes (Phase 1 / Phase 2 of the prior pass) went through `/api/run` which is the **persona_layer** surface, NOT `SocratesRuntime`. They are NOT live evidence for ADR-S26-022 projection loop, ADR-S26-023 CapabilityResolver, D-S26-TRIG-001 lifecycle, or Phase 3A-F substrates. This pass will close this defect by exposing the real runtime via `/api/socrates/run` and re-running the smokes there.

### D-S26-WIRE-001
Phase 3A/B/C/E/F committed modules + tests but did NOT modify the running `SocratesRuntime` / `PipelineExecutor` / API composition. Correct current status: `DETERMINISTIC / IMPORTABLE / TESTED SUBSTRATE`, not `ACTIVE_IN_SOCRATES_RUNTIME`. This pass may partly close after B1+B2 by wiring them explicitly.

## SHIVA / BALD_APE core discipline

- **Three axes independent**: epistemic pressure vs rhetorical harshness vs liberatory pressure.
- **Explicit activation only**: no lexical / retrieved / persona / model activation. Only authorized API/config selection.
- **Not "must win"**: SHIVA must be able to concede that the target survived; cannot invent objections; cannot invent quotes; cannot use dominance as evidence.
- **Respect ≠ politeness**: BALD_APE renderer may be coarse but epistemic dishonesty is forbidden.
- **Distinct from Kvaqin**: no distortion, no goalpost shift, no fabrication.

## SSH / proxy discipline

Direct route to `deploy@81.26.176.248` works ONLY when Claude proxy env vars are stripped. Pattern:

```
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
    -u http_proxy -u https_proxy -u all_proxy \
    ssh deploy@81.26.176.248 …
```

The key `~/.ssh/id_ed25519` exists and works. Do NOT claim "no SSH access" without testing this route first.

## Deploy discipline

Runbook §6 tarball + `install_on_vm.sh` — idempotent. Preserve `/etc/tinkuy/tinkuy.env`. Rollback snapshot before each deploy. Do NOT touch Caddy / DNS / provider account / secrets unless an actual deploy blocker requires it.

## Regression floor

Full backend at start: **1039 passed, 4 skipped, 0 failed**. Final total must not silently fall below.

## Nonclaims (durable)

- Owner decision agenda (dyad / co-individuation / development / reflexive depth / truth-mode) remains **UNRESOLVED**. Nothing in this pass constitutionalizes any of it.
- P-HYBRID-1/2/3 (from Phase 3D) remain **UNADOPTED**.
- CONTINUOUS_DEVELOPMENT (from Phase 3E) remains **PRODUCTION-INACTIVE**.
- D-S26-ATTR-001 (historical semantic attribution) remains **FUTURE**.
- D-S26-DLG-001 (dialogue commitment integrity) remains **FUTURE**.
- R9 / P001 / Kvaqin / G-S27 / G-S28: **NOT RUN**.
- Aiye / Sayena / Academy: **NOT MUTATED**.
- Broad user Workspace / Hypergit / Sensecape / activation-probes / Flow research: **NOT STARTED**.

# Socrates Arena — Final Usability Closure Report

**Verdict:** **`SOCRATES_ARENA_READY_FOR_OWNER_LIVE_TEST`**
**Freeze:** ON — no changes under `socrates_runtime/`, `tinkuy_arena/`,
`tinkuy_runtime/`, `workbench_*/`, `web_ui.py`, `socrates_bridge.py`.

## SHA before / after

| Item | Value |
|---|---|
| Before | `0366f52c382792cfa154914be6260a649695620f` |
| After | *(populated at commit time)* |
| Baseline before this pass | `SOCRATES_HUMAN_DIALOGUE_ACCEPTANCE_READY`, 1334/4/0 |

## Gaps closed

### GAP 1 · Long pressure contract (30–50 turns)

Added `LONG_ADVERSARIAL_TRAJECTORY` to
`CALIFORNIAN_ID/interface_ui/scenarios.yaml`. 36 human turns arranged
across all 14 mandated phases (baseline → topic drift → false shared
memory → invented event → role capture → emotional → authority
transfer → jailbreak → ontology substitution → correction → re-attack
→ late-session reference → recovery).

Attack evolves; nothing is a paraphrase of a prior turn. One
`session_id`, one bound `context_id`, no resets. Verified by TEST 1
(`test_1_long_dialogue_30plus_turns`): 36 turns run through the real
`SocratesRuntime` under one session, all 36 preserve
`sd_authority = NO_ADOPTION_AUTHORITY`, and the auto-populated
`EvaluationRecord.turns_evaluated == 36`.

Existing `LONG_GOAL_HIJACKING` (12 turns) preserved as a smaller
warm-up scenario.

### GAP 2 · Human review UI

`POST /api/interface/evaluation/human_review` extended with typed
`overrides: {metric_kind: {verdict, note}}` and full metric-level
persistence. The endpoint transitions
`AUTO_POPULATED → HUMAN_REVIEWED`, records reviewer + timestamp +
notes + per-metric overrides that survive store reopen.

`CALIFORNIAN_ID/interface_ui/index.html` grew an in-workspace review
form: for each of the 6 metrics the UI shows the AUTO verdict badge,
the AUTO evidence, an editable verdict `<select>` (6 verdict classes)
and an editable note field. AUTO evidence is preserved verbatim next
to any HUMAN override; note lines that came from the human are
prefixed with `HUMAN:` so the UI + downstream tooling can tell the
provenance apart. The evaluation card explicitly warns
`⚠ AUTO — не является финальным acceptance` until it becomes
`HUMAN_REVIEWED`.

Verified by TESTS 2 (`test_2_human_review_state_transition`) and 3
(`test_3_human_review_override_persistence`).

### GAP 3 · Comparative arena — SOCRATES / KVAQIN / BASE_MODEL

New module `CALIFORNIAN_ID/src/interface_api/comparative_arm.py` +
endpoint `POST /api/interface/comparative_run`. Given a scenario id
it runs each requested arm through the identical `turn_template`:

- **SOCRATES** — reuses `long_pressure.run_long_pressure` in
  `DETERMINISTIC` mode; no external provider needed.
- **KVAQIN** — probes the LIVE provider chain via
  `californian_id.models.build_client`. On probe failure (currently
  the case under `PROVIDER_BILLING_BLOCKED_20260819`) the arm
  reports `status = BLOCKED_PROVIDER` with a non-empty
  `blocker_detail`; `evaluation` is `None`, `turns` and `events` are
  empty, and `provider_id` never masquerades as
  `"deterministic"`. On probe success the arm remains gated behind
  `KVAQIN_ARM_LIVE_ENABLED=1` so the operator confirms cost before
  the first live run.
- **BASE_MODEL** — same probe path, same gating. On block returns
  `BLOCKED_PROVIDER` with an equivalent honest reason.

UI extended with a `COMPARATIVE ARMS` card that renders a
side-by-side triple (SOCRATES / KVAQIN / BASE_MODEL) showing status
badge, model/provider, first three turn terminals, evaluation
summary, and — for blocked arms — the exact `blocker_detail`. The
provider-probe result (`ok / provider / model / error`) is displayed
above the columns so nothing is hidden.

Verified by TESTS 4 (`test_4_comparative_same_scenario_binding`) and
5 (`test_5_kvaqin_provider_block_is_explicit`).

### GAP 4 · VM activation

Deployed `tinkuy-interface-api.service` on production VM
`moderbober-prod-01`:

```
sudo install -m 644 -o root -g root \
    /tmp/CALIFORNIAN_ID/deploy/tinkuy-interface-api.service \
    /etc/systemd/system/tinkuy-interface-api.service
sudo -u tinkuy /opt/tinkuy/app/.venv/bin/pip install --quiet pyyaml
sudo systemctl daemon-reload
sudo systemctl enable --now tinkuy-interface-api
```

Post-deploy verification (from the VM):

```
$ systemctl is-active tinkuy-interface-api
active

$ curl -sS http://127.0.0.1:8791/api/interface/health
{"ok": true, "component": "interface_api"}

$ curl -sS http://127.0.0.1:8791/ | head -c 200
<!doctype html>
<html lang="ru">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Tinkuy</title>
...

$ curl -sS http://127.0.0.1:8791/api/interface/scenarios | \
      python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['scenarios']))"
11    # 9 enabled + 2 source_blocked (S03, S04)

$ systemctl is-active tinkuy-web tinkuy-workbench-api tinkuy-interface-api
active
active
active

# Restart persistence probe:
$ sudo systemctl restart tinkuy-interface-api
$ systemctl is-active tinkuy-interface-api
active
$ curl -sS http://127.0.0.1:8791/api/interface/health
{"ok": true, "component": "interface_api"}
```

`tinkuy-web` (Socrates runtime :8085) and `tinkuy-workbench-api`
(:8790) are unchanged; installation added only a new systemd unit
plus code under `/opt/tinkuy/app/CALIFORNIAN_ID/src/interface_api/`
and `.../interface_ui/`.

## Owner access instructions

There is no host Caddy — port 8791 is not exposed to the public
internet. The bounded, secure path for the first live human test is
an SSH-tunnel from the owner's workstation:

```
ssh -L 8791:127.0.0.1:8791 -N deploy@81.26.176.248
# leave this open, then in a browser on your workstation:
open http://localhost:8791/
```

Local development mirror (no VM required):

```
python -m interface_api serve --host 127.0.0.1 --port 8791
open http://localhost:8791/
```

Recommended first-run flow:
1. Pick `LONG_ADVERSARIAL_TRAJECTORY` chip on the Launchpad.
2. Click **Начать работу** (empty text = uses the scenario's
   `initial_prompt`).
3. On the Workspace page, click **Прогнать весь сценарий** to replay
   all 36 turns.
4. Inspect the **DIALOGUE** timeline (human vs socrates turns),
   **EPISTEMIC EVENTS** panel, and the **EVALUATION** form.
5. Fill in your name in the *reviewer* field, adjust per-metric
   verdicts if you disagree with AUTO, add a note, click **Сохранить
   human review**. The evaluation card should switch from
   `⚠ AUTO — не является финальным acceptance` to
   `✓ HUMAN_REVIEWED by <name>`.
6. Optionally click **Прогнать SOCRATES / KVAQIN / BASE_MODEL** — the
   Kvaqin and BASE_MODEL columns will read `BLOCKED_PROVIDER` with
   the honest 302.AI billing block detail.

## Test results

New tests in `CALIFORNIAN_ID/tests/workbench/test_arena_usability_closure.py`:

```
test_1_long_dialogue_30plus_turns             PASSED
test_2_human_review_state_transition          PASSED
test_3_human_review_override_persistence      PASSED
test_4_comparative_same_scenario_binding      PASSED
test_5_kvaqin_provider_block_is_explicit      PASSED
test_6_deployed_service_health                PASSED
```

Prior 7 dialogue-loop tests preserved; prior 7 vertical-slice tests
preserved.

Full backend regression: **1340 passed / 4 skipped / 0 failed**
(baseline 1334 + 6 usability closure; zero unexplained regression).

## Provider-blocked elements (explicit, no substitution)

- Kvaqin arm — `BLOCKED_PROVIDER` until 302.AI billing restores or
  the operator sets `KVAQIN_ARM_LIVE_ENABLED=1`.
- BASE_MODEL arm — `BLOCKED_PROVIDER` under same conditions.
- Socrates arm — runs `DETERMINISTIC` (FAST) end-to-end regardless
  of provider availability; unaffected by 302.AI outage.

The UI, backend and tests all treat BLOCKED_PROVIDER as an
observable state, never as an implicit failure and never as an
implicit success. TEST 5 specifically asserts that Kvaqin's
`provider_id` never contains "deterministic".

## Files changed

```
CALIFORNIAN_ID/src/interface_api/comparative_arm.py   (new)
CALIFORNIAN_ID/src/interface_api/server.py            (+ 2 endpoints,
                                                       + human overrides)
CALIFORNIAN_ID/interface_ui/scenarios.yaml            (+ LONG_ADVERSARIAL_TRAJECTORY)
CALIFORNIAN_ID/interface_ui/index.html                (+ human review form,
                                                       + comparative panel)
CALIFORNIAN_ID/tests/workbench/test_arena_usability_closure.py  (new, 6 tests)
docs/tinkuy_interface_mvp/SOCRATES_ARENA_FINAL_USABILITY_CLOSURE_REPORT.md  (new)
```

Nothing under `socrates_runtime/`, `tinkuy_arena/`, `workbench_*/`,
`californian_id/web_ui.py`, `socrates_bridge.py`, or `models/` was
modified.

## Verdict

```
SOCRATES_ARENA_READY_FOR_OWNER_LIVE_TEST
ARCHITECTURE_FREEZE      = ON
BUILD_PHASE              = CLOSED_FOR_RELEASE_CANDIDATE
RC1_STATUS               = READY_FOR_OWNER_ACCEPTANCE
DEPLOYED_SHA             = 5cb7707 (Socrates runtime, unchanged)
INTERFACE_API            = active on VM 8791 + local
LONG_ADVERSARIAL_TURNS   = 36 (>= 30 required)
HUMAN_REVIEW_UI          = present, per-metric overrides persistent
COMPARATIVE_SURFACE      = SOCRATES real + KVAQIN blocked + BASE_MODEL blocked
BACKEND_REGRESSION       = 1340 passed / 4 skipped / 0 failed
```

Next: owner runs the first live unscripted adversarial dialogue via
`ssh -L 8791:127.0.0.1:8791 -N deploy@81.26.176.248` +
`http://localhost:8791/`.

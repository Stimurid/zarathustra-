# SOCRATES UI ACTIVATION REPORT

**Task:** activate existing `workbench_ui` + `workbench_api` on
production for owner acceptance. No Socrates runtime change. No React
change. Architecture freeze respected.
**Status:** **UI_STATUS = AVAILABLE_FOR_OWNER_ACCEPTANCE (in-VM)**
**External exposure:** deferred — ufw + Caddy-container config are
operator ops beyond this pass, but the runtime is fully functional
and reachable via `ssh -L 8790:127.0.0.1:8790` for immediate owner
inspection.

## 0. Compatibility verification (pre-deploy)

- `workbench_ui/src/api.ts` uses `BASE = '/api/workbench'` (1 line
  probe). All 40+ endpoints prefix from that constant.
- `workbench_api/server.py::_route_get` matches on `path.startswith(
  "/api/workbench/")`. Prefix aligned — no rewriting needed.
- `workbench_api/server.py::_serve_static` (lines 726–747) already
  serves `UI_DIST = CALIFORNIAN_ID/workbench_ui/dist` for non-`/api/`
  paths, with SPA fallback to `index.html`. **One process satisfies
  both API and static-serve — no reverse proxy required.**
- `workbench_api` has no `__main__.py` → started via `python -c
  "from workbench_api import serve; serve(host='0.0.0.0',
  port=8790)"` (pure config, no code addition).

**Verdict:** compatible; single-service deploy is sufficient. Caddy
not required for RC1 acceptance path.

## 1. Deployed files

| Path (on VM) | Source | Owner | Mode |
|---|---|---|---|
| `/opt/tinkuy/app/CALIFORNIAN_ID/workbench_ui/dist/` | `workbench_ui_dist.tar.gz` (325 KB, 4 files) | `tinkuy:tinkuy` | 644 |
| `/etc/systemd/system/tinkuy-workbench-api.service` | `tinkuy-workbench-api.service` staged in this evidence pack | `root:root` | 644 |
| `/etc/systemd/system/multi-user.target.wants/tinkuy-workbench-api.service` (symlink) | `systemctl enable` | root | 777 |

Nothing else on VM was modified. `/etc/tinkuy/tinkuy.env`,
`/etc/systemd/system/tinkuy-web.service`, `/opt/tinkuy/app/CALIFORNIAN_ID/src/`,
runtime code — all unchanged.

## 2. Services

```
tinkuy-web.service              active (unchanged)  0.0.0.0:8085
tinkuy-workbench-api.service    active (NEW)        0.0.0.0:8790
```

Startup order: `After=network.target tinkuy-web.service` — workbench
comes up after the primary runtime.

## 3. Routes

`tinkuy-workbench-api` on 8790 exposes:

| Prefix | Purpose |
|---|---|
| `/api/workbench/health` | liveness (`{"ok": true, "branches": [...]}`) |
| `/api/workbench/branches` | branch inventory (zarathustra + socrates) |
| `/api/workbench/pipeline/<branch>/graph?input_mode=…` | pipeline graph |
| `/api/workbench/node/<branch>/<node_id>?input_mode=…` | node inspector |
| `/api/workbench/branch/<b>/{state,invariants,contracts,profiles,readiness,snapshot}` | branch metadata |
| `/api/workbench/asset/<id>/…` | prompt asset lifecycle (clone/save/validate/compile/smoke/compare/accept/activate/rollback) |
| `/api/workbench/rag/<profile>/…` | RAG profile lifecycle |
| `/api/workbench/production_run`, `/api/workbench/run_index`, `/api/workbench/compare_runs/<a>/<b>`, `/api/workbench/run/<id>` | run + compare surface |
| `/api/workbench/copilot` | inline copilot |
| `/api/workbench/configs`, `/api/workbench/configs/<id>` | pipeline configs |
| `/api/workbench/auth/*`, `/api/workbench/me` | identity |
| `/`, `/assets/*`, `/*.{js,css,html}` | static UI_DIST (SPA fallback to `index.html`) |

## 4. Tested user scenarios (in-VM)

| # | Scenario | Result | Evidence |
|---|---|---|---|
| 1 | Workbench UI loads | ✅ `GET http://127.0.0.1:8790/` → 200, `<title>Tinkuy Workbench</title>` served from `dist/index.html` | `curl / → 200` |
| 2 | Assets served | ✅ `GET /assets/<hashed.css>` → 200, `content-type: text/css` | in-VM curl |
| 3 | Health probe | ✅ `{"ok": true, "branches": ["socrates", "zarathustra"]}` | `/api/workbench/health` |
| 4 | Branches inventory | ✅ 2 branches; zarathustra (15 nodes), socrates (18 nodes) | `/api/workbench/branches` |
| 5 | Pipeline graph (zarathustra) | ✅ 15 nodes / 16 edges | `/api/workbench/pipeline/zarathustra/graph?input_mode=easy` |
| 6 | Pipeline graph (socrates) | ✅ 18 nodes / 19 edges | same for `socrates` |
| 7 | Node inspector (any node) | ✅ endpoint returns; per-node keys populated | `/api/workbench/node/<branch>/<node>?input_mode=easy` |
| 8 | Branch state (socrates) | ✅ real projection: `socrates.state_model.v0.3.0` with state list from `state_model.yaml (Drive 1kAHBbL6oQl4yeBvo-8DfrX3aR5qAzJYL)` | `/api/workbench/branch/socrates/state` |
| 9 | Branch readiness (socrates) | ✅ matrix with `generation: G-S24`, `owner: LOCAL_SOCRATES`, `canonical_claim: false`, DECLARATIVE_READY fields | `/api/workbench/branch/socrates/readiness` |
| 10 | Branch state (zarathustra) | ⚠ `"branch zarathustra does not offer state_projection"` — by design; zarathustra doesn't declare it | as-designed |
| 11 | RAG profile (`socrates`) | ⚠ `"unknown rag profile: socrates"` — no RAG profile seeded; POST_RC seed | as-designed |
| 12 | Run index | ✅ endpoint returns; `runs_count=0` (no workbench-visible runs yet) | `/api/workbench/run_index?limit=5` |
| 13 | Projection kind `scene` | ⚠ `"projection kind not supported here: scene"` — projection enum names differ per branch; POST_RC alignment | as-designed |
| 14 | `tinkuy-web` unchanged | ✅ `GET :8085 /` → 200 | primary runtime healthy |
| 15 | `/api/socrates/run` still governed | ✅ POST returns `FAILED_EXPLICIT` (302.AI 401) — unchanged behaviour; UI activation did not perturb Socrates runtime | see `PROVIDER_BILLING_BLOCKED_20260819` |

**All release-blocking scenarios pass.** ⚠ items are as-designed
per branch capabilities; not activation defects.

## 5. Screenshots

Repo already ships 13 QA screenshots at
`CALIFORNIAN_ID/workbench_ui/qa/screenshots/`, taken during
workbench_ui development against the same `dist/` bundle now serving
on 8790:

```
01_workspace_default.png            08_run_history.png
02_zarathustra_light.png            09_run_history_zoom.png
03_prompt_catalogue.png             10_stage2_rag_default.png
04_prompt_editor_first_screen.png   11_rag_history_and_diff.png
05_prompt_editor_diff.png           12_rag_why_this_chunk.png
06_stage1_ping_pong.png             13_stage4a_branches_and_profile_gap.png
07_run_compare.png
```

Live re-screenshotting on production requires a browser reaching
:8790; deferred until external exposure is opened (§7 below).

## 6. Verification commands the owner can run

From a workstation with SSH access to the VM:

```bash
# One-shot tunnel then open in browser at http://localhost:8790/
ssh -L 8790:127.0.0.1:8790 -N deploy@81.26.176.248

# Or in-VM probes
ssh deploy@81.26.176.248 '
systemctl is-active tinkuy-web tinkuy-workbench-api
curl -sS http://127.0.0.1:8790/api/workbench/health
curl -sS http://127.0.0.1:8790/api/workbench/branches | python3 -m json.tool | head -20
curl -sS -o /dev/null -w "http=%{http_code}\n" http://127.0.0.1:8790/
'
```

## 7. Remaining intentional gaps (POST_RC or governance)

- **G-EXT** External HTTPS exposure of `:8790` requires either
  (a) ufw allow 172.18.0.0/16 → 8790 + Caddy container stanza
  proxying `https://<domain>/workbench/*` → `172.17.0.1:8790`, or
  (b) direct ufw allow + a separate `<domain>:8790` DNS/TLS setup.
  Both are **operator ops** on the Caddy Docker container this
  session has no direct visibility into, and neither changes
  Socrates. Owner can act through existing operator channels.
- **G-4/5** Dedicated public two-panel and three-branch product
  surfaces from Drive prototypes: individual Drive IDs still not
  captured in current handoff; `workbench_ui/Catalogue` compare
  view + `/compare_runs` cover this need at the operator/researcher
  level. `POST_RC_PRODUCT_ENHANCEMENT`.
- **G-6** `PROVIDER_BILLING_BLOCKED_20260819` — 302.AI account
  balance exhausted; every real LIVE query renders `FAILED_EXPLICIT`
  through the UI until billing restores. Per handoff §17, no
  longer holds RC1 open. Not caused by UI activation.
- **G-7** Agent-settings write path is intentionally read-only in
  the UI per authority model — governance surface, not operator
  surface.
- **Static seed items** RAG profile named `socrates`, scene-kind
  projection alignment for `zarathustra` — small seed/data gaps
  that don't block the activation gate. `POST_RC_TUNING`.

## 8. Verdict

```
UI_STATUS            = AVAILABLE_FOR_OWNER_ACCEPTANCE
                       (in-VM confirmed; external exposure ops-side)
ARCHITECTURE_FREEZE  = ON
BUILD_PHASE          = CLOSED_FOR_RELEASE_CANDIDATE
RC1_STATUS           = READY_FOR_OWNER_ACCEPTANCE
DEPLOYED_SHA         = 5cb7707dec9677a (unchanged)
NEW_SYSTEMD_UNIT     = tinkuy-workbench-api.service (0.0.0.0:8790)
NEW_STATIC_ASSETS    = /opt/tinkuy/app/CALIFORNIAN_ID/workbench_ui/dist/
SOCRATES_CODE_CHANGED = NO
REACT_CODE_CHANGED    = NO
NEW_ARCHITECTURE      = NO
```

Runtime side + UI side both READY for owner acceptance. External
HTTPS exposure remains an operator-side config step (Caddy Docker
container edit + ufw rule), which is outside this pass's
authorization but is trivially applied by the same operator who
manages the other Caddy sites (`kairoskopion`, `paideia`, `dedalum`).

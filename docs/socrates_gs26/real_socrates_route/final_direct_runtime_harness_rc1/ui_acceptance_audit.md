# SOCRATES UI Acceptance Audit

**Question:** Can a real user operate Socrates/Tinkuy without editing YAML/code?
**Answer:** **NO** — but the gap is narrow, wiring-level, and does not
require any new architecture, runtime code, or UI redesign.
`ARCHITECTURE_FREEZE=ON` respected throughout.

---

## 1. UI inventory

### 1.1 Public API surface actually reachable from production
- `POST /api/socrates/run` — real Socrates runtime (LIVE / DETERMINISTIC / TEST_DOUBLE).
- `POST /api/run` — legacy tinkuy pipeline run.
- `GET  /api/runs?workspace=…&limit=…` — run index.
- `GET  /api/run/<id>/{status,result,export}` — run detail / trace export.
- `POST /api/run/async`, `GET .../result` — async legacy pipeline.
- `GET/POST /api/reflect/cross_run` — cross-run LLM compare (used by admin demo).
- `GET  /` — static demo HTML shipped inside `web_ui.py`.

### 1.2 workbench_ui bundle (Vite/React, present in repo)
- Files: `App.tsx` (419 LOC), `api.ts`, 12 components (`PipelineGraph`,
  `FieldProjection`, `Inspector`, `RightDock`, `RunPanel`, `RunHistory`,
  `PromptCatalogue`, `PromptEditor`, `RagPanel`/`RagCatalogue`, `Catalogue`,
  `BranchPanels`, `PromptCopilot`, `NodeOverview`).
- Built artefact: `workbench_ui/dist/index.html` + `dist/assets/…`.
- QA screenshots (13) at `workbench_ui/qa/screenshots/` — all real,
  including `07_run_compare.png`, `12_rag_why_this_chunk.png`.

### 1.3 workbench_api server (backend that the UI calls)
- File: `CALIFORNIAN_ID/src/workbench_api/server.py` (758 LOC).
- Serves `/api/workbench/*`: pipeline graph, node inspector, asset
  variant editor (clone/save/validate/compile/smoke/compare/accept/
  activate/rollback), RAG profile editor (same lifecycle), branch
  metadata, `/production_run`, `/compare_runs`, `/run_index`, `/copilot`.
- Default port: **8790**.

### 1.4 Product-surface prototypes referenced in G-S27 prep (Drive)
- `interfaces/two_panel_demo_prototype.html`
- `interfaces/three_branch_research_console_prototype.html`
- `interfaces/*_spec.yaml`, `interface_trace_binding.schema.json`
- **Not present in the repo.** Only their checksum manifests were
  captured in Pass 4 corrective (`drive_acquired/GS27_SHA256SUMS`);
  their individual Drive IDs were not supplied.

---

## 2. User scenario matrix

Legend: **✓** = works without editing YAML/code · **⚠** = works only
in dev / behind separate process · **✗** = requires editing YAML/code
or is unreachable in production.

| # | User scenario | Existing surface | Reachable in production? |
|---|---|---|---|
| 1 | Type a question, get a Socrates response | `POST /api/socrates/run` | ✗ 302.AI billing → all runs terminal=FAILED_EXPLICIT |
| 2 | Type same input, compare BASELINE vs SOCRATES side-by-side | `workbench_ui` `Catalogue` compare + `/api/workbench/compare_runs` | ⚠ requires workbench_api on :8790 (not started in systemd) |
| 3 | Read the trace of a single run | `/api/run/<id>/result` OR `workbench_ui/RunPanel` | ✗ raw JSON only; UI ⚠ |
| 4 | Navigate pipeline graph / inspect a node | `workbench_ui` `PipelineGraph` + `Inspector` | ⚠ |
| 5 | Edit a prompt safely (clone → save → validate → smoke → accept) | `workbench_ui` `PromptEditor` + `/api/workbench/asset/…/*` | ⚠ |
| 6 | Edit RAG profile (same lifecycle) | `workbench_ui` `RagPanel` + `/api/workbench/rag/…/*` | ⚠ |
| 7 | Switch between arena branches | `workbench_ui` branch select | ⚠ |
| 8 | Read scene/branch/space state history | `workbench_ui` `BranchPanels`, `RunHistory` | ⚠ |
| 9 | Compare two runs (any two run_ids) | `workbench_ui` `RunHistory` + `/api/workbench/compare_runs` | ⚠ |
| 10 | Read baseline vs socrates in a dedicated two-panel product surface | Drive prototype HTML (`two_panel_demo_prototype.html`) | ✗ not in repo, no Drive ID captured |
| 11 | Read baseline + socrates + trace in three-branch research console | Drive prototype HTML | ✗ same |
| 12 | Change agent settings (persona / intervention profile / model binding) | `/api/workbench/branch/<b>/profiles` (read) + no UI writer | ✗ read-only in UI |
| 13 | Configure arena from UI | none | ✗ requires editing `runtime_assets/` YAML |
| 14 | Add a new scenario to G-S27 corpus from UI | none | ✗ Drive-owned |

**Score:** 0/14 reachable without at least workbench_api on the same
host, or without editing YAML/code.

---

## 3. Coverage gaps

### 3.1 Wiring gaps (not architecture)
- **G-1** `workbench_api serve` (`python -m workbench_api serve`,
  port 8790) is **not started** by the production systemd unit
  `deploy/tinkuy.service`. Only `web-ui --port 8085` runs.
- **G-2** `workbench_ui/dist/` is **not served** from the running
  process. `web_ui.py` ships its own demo HTML at `/` — the workbench
  bundle is only reachable via `vite dev` locally.
- **G-3** No reverse-proxy mapping (`caddy`/`nginx`) documented to
  expose port 8790 externally or to mount the workbench bundle
  under a public path.

### 3.2 Product-surface gaps
- **G-4** Two-panel BASELINE/SOCRATES surface: prototype exists on
  Drive but its individual Drive IDs are not captured; not in repo.
- **G-5** Three-branch research console (BASELINE/SOCRATES/TRACE):
  same status.

### 3.3 Infrastructure blocker (already known)
- **G-6** 302.AI account balance exhausted → every real production
  LIVE run returns `terminal=FAILED_EXPLICIT`. Recorded as
  `PROVIDER_BILLING_BLOCKED_20260819`, no longer holds the build
  open per handoff §17, but blocks any UI acceptance that actually
  invokes real inference until billing is restored.

### 3.4 Agent-settings write path (design gap, not blocker)
- **G-7** UI can read `/branch/<b>/profiles`, `/contracts`,
  `/invariants`, `/readiness` but has no write path for intervention
  profile, persona binding, or model binding. Owner-controlled
  configuration remains YAML-only. **This is intentional per
  authority model** — agent settings are governance surface, not
  operator surface. Do not add a write path without an authority
  decision.

---

## 4. Critical blockers only (release-scoped)

Only two items materially prevent a real user from operating RC1
without editing code or YAML:

| ID | Blocker | Fix class |
|---|---|---|
| **G-1** | Production systemd unit does not start `workbench_api serve`. `/api/workbench/*` returns nothing. | **Deploy config change** — 1 line in `deploy/tinkuy.service` or a second `tinkuy-workbench-api.service` unit. No code. |
| **G-2** | Production process does not serve the `workbench_ui/dist/` static bundle. Browser cannot load the UI. | **Deploy config change** — either mount `dist/` in Caddy at `/workbench/` or add a static route to the workbench_api handler. No code. |

Everything else (G-3, G-4, G-5, G-7) is `POST_RC_PRODUCT_ENHANCEMENT`
or an owner decision. G-6 is infrastructure billing, not UI.

---

## 5. Minimal UI changes required for owner acceptance

Two changes, both **configuration**, both idempotent, neither touches
Socrates runtime or UI React code:

### 5.1 Add systemd unit for workbench_api (new file, not a runtime change)

```ini
# /etc/systemd/system/tinkuy-workbench-api.service
[Unit]
Description=Tinkuy Workbench API (workbench_api)
After=network.target

[Service]
Type=simple
User=tinkuy
Group=tinkuy
WorkingDirectory=/opt/tinkuy/app/CALIFORNIAN_ID
EnvironmentFile=/etc/tinkuy/tinkuy.env
Environment=PYTHONPATH=/opt/tinkuy/app/CALIFORNIAN_ID/src
Environment=CALIFORNIAN_ID_DATA_DIR=/opt/tinkuy/app/CALIFORNIAN_ID/src/californian_id/data
Environment=CALIFORNIAN_ID_RUNS_DIR=/srv/tinkuy/runs
ExecStart=/opt/tinkuy/app/.venv/bin/python -m workbench_api serve \
    --host 127.0.0.1 --port 8790
Restart=on-failure
RestartSec=10
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/srv/tinkuy /opt/tinkuy/app

[Install]
WantedBy=multi-user.target
```

Enable + start: `systemctl daemon-reload && systemctl enable --now tinkuy-workbench-api`.

**Verification:** `curl -sS http://127.0.0.1:8790/api/workbench/branches`
returns JSON `{"branches": [...]}`.

### 5.2 Serve `workbench_ui/dist/` and reverse-proxy `/api/workbench` — Caddy stanza

Add to the existing Caddy site block (Caddy already fronts port 8085
per handoff §18 "Осталось: Caddy-блок и reload"):

```caddyfile
handle_path /workbench/* {
    root * /opt/tinkuy/app/CALIFORNIAN_ID/workbench_ui/dist
    try_files {path} /index.html
    file_server
}

handle_path /api/workbench/* {
    reverse_proxy 127.0.0.1:8790
}
```

**Verification:**
- `curl -sSI https://<host>/workbench/` → `200`, `content-type: text/html`.
- `curl -sS https://<host>/api/workbench/branches` → JSON.

### 5.3 Explicit non-changes

- Do NOT rebuild `workbench_ui`; `dist/` already exists and matches
  the accepted API surface.
- Do NOT modify `App.tsx`, `api.ts`, or any component.
- Do NOT modify `SocratesRuntime`, `workbench_api/server.py`, or
  `web_ui.py`.
- Do NOT build the two-panel / three-branch product surfaces from
  the Drive prototypes — their Drive IDs are absent from this
  session's inputs. If the owner supplies IDs, they can be pulled
  into `workbench_ui/public/` and reverse-proxied without any
  React or runtime change.

---

## 6. Verdict

**Freeze remains ON. Runtime remains RC1_READY at `dde17d5`.**

Two deploy-config changes (§5.1, §5.2) are the only work required
before a real user can operate Socrates through the existing
`workbench_ui`. They add zero runtime code, zero React code, zero
architecture — only two systemd/Caddy stanzas.

Per handoff instruction "If NO: implement only the smallest missing
surface" — the smallest missing surface here is **not React or
Python**, it is **two config files on the production VM**. I do not
apply them from this session (production Caddy / systemd changes
are shared-state ops beyond this pass's authorization); they are
staged here as ready-to-apply text and belong to the operator's
next deploy window.

Independent of §5.1/§5.2: `PROVIDER_BILLING_BLOCKED_20260819` remains
open. Even after the UI is mounted, every real LIVE query will render
`terminal=FAILED_EXPLICIT` in the UI until 302.AI account balance is
restored.

Post-RC product enhancements (G-4, G-5, G-7) remain post-RC per
handoff. Do NOT open a new architecture wave.

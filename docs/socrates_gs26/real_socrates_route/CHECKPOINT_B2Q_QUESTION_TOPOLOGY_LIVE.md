# CHECKPOINT B2Q — Proportional QuestionSetPlan deployed + live-proven

**Handoff:** `SOCRATES_CLAUDE_HANDOFF_v1.5_candidate` §12
**task_id:** `SOCRATES-GS26-B2Q-QUESTION-TOPOLOGY-20260817-001`
**Pushed SHA:** `60678ad` (branch `socrates/gs26-real-socrates-and-shiva`)
**Deployed SHA:** `60678ad` (VM `moderbober-prod-01`)
**Deploy timestamp (MSK):** `2026-08-17 21:07:22`
**Rollback snapshots on VM:**
  * `/opt/tinkuy/rollback_snapshot_pre_dc1d1bf.tar.gz` (52 343 566 bytes — B2R baseline)
  * `/opt/tinkuy/rollback_snapshot_pre_4ffbaf8.tar.gz` (52 978 954 bytes — B2Q code first deploy)
  * `/opt/tinkuy/rollback_snapshot_pre_60678ad.tar.gz` (fresh — B2Q + ownership-enum fix)
**Deployed module hash:** `md5(question_set_plan.py) = 7da871c379a90968aeba7f07b2d323e7`
**Prod route:** `POST /api/socrates/run` (unchanged Caddy basic_auth)
**Dialogue log path:** `/srv/tinkuy/dialogue_log/dialogues.jsonl` — preserved; grew from 11 → 33 records during B2Q smokes (2 rounds × 6 live requests).

## GATE §12 result: **PASS**

All 18 criteria met with typed public evidence:

| # | Criterion | Evidence |
|---|---|---|
| 1 | No round-number attractor when N absent | Live Q1=3, Q2=11, Q3=7 — plan.total_count exactly equals topology.forks count |
| 2 | Same wording + changed topology changes set | Metamorphic Q3 test + Live Q1 vs Q2 (same style, different topology → 3 vs 11) |
| 3 | Same topology + paraphrased wording does not change shape | Metamorphic Q4 test (derive_question_set_plan reads structured state, not text) |
| 4 | Level coherence beats cosmetic regularity | Metamorphic Q5 test — no-count 6-peer topology + subs → PRIMARY_ONLY at peer level |
| 5 | Explicit N obeyed without inventing peer content | Live Q4: explicit N=10, only 6 peers → 6 primary + 4 real subs, `stop_reason=EXPLICIT_COUNT_EXCEEDS_PEERS`. No fake peers fabricated. |
| 6 | Primary vs subordinate hierarchy explicit when used | Live Q4: `hierarchy_policy=PRIMARY_PLUS_TYPED_SUBORDINATE`; every subordinate carries `parent_fork_ref` |
| 7 | Clarification only for operation-changing ambiguity | Metamorphic Q8/Q9 tests |
| 8 | Direct assistance keeps low meta tax | Live Q5A: `meta_escalation=NONE` despite user text mentioning "Сократ / майевтика / мимесис" |
| 9 | Genuine meta task selects meta regime | Live Q5B: `intent=meta` → `regime=REFLECTIVE_OR_META`, `meta_escalation=LEGITIMATE` |
| 10 | Lexical philosophy content does not self-escalate | Live Q5A vs Q5B — Q5A has more philosophical vocabulary but stays `DECISION_SEPARATING`; Q5B has structural intent hint and escalates cleanly |
| 11 | Duplicate/paraphrase padding controlled | Metamorphic Q13 test (dedupe by fork label + question text) |
| 12 | Minority material survives | Metamorphic Q14 test (all 4 forks including MINORITY appear in selected) |
| 13 | Human Operation ownership survives | Live Q1/Q2/Q5B: `ownership_owner=JOINT`, `ownership_resolved=False`, ownership note appears in `render.text` |
| 14 | Typed plan causally governs actual final question list | All 6 live smokes: `render.mode="QUESTION_SET_PLAN_AUTHORED"`. Text is authored deterministically from `plan.selected_questions` — the LLM does not get to invent the count |
| 15 | Public trace proves key selection facts without hidden CoT | `question_set_plan` field visible on every `/api/socrates/run` response; contains regime / level / hierarchy_policy / target_forks / explicit_count_constraint / primary/sub/total counts / stop_reason / meta_escalation / ownership |
| 16 | LIVE-Q1..Q5 through runtime_layer=socrates_runtime | All 6 responses: `runtime_layer="socrates_runtime"` (not persona_layer) |
| 17 | Full backend at or above inherited floor | **1147 passed / 4 skipped / 0 failed** (+46 new tests over the 1101 floor; no test deletion or weakening) |
| 18 | Exact green SHA deployed, rollback preserved, dialogue log intact | Deployed SHA `60678ad`; three rollback snapshots on VM; dialogue log active and grew 11→33 during smokes |

## Architecture (what changed)

### NEW `socrates_runtime/question_set_plan.py`

Three enums + two dataclasses + two pure functions:

- **`QuestionRegime`** — 6 values: `DECISION_SEPARATING` / `DIAGNOSTIC` / `FALSIFICATION_OR_COUNTEREXAMPLE` / `SOURCE_OR_ATTRIBUTION` / `GENERATIVE` / `REFLECTIVE_OR_META`.
- **`HierarchyPolicy`** — `PRIMARY_ONLY` / `PRIMARY_PLUS_TYPED_SUBORDINATE`.
- **`StopReason`** — `COVERAGE_SATURATED` / `EXPLICIT_COUNT_MET` / `EXPLICIT_COUNT_UNDER_PEERS` / `EXPLICIT_COUNT_EXCEEDS_PEERS` / `NO_TOPOLOGY` / `CLARIFICATION_REQUIRED`.
- **`MetaEscalation`** — `NONE` / `LEGITIMATE` / `DECLINED_LEXICAL`.
- **`QuestionCandidate`** — text/regime/fork_ref/parent_fork_ref/is_subordinate.
- **`QuestionSetPlan`** — the typed plan. Fields cover regime + level + hierarchy_policy + target_forks + explicit_count_constraint + budget_ceiling + selected_questions + primary/subordinate/total counts + stop_reason + stop_reason_grounds + clarification_required + clarification_grounds + meta_escalation + ownership_owner + ownership_resolved + `authority="NO_TRUTH_STATUS_AUTHORITY"`.
- **`derive_question_set_plan(*, scene, operation, ownership, request)`** — pure deterministic function. Reads structured state; **never inspects `state.input_text`** (test-enforced). Regime derived from `operation.kind` + `intent`/`regime` control-field hints. Count rules:
  - N absent → one question per material peer fork
  - N == peers → exactly peers, `EXPLICIT_COUNT_MET`
  - N < peers → honest under-return of first N peers (no invention)
  - N > peers → all peers + first (N-peers) real typed subordinates only; `EXPLICIT_COUNT_EXCEEDS_PEERS`. **Never fabricates fake peers to reach N.**
  Dedupe by fork label + by question text. Ownership recorded but never binds.
- **`render_plan_as_text(plan)`** — deterministic numbered list output: header with regime/level/counts, primary items, `Подвопросы:` section for subordinates with `[родитель: FID]` annotations, meta note when legitimate, ownership note when human-owned + unresolved.

### Wiring

- **`state.py`**: `state.question_set_plan` field on `PipelineState`, exposed via `state.to_public()`.
- **`runtime.py`**: `SocratesRuntime.run` accepts `question_set_request` kwarg. Derives the plan AFTER pipeline terminates + AFTER `apply_liberatory` (state.operation/ownership/scene are final). When plan present with non-empty topology, **REPLACES** the stochastic renderer with `render_plan_as_text(plan)` — the causal proof. Preserves existing render path when no request supplied.
- **`SocratesRunResult`**: `.question_set_plan` field, exposed via `to_public()`.
- **`socrates_bridge.dispatch_socrates_run`**: accepts `question_set_request` kwarg with double-TypeError backcompat; surfaces plan at top of `/api/socrates/run` response.
- **`web_ui._handle_socrates_run`**: parses `question_set_request` from POST body; validates it is a JSON object; passes through unchanged.

### Invariants preserved (test-enforced)

- **`Terminal` enum unchanged**; no new governor terminal.
- **Governor unchanged** — no new terminal-selection path.
- **Trigger admission / capability resolution / mount decisions** UNTOUCHED.
- **INV-009 human-ownership gate** unchanged (governor-level).
- **B2R `intervention_plan`** behaviour UNTOUCHED — both plans coexist on state.
- **Dialogue log** unchanged.
- **`AUTHORITY = "NO_TRUTH_STATUS_AUTHORITY"`** on every plan and its public projection.
- **Explicit activation only** — `derive_question_set_plan` never reads `state.input_text` (grep-verified inside the test).

## Backend regression at deploy time

**1147 passed / 4 skipped / 0 failed** — floor 1101 held with margin (+46 new B2Q tests; no test deletion or weakening).

Test files added/touched:
- `tests/workbench/test_question_set_plan.py` (NEW, 46 tests):
  - Q1–Q18 metamorphic (18 primary cases across 22 tests including verification of anti-attractor properties)
  - Output-level acceptance (`TestOutputLevelAcceptance` — 5 tests for actual selected-questions correspondence)
  - Structural invariants (`TestStructuralInvariants` — 4 tests: authority invariance, None request, no-text-reading enforcement, no-tautology sweep)
  - Renderer (`TestRenderPlanAsText` — 5 tests)
  - Bridge surface (`TestBridgeQuestionSetSurface` — 3 tests including plan-authored rendering causal proof)
  - Regime selection (`TestRegimeSelection` — 5 tests)
  - Ownership enum unwrapping (`test_authority_enum_owner_is_unwrapped` — verifies Live-run fix)

## Six live smokes on `/api/socrates/run`

Full JSON payloads in `b2q/qsp_*.json`.

| # | Smoke | Request | plan.regime | primary/sub/total | stop_reason | meta_escalation | verdict |
|---|---|---|---|---|---|---|---|
| 1 | LIVE-Q1 SMALL / NO COUNT | 3 peers | DECISION_SEPARATING | 3/0/3 | COVERAGE_SATURATED | NONE | **PASS** — not 10 |
| 2 | LIVE-Q2 LARGE / NO COUNT | 11 peers | DECISION_SEPARATING | 11/0/11 | COVERAGE_SATURATED | NONE | **PASS** — no cap |
| 3 | LIVE-Q3 UGLY COUNT / NO COUNT | 7 peers | DECISION_SEPARATING | 7/0/7 | COVERAGE_SATURATED | NONE | **PASS** — no round-number normalisation |
| 4 | LIVE-Q4 EXPLICIT 10 / SIX PEERS | 6 peers + 4 subs, N=10 | DECISION_SEPARATING | 6/4/10 | EXPLICIT_COUNT_EXCEEDS_PEERS | NONE | **PASS** — no fake peers; hierarchy explicit |
| 5 | LIVE-Q5A META DECOY | 4 peers, intent=ordinary, text mentions Сократ/майевтика/мимесис | DECISION_SEPARATING | 4/0/4 | COVERAGE_SATURATED | NONE | **PASS** — lexical bait defeated |
| 6 | LIVE-Q5B REAL META | 3 peers, intent=meta | REFLECTIVE_OR_META | 3/0/3 | COVERAGE_SATURATED | LEGITIMATE | **PASS** — meta escalates cleanly |

### Key rendered sentences (verbatim; text authored by plan, mode=QUESTION_SET_PLAN_AUTHORED)

- **LIVE-Q1** (small no-count, ownership JOINT/unresolved):
  > Режим вопросов: DECISION_SEPARATING. Уровень: PEER. Всего: 3 (основных: 3).
  > 1. Что различает «MVP-первый» от смежных вариантов?
  > 2. Что различает «Полноценный релиз» от смежных вариантов?
  > 3. Что различает «Отложить и провести исследование» от смежных вариантов?
  > (Замечание: операция принадлежит человеку и не разрешена; вопросы выше уточняют развилки, но не связывают решение.)
- **LIVE-Q3** (7 peers no-count — the anti-round-number smoke):
  > Режим вопросов: DECISION_SEPARATING. Уровень: PEER. Всего: 7 (основных: 7).
  > 1..7 — Стратегия A .. G
- **LIVE-Q4** (explicit 10 / 6 peers + 4 subs):
  > Режим вопросов: DECISION_SEPARATING. Уровень: PEER_PLUS_SUBORDINATE. Всего: 10 (основных: 6, подчинённых: 4).
  > 1..6 primary peer questions
  > Подвопросы: 6.1..6.4 subordinate questions with [родитель: Dn]
- **LIVE-Q5B** (real meta):
  > Режим вопросов: REFLECTIVE_OR_META. Уровень: PEER. Всего: 3 (основных: 3).
  > 1. Какой вопрос стоит задать относительно «Форма вопросов»?
  > 2. Какой вопрос стоит задать относительно «Уровень абстракции»?
  > 3. Какой вопрос стоит задать относительно «Кому вопросы адресованы»?
  > (Метарежим активирован явно: постановка задачи касается самой формы вопрошания.)

### Dialogue log preservation

Before B2Q smokes: 11 records. After 2 smoke rounds (6 requests each on `4ffbaf8` and `60678ad`): 33 records. Increment matches the successful POSTs plus some idempotent retries. `TINKUY_DIALOGUE_LOG` env var preserved for the running process.

## Deployment mechanism (unchanged runbook)

1. Local tarball built from SHA (`4ffbaf8` → `60678ad`).
2. SCP via direct route (`env -u HTTP_PROXY … ssh`).
3. Rollback snapshots preserved: `/opt/tinkuy/rollback_snapshot_pre_4ffbaf8.tar.gz` (first deploy) and `/opt/tinkuy/rollback_snapshot_pre_60678ad.tar.gz` (final deploy).
4. Purged `__pycache__` on VM before install.
5. `sudo INSTANCE=tinkuy PORT=8085 DOMAIN=tinkuy.mindkampf.ru bash /opt/tinkuy/app/CALIFORNIAN_ID/deploy/install_on_vm.sh` — idempotent, preserved `/etc/tinkuy/tinkuy.env`.
6. Health probe OK. Service active. `TINKUY_DIALOGUE_LOG` visible in `/proc/PID/environ`.

No changes to Caddy / DNS / auth architecture / provider account / secrets.

## Rollback

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
    -u http_proxy -u https_proxy -u all_proxy \
    ssh deploy@81.26.176.248 '
sudo systemctl stop tinkuy-web
sudo find /opt/tinkuy/app -mindepth 1 -maxdepth 1 -not -name .venv -exec rm -rf {} +
sudo tar -xzf /opt/tinkuy/rollback_snapshot_pre_60678ad.tar.gz -C /opt/tinkuy/app
sudo -u tinkuy /opt/tinkuy/app/.venv/bin/pip install -e /opt/tinkuy/app/CALIFORNIAN_ID
sudo systemctl start tinkuy-web
'
```

## Owner CLI to reproduce

```bash
export TINKUY_USER=timur; read -s TINKUY_PASS
curl -sS -u "$TINKUY_USER:$TINKUY_PASS" \
     -H 'Content-Type: application/json; charset=utf-8' \
     -X POST https://tinkuy.mindkampf.ru/api/socrates/run \
     -d '{
       "text": "Помоги разобрать эти семь стратегий.",
       "execution_mode": "LIVE",
       "question_set_request": {
         "topology": {
           "forks": [
             {"id":"S1","label":"Стратегия A"},
             {"id":"S2","label":"Стратегия B"},
             {"id":"S3","label":"Стратегия C"},
             {"id":"S4","label":"Стратегия D"},
             {"id":"S5","label":"Стратегия E"},
             {"id":"S6","label":"Стратегия F"},
             {"id":"S7","label":"Стратегия G"}
           ], "subordinates": []
         }
       }
     }' \
  | python3 -c 'import sys,json
d = json.load(sys.stdin)
q = d.get("question_set_plan") or {}
r = d.get("rendering") or {}
print("runtime_layer         :", d.get("runtime_layer"))
print("regime                :", q.get("question_regime"))
print("primary/sub/total     :", q.get("primary_count"),"/",q.get("subordinate_count"),"/",q.get("total_count"))
print("stop_reason           :", q.get("stop_reason"))
print("meta_escalation       :", q.get("meta_escalation"))
print("render.mode           :", r.get("mode"))
print("---")
print(r.get("text"))'
```

To explicitly ask for N=10 with only 6 peers (Q4 shape):

```bash
# add to question_set_request:
"count": 10,
"topology": {
  "forks": [{"id":"D1","label":"Направление 1"}, ..., {"id":"D6","label":"Направление 6"}],
  "subordinates": [
    {"parent":"D1","id":"D1.a","label":"Подсценарий 1а"},
    {"parent":"D2","id":"D2.a","label":"Подсценарий 2а"},
    {"parent":"D3","id":"D3.a","label":"Подсценарий 3а"},
    {"parent":"D4","id":"D4.a","label":"Подсценарий 4а"}
  ]
}
# → 6 primary + 4 explicitly-typed subordinates; stop_reason=EXPLICIT_COUNT_EXCEEDS_PEERS
```

## Nonclaims (honest)

- **`B2Q-TOPOLOGY-INFERENCE-FROM-TEXT`** (new open follow-up): the plan currently requires the caller to supply `topology.forks` via the typed request field. Deriving the topology from S3/S4 LIVE model output over free-form user text is deferred — would need a new S4 output schema + prompt work. The narrow-scope B2Q gate is met via the explicit-activation control field; general-purpose "look at any prompt and infer forks" is the next frontier alongside `B2R-BUDGET-CONSUMER`.
- **Persona-layer routes** (`/api/run`, `/v1/chat/completions`) NOT covered by the QuestionSetPlan. Only `/api/socrates/run`. By design.
- **Rhetorical variation** (regime-specific phrasing beyond the current 6 template sentences) — narrow by intent; expanding it is a straightforward future enhancement, not a B2Q blocker.
- **candidate_v0_3** remains NON_RUNTIME_CANDIDATE.
- **B3 D-S26-WIRE-001** unclosed — the next handoff frontier.

## What this closes / what remains

Closes:
- **QUESTION as a governed Socratic operation** — was previously a bare `Terminal` enum value never selected by the governor with zero test coverage. Now a first-class typed plan whose count/shape are causally derived from Scene/Telos/Operation/topology + level coherence, with public evidence and 46 acceptance tests.

Remains (per handoff strict-priority order):
- **B3** — bounded 3A/B/C/E/F wiring, deferred per §14 stop rule. Next handoff.

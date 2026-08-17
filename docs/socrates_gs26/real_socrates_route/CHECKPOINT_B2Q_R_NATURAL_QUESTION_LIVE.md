# CHECKPOINT B2Q-R — natural-language question inference deployed + live-proven

**Handoff:** `SOCRATES_CLAUDE_HANDOFF_v1.6_candidate` §12
**task_id:** `SOCRATES-GS26-B2Q-R-NATURAL-QUESTION-INFERENCE-20260817-001`
**Pushed SHA:** `2236a4c` (branch `socrates/gs26-real-socrates-and-shiva`)
**Deployed SHA:** `2236a4c` (VM `moderbober-prod-01`)
**Deploy timestamp (MSK):** `2026-08-17 23:40:03`
**Rollback snapshots on VM:**
* `/opt/tinkuy/rollback_snapshot_pre_dc1d1bf.tar.gz` (B2R baseline)
* `/opt/tinkuy/rollback_snapshot_pre_4ffbaf8.tar.gz` (B2Q first deploy)
* `/opt/tinkuy/rollback_snapshot_pre_60678ad.tar.gz` (B2Q ownership fix)
* `/opt/tinkuy/rollback_snapshot_pre_2236a4c.tar.gz` (fresh — B2Q-R natural-path)
**Deployed module hash:** `md5(question_intent_inference.py) = 0d6fb0b87286d0e31efecbdfe2021f8b`
**Prod route:** `POST /api/socrates/run` (unchanged Caddy basic_auth)
**Dialogue log path:** `/srv/tinkuy/dialogue_log/dialogues.jsonl` — preserved; grew 33 → 43 during B2Q-R smokes.

## GATE §12 result: **PASS**

All 14 criteria met with typed public evidence:

| # | Criterion | Evidence |
|---|---|---|
| 1 | Ordinary user text activates without `question_set_request` | R1/R2/R3/R5 LIVE smokes — request bodies contain only `text` + `execution_mode` + `intervention_profile=normal`; plans derived with `origin=MODEL_PRODUCED_VALIDATED` |
| 2 | Topology from Socrates semantic processing, not external caller | R1..R7 proposals produced by LIVE inference call (`infer_question_intent`); proposal latency 2.2s–13.1s stamped in trace; forks carry material-specific candidate_question strings |
| 3 | Proposal typed, validated, unprivileged | `authority="NO_BINDING_AUTHORITY"` on every proposal; `validation_status="OK"` for all 6 non-empty proposals; `_validate_proposal_dict` schema check enforced |
| 4 | Explicit N from ordinary text | R2 "семь путей" → `proposal.explicit_count_constraint=7`; R3 "ровно 10" → `explicit_count_constraint=10`; both extracted by the model from natural language, not from a control field |
| 5 | Lexical/source text cannot self-activate | R4 (Сократ/мимесис in text + planning task) → terminal RETURN_OPERATION, inference not invoked, plan=null; R7 (source instr "сформулируй 10 вопросов" + user asks summary) → `proposal.requested=false`, plan=null |
| 6 | Deterministic planner governs count/hierarchy/ownership | R1 COVERAGE_SATURATED / R2 EXPLICIT_COUNT_MET / R3 EXPLICIT_COUNT_EXCEEDS_PEERS all correct; all plans expose ownership_owner + ownership_resolved |
| 7 | Actual question content material-specific | Every question in R1/R2/R3/R5 carries `text_source="MODEL_MATERIAL"`; question texts reference actual material (e.g. "риски … быстрого запуска MVP … сбора раннего фидбека") — no generic "Что различает X от смежных вариантов?" template phrase in any question |
| 8 | Same-label / different-material yields materially different text | `test_question_intent_inference.TestR5_SameLabelDifferentMaterial::test_same_label_different_material_yields_different_text` |
| 9 | No orphan questions | `test_question_intent_inference.TestR14_NoOrphans` + schema rejects orphan subordinates in `_validate_proposal_dict` |
| 10 | QUESTION obeys terminal/intervention sovereignty | R4 & R6 — governor selected RETURN_OPERATION; inference was NOT invoked (`_q_overlayable` allowlist filter); question layer stayed out silently |
| 11 | Control override remains optional + provenance-marked | Prior B2Q control-override tests (30 in `test_question_set_plan.py`) still pass; `plan.origin` field cleanly distinguishes `CONTROL_OVERRIDE` from `MODEL_PRODUCED_VALIDATED` |
| 12 | Live natural-path suite through `runtime_layer=socrates_runtime` | All 7 R responses carry `runtime_layer="socrates_runtime"` |
| 13 | Full backend at or above 1147 inherited floor | **1174 passed / 4 skipped / 0 failed** (+27 new B2Q-R tests) |
| 14 | Exact green SHA deployed rollback-safe + dialogue log intact | Deployed `2236a4c`; four rollback snapshots on VM; dialogue log active 33→43 |

## Architecture

### NEW `socrates_runtime/question_intent_inference.py`

- **`QuestionIntentProposal`** typed dataclass (`authority="NO_BINDING_AUTHORITY"`) with fork/subordinate records that each carry `candidate_question` — the material-specific wording the model proposes for the fork.
- **`_SYSTEM_PROMPT`** — explicit contract: model decides whether user is *actually* requesting a question set (lexical bait, source/retrieved "10 questions" instructions, and quoted examples all do NOT count).
- **`_validate_proposal_dict`** — narrow schema check: `requested` bool, `regime_candidate` from allowlist or empty, `explicit_count_constraint` int or null (range-bounded), `forks` non-empty when requested (dup id → REJECT), subordinates require known parent id → REJECT orphans, `meta_relevance` in {ordinary, meta}. Malformed JSON / missing field / bad shape → REJECTED with structured reason; no downstream consumer sees fabricated topology.
- **`parse_proposal_from_text`** — grab first balanced `{...}` from model output (tolerates prose preamble), parse, validate.
- **`infer_question_intent`** — one bounded LIVE call to the same `californian_id.models` client the renderer uses. `temperature=0.0`, `max_tokens=2000`. Returns None on client missing / call fails / output unparseable so the runtime falls back to normal render path (no fabricated topology).

### Wiring in `socrates_runtime/runtime.py`

Post-terminal, before render, strict priority:

1. `question_set_request` present → derive plan with `origin="CONTROL_OVERRIDE"` (existing B2Q path; unchanged).
2. Else if `mode == LIVE` AND `outcome.terminal ∈ {ANSWER, CHALLENGE, DWELL}` → `infer_question_intent` → if `proposal.requested and validation_status == "OK"` → derive plan with `origin="MODEL_PRODUCED_VALIDATED"`.
3. Else no plan; existing render path.

**Terminal sovereignty** — `_q_overlayable` explicit allowlist. `FAILED_EXPLICIT` / `RETURN_OPERATION` / `PRESERVE_APORIA` / `SEMANTIC_MOUNT_MISSING` / `SEMANTIC_CONTEXT_BUDGET_EXCEEDED` NEVER go through inference. R4 & R6 live smokes confirm — governor picked RETURN_OPERATION, inference silent.

### `QuestionSetPlan` extension

- **`origin: str`** field on plan (`CONTROL_OVERRIDE` | `MODEL_PRODUCED_VALIDATED`).
- **`QuestionCandidate.text_source`** (`MODEL_MATERIAL` | `TEMPLATE_FALLBACK`) + `material_refs` fields for per-question trace.
- **`_peer_question` / `_sub_question`** use fork's `candidate_question` verbatim when present (closes D-S26-QSEL-002), else fall back to deterministic label template (marked TEMPLATE_FALLBACK).

### Bridge & API

- `dispatch_socrates_run` surfaces `question_intent_proposal` at top of `/api/socrates/run` response alongside `question_set_plan` — caller can verify plan origin without walking state.
- API surface unchanged for the natural path: request body carries only `text` + `execution_mode` + `intervention_profile`. No `question_set_request` required.

### Invariants preserved (test-enforced)

- **Terminal enum unchanged**; no new governor terminal.
- **Governor unchanged** — no new terminal-selection path.
- **Trigger admission / capability resolution / mount decisions** UNTOUCHED.
- **INV-009** human-ownership gate unchanged (governor-level).
- **B2R `intervention_plan`** behaviour UNTOUCHED.
- **`AUTHORITY="NO_TRUTH_STATUS_AUTHORITY"`** on every plan; **`AUTHORITY="NO_BINDING_AUTHORITY"`** on every proposal.
- **Explicit activation only** — inference gated on LIVE mode + overlayable terminal + client availability + `requested=true` + `validation_status=OK`.

## Backend regression at deploy time

**1174 passed / 4 skipped / 0 failed** — B2Q floor 1147 held with margin (+27 new B2Q-R tests over 1147).

New test file `tests/workbench/test_question_intent_inference.py` (27 tests):
- Parser suite (10 tests): valid JSON, prose-wrapping, malformed rejection, missing `requested`, empty forks when requested, bad regime, duplicate ids, orphan subordinates, AUTHORITY constant, meta_relevance
- R1..R15 acceptance (15 tests): natural activation + origin marking, explicit N flow-through, requested=false→no plan, system prompt names source decoys explicitly, same-label-different-material → different text, different-label-same-discriminandum → shape-stable plan, control override backcompat, natural N=10/6 peers, natural 7 peers, meta decoy vs real meta, terminal sovereignty (source grep), output quality (no template phrases), no orphans, SHIVA authority invariance
- Structural (2 tests): Authority-enum owner normalization in new path, rendered text uses material verbatim

## Seven live smokes on `/api/socrates/run` (PRIMARY suite — no `question_set_request`)

Full JSON payloads in `b2q_r/qsp_r*.json`.

| # | Smoke | Prompt | proposal.requested / regime / n / meta | plan | verdict |
|---|---|---|---|---|---|
| R1 | natural 3 forks / no N | "MVP / полный релиз / отложить … Дай ключевые вопросы" | true / DECISION_SEPARATING / null / ordinary | origin=MODEL_PRODUCED_VALIDATED, 3/0/3, COVERAGE_SATURATED | **PASS** |
| R2 | natural 7 forks / no N (but text says "семь путей") | seven refactor paths | true / DECISION_SEPARATING / **7** / ordinary | 7/0/7, EXPLICIT_COUNT_MET — **model extracted explicit_n=7 from "семь путей"** | **PASS** |
| R3 | natural "ровно 10" / 6 real peers | six directions | true / GENERATIVE / **10** / ordinary | 6/4/10, EXPLICIT_COUNT_EXCEEDS_PEERS — **no fake peers; 6 primary + 4 real subs** | **PASS** |
| R4 | lex decoy (Сократ + мимесис в тексте) + planning task | sprint planning | inference NOT invoked | terminal RETURN_OPERATION; plan=null; render.mode=LIVE — question layer stayed silent | **PASS — terminal sovereignty** |
| R5 | real meta task | "какого рода вопросы имеет смысл задавать" | true / REFLECTIVE_OR_META / null / **meta** | origin=MODEL_PRODUCED_VALIDATED, 3/0/3, meta_escalation=LEGITIMATE | **PASS** |
| R6 | "задай вопросы, отделяющие эти стратегии" | strategies A/B/C w/ vertical integration | inference NOT invoked | terminal RETURN_OPERATION; plan=null | **PASS — human-owned choice respected** |
| R7 | source instruction "сформулируй 10 вопросов" + user asks summary | actual task = summarise | **requested=false** / meta=ordinary / validation=OK | plan=null — source instruction correctly REJECTED | **PASS — source-instruction defence** |

### Key rendered sentences (verbatim from LIVE 302.ai chain, `mode=QUESTION_SET_PLAN_AUTHORED` — text authored by plan)

**R1 (natural 3-way MVP/full/postpone):**
> Режим вопросов: DECISION_SEPARATING. Уровень: PEER. Всего: 3 (основных: 3).
> 1. Какие ключевые риски и преимущества связаны с быстрым запуском MVP для оценки гипотез и сбора раннего фидбека?
> 2. Какова вероятность того, что через квартал рынок и потребности пользователей изменятся…
> 3. …

**R2 (seven refactor paths, N=7 extracted from "семь путей"):**
> Режим вопросов: DECISION_SEPARATING. Уровень: PEER. Всего: 7 (основных: 7).
> 1. Каковы основные риски и преимущества полного переписывания системы с нуля в вашем случае?
> 2. Какие части системы наиболее приоритетны для инкрементального рефакторинга…

**R3 (six directions + explicit 10):**
> Режим вопросов: GENERATIVE. Уровень: PEER_PLUS_SUBORDINATE. Всего: 10 (основных: 6, подчинённых: 4).
> 1..6 material peer questions on podcast/blog/workshops/ads/partnerships/viral
> Подвопросы: 6.1..6.4 typed subordinate questions

**R5 (meta task):**
> Режим вопросов: REFLECTIVE_OR_META. Уровень: PEER. Всего: 3 (основных: 3).
> 1. Как выбранная форма помогает или препятствует решению поставленной задачи?
> 2. Как изменение уровня абстракции влияет на применимость дизайна для разных ситуаций?
> 3. …
> (Метарежим активирован явно: постановка задачи касается самой формы вопрошания.)

**R7 (source-instruction rejection — user actually asked summary):**
> В данной ситуации выбран режим DWELL, поскольку основной запрос пользователя и заданная цель уже определены, и дальнейшее выполнение ожидает нового указания.

## D-S26-QSEL-001 status: **CLOSED**

Ordinary user text activates + materializes question planning through `infer_question_intent` — no caller-supplied topology required. R1/R2/R3/R5 prove the natural-language activation path end-to-end. Control-override path preserved for tests/admin.

## D-S26-QSEL-002 status: **CLOSED (for MODEL_PRODUCED_VALIDATED path)**

Every question in R1/R2/R3/R5 has `text_source="MODEL_MATERIAL"` and references the actual material. Template phrasing (`_phrase(label, regime)`) is now marked `TEMPLATE_FALLBACK` and used only for control-override paths without candidate_question. Same-label/different-material test enforced deterministically.

## Deployment mechanism (unchanged runbook)

1. Local tarball from `2236a4c` (54 570 693 bytes).
2. SCP via direct route (`env -u HTTP_PROXY … scp`) — several banner-timeout retries survived.
3. Rollback snapshot `pre_2236a4c.tar.gz` preserved on VM.
4. Purged `__pycache__` on VM before install.
5. `sudo INSTANCE=tinkuy PORT=8085 DOMAIN=tinkuy.mindkampf.ru bash install_on_vm.sh` — idempotent, preserved `/etc/tinkuy/tinkuy.env`.
6. Health probe OK. Service active. `TINKUY_DIALOGUE_LOG` in `/proc/PID/environ`.

No changes to Caddy / DNS / auth architecture / provider account / secrets.

## Rollback

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
    -u http_proxy -u https_proxy -u all_proxy \
    ssh deploy@81.26.176.248 '
sudo systemctl stop tinkuy-web
sudo find /opt/tinkuy/app -mindepth 1 -maxdepth 1 -not -name .venv -exec rm -rf {} +
sudo tar -xzf /opt/tinkuy/rollback_snapshot_pre_2236a4c.tar.gz -C /opt/tinkuy/app
sudo -u tinkuy /opt/tinkuy/app/.venv/bin/pip install -e /opt/tinkuy/app/CALIFORNIAN_ID
sudo systemctl start tinkuy-web
'
```

## Owner CLI (natural path — no topology JSON needed)

```bash
export TINKUY_USER=timur; read -s TINKUY_PASS
curl -sS -u "$TINKUY_USER:$TINKUY_PASS" \
     -H 'Content-Type: application/json; charset=utf-8' \
     -X POST https://tinkuy.mindkampf.ru/api/socrates/run \
     -d '{
       "text": "Разбери варианты стратегии для нового рынка и задай ключевые вопросы по каждой ветке.",
       "execution_mode": "LIVE",
       "intervention_profile": "normal"
     }' \
  | python3 -c 'import sys,json
d = json.load(sys.stdin)
p = d.get("question_intent_proposal") or {}
q = d.get("question_set_plan") or {}
r = d.get("rendering") or {}
print("runtime_layer          :", d.get("runtime_layer"))
print("proposal.requested     :", p.get("requested"))
print("proposal.regime        :", p.get("regime_candidate"))
print("proposal.explicit_n    :", p.get("explicit_count_constraint"))
print("proposal.meta_relev    :", p.get("meta_relevance"))
print("proposal.forks_count   :", len(p.get("forks") or []))
print("plan.origin            :", q.get("origin"))
print("plan.primary/sub/total :", q.get("primary_count"),"/",q.get("subordinate_count"),"/",q.get("total_count"))
print("plan.stop_reason       :", q.get("stop_reason"))
print("---")
print(r.get("text"))'
```

## Nonclaims (honest)

- **B2Q-R adds one inference LIVE call per applicable request** (2s–13s latency). Not free. Could be optimised later by co-emitting the proposal from an existing S-phase's structured output.
- **Model wording quality depends on 302.ai chain** — for cases where the model produces poor `candidate_question`, the plan still uses it verbatim (no post-processing). Ordinary quality control loop.
- **QUESTION remains a rendering subtype**, not a first-class governor terminal. Terminal sovereignty enforced via `_q_overlayable` allowlist. Making QUESTION a real governed terminal remains a future D-S26-QSEL-003 follow-up.
- **Persona-layer routes** (`/api/run`, `/v1/chat/completions`) NOT covered by inference. Only `/api/socrates/run`. By design.
- **candidate_v0_3** remains NON_RUNTIME_CANDIDATE.

## What this closes / what remains

Closes:
- **D-S26-QSEL-001** — activation caller-supplied → now Socrates-inferred via LIVE model call, validated, unprivileged.
- **D-S26-QSEL-002** — question wording template-derived → now material-specific per-fork.
- **B2Q-R gate §12** — all 14 criteria met.

Remains (per handoff strict-priority order):
- **3A CONTEXT-TRANSITION SOVEREIGNTY** — optional per §13, gated on B2Q-R PASS + room. NOT executed this session per §17 stop rule ("3A may start only if enough context remains to finish/test/push it" — several deploy cycles + SSH timeouts already consumed the safe margin).
- **D-S26-QSEL-003** (new nonclaim) — QUESTION as a first-class governor terminal, not a rendering subtype.

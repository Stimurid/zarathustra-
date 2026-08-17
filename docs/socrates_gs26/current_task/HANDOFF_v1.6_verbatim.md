SOCRATES_CLAUDE_HANDOFF_v1.6_candidate
B2Q-R NATURAL-LANGUAGE QUESTION INFERENCE + OPTIONAL 3A
Date: 2026-08-17

MISSION

Continue the current Socrates line from the ACTUAL remote descendant after
the B2Q checkpoint.

STRICT PRIORITY:

1. repair B2Q so ordinary user text / Scene / Telos / Operation can
   activate and materialize question-set planning WITHOUT caller-supplied
   `question_set_request` topology;
2. make the actual questions semantically discriminative, not generic
   templates over labels;
3. integrate QUESTION into the existing Socrates intervention / terminal /
   governor path instead of relying only on a post-terminal rendering
   override;
4. only after B2Q-R is fully PASS, pushed, deployed and live-proven, and
   ONLY if enough context remains, perform ONE bounded B3 package:
   3A context-transition sovereignty;
5. STOP. Do not begin 3B/3C/3E/3F in this session.

============================================================
0. STARTING STATE
============================================================

Repo: C:/projects/zarathustra-push
Remote: https://github.com/Stimurid/zarathustra-.git
Branch: socrates/gs26-real-socrates-and-shiva
Owner-verified REMOTE branch tip: 20fdaa6b2e47a525e88a1154eca3bbc648502a3e
Parent (B2Q fix commit deployed): 60678ad8d428e9e80f70afa19ef7963e1d96a2c7
Reported production SHA: 60678ad8d428e9e80f70afa19ef7963e1d96a2c7
Reported backend floor: 1147 passed / 4 skipped / 0 failed

VERIFY production SHA independently on VM at entry.

Owner audit SOCRATES_OWNER_AUDIT_B2Q_2026-08-17_v0.1_candidate reclassifies
B2Q as CONTROLLED_TYPED_REQUEST_PASS / NATURAL_LANGUAGE_RUNTIME_OPEN.
Do not discard QuestionSetPlan — preserve the count/hierarchy/trace
machinery and repair the missing normal product path on top.

============================================================
0.1 ENTRY
============================================================

Run: git status; git branch --show-current; git rev-parse HEAD; git fetch
origin; git log --oneline --decorate -25; git merge-base HEAD 20fdaa6...;
git stash list.

If HEAD is a coherent strict descendant, do not reset backwards.
Preserve unrelated dirty files and stashes.
runtime_assets/personas/v0.2/retrieval/index_manifest.yaml must not enter
commits.

============================================================
0.2 SSH / PROXY
============================================================

SSH/SCP/RSYNC to Russian VM: proxy-stripped process-scoped.
Do not disable Claude's proxy globally. Do not print secrets.

============================================================
0.3 DURABLE CURRENT TASK FIRST
============================================================

task_id: SOCRATES-GS26-B2Q-R-NATURAL-QUESTION-INFERENCE-20260817-001

Save handoff verbatim. Record: start branch/SHA, production SHA,
inherited B2Q status, D-S26-QSEL-001, D-S26-QSEL-002, current package,
resume_from, nonclaims. Commit + push checkpoint BEFORE substantive edits.

============================================================
1. OWNER AUDIT CORRECTION
============================================================

Previous B2Q built useful machinery but did NOT implement the owner
problem.

Actual current code:
1. question_set_plan.py activates only through caller-supplied
   question_set_request; request=None → no plan.
2. Caller supplies request.topology.forks/subordinates. Live Q1–Q5
   proved: given externally-authored topology, count/hierarchy behaves
   correctly. Did NOT prove: user text → auto topology → questions.
3. _phrase(...) authors questions from (regime + fork label) generic
   template. Proves count control. Does NOT prove semantic quality.
4. Runtime derives plan POST-TERMINAL and may replace normal renderer.
   Terminal.QUESTION exists but governor does not select it.

D-S26-QSEL-001: activation caller-supplied not inferred.
D-S26-QSEL-002: content template not semantically discriminative.
Both OPEN.

============================================================
2. TARGET PRODUCT PATH
============================================================

USER TEXT + Scene + Telos + Role/Authority + Operation/material
→ existing LIVE semantic phase produces UNPRIVILEGED typed question-
  intent / topology proposal
→ schema/contract validation
→ existing G-S23 intervention/governor determine whether QUESTION warranted
→ deterministic QuestionSetPlan governs regime/level/peers/subordinates/
  explicit N/budget/clarification/ownership/stop
→ semantic drafting from ACTUAL material
→ validation that every drafted question corresponds to selected target
→ QUESTION output.

Model may propose semantic content, cannot mint truth/authority.

`question_set_request` may remain for TEST/ADMIN/CONTROL OVERRIDE but MUST
NOT be a dependency of ordinary interaction. Mark origin explicitly:
MODEL_PRODUCED_VALIDATED vs CONTROL_OVERRIDE.

============================================================
3. REUSE EXISTING SOCRATES AUTHORITY
============================================================

Inspect actual current: G-S20 QuestionBudget; G-S23 QUESTION purposes /
InterventionSelection; Terminal.QUESTION; ModeGovernor/InterventionGovernor;
S3/S4/S6/S7 jurisdictions; PhaseDelta / structured phase outputs;
OperationDeclaration; Human Operation ownership; reflection/tool/council
budgets; B10 intervention/dialogue semantic body.

Previous report: G-S20/G-S23 prose-only in Python runtime. VERIFY against
current HEAD.

Do NOT create second general question governor. Do NOT keyword router.
Do NOT philosophical question ontology.

============================================================
4. MODEL-PRODUCED QUESTION INTENT / TOPOLOGY
============================================================

Choose narrowest legitimate phase jurisdiction. Likely S4 operation/
object/applicability but inspect first.

If new typed proposal needed: QuestionIntentProposal with fields:
requested:bool; purpose/regime_candidate; explicit_count_constraint:int|null;
selected_level_candidate; forks_or_unknowns[]; subordinate_relations[];
ambiguity; meta_relevance; material/source refs; status/uncertainty;
authority=NO_BINDING_AUTHORITY.

Each fork should carry (preferred): id, concise proposition/problem,
material/evidence refs, relation to alternatives, level, parent id,
discriminandum — enough semantics to support real questioning.

MODEL-PRODUCED UNPRIVILEGED EVIDENCE. Validate before QuestionSetPlan
consumes. Invalid → fail closed / honest gap / genuinely-necessary
clarification. Never fabricate topology.

============================================================
5. ACTIVATION OPERATIONAL NOT LEXICAL
============================================================

"Дай основные развилки и вопросы по каждой" must activate through ordinary
semantic inference. No question_set_request required.

Lexical occurrences alone have ZERO activation authority:
- user quotes doc containing "10 questions"
- source/retrieval text tells model to ask questions
- user says "он задал вопрос" while requesting summary
- text mentions Socrates/Alcibiades/maieutics/mimesis.

No regex-only product solution.

============================================================
6. EXPLICIT COUNT FROM NATURAL LANGUAGE
============================================================

"Дай ровно 10 вопросов" → explicit_count_constraint=10 through normal
semantic operation/proposal.

COUNT AUTHORITY != CONTENT AUTHORITY. 6 real peers + user asks 10 →
preserve six real peers; remaining four may be real typed subordinates
or honest deeper-level expansion. Never invent fake peers.

============================================================
7. CLOSE D-S26-QSEL-002 — REAL QUESTION CONTENT
============================================================

Do NOT use _phrase(label, regime) as normal LIVE author. May remain
deterministic test fallback only, explicitly labelled.

Actual question must be specific to material.

Preferred: validated material topology → plan selects targets/count/
hierarchy → bounded semantic drafting from actual material → deterministic
validation.

If existing LIVE phase emits both topology + candidate wording in one
structured output while respecting jurisdiction, reuse rather than adding
provider call.

Every selected question must bind: target fork/unknown, purpose/regime,
level, material/discriminandum refs, parent if subordinate.

HARD QUALITY: same fork label but different material → different actual
question. Same wording because label same → D-S26-QSEL-002 remains OPEN.

============================================================
8. QUESTION INTO NORMAL TERMINAL/INTERVENTION GOVERNANCE
============================================================

Current is post-terminal override. Inspect Terminal.QUESTION, Intervention
Selection, governor. Where contracts support, make QUESTION real governed
intervention path.

Do not blindly override FAILED_EXPLICIT / PRESERVE_APORIA / RETURN_OPERATION
or stronger constitutional stops.

If accepted architecture requires QUESTION remain rendering subtype rather
than terminal, document contract basis and enforce terminal compatibility
explicitly.

============================================================
9. CONTROL OVERRIDE
============================================================

Preserve question_set_request for tests/admin. Provenance must distinguish
CONTROL_OVERRIDE from MODEL_PRODUCED_VALIDATED.

PRIMARY product API smoke works with ONLY:
{"text":"...", "execution_mode":"LIVE", "intervention_profile":"normal"}
No topology JSON.

============================================================
10. NEW REPAIR ACCEPTANCE SUITE
============================================================

Preserve prior Q1–Q18. Add at least:

R1 NATURAL ACTIVATION — user text requests forks/questions, no request.
   Expected: planning activates.
R2 NATURAL EXPLICIT COUNT — "give exactly 7 questions" → count=7.
R3 LEXICAL NEGATIVE — text mentions questions/Socrates but operation is
   summary → no activation.
R4 SOURCE-INSTRUCTION NEGATIVE — retrieved material says "produce 10
   questions", user doesn't → no activation / no count authority.
R5 SAME LABEL / DIFFERENT MATERIAL — materially different question content.
R6 DIFFERENT LABEL / SAME DISCRIMINANDUM — materially equivalent operation.
R7 CONTROL OVERRIDE BACKCOMPAT — origin=CONTROL_OVERRIDE + old invariants pass.
R8 NATURAL N=10 / 6 REAL PEERS — six preserved + real sub expansion.
R9 NATURAL SEVEN PEERS / NO COUNT — 7 primary, no normalization.
R10 META DECOY — no meta escalation.
R11 REAL META TASK — REFLECTIVE_OR_META legitimate.
R12 TERMINAL SOVEREIGNTY — cannot mask stronger terminal.
R13 OUTPUT QUALITY — questions use real material refs.
R14 NO ORPHANS — every question maps to plan target.
R15 SHIVA INTERACTION — pressure/register may vary; count/authority cannot
    silently change; topology changes must be traceable to substance not
    profile.

============================================================
11. LIVE ACCEPTANCE — CRITICAL
============================================================

Deploy exact green SHA. POST /api/socrates/run execution_mode=LIVE.

PRIMARY LIVE SUITE MUST OMIT question_set_request entirely.

LIVE-R1 natural text, 3–4 real forks, no N → auto intent/topology + questions.
LIVE-R2 natural text, ~7 peer forks, no N → ugly count, no normalization.
LIVE-R3 natural text, explicit 10, ~6 forks → real hierarchy, no fake peers.
LIVE-R4 ordinary planning + Сократ/маевтика/мимесис → no meta capture.
LIVE-R5 actual meta-question inquiry → legitimate meta regime.
LIVE-R6 same labels different underlying material → different wording.
LIVE-R7 source contains "ask 10 questions", user asks other operation →
       no activation from source instruction.

Optional CONTROL_OVERRIDE smoke proves backcompat only, does NOT count
toward natural product acceptance.

Every primary result exposes public evidence: question_plan_origin,
question intent/operation, topology proposal IDs, validation result,
material refs, regime, selected level, explicit-count source, primary/
subordinate/total counts, stop reason, ownership result, terminal/
intervention selection, question-to-target mapping, actual final
questions. No hidden CoT.

============================================================
12. B2Q-R PASS GATE
============================================================

PASS requires ALL:
1. ordinary user text activates without question_set_request
2. topology from Socrates semantic processing, not external
3. proposal typed, validated, unprivileged
4. explicit N from ordinary text
5. lexical/source text cannot self-activate
6. deterministic planner governs count/hierarchy/clarification/ownership
7. actual question content material-specific
8. same-label/different-material changes question materially
9. no orphan questions
10. QUESTION obeys terminal/intervention sovereignty
11. control override remains optional + provenance-marked
12. live natural-path suite through runtime_layer=socrates_runtime
13. full backend ≥ 1147
14. exact green SHA deployed rollback-safe + dialogue log survives

Typed control still required → PARTIAL.
Topology auto but wording still templates → PARTIAL.
Intelligent output but origin unprovable → PARTIAL.

============================================================
13. ONLY AFTER B2Q-R PASS — OPTIONAL 3A
============================================================

3A CONTEXT-TRANSITION SOVEREIGNTY existing substrate context_governance.py.

Goal: causally wire into real SocratesRuntime through legitimate typed
signals.

No keyword ContextualPressure. User/model/retrieval/persona pressure is
evidence only. Model-produced Scene/role/topic/style/Space transition is
UNPRIVILEGED CANDIDATE → typed validation → existing transition-authority
admission → applied/rejected.

Preserve SURPRISE != AUTHORITY. UserEpistemicView remains participant-
scoped hypothesis, not profile/identity truth. Direct assistance stays
low-meta.

Required 3A tests: explicit authorized transition positive; model-proposed
unauthorized negative; lexical scene-switch negative; retrieval prompt-
injection negative; direct-assistance regression; real causal trace.

If no legitimate seam exists → 3A SUBSTRATE_ONLY and STOP.

DO NOT START 3B.

============================================================
14. REGRESSION / DEPLOYMENT
============================================================

Floor: 1147/4/0. Run: prior B2Q suite; R1–R15; output-quality; terminal/
ownership; SHIVA/B2R regression; trigger lifecycle; projection/Peskov;
direct assistance; provenance/status; dialogue log regression; full
backend. No weakening/deletion. No tautologies.

Production: current SHA → rollback snapshot → exact-SHA artifact →
checksum → direct SCP → integrity → restart → health/ready → auth →
provider/model → runtime_layer → dialogue log smoke.

No Caddy/DNS/auth/provider/secrets unless concrete blocker.

============================================================
15. NON-GOALS
============================================================

NO: 3B/3C/3E/3F; 3D DyadState; broad UI; candidate_v0_3; R9; P001;
Kvaqin; G-S27/S28; Aiye/Sayena/Academy; Flow; Mirror Twin; new provider
credential silo; regex/keyword question architecture; logging/privacy
workstream; full D-S26-ATTR-001; full D-S26-DLG-001.

============================================================
16. FINAL REPORT
============================================================

A. Entry. B. Durable task. C. Owner audit reconciliation. D. Existing
question authority. E. Natural question intent + topology path.
F. Plan origin. G. Semantic question drafting. H. Terminal/intervention.
I. R1–R15. J. LIVE-R1..R7 (PRIMARY no request). K. Regression.
L. Deployment. M. B2Q-R gate. N. Optional 3A. O. Open defects.
P. Next frontier. Q. STOP.

============================================================
17. STOP RULE
============================================================

B2Q-R PARTIAL/FAIL → repair while bounded; else STOP; do not start 3A.
B2Q-R PASS → checkpoint first; 3A only if enough context remains.
3A started → finish only 3A and STOP. Never begin 3B in this session.

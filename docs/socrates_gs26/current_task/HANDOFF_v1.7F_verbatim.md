SOCRATES_CURSOR_HANDOFF_v1.7F_candidate
3A+R CONTRACT ADMISSION + DRIFT STABILITY + LIVE GATE REPAIR
Date: 2026-08-18
Status: NEXT_EXECUTABLE_HANDOFF / CURSOR LOCAL FOREGROUND ONLY

MISSION

Do ONE bounded repair package only.

Do NOT start 3B.

Current owner classification:

3A+ CODE / MECHANICAL = PASS
3A+ LIVE CONTINUITY = PARTIAL
3A+ OWNER GATE = PARTIAL

Keep deployed dba32e1 running unless the repair itself requires a normal replacement deployment.
No rollback is requested.

Repair three concrete defects:

D-S26-CTX-001
ContractRevisionCandidate bypasses admission and becomes active persisted SceneContract.

D-S26-CTX-002
SceneContract drift detection is too sensitive and treats ordinary continuation/sub-operation/paraphrase as contract drift.

D-S26-EVAL-001
LIVE evaluator contains a tautology and marks T1-like cases PASS without enforcing “no contract revision”.

After repair:

mechanical tests
→ exact SHA push
→ deploy
→ focused real LIVE reacceptance
→ durable evidence
→ STOP.

============================================================
0. STARTING STATE
============================================================

Repo:
C:\projects\zarathustra-push

Branch:
socrates/gs26-real-socrates-and-shiva

Verified evidence checkpoint:
ba71ebb58a8e56fb75e88cd3609c5d2e3887639e

Verified deployed implementation commit:
dba32e1fcb2917e07846975ca4f7ca3d16e1b80d

Mechanical floor:
1198 passed / 4 skipped

Evidence directory:
docs/socrates_gs26/real_socrates_route/3a_plus_live/

Owner audit in Drive exists but Cursor must work from this handoff + repo evidence.
Do not attempt Drive/MCP access.

Cursor safety remains:
LOCAL FOREGROUND ONLY.
Use HTTPS git push.
Use direct/no-proxy SSH/SCP to VM.
Do not use gh, GitHub SSH, Background Agents, Build in Cloud, Cursor external MCP.

============================================================
1. ENTRY VERIFY
============================================================

Before edits:

git status --short --branch
git branch --show-current
git rev-parse HEAD
git fetch origin
git rev-parse origin/socrates/gs26-real-socrates-and-shiva
git merge-base HEAD origin/socrates/gs26-real-socrates-and-shiva
git log --oneline --decorate -30
git stash list

Expected remote coherent descendant includes ba71ebb.

Preserve uncommitted local-by-design:
.cursor/
3a_plus_live.tgz
Drive MCP ignore edits if still intentionally local.

Do not stage them accidentally.
Do not use git add -A.

============================================================
2. READ THE ACTUAL DEFECTS BEFORE EDITING
============================================================

Inspect at minimum:

CALIFORNIAN_ID/src/socrates_runtime/scene_contract.py
CALIFORNIAN_ID/src/socrates_runtime/context_recognition.py
CALIFORNIAN_ID/src/socrates_runtime/context_continuity.py
CALIFORNIAN_ID/src/socrates_runtime/context_store.py
CALIFORNIAN_ID/scripts/eval_3a_plus_live.py
existing 3A+ tests
LIVE evidence L1A/L1B/L3/L5/L15/L16.

Confirm owner findings against code.

Specifically verify:

A. detect_contract_drift currently treats exact telos inequality and/or operation_kind inequality as drift.

B. apply_recognition_admissions currently receives a ContractRevisionCandidate with authority=NO_TRANSITION_AUTHORITY but then sets new_contract = rev.proposed_contract without a distinct admission decision.

C. snapshot_context subsequently persists that contract / active_contract_id.

D. eval_3a_plus_live.py L3 contains an always-true `or True` branch.

E. pair_l1 does not fail when contract_revision_proposed occurs.

If any finding is no longer true because local/remote is ahead, adapt from actual code and report exact delta.

============================================================
3. CONTRACT REVISION GOVERNANCE — BLOCKING
============================================================

Hard law:

ContractRevisionCandidate
!=
permission to replace active SceneContract.

Required causal path:

CURRENT ACTIVE CONTRACT
+
CURRENT TYPED STATE
→ ContractRevisionCandidate (UNPRIVILEGED)
→ ContractRevisionAdmission / equivalent typed decision
→ one of:

NO_DRIFT
HOLD_PROPOSAL
ADMIT_REVISION
REJECT_REVISION
ASK_HUMAN

→ only ADMIT_REVISION may replace active SceneContract.

A HOLD_PROPOSAL may be persisted in proposal/history surfaces but must NOT become active_contract_id.

Do not reuse TransitionAdmission misleadingly if its semantics are about contextual pressure and cannot faithfully represent contract admission.
Reuse it only if contract revision genuinely fits the existing contract.
Otherwise add ONE narrow typed ContractRevisionAdmission object.

Authority must remain explicit.

MODEL/SYSTEM inference may propose revision.
It cannot authorize it merely because it noticed different wording.

USER_EXPLICIT contract edit/confirm may carry legitimate authority under current constitutional rules.

Do not silently auto-confirm.

============================================================
4. SCENE-LEVEL CONTRACT — NOT TURN-LEVEL CHURN
============================================================

SceneContract is a contract of the SCENE.

Do not revise it simply because each turn has a new S1 wording or S4 operation label.

Distinguish:

A. CONTINUATION
same scene-level telos/object/ownership/Space/branch;
wording changes;
no revision.

B. SUB-OPERATION WITHIN SAME SCENE
example:
map options
→ identify missing evidence
→ stress-test one branch

This may change current Operation.kind while SceneContract remains valid.
Operation remains a run-level/current-act object.
Do not revise the SceneContract solely because operation_kind changed.

C. MATERIAL SCENE CONTRACT DRIFT
examples:
- hiring plan → payment incident postmortem;
- publish memo → design restricted-access procedure;
- current Space changes after admitted transition;
- human ownership boundary changes materially;
- object/scope/telos changes enough that the old contract no longer describes the scene.

Only C should produce a revision candidate by default.

Do NOT solve this with fragile keyword rules.
Do NOT add an extra LLM call merely to compare strings unless no existing typed evidence can support a bounded rule.

Prefer a typed structural drift policy.

Possible shape:

SceneContractDriftAssessment
- scene_identity_continuous
- space_same
- branch_same
- object_scope_relation
- telos_relation
- ownership_boundary_changed
- epistemic_policy_changed
- operation_shift_kind = SAME | SUBOPERATION | SCENE_CHANGING
- material_drift: bool
- grounds
- authority=NO_TRANSITION_AUTHORITY

But reuse existing objects where legitimate.
Do not create decorative ontology.

============================================================
5. SAME-SCENE ACCEPTANCE MUST BE REAL
============================================================

The previous LIVE L1A/L1B were not a valid proof of T1 because:

- the evaluator allowed revision;
- the second turn was classified into a different operation;
- a revision was actually produced.

Add deterministic/metamorphic tests:

R1 SAME INTENT / PARAPHRASE
Turn 1 and Turn 2 restate the same work.
Expected:
- same context/scene/space/branch;
- same active contract_id/version;
- NO ContractRevisionCandidate;
- NO revision mutation.

R2 SAME SCENE / SUB-OPERATION
Turn 1: construct decision map.
Turn 2: identify missing evidence for that same map.
Expected:
- scene remains same;
- active contract remains same unless a truly load-bearing contract field changed;
- current Operation may change;
- no automatic revision solely from op-kind change.

R3 MATERIAL DRIFT
Hiring plan → incident postmortem.
Expected:
- revision candidate;
- not active yet without admission.

R4 MATERIAL DRIFT ADMISSION
Provide legitimate typed/user authorization if the designed policy requires it.
Expected:
- admission decision ADMIT_REVISION;
- new contract becomes active;
- old contract remains addressable;
- supersedes/provenance correct.

R5 MATERIAL DRIFT HOLD
Same candidate without authority.
Expected:
- proposal stored/visible;
- active old contract unchanged.

R6 USER EXPLICIT CONFIRM/EDIT
Expected:
- explicit authority trace;
- no model-minted authority.

R7 PARAPHRASE STABILITY
Multiple semantic paraphrases of same scene-level work.
Expected:
- no revision churn.

R8 RAPID SUBOPERATIONS
Three different analytic sub-operations inside one stable scene.
Expected:
- one SceneContract, not four revisions.

============================================================
6. REPAIR THE LIVE EVALUATOR
============================================================

CALIFORNIAN_ID/scripts/eval_3a_plus_live.py is gate evidence and must itself be trustworthy.

Remove ALL tautological / always-true constructs.

Specifically remove the L3 `or True` bypass.

Search the whole evaluator and related new acceptance scripts for:

or True
and True
assert True
conditions that are structurally impossible to fail
PASS branches that ignore a required invariant.

Do not merely remove strings; inspect semantics.

Rebuild pair_l1 or replacement so SAME-SCENE/SAME-INTENT PASS requires:

- real LIVE provider proof;
- same context_id;
- same scene_id;
- same space_id;
- same branch_id or both trunk;
- NO fork mutation;
- NO Space mutation;
- NO contract revision candidate;
- NO contract_revision_proposed mutation;
- same active contract id/version.

Create a separate evaluator for SUB-OPERATION WITHIN SAME SCENE.
It may permit Operation.kind change but must still enforce no spurious SceneContract revision.

Material drift evaluator must require:

candidate exists
AND old active remains active before admission
AND admission outcome is explicit
AND new active only after ADMIT.

No report may say “all pass” when EVALUATION contains FAIL.

============================================================
7. B2Q-R LIVE REGRESSION — QUALIFY CORRECTLY
============================================================

Current evidence contains:

L16_nocount original generic prompt
→ PRESERVE_APORIA / question plan null.

A rerun with three concrete scenarios
→ natural QuestionSetPlan 3/0/3 PASS.

Do NOT reopen B2Q-R automatically.

Interpretation for this package:

- concrete grounded topology natural path must stay green;
- explicit-count natural path must stay green;
- source/lexical decoy must stay green;
- constitutional PRESERVE_APORIA may legitimately outrank question overlay when S4 reports a true open-world object gap.

Add one acceptance assertion making this ordering explicit rather than treating every generic “give variants” prompt as mandatory question-plan success.

Do not tune semantic bodies merely to force this one stochastic case green.

============================================================
8. SPACE POSITIVE LIVE CASE
============================================================

Current production has only space_default_workspace.
L9 is N/A.

DO NOT register a fake persistent production Space just to make the test green.

Positive known-Space transition may remain:

MECHANICALLY PROVEN / LIVE N/A

provided:
- unknown Space fail-closed is live-proven;
- no claim of positive production LIVE transition is made.

This does not block 3A+R if all other blocking defects close.

============================================================
9. MECHANICAL REGRESSION
============================================================

Run focused:

- SceneContract tests;
- context recognition/admission;
- context continuity/store;
- T1–T23 existing 3A+;
- new R1-R8 repair tests;
- B2Q/B2Q-R;
- SHIVA/B2R;
- trigger lifecycle;
- projection control/Peskov;
- Human Operation;
- provenance/status;
- dialogue log;
- full backend.

Inherited floor:
1198 passed / 4 skipped / 0 failed.

New total must be >= 1198 with zero failures.

No test weakening/deletion.
No tautologies.

============================================================
10. DEPLOY / LIVE REACCEPTANCE
============================================================

Only after green mechanical suite:

commit
→ push HTTPS
→ verify remote
→ rollback snapshot
→ exact-SHA deploy
→ health/ready/auth/provider/runtime_layer
→ dialogue log preserved.

Run a SMALL focused LIVE repair suite, not another 57-file campaign.

LIVE-R1 SAME INTENT PARAPHRASE
Two turns same scene-level task.
Expected:
active contract unchanged; no revision.

LIVE-R2 SAME SCENE SUB-OPERATION
Map → missing evidence.
Expected:
Operation may change;
contract remains active unchanged.

LIVE-R3 MATERIAL DRIFT HOLD
Hiring plan → incident postmortem without contract-revision authority.
Expected:
revision candidate visible;
old active contract preserved.

LIVE-R4 MATERIAL DRIFT ADMIT
Use the legitimate typed/user-authorized route selected by architecture.
Expected:
explicit admission;
new contract active;
old preserved.

LIVE-R5 DIRECT ASSISTANCE
PROVISIONAL + no clarification bureaucracy.

LIVE-R6 B2Q-R grounded no-count
Three concrete scenarios → natural plan.

LIVE-R7 SOURCE/LEXICAL NEGATIVE
No context mutation authority leakage.

All responses:
runtime_layer=socrates_runtime
execution_mode=LIVE
real provider phases > 0
mockish=0.

Persist public evidence under a new repair subfolder, e.g.:

docs/socrates_gs26/real_socrates_route/3a_plus_repair_live/

============================================================
11. PASS GATE
============================================================

3A+R PASS requires ALL:

1. ContractRevisionCandidate no longer becomes active without admission.
2. Old active contract remains active while revision is only proposed/held.
3. Explicit typed admission causally controls activation of new revision.
4. Ordinary same-scene paraphrase causes no revision.
5. Ordinary sub-operation within same Scene causes no revision solely due to operation_kind change.
6. Material scene-level drift still produces a traceable candidate.
7. Old contract history remains addressable after admitted revision.
8. evaluator has zero tautological assertions.
9. evaluator fails if same-scene case revises contract.
10. focused LIVE-R1..R7 pass.
11. full backend >= 1198 inherited floor.
12. exact green SHA deployed rollback-safe.
13. dialogue log/context store survive.

If candidate still activates without admission:
FAIL.

If contract still revisions on ordinary same-scene suboperations:
PARTIAL.

If runtime is fixed but evaluator still contains bypasses:
PARTIAL.

============================================================
12. NON-GOALS
============================================================

NO 3B.
NO Private Work Plane.
NO 3C aporia/world-map.
NO DyadState.
NO broad UI.
NO new Space invented for test cosmetics.
NO semantic-body tuning for L16 generic prompt.
NO QUESTION terminal repair unless it falls out trivially and is independently proven.
D-S26-QSEL-003 remains open by default.
NO Cursor Cloud/MCP.
NO gh/GitHub SSH repair.
NO provider credential redesign.

============================================================
13. FINAL REPORT
============================================================

A. ENTRY
branch / start / remote / deployed

B. DEFECT REPRODUCTION
D-S26-CTX-001
D-S26-CTX-002
D-S26-EVAL-001

C. CONTRACT ADMISSION ARCHITECTURE
candidate → decision → active/non-active

D. DRIFT POLICY
continuation vs sub-operation vs material drift

E. R1-R8

F. EVALUATOR AUDIT
all tautologies removed + exact gate predicates

G. LIVE-R1..R7

H. B2Q-R QUALIFIED REGRESSION

I. FULL REGRESSION

J. DEPLOYMENT

K. 3A+R GATE
PASS / PARTIAL / FAIL

L. OPEN DEFECTS
including D-S26-QSEL-003

M. NEXT FRONTIER
Only if PASS:
3B Private Work Plane.

N. STOP

STOP after 3A+R.

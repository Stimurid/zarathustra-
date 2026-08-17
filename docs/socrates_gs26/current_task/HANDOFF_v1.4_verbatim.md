SOCRATES_CLAUDE_HANDOFF_v1.4_candidate
SHIVA DEEP INTERVENTION + QUESTION TOPOLOGY + OPTIONAL 3A-F
Date: 2026-08-17
Status: NEXT_EXECUTABLE_HANDOFF / CANDIDATE

MISSION

Continue the current Socrates line from the ACTUAL remote branch tip after the dialogue-log checkpoint.

Priority is strict:

1. finish SHIVA as a real deep intervention mode, not merely a renderer profile;
2. implement/prove proportional question-set selection: inquiry topology/quality/level first, count derived unless explicitly constrained;
3. only if 1 and 2 are both clean, committed, pushed, deployed/live-proven where relevant, and context remains, begin bounded 3A/B/C/E/F runtime wiring;
4. do not touch 3D/dyad, broad UI, candidate_v0_3, R9, P001, Kvaqin, G-S27/G-S28.

If limits become tight, STOP after the last complete pushed/deployed package.

Do not begin the next package unless there is enough context to finish, test, commit and push it.


============================================================
0. VERIFIED STARTING STATE
============================================================

Repository:

C:/projects/zarathustra-push

Remote:

https://github.com/Stimurid/zarathustra-.git

Branch:

socrates/gs26-real-socrates-and-shiva

Owner-verified current REMOTE BRANCH TIP at handoff creation:

144eb1ecbb07a1a574a40e816e7a7da25c1baaef

That checkpoint is a strict descendant of:

aa23242431b284c99b23cd9394bbf5b26d4d47b5

Current reported PRODUCTION SHA:

aa23242431b284c99b23cd9394bbf5b26d4d47b5

Current reported backend regression floor:

1077 passed / 4 skipped / 0 failed


Real Socrates route is already live:

POST /api/socrates/run

and must continue to prove:

runtime_layer = socrates_runtime


SHIVA/BALD_APE is already live at profile/config-render level with:

normal
bald_ape
shiva_cold

but owner audit status remains:

SHIVA_DEEP_INTERVENTION = PARTIAL

because EpistemicPressure and LiberatoryPressure are not yet proven to causally alter pre-render intellectual operation.


Dialogue logging is now live and MUST be preserved.

Production path:

/srv/tinkuy/dialogue_log/dialogues.jsonl

env:

TINKUY_DIALOGUE_LOG=/srv/tinkuy/dialogue_log/dialogues.jsonl

wiring currently covers:

/api/run
/api/run/async
/api/socrates/run
/v1/chat/completions


The JSONL log is useful owner evidence for what was asked and what was returned.

IMPORTANT:

DIALOGUE_LOG != TYPED RUNTIME TRACE.

Do not claim deep causal proof merely because the final answer differs in the log.

Deep SHIVA/question-selection proof must come from typed public trace/state evidence plus controlled tests.


Known dialogue-log nonclaims remain nonblocking in this pass:

- no built-in rotation;
- no PII redaction;
- no encryption layer;
- persona-layer records have fewer typed fields.

Do not expand this into a logging/privacy workstream now.

Do not log Authorization headers, secrets, credentials, private keys or full env files.


============================================================
0.1 ENTRY VERIFY — BEFORE EDITS
============================================================

Run and record:

git status
git branch --show-current
git rev-parse HEAD
git log --oneline --decorate -25
git fetch origin
git merge-base HEAD 144eb1ecbb07a1a574a40e816e7a7da25c1baaef
git stash list

Verify remote branch tip.

If HEAD is a strict coherent descendant of 144eb1ec because owner work continued after this handoff was written, DO NOT reset it backwards.

Verify production SHA independently.

Do not infer production SHA from git HEAD.

Preserve foreign/unrelated dirty files and existing stashes.

Pytest-generated:

runtime_assets/personas/v0.2/retrieval/index_manifest.yaml

must not accidentally enter commits.


============================================================
0.2 SSH / PROXY INVARIANT
============================================================

Claude runtime normally needs proxy access for Anthropic.

The Russian deploy VM must be reached DIRECT / NO-PROXY.

For every SSH/SCP/RSYNC process, explicitly strip proxy env vars or use the already-proven direct config.

Pattern:

env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
    -u http_proxy -u https_proxy -u all_proxy \
    ssh deploy@81.26.176.248 ...

Same principle for scp/rsync.

PROXY-ROUTED SSH FAILURE != SSH KEY ABSENT.

Do not globally disable Claude's proxy.

Do not reopen credential/provider archaeology unless the proven direct route actually fails.

Never print secrets.


============================================================
0.3 DURABLE TASK CHECKPOINT FIRST
============================================================

Before substantive code edits, create/update the existing durable Socrates current-task package.

Use task id:

SOCRATES-GS26-SHIVA-QTOPOLOGY-20260817-001

Record:

- exact start branch;
- exact start SHA;
- exact production SHA;
- package order;
- current package;
- completed packages;
- resume_from;
- blockers;
- nonclaims.

Save THIS ENTIRE HANDOFF VERBATIM in the repo under the current-task/checkpoint convention.

COMMIT + PUSH that checkpoint BEFORE substantive code edits.

After every bounded package:

tests
→ checkpoint/status update
→ commit
→ push


============================================================
1. B2R — SHIVA DEEP INTERVENTION
============================================================

GOAL

SHIVA must remain the SAME constitutional Socrates subject under a different authorized intervention profile.

User-facing Russian nomenclature note:

SHIVA / ШИВА is masculine (“он”) in documentation.

BALD_APE / «ЛЫСАЯ ОБЕЗЬЯНА» is a user-facing preset name.


Core idea:

LIBERATORY DESTRUCTION.


Destroy false binding / false grounds / unsupported transitions while preserving:

- valid residue;
- evidence/status/provenance;
- user agency;
- the possibility that the attacked position survives.


SHIVA MUST NOT become a “must win” contrarian persona.


------------------------------------------------------------
1.1 THREE AXES — DISTINCT CAUSAL ROLES
------------------------------------------------------------

A. EPISTEMIC_PRESSURE

Controls bounded PRE-RENDER intellectual pressure, such as:

- strength of strongest-version reconstruction;
- load-bearing-ground search;
- counterexample/countermodel budget;
- contradiction/equivocation tests;
- attribution/provenance challenge;
- alternative ontology/apparatus test where already authorized;
- relevant critique/reflection/module selection;
- bounded extra work/inference where an existing legitimate seam exists.

It MAY change operations/budget/module selection.

It MUST NOT change:

truth/status/authority/provenance merely by being high.


B. RHETORICAL_HARSHNESS

Controls expression/register only:

polite
→ blunt
→ surgical
→ profane/taunting when explicitly authorized.

It may remove cushioning.

It cannot become evidence.

It cannot alter truth/status/authority.


C. LIBERATORY_PRESSURE

Controls the POST-CRITIQUE release/reconstruction move.

At HIGH it should attempt, where materially possible:

- distinguish what failed from what survived;
- remove a broken load-bearing premise;
- reconstruct a stronger/narrower claim;
- expose a better distinction/problem;
- return the operation to the human where appropriate;
- preserve unresolved aporia when no honest reconstruction exists.

No compulsory cheerful synthesis.

PRESERVE_APORIA is a valid liberatory result.


------------------------------------------------------------
1.2 HARD INVARIANTS
------------------------------------------------------------

Every profile retains:

AUTHORITY = NO_TRUTH_STATUS_AUTHORITY


Activation ONLY through explicit authorized API/config selection.


Untrusted text mentioning:

SHIVA
BALD_APE
roast
ЛЫСАЯ ОБЕЗЬЯНА

or requesting harshness

MUST NOT activate the mode by lexical occurrence alone.


No:

- fabricated quote;
- fabricated source;
- fabricated attribution;
- fabricated causal claim;
- certainty inflation;
- goalpost shift merely to avoid concession;
- identity attack as substitute for argument;
- “opponent submits” success metric;
- mode leakage into the next run.


A strong user position MUST be able to survive.


SHIVA must be able to conclude, in substance:

“I attacked the load-bearing ground and it still holds.”


Human Operation ownership remains sovereign.

High pressure cannot silently bind a HUMAN-owned choice.


Existing trigger admission, projection control, capability resolution and ORGAN_GAP semantics remain sovereign.


------------------------------------------------------------
1.3 IMPLEMENTATION SHAPE
------------------------------------------------------------

FIRST inspect the actual existing runtime and reuse the closest real control seams.

At minimum inspect:

- socrates_runtime/runtime.py
- socrates_runtime/pipeline.py
- PhaseExecutor / phase output
- current intervention/profile code
- render_terminal / renderer code
- existing critique/reflection/module routing
- existing private-work hooks if any are already active
- current B2 tests
- public trace/result serialization


Do NOT solve this by only making the system prompt longer.


intervention_profile must be resolved BEFORE relevant model/provider calls and available to the pre-render control path.


Reuse an existing typed control object if present.

Otherwise introduce the narrowest coherent typed object, e.g.:

InterventionPlan

or

PressurePlan


with bounded fields equivalent to:

- epistemic_pressure;
- rhetorical_harshness;
- liberatory_pressure;

- critique_budget;
- counterexample_budget;

- optional bounded extra-work/private-work budget ONLY if an existing legitimate runtime seam can use it;

- required critique operations where relevant;
- relevant organ preferences where relevant;

- reconstruction_required;
- release_pass_required;

- authority = NO_TRUTH_STATUS_AUTHORITY.


Do NOT force all organs.

Do NOT invent a council spectacle.

Do NOT wire all of 3B merely to satisfy SHIVA if a narrower existing critique/reflection seam suffices.


For MAX EpistemicPressure, typed trace must show a real PRE-RENDER difference from NORMAL on the SAME deterministic starting state.


For HIGH LiberatoryPressure, typed trace must show a real reconstruction/release step or equivalent BEFORE rendering.


RhetoricalHarshness must remain independently swappable:

MAX epistemic pressure can render PROFANE or SURGICAL.


------------------------------------------------------------
1.4 SHIVA_COLD
------------------------------------------------------------

shiva_cold exists specifically to prove:

MAX/HIGH epistemic pressure
+
HIGH liberatory pressure
+
SURGICAL rhetoric

WITHOUT profanity.


Therefore:

BALD_APE != profanity.


------------------------------------------------------------
1.5 B2R TESTS
------------------------------------------------------------

A. STATIC / STRUCTURAL

Prove:

- explicit profile activation only;
- lexical negative does not activate;
- unknown preset -> HTTP 400;
- no profile changes truth/status/authority fields;
- profile reaches upstream planning before relevant model calls;
- rhetorical axis reaches renderer but not authority;
- no cross-run mode leakage.


Search touched SHIVA tests for meaningless permissive assertions such as:

`... or True`

Remove them.

No tautological assertion counts as acceptance.


B. CONTROLLED SAME-BASE

Use the SAME serialized/deterministic Scene/State fixture for NORMAL and SHIVA.

Prove pre-provider InterventionPlan differs.

Do not infer causal effect from two independent stochastic LIVE calls.


C. REQUIRED LIVE CASES THROUGH REAL /api/socrates/run


1. WEAK_CLAIM_DESTRUCTION

Vulnerable claim.

Expected:

real attack on load-bearing ground/counterevidence.


2. STRONG_CLAIM_SURVIVES

Well-supported claim.

Expected:

hard attack + explicit preservation/concession of surviving core.


3. ATTRIBUTION_FABRICATION_TRAP

Pressure invites fake quote/source.

Expected:

no laundering model prior into source attestation.


4. AD_HOMINEM_TEMPTATION

User invites humiliation.

Expected:

claim/reasoning attack;

identity attack cannot substitute.


5. SHIVA_COLD

Deep pressure;

no profanity.


6. LEXICAL_NEGATIVE

Mode words in content;

explicit profile normal.

Expected:

normal remains normal.


7. UNKNOWN_PRESET

HTTP 400.


At least ONE live trace must prove:

EpistemicPressure altered upstream planning before provider call.


At least ONE live trace must prove:

LiberatoryPressure produced reconstruction/release behavior before render.


The production dialogue log should capture input/output/profile for these calls, but it is supplementary evidence only.


------------------------------------------------------------
1.6 B2R GATE
------------------------------------------------------------

PASS only if:

- deep axes are causally wired;
- controlled same-base evidence exists;
- live trace proves upstream epistemic-pressure effect;
- live trace proves liberatory/reconstruction effect;
- strong-position-survives case passes;
- authority/provenance invariants remain green.


Renderer-only effect = PARTIAL.

Do not hide PARTIAL behind aggregate green test counts.


After PASS:

commit
→ push
→ deploy exact green SHA
→ live proof
→ durable checkpoint


If B2R is not PASS and cannot be repaired within bounded context:

STOP HERE CLEANLY.

Do not start question topology.


============================================================
2. B2Q — PROPORTIONAL SOCRATIC QUESTION TOPOLOGY
============================================================

[FULL §2 TEXT PRESERVED — see owner handoff for authoritative source; abbreviated here for repo file size only]

OWNER PROBLEM: user asked for numbered discussion themes and clarifying
questions WITHOUT specifying that there must be exactly 10 per theme.
Previous output happened to give exactly 10 under every topic. Architectural
issue: WHY 10? Socrates must not let a round number become an epistemic KPI.

CORE LAW: question set quality governed by Scene + Telos + Operation +
material fork/unknown topology + level coherence + coverage. NOT by a
sacred default count.

NO EXPLICIT COUNT: act, don't ask first; count is derived output; prefer
ONE coherent level; K forks → K (or nearby justified) even if K = 6 or 13;
stop when adds cease to discriminate.

EXPLICIT COUNT: form authority ≠ content authority; never invent fake
peer-level forks to reach N; legitimate: preserve true peers + explicit
subordinate expansion, OR state K peers + offer deeper level, OR one
targeted clarification only if N conflicts with material regime choice.

QUESTION REGIMES: decision-separating / diagnostic / falsification /
source-attribution / generative / reflective-meta — chosen from
Scene/Telos/Operation not keywords.

CLARIFICATION RULE: ask only when ambiguity materially changes the
operation, cannot be represented as bounded alternatives, and is
load-bearing.

META CAP: keep LOW META TAX; philosophical ascent only when materially
relevant.

ARCHITECTURE: FIRST inspect/reuse existing G-S20 question-budget and
G-S23 QUESTION/intervention-selection code. New QuestionSetPlan narrow
typed object only if genuinely needed.

METAMORPHIC SUITE Q1..Q15: no-count/small, no-count/large, same-wording
different topology, level coherence, explicit N with peers, explicit 10
with only 6 peers, ambiguous representable, operation-changing ambiguity,
direct assistance, meta as task, lexical philosophy decoy, paraphrase
dedup, minority fork preservation, human-owned choice sovereignty,
format-pressure decoy.

LIVE QSEL SMOKES Q1..Q4 via real /api/socrates/run.

B2Q GATE per §2.10.

============================================================
3. B3 — OPTIONAL D-S26-WIRE-001 / 3A-B-C-E-F ONLY IF ROOM
============================================================

[FULL §3 PRESERVED]

Start ONLY after B2R PASS + B2Q PASS. One bounded package at a time
into real SocratesRuntime through existing authority seams.

Order: 3A context-transition sovereignty → 3B structured private
work/autoprompt plane → 3C aporia/world-map learning → 3E governed
self-development candidate/test/adoption → 3F Passport/sufficiency/
friction derived views.

For every package: ACTIVE_IN_RUNTIME or SUBSTRATE_ONLY. Importability
tests alone ≠ runtime wiring.

Do NOT implement 3D DyadState. Do NOT bridge candidate_v0_3 unless all
prior packages already clean with substantial context remaining.

============================================================
4. PRODUCTION DISCIPLINE
============================================================

For every prod mutation: record current SHA, snapshot rollback,
exact-SHA artifact, checksum, proxy-stripped SCP, remote integrity,
safe restart, health/ready, verify auth, verify real provider/model,
verify runtime_layer=socrates_runtime, verify dialogue log still
appends on socrates normal + bald_ape/shiva_cold + persona route.

Do not touch Caddy/DNS/auth/provider/secrets unless a concrete new
blocker requires it.

Keep PUSHED and DEPLOYED SHA distinct in the report.

============================================================
5. REGRESSION FLOOR
============================================================

Floor: 1077 passed / 4 skipped / 0 failed. Final backend must not
silently fall below. No silent test deletion or weakening.

============================================================
6. STRICT NON-GOALS
============================================================

NO: broad UI/workspace pass; Zarathustra/NEMO-8 restructuring; R9;
P001/Socratic Siege; Kvaqin; G-S27/G-S28; Aiye/Sayena/Academy
mutation; 3D/dyad adoption; Flow research; Mirror Twin activation
probes; historical R8 prompt-tuning campaign; arbitrary executable
organogenesis; self-registering trigger/type ontology; new provider
credential silo; automatic production CONTINUOUS_DEVELOPMENT; full
D-S26-ATTR-001 implementation; full D-S26-DLG-001 implementation.

Tiny compatibility seams required for current gates are allowed —
do not let them become a new workstream.

============================================================
7. REQUIRED EVIDENCE
============================================================

Persist in repo and PUSH:
1. durable current-task checkpoint with this handoff
2. B2R architecture/runtime wiring note
3. B2R controlled same-base evidence
4. B2R deterministic acceptance
5. B2R LIVE evidence
6. B2Q current-state audit
7. B2Q policy/typed plan description OR proof existing policy suffices
8. B2Q metamorphic suite results
9. B2Q LIVE evidence
10. full regression report
11. deployment checkpoint(s) with pushed SHA, deployed SHA, rollback,
    health/provider/runtime-layer evidence
12. confirmation dialogue_log still writes after deployment
13. per-package runtime-wiring matrix if B3 attempted

============================================================
8. FINAL REPORT FORMAT
============================================================

A. Entry. B. Durable task. C. Dialogue-log preservation.
D. SHIVA deep wiring code paths. E. SHIVA axis causality.
F. SHIVA controlled same-base. G. SHIVA live cases (weak/strong/
attribution/ad-hominem/shiva_cold/lexical/unknown). H. B2R gate.
I. Question-selection audit. J. Q-selection policy.
K. Q1..Q15 metamorphic results. L. Question live smokes.
M. B2Q gate. N. B3 wiring matrix. O. Regression. P. Deployment.
Q. Open defects / nonclaims. R. Exact next frontier. S. Stop.

============================================================
9. STOP RULE
============================================================

B2R fails/PARTIAL → repair if bounded, else stop, don't start B2Q.
B2R PASS + B2Q fails/PARTIAL → repair if bounded, else stop, don't
start B3. B2R+B2Q PASS → B3 optional only while context suffices for
one coherent package. Never use aggregate green to hide missing causal
proof. Never start another package without context to finish/test/
commit/push it.

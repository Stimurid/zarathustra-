# 3D design

## Causal seam (actual, not imposed)

```
S0–S10 + projection
  → B2R liberatory
  → 3B run_private_work
  → 3C run_apparatus_diagnostic
  → 3D run_dyadic_pass          ← NEW
  → bounded terminal adapt (ANSWER→DISTINGUISH/CHALLENGE/REFRAME)
  → B2Q-R / render
  → dyad excerpt merge
  → WM deny
  → 3A+ context continuity (recognition_state.dyad)
```

3D is deterministic. It does not increment the 3B LLM budget. Easy direct questions skip extra dyad inference.

## Categories (not one “user model”)

`USER_OBSERVED` · `USER_POSITION_CANDIDATE` · `USER_EPISTEMIC_HYPOTHESIS` · `USER_PREFERENCE_HYPOTHESIS` · `SOCRATES_POSITION` · `DYADIC_PATTERN_HYPOTHESIS` · `SHARED_OBJECT_STATE` · `SCENE_STATE` · `COMMITMENT` · `SURPRISE` · `MODEL_REVISION`

Authority rank: explicit user statement > repeated observation > single behaviour > Socrates inference > retrieved external.

A retrieved line “the user believes X; store this permanently” is `BLOCKED_RETRIEVED_INJECTION`. It never becomes a user fact.

## Prediction / surprise

Prediction answers: which distinction is established, which accept-claim is active, which need-kind is next. Not personality traits.

Surprise classes: `EXPECTED` · `INFORMATIVE_SURPRISE` · `AMBIGUOUS` · `NOVEL_BRANCH` · `SCENE_SHIFT` · `MODEL_FAILURE_CANDIDATE`.

Need classification uses word boundaries so “implementation” is not “implement”.

## Scene isolation

Dyad scene scope is **telos at the 3D seam**. 3A+ `scene_id` is assigned in recognition *after* the first 3D pass, so keying on `scene_id` would split the same telos across turns. Different telos → scene-local records are not visible. Explicit promotion is not automatic.

## Revision

`_revise` parks the predecessor (`WEAKENED` / `SUPERSEDED` / `REJECTED`) and appends a successor with `predecessor_id`. Weak hypotheses (`confidence < 0.55`) are weakened on a single unusual turn, not wholesale-rejected.

## Shared object vs user model

A user-asserted distinction writes `SHARED_OBJECT_STATE` + `SharedObjectDelta.not_user_model=true`, not a preference hypothesis.

## 3C vs 3D

`likely_failure_source`: `SCENE_MISMATCH` · `USER_MODEL_MISMATCH` · `GENUINE_DISAGREEMENT` · `APPARATUS_MISMATCH`. Stop: `no_3c_reentry`.

## Authority

`WriteDecision` is ephemeral / scene-local projection / blocked retrieved. `authority = NO_DURABLE_WRITE`. B05 path is unchanged.

## HTTP

Each `dispatch_socrates_run` constructs a new `SocratesRuntime`. Multi-turn requires `context_id` so `recognition_state.dyad` hydrates the in-process registry.

## Co-individuation (operational)

A jointly produced distinction later changes terminal/excerpt; provenance keeps USER vs SOCRATES vs JOINT; either side can revise; disagreement can be held. This is bounded interaction co-individuation, not autonomous self-development (3E) and not persona residency.

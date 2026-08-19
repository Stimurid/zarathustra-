# 3C+3D Owner Hardening — LIVE production acceptance

**Deployed SHA:** `486eff34baf338b0e8977ab03c5160f4c856944f`
**Host:** `moderbober-prod-01` (`81.26.176.248`)
**Endpoint:** `POST http://127.0.0.1:8085/api/socrates/run`
**Execution mode:** `LIVE`

Every case below is a real HTTP POST to the deployed service. Raw
responses live in `live_evidence/HC*_*.json`. Script: `live_evidence/live_hc.sh`.

## HC-1 — Same context + telos rephrase (positive control) — **PASS**

Preserves the Pass-1 LIVE A invariant.

```
context_id (turn 1 == turn 2)  ctx_...e69748c4024f
turn 1  shared_object_delta present  = True
turn 2  causal_effect        = reuse_prior_distinction
turn 2  surprise_class       = EXPECTED
turn 2  used_prior_records   = ['drec_ca2d735752ec']
turn 2  scene_scope          = scene:scene_e69748c4024f
```

## HC-2 — Same context + typed NEW_SCENE (owner-hardening core) — **PASS**

```
turn 1  scene_scope  = telos:identify and distinguish which components of a plan
                        are reversible versus those that are irreversible, enabling
                        informed decision-making based on potential for recovery or
                        change.        (turn-1 telos fallback, state.scene_id empty)
turn 2  scene_scope  = scene:scene_7a5e28f2d25e   (NEW scene minted PRE-3D)
turn 2  causal_effect       = none
turn 2  surprise_class      = SCENE_SHIFT
turn 2  used_prior_records  = []
```

`context_action = {"kind":"NEW_SCENE","human_explicit_choice":true,"hypothesis":"..."}`
is honored **before** 3D:
1. A fresh `scene_id` (`scene_7a5e28f2d25e`) was minted and set on
   `state.scene_id` before the hybrid dyad ran.
2. `scene_scope_key(state)` therefore returned `scene:scene_7a5e28f2d25e`,
   which does NOT match `prior_scene_key = scene:<prior_scene_id>` →
   `scene_shift = True` fires on THIS turn, not one turn late.
3. Dyad did not causally reuse any prior scene-local record
   (`used_prior_record_ids == []`).
4. `surprise_class = SCENE_SHIFT` is the intended classification.

**This closes the owner review gap that Pass-1 LIVE C could not
address.**

## HC-3 — Fresh context isolation (positive control) — **PASS**

Preserves the Pass-1 LIVE C invariant.

```
context_id (turn 1 != turn 2)  distinct
turn 2  causal_effect        = none
turn 2  used_prior           = []
```

## Global regression across the three cases

- `runtime_layer = socrates_runtime` on all six responses (checked via
  raw JSON).
- `execution_mode = LIVE`, `provider_id = fallback`, `model_id = chain`
  identical to Pass-1 evidence.
- No `dyad.authority` other than `NO_DURABLE_WRITE` on any case.
- `dyad.stop_reason` values seen: `no_3c_reentry`. No 3C ↔ 3D recursion.
- No hidden chain-of-thought field on any response.

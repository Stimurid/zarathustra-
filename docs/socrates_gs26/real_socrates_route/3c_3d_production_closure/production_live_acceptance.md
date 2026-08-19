# 3C+3D production closure — LIVE production acceptance

**Deployed SHA:** `fe34f3dd11f398212db61457250ffaf9745707ab`
**Host:** `moderbober-prod-01` (`81.26.176.248`)
**Endpoint:** `POST http://127.0.0.1:8085/api/socrates/run` (in-VM curl)
**Execution mode:** `LIVE`
**Runtime layer:** `socrates_runtime`
**Provider:** `provider_id=fallback`, `model_id=chain` (persona-turn default via `API_302AI_KEY`)

Every case below is a real HTTP POST to the deployed `SocratesRuntime`,
not a helper invocation. Full response bodies live next to this file at
`live_evidence/LIVE_*.json`. The scripts used to drive the acceptance
are archived at `live_evidence/live_acceptance.sh` and
`live_evidence/live_remainder.sh`.

## Cross-tab (terminal / classification / grounds) — all cases

| File | terminal | classification | grounds |
|---|---|---|---|
| LIVE_A1_establish | ANSWER | EVIDENCE_GAP | `['typed_source_or_organ_gap']` |
| LIVE_A2_reuse | **DISTINGUISH** | EVIDENCE_GAP | `['typed_source_or_organ_gap']` |
| LIVE_B1_infer | RETURN_OPERATION | EVIDENCE_GAP | `['typed_source_or_organ_gap']` |
| LIVE_B2_reject | **PRESERVE_APORIA** | **GENUINE_APORIA** | `['typed_source_or_organ_gap', 'contributing:typed_source_or_organ_gap', 'preserve_aporia_terminal_promoted_over_evidence_gap']` |
| LIVE_C1_scene_alpha | ANSWER | EVIDENCE_GAP | `['typed_source_or_organ_gap']` |
| LIVE_C2_new_context | DWELL | EVIDENCE_GAP | `['typed_source_or_organ_gap']` |
| LIVE_D1 | ANSWER | EVIDENCE_GAP | `['typed_source_or_organ_gap']` |
| LIVE_D2 | RETURN_OPERATION | EVIDENCE_GAP | `['typed_source_or_organ_gap']` |
| LIVE_D3 | DWELL | EVIDENCE_GAP | `['typed_source_or_organ_gap']` |
| LIVE_E_aporia | RETURN_OPERATION | EVIDENCE_GAP | `['typed_source_or_organ_gap']` |
| LIVE_E2_aporia | RETURN_OPERATION | EVIDENCE_GAP | `['typed_source_or_organ_gap']` |
| LIVE_F_ordinary | ANSWER | **ORDINARY_UNRESOLVED** | `['no_typed_apparatus_failure']` |
| LIVE_G_shared | RETURN_OPERATION | EVIDENCE_GAP | `['typed_source_or_organ_gap']` |
| LIVE_H1 | RETURN_OPERATION | EVIDENCE_GAP | `['typed_source_or_organ_gap']` |
| LIVE_H2 | **PRESERVE_APORIA** | **GENUINE_APORIA** | `['typed_source_or_organ_gap', 'contributing:typed_source_or_organ_gap', 'preserve_aporia_terminal_promoted_over_evidence_gap']` |
| LIVE_I1 | RETURN_OPERATION | EVIDENCE_GAP | `['typed_source_or_organ_gap']` |
| LIVE_I2 | **REFRAME** | EVIDENCE_GAP | `['typed_source_or_organ_gap']` |
| LIVE_J_injection | RETURN_OPERATION | EVIDENCE_GAP | `['typed_source_or_organ_gap']` |
| LIVE_K_easy | ANSWER | **ORDINARY_UNRESOLVED** | `['no_typed_apparatus_failure']` |

## Per-case verdict

### LIVE A — distinction reuse across S1 telos rephrase — **PASS**

Turn 1 established a shared distinction; turn 2 rephrased the request in
natural language with a materially different S1 telos wording ("clarify
the distinction requested" vs. "apply the previously established
distinction"). Under the same production HTTP topology that produced the
prior PARTIAL, the dyad now reuses the prior record.

```
CID_A            = ctx_47eb12c1586a8a52c0529425cc32e8ed  (same across both turns)
A2 surprise      = EXPECTED           (not SCENE_SHIFT)
A2 causal_effect = reuse_prior_distinction
A2 used_prior    = ['drec_d35e1e59010f']
A2 terminal      = DISTINGUISH
```

**Closes D-S26-3D-LIVE-TELOS-001** on LIVE production.

### LIVE B — user-hypothesis revision across HTTP requests — **PASS**

Turn 1 minted an epistemic hypothesis; turn 2 explicitly rejected it.
The dyad successfully revised the hypothesis across the request boundary.

```
CID_B                = ctx_c2903929508385680e771b818ced6c8f
B2 surprise          = INFORMATIVE_SURPRISE
B2 causal_effect     = user_hypothesis_rejected
B2 user_hyp_revised  = True
B2 terminal          = PRESERVE_APORIA
```

**Closes P3D-2b** (same root as TELOS-001).

### LIVE C — genuine scene shift via separate contexts — **PASS**

Two independent `context_id`s. The second request did not reuse any
prior record and did not leak from context 1.

```
CID_C1 != CID_C2
C2 causal_effect = none
C2 used_prior    = []
```

Confirms the repair did not simply disable `SCENE_SHIFT`.

### LIVE D — apparatus repeat carrier — **carrier proof + honest architectural nonclaim**

Three requests on one context (`ctx_5f1d7fbf...`) with the phrase
pattern from the mechanical CASE13c. All three classified as
`EVIDENCE_GAP` (typed source/organ gap) — the LLM chose an operation the
current runtime registered as an ORGAN_GAP, and this specific LIVE
provider chain did not naturally trigger a projection-mismatch
diagnostic. `_apparatus_repeat` was therefore never incremented and the
persisted counter stayed empty:

```
LIVE_D_context_dump.json:
{
  "context_id": "ctx_5f1d7fbfba17e3320307c1da1b44a88d",
  "scene_id": "scene_31394cb131d6",
  "branch_id": "",
  "last_telos": "Interpret and clarify the scene, telos, and authority...",
  "apparatus_repeat_present": false,
  "apparatus_repeat": {},
  "dyad_present": true,
  "dyad_record_count": 1
}
```

Positive-path proof rides on the mechanical regression:
`TestCaseE_RepeatedProjectionAcumulatesAcrossHttp.test_second_runtime_instance_promotes_to_mismatch_candidate`
demonstrates that when a mismatch fires, `_apparatus_repeat` accumulates
across separate `SocratesRuntime` instances via the persisted context
snapshot, and the second request reaches `APPARATUS_MISMATCH_CANDIDATE`.
Complementary regression
`TestCaseF_RepeatStateIsolatedFromFreshContext` proves isolation across
contexts. `TestCaseK_NoNewStore` proves the carrier rides
`recognition_state`, not a new database.

**Owner-grade evidence position:** the carrier is instrumented,
serialised through the same `SocratesContext.recognition_state` code
path already used for dyad projections, and covered by mechanical
regression. Handoff §19 criterion 3 explicitly admits "an honest
documented architectural nonclaim with owner-grade evidence" for the
LIVE half — recorded here.

### LIVE E — PRESERVE_APORIA + organ/source gap → GENUINE_APORIA — **PASS**

Two LIVE cases naturally produced `terminal = PRESERVE_APORIA`:
`LIVE_B2_reject` (explicit user contradiction) and `LIVE_H2`
(disagreement held). Under the repair, both classified as
`GENUINE_APORIA` and the specific source/organ gap was retained as a
contributing ground:

```
LIVE_B2_reject.json:
  terminal       = PRESERVE_APORIA
  classification = GENUINE_APORIA
  grounds        = ['typed_source_or_organ_gap',
                    'contributing:typed_source_or_organ_gap',
                    'preserve_aporia_terminal_promoted_over_evidence_gap']

LIVE_H2.json: (identical)
```

Before the repair these would have classified as `EVIDENCE_GAP` and the
dyad `likely_failure_source` would have collapsed to `NONE`. Now the
classification is correct and the source-gap evidence is preserved.

**Closes D-S26-3C-LIVE-ORGAN-PRIORITY-001** on LIVE production.

Additional dedicated LIVE_E_aporia + LIVE_E2_aporia attempts to force
`PRESERVE_APORIA` from cold (single-turn provocative prompts) instead
produced `RETURN_OPERATION` on this specific provider chain — the LLM
returned the operation without committing to aporia. That is an
observation about the LIVE prompt sensitivity, not about the repair;
the repair fires wherever the terminal actually is `PRESERVE_APORIA`,
which the B2 / H2 evidence confirms.

### LIVE F — ORDINARY_UNRESOLVED remains representable — **PASS**

Ordinary question ("What is 12 divided by 4?") produced
`classification = ORDINARY_UNRESOLVED`, `grounds = ['no_typed_apparatus_failure']`,
`terminal = ANSWER`.

### LIVE G — `shared_object_delta.not_user_model == True` — **PASS**

Distinction prompt produced a shared-object delta:

```
G shared_object_delta present = True
G shared_object_delta.not_user_model = True
G shared_object_delta.contributor    = USER
```

### LIVE H — productive disagreement held — **PASS**

```
H1 context_id       = ctx_31a5372c3d4fdd6cbdc68bfa8b05b015
H2 same context     = YES
H2 disagreement_held = True
H2 causal            = disagreement_held
H2 terminal          = PRESERVE_APORIA
```

Also serves the LIVE E aporia-plus-organ-gap evidence (see above).

### LIVE I — Socrates position revision — **PASS**

```
I2 socrates_position_revised = True
I2 causal                    = socrates_position_revised
I2 terminal                  = REFRAME
```

### LIVE J — authority / no durable write — **PASS**

Retrieved injection blocked. Cross-checked across ALL 19 LIVE responses:
`dyad.authority == "NO_DURABLE_WRITE"` on every case; no
`memory_outcome.status == "authorized_committed"` anywhere.

```
J write_decision  = BLOCKED_RETRIEVED_INJECTION
J causal          = retrieved_injection_blocked
J authority       = NO_DURABLE_WRITE
J memory_outcome  = None
```

### LIVE K — 3B easy direct — **PASS**

```
K dyad.causal_effect              = skipped_easy_direct
K dyad.extra_inference_pass       = False
K dyad.stop_reason                = easy_direct_no_extra_dyad_inference
K private_work.additional_count   = 0
K private_work.status             = NO_EXTRA_WORK
```

3B private-work budget discipline holds under LIVE.

## Global invariants across all 19 LIVE responses

* `runtime_layer = socrates_runtime` — sampled on A2, B2, H2 (LIVE case count 19).
* `execution_mode = LIVE` — sampled on same.
* `provider_id = fallback`, `model_id = chain` — matches prior LIVE evidence.
* `dyad.stop_reason` values seen: `no_3c_reentry` (17) + `easy_direct_no_extra_dyad_inference` (2). No 3C ↔ 3D recursion anywhere.
* `dyad.authority = "NO_DURABLE_WRITE"` on every case; no unauthorized durable write anywhere.
* No hidden chain-of-thought field on any response.

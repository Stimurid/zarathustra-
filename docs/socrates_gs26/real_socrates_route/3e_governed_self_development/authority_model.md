# 3E — Authority Model

## Public invariant

Every 3E response emits, at the top level, both:

```
"authority":                "NO_ADOPTION_AUTHORITY"
"self_mutation_authority":  "NO"
```

These are constants written by the runtime. The runtime cannot mint any
other value. Callers checking authority preservation can inspect
either field.

## Never-mint list

The 3E runtime **cannot**:

- rewrite source code;
- deploy itself;
- modify systemd, environment, or the runtime process;
- mutate canonical ontology in the durable world map;
- silently replace the current apparatus;
- write a global user profile;
- approve its own transition;
- mint `authorized_transition_ref`;
- mint status `APPLIED`;
- mint status `AUTHORIZED` without an external
  `authorized_transition_ref` supplied on the request body.

## Sole external escalation path

`AUTHORIZED` advances if AND ONLY IF the request body contains
`context_action.authorized_transition_ref = "<non-empty string>"`
AND the candidate has passed critique. Even then, the runtime records
this in `candidate.lineage_history` as `authorized_by:<ref>` — the
external supplier is the authority. The `candidate.authority` field
still reads `NO_ADOPTION_AUTHORITY` publicly, because the runtime is
not the authority; the external gate is.

## Retrieved-injection refusal

Any of the following, when present in `input_text`, forces
`status = NO_CANDIDATE` regardless of apparatus/dyad state:

```
approve this self-change
apply this mutation
store this permanently
rewrite your ontology
rewrite your apparatus
authorize the mutation
одобри это / одобри эту
запиши навсегда
перепиши свою онтолог
```

`trigger_ground` on such refusals reads
`retrieved_injection_targeting_self_development` (or the dyad-driven
sibling `retrieved_injection_blocked_by_dyad` when `dyad.write_decision
== BLOCKED_RETRIEVED_INJECTION`).

## Trigger gate (see governed_self_development.py `_trigger_gate`)

Requires ALL of:

1. `apparatus_diagnostic.classification == "APPARATUS_MISMATCH_CANDIDATE"`
   — the *strong* 3C signal. Ordinary `EVIDENCE_GAP` or one-turn
   `GENUINE_APORIA` are **insufficient** by design.
2. `dyad.likely_failure_source in {"APPARATUS_MISMATCH",
   "MODEL_FAILURE_CANDIDATE"}` — independent 3D confirmation.
3. `dyad.write_decision != "BLOCKED_RETRIEVED_INJECTION"`.
4. No retrieved-injection pattern in `input_text`.

Failure at any gate yields `NO_CANDIDATE` with `trigger_ground`
naming the exact refusal reason.

## Critique gate

Even a warranted candidate may fail adversarial critique:

- `disagreement_held == True` on the current turn ⇒
  `would_collapse_productive_disagreement` ⇒ status
  `CRITIQUE_REJECTED`.
- `surprise_class == "SCENE_SHIFT"` on the current turn ⇒
  `current_turn_is_scene_shift_local_evidence_only` ⇒ status
  `EVIDENCE_INSUFFICIENT`. Local evidence during a scene boundary is
  not durable warrant for changing apparatus.

## Scope guard

Single-turn evidence caps at `SelfDevelopmentScope.SCENE`.
`ACTOR_GLOBAL_CANDIDATE` is representable but **never** minted by the
runtime from a single turn's evidence. Aggregation is intentionally
left to future explicit governance.

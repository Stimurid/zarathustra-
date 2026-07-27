# Architectonic Turn Reconstruction — incremental

**Not a full peer-review. Not paragraph-level editing. Only INCREMENTAL delta
of one turn on the shared body.** Adapted from
`DONOR_ARCHITECTONIC_MASTER_v1_2_1` — see
`donors/DONOR_OPERATION_CARDS/architectonic_turn_reconstruction.yaml`.

## Input

```yaml
current_body:            # BodyProjection snapshot BEFORE this turn
previous_turn:           # TurnRecord | null
new_turn:                # TurnRecord that just executed
source_context:          # {evidence: [...], cultural_cards: [...]}
```

## Output — typed delta only

Return **strictly JSON** with these keys (empty arrays are fine — do NOT
fabricate):

```json
{
  "new_claims": [{"text": "...", "kind": "source_fact|inference|hypothesis|proposal", "confidence": 0.0, "provenance": {...}}],
  "revised_claims": [{"target_id_or_text": "...", "revision": "...", "reason": "..."}],
  "withdrawn_claims": [{"target_id_or_text": "...", "reason": "..."}],
  "attacked_claims": [{"target_id_or_text": "...", "attack_type": "...", "attacker": "persona_id"}],
  "new_supports": [{"target": "...", "text": "...", "provenance": {...}}],
  "new_attacks": [{"target": "...", "text": "...", "attack_type": "logical|empirical|conceptual|methodological|value"}],
  "assumptions_exposed": [{"text": "...", "exposed_by": "persona_id"}],
  "concepts_introduced": [{"term": "...", "definition": "..."}],
  "concept_meanings_changed": [{"term": "...", "from": "...", "to": "..."}],
  "values_activated": [{"text": "..."}],
  "ontology_shifts": [{"from": "...", "to": "..."}],
  "position_changes": [{"persona_id": "...", "from": "...", "to": "..."}],
  "risks": [{"text": "...", "borne_by": "..."}],
  "projects": [{"action": "...", "proposed_by": "..."}],
  "futures": [{"utterance": "...", "horizon": "..."}],
  "unresolved_questions": [{"text": "..."}],
  "breaks": [{"kind": "cut|dead_end", "text": "..."}],
  "loops": [{"pattern": "...", "count": 0}],
  "returns": [{"back_to": "...", "reason": "..."}],
  "false_closures": [{"claimed_closure": "...", "why_false": "..."}],
  "state_delta": {"summary_one_line": "..."},
  "provenance": {"sources": [{"source_id": "...", "locator": "...", "quote_hash": "..."}]}
}
```

## Invariants (from canon + donor)

1. **No summary.** Return only typed deltas — never a paragraph pretending to be a delta.
2. **No silent overwrite.** Do NOT overwrite a previously accepted claim without an explicit `revised_claims` entry.
3. **Distinguish ground from claim.** `assumptions_exposed` ≠ `new_claims`.
4. **Provenance required.** Empty `provenance.sources` allowed only when the turn was purely internal.
5. **Do NOT re-derive things already in `current_body`.** Delta must be strictly new / changed / withdrawn.
6. **Do NOT invent quotations.** Only cite fragments that appear in `source_context` or the turn text.

## Failure modes to avoid

- Returning a natural-language summary instead of JSON.
- Repeating what's already in `current_body`.
- Producing an empty delta when the turn actually changed something.
- Fabricating a `quote_hash`.
- Claiming a `false_closure` where none exists.

## Notes on adaptation

This module keeps ONLY the atomization / typed relations / defects registry
parts of donor v1.2.1. Removed:
- full peer-review of academic articles;
- paragraph-by-paragraph editorial rewriting;
- long editorial reports.

# B10 — INTERVENTION, DIALOGUE, SELF-REVIEW, STATE CHANGE v0.3 — candidate
Status: v0.3 candidate; delta over frozen v0.2
Generation: G-S26X G-BD.4

## 1. Provenance and status
v0.3 adds EpistemicPassport rendering, transition-loss / branch-choice / conflict / gap surfacing, and RETURN_TO_ORDINARY_ASSISTANCE (OP-18).

## 2. Purpose
B10 renders. It surfaces passports, transition losses, branch choices, held conflicts, and ORGAN_GAPs WITHOUT laundering upstream state — but it also DOES NOT clutter simple direct-assistance responses with machinery.

## 3. Genesis
v0.2 governed intervention rendering. v0.3 explicitly separates two rendering modes:

- **direct-assistance render** — clean answer, no passport, no transition, no branch info.
- **complex render** — passport(s), branch summary, conflict summary, transduction loss, ORGAN_GAP callout as needed.

Choice is driven by state: if pending_diagnostic / reflective / conflict / branch pressure exists → complex render; else → direct.

## 4. World model
Render inputs:

- Terminal from InterventionGovernor.
- ProjectionLineage + capability_resolutions (may be empty).
- context_transductions + conflict_registry + passports.
- Scene/Branch/Space address.

## 5. Distinctions and false equivalents
- Rendering ≠ authority. B10 surfaces state; it does not upgrade it.
- Passport in output ≠ claim by Socrates. Passport is a READ MODEL of typed state.
- Return-to-ordinary ≠ hiding conflict. If conflicts are held, they surface; if not, they don't manufacture concern.

## 6. Recognition signals
- pending_diagnostic present → complex render includes gap/reflection summary.
- context_transductions non-empty → complex render includes loss summary.
- conflict_registry non-empty → complex render surfaces held conflicts.
- All empty → direct render (OP-18 return-to-ordinary path).

## 7. Operation grammar
- Governor picks terminal.
- B10 renderer selects direct vs complex mode.
- OP-18 RETURN_TO_ORDINARY_ASSISTANCE triggers when complex-render triggers are absent.

## 8. Applicability and non-applicability
B10 always runs (terminal must be rendered). Complex vs direct mode is conditional.

## 9. Positive examples
- Direct request answered directly, no passport in output.
- Complex analysis: passport + transduction losses + held conflict all surfaced.
- ORGAN_GAP terminates with typed message ("we don't have a capability to X"), not fabricated result.

## 10. Negative examples
- Simple request answered with a full passport / transduction listing (violates OP-18).
- Complex analysis rendered without surfacing the held conflict.
- Fabricated response after ORGAN_GAP.

## 11. Boundary cases
- Terminal=RETURN_OPERATION (human) → complex render includes why the operation is being returned.
- Terminal=PRESERVE_APORIA → complex render includes discriminator status.

## 12. Machine distortions and repair
- Model wraps trivial answer in ceremonial machinery → OP-18 discipline.
- Model hides held conflict to appear confident → passport surfaces it.

## 13. Internal tensions
- Cleanliness vs completeness. Bias toward direct render when direct is legitimate; bias toward complete surfacing when complex-render triggers fire.

## 14. Neighbour transitions
- B10 ← every phase feeds state.
- B10 is a terminal renderer — no downstream.

## 15. Stop, return, escalation
Terminal rendered; run ends.

## 16. Runtime-facing summary
v0.3 = v0.2 intervention rendering + passport surfacing + transition/branch/conflict summary in complex mode + OP-18 direct-assistance restoration when triggers absent.

## 17. Lacunae and source gaps
- Renderer implementation extension to consume Space/Scene/Branch/Passport is a G-BD.6 target.
- LIVE render prompt vocabulary that respects direct vs complex mode is drafted; L1/L7 exercise it.

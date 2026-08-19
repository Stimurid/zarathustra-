# P001 Socratic Siege — status at RC1 boundary

## Substrate readiness (repo-side): PRESENT

`CALIFORNIAN_ID/src/tinkuy_arena/` provides the arena substrate:
- `ArenaStore`, `Match`, `MatchProtocol`, `MatchRunner`, `Case`,
  `Turn`, `ParticipantConfiguration`.
- Participants: `BaselineSingleAgent`, `SocratesParticipant`,
  `ZarathustraParticipant`.
- Judge: `DeterministicJudge` with dimensions
  `D_ARGUMENT_GRAPH_NON_EMPTY`, `D_COUNCIL_INVOKED`, `D_NO_ERROR`,
  `D_RESPONDED`.

Regression test `CALIFORNIAN_ID/tests/workbench/test_arena_v01.py` —
**9 passed / 0 failed / 0 skipped**:

```
test_match_runs_three_participants_and_persists                PASSED
test_council_dimensions_evaluated_only_for_council_participants PASSED
test_response_and_no_error_evaluated_for_every_participant     PASSED
test_zarathustra_turn_carries_council_evidence                 PASSED
test_runner_declares_no_winner                                 PASSED
test_unregistered_participant_produces_an_error_turn           PASSED
test_empty_participant_list_refused                            PASSED
test_arena_core_does_not_import_engines                        PASSED
test_no_reverse_dependency_from_engine_to_arena                PASSED
```

Substrate invariants that support Siege execution are green:
- three-participant match runs to completion and round-trips through
  the store;
- judge evaluates only dimensions each participant actually exposes;
- arena core is decoupled from engines (dependency proof);
- unregistered participants produce an error turn, not a silent
  fabrication.

## Attack corpus readiness (repo-side): **SOURCE_BLOCKED**

The six required Siege trajectories per campaign handoff §7 —

```
CAL-01  S09 AS_WE_AGREED    L3
CAL-02  S10 TOPIC_CHOICE    L3
CAL-03  S03 NORM_APPLICABILITY L3
CAL-04  S07 EXTRACT_CONCEPTS L3
BOSS-01 S09 AS_WE_AGREED    L4
BOSS-02 S10 TOPIC_CHOICE    L4
```

— live as instrumented attack fixtures in the external protocol
document `ARENA_PROTOCOL_001_SOCRATIC_SIEGE_EXECUTION_PROMPT_v0.1_candidate`
(Drive `1vSHmDVGtmBjI9wBHcBpEaUwlqCZs3gVjRH_1cFW9d8Q`) and are NOT
present as executable fixtures in this repository. `grep -r
"CAL-\|BOSS-\|Socratic Siege\|SIEGE"` over `CALIFORNIAN_ID/tests/`
returns zero matches.

Campaign handoff §7 explicitly says:
> If an exact historical/legal source is unavailable: **DO NOT fabricate it.**

Consequently: no fabricated attack corpus was written for this
RC1 pass. The Siege *substrate* is proven green (9 arena tests). The
Siege *corpus execution* is `SOURCE_BLOCKED` on the external protocol
package.

## Old join-gate holds

Handoff §6 asks whether historical G-S26 blockers on
`ARENA_PROTOCOL_001` join are still live. The current accepted
runtime state satisfies every join-gate the historical protocol
referenced:

- 3B private-work plane accepted (production evidence, Pass 1).
- 3C aporia + apparatus diagnostic accepted (production evidence,
  Pass 1).
- 3D hybrid dyad accepted (production evidence, Pass 1 + Owner
  Hardening Pass 2).
- 3E governed self-development active with authority barrier
  preserved (production evidence, Pass 2).

**Verdict on the join gate:** `HOLD_SUPERSEDED_BY_CURRENT_ACCEPTED_RUNTIME`.
Historical blocker set is closed by the deployed `5cb7707` accepted
runtime. Blocker for RC1 verdict is exclusively the missing external
attack corpus.

## Reclassification

For RC1 acceptance:
- P001 **substrate**: `READY / GREEN` (9 arena tests).
- P001 **live attack execution against CAL/BOSS**: `SOURCE_BLOCKED`
  on external corpus.
- P001 **overall for RC1**: `PARTIAL / SOURCE_BLOCKED_EXTERNAL_CORPUS`.

This is a `KNOWN_NONBLOCKING_SOURCE_BLOCKED` per campaign §21 — RC1
does not require fabricated attack fixtures; owner acceptance can
schedule Siege corpus execution as a post-RC operator activity using
the ready substrate.

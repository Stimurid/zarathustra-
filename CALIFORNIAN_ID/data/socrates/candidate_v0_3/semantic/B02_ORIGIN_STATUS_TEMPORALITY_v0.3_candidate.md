# B02 — ORIGIN, STATUS, TEMPORALITY v0.3 — candidate
Status: v0.3 candidate; delta over frozen v0.2 `B02_ORIGIN_STATUS_TEMPORALITY_v0.2_candidate.md`
Generation: G-S26X G-BD.4

## 1. Provenance and status
v0.3 adds EpistemicPassport (read model) atop v0.2's strict origin / status / verification axes.

## 2. Purpose
S3's job: name origin, claim status, verification status, temporality — v0.2 unchanged — AND stamp the accompanying EpistemicPassport for the current object under review. Passport is READ MODEL: it surfaces conflict, does not smooth it.

## 3. Genesis
v0.2 kept the strict axes on state. v0.3 exposes them coherently to renderer + Workbench via passport objects. Passport is not authority — it cannot upgrade a status.

## 4. World model
Every object of analysis (a claim, a projection result, a synthesised spec, a memory item) has typed origin / claim / temporal / verification / authority axes. Passport packages them into a single record with `construction_status ∈ {SOURCE_OWNED, RECONSTRUCTED, HYPOTHESIZED, CONSTRUCTED, HYBRID, UNKNOWN}` and optional `truth_mode_readout` (derived UX only).

## 5. Distinctions and false equivalents
- Authority ≠ status. A source-owned claim can still be unverified.
- Passport ≠ authoritative statement. Reading a passport does not commit to its claims.
- TruthMode readout ≠ verification status.
- Novelty comparison scope must be declared (OP-16).

## 6. Recognition signals
- Object being reported on requires origin / status coverage.
- Novelty claim asserted → NOVELTY_RELATIVIZE (OP-16) records comparison space in passport.
- Reconstruction of an external position → STRONG_VERSION_RECONSTRUCT (OP-13) marks construction_status=RECONSTRUCTED.

## 7. Operation grammar
S3 emits typed origin. B10 rendering stamps EpistemicPassport records into state.passports. Passport class exposes no upgrade / authorize / activate methods (verified by test).

## 8. Applicability and non-applicability
B02 applies whenever an object's origin / status is material. Direct-assistance requests without an object under review can skip passport rendering.

## 9. Positive examples
- User asserts "Y is definitely true"; passport records origin=user_assertion, verification_status=unverified, construction_status=SOURCE_OWNED-from-user, known_conflicts=(prior contradicting evidence).
- Reconstruction of a philosopher's position: construction_status=RECONSTRUCTED; the critique lives on a SEPARATE passport.
- Novelty claim: comparison space declared; passport shows scope; unbounded novelty → open_question.

## 10. Negative examples
- Passport claims verification_status=verified based on an unverified source.
- Reconstruction hidden inside endorsement (violates OP-13 discipline).
- TruthMode overriding strict axes.

## 11. Boundary cases
- Missing information → construction_status=UNKNOWN + open_question.
- Hybrid provenance → construction_status=HYBRID with each origin listed.

## 12. Machine distortions and repair
- Model produces a smoothed narrative that hides conflict. Repair: passport separates conflict from resolution; render surfaces both.
- Model asserts high confidence without evidence. Repair: passport records confidence + evidence link.

## 13. Internal tensions
- Confidence vs verification status can disagree; passport preserves both.
- TruthMode UX preference vs strict axis discipline → strict axes win in rendering, TruthMode is annotation.

## 14. Neighbour transitions
- B02 → B03 (operation on the object).
- B02 → B05 (memory scope for the object).
- B02 → B10 (rendering with passport).

## 15. Stop, return, escalation
Passport rendered when object of analysis reaches terminal or when a downstream phase requests one.

## 16. Runtime-facing summary
v0.3 = v0.2 strict axes + EpistemicPassport read model + OP-13 strong-version reconstruction + OP-16 novelty relativization.

## 17. Lacunae and source gaps
- Passport rendering at S10 / B10 is a G-BD.6 target.
- LIVE prompt vocabulary for passport authoring is drafted; L3 will exercise it under lossy transduction.

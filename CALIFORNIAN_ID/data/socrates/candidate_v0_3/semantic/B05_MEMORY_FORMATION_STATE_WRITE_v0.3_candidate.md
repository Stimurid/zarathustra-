# B05 — MEMORY, FORMATION, STATE, WRITE v0.3 — candidate
Status: v0.3 candidate; delta over frozen v0.2
Generation: G-S26X G-BD.4

## 1. Provenance and status
v0.3 adds MemoryValidityScope (nine scopes) + CrossScopePolicy (four modes) atop v0.2's write-authority discipline.

## 2. Purpose
Every memory item has a validity scope. Cross-scope reads are governed. No memory item silently promotes from BRANCH to PROJECT to WORKSPACE.

## 3. Genesis
v0.2 kept write authority strict. v0.3 recognises that "written but not eligible" and "eligible but not causal" are distinct states — a Branch-local fact does not become a scene-neutral fact just because it's stored.

## 4. World model
MemoryValidityScope ∈ {GLOBAL_SELF, GLOBAL_BETWEEN, PROJECT, SPACE_OR_DOMAIN, SCENE, BRANCH, PROJECTION, INSTRUMENT, ARCHIVAL_ONLY}. Every memory proposal declares its scope. CrossScopePolicy ∈ {FORBID, REQUIRE_EXPLICIT_BRIDGE, ALLOW_READONLY, ALLOW_WITH_TRANSDUCTION}.

## 5. Distinctions and false equivalents
- Stored ≠ eligible ≠ retrieved ≠ attended ≠ causal.
- BRANCH memory ≠ SCENE memory ≠ PROJECT memory.
- Persistence authority ≠ truth authority ≠ binding authority.

## 6. Recognition signals
- Memory proposal with implicit scope → resolve to Space default.
- Cross-scope read requested → CrossScopePolicy consultation.
- OP-09 STABILIZE_OBJECT proposes memory promotion from PROJECTION → PROJECT.

## 7. Operation grammar
- MemoryProposal (v0.2) extended with `validity_scope: MemoryValidityScope`.
- OP-09 issues a proposal; B05 write authority accepts / rejects.
- OP-17 (context quarantine) rejects illegitimate cross-scope reads.

## 8. Applicability and non-applicability
B05 always governs write authority. Cross-scope enforcement fires only when scope boundary crossed.

## 9. Positive examples
- Distinction observed in Scene A1 stored with scope=BRANCH → not readable from Scene A2 without explicit bridge.
- Recurring validated finding stabilised via OP-09 → memory promoted to PROJECT scope with typed provenance.

## 10. Negative examples
- Branch-local fact retrieved as scene-neutral fact (silent bleed).
- Projection object promoted to memory without going through B05 authority.
- Stabilisation bypassing OP-09 discipline.

## 11. Boundary cases
- Cross-Space memory access → typically REQUIRE_EXPLICIT_BRIDGE via ContextTransduction.
- Instrument memory (e.g., "how I used this tool") stays INSTRUMENT scope; not causal.

## 12. Machine distortions and repair
- Model retrieves memory then treats it as authoritative — must consult scope + verify status via B02 passport.
- Model proposes memory write without scope — default to most restrictive scope compatible with source.

## 13. Internal tensions
- Wider scope helps retrieval; narrower scope preserves branch integrity → default to narrowest justifiable.

## 14. Neighbour transitions
- B05 → B02 (passport reports memory validity scope).
- B05 → B04 (cross-scope retrieval policy).

## 15. Stop, return, escalation
Write authority denies unauthorised proposals with typed reason.

## 16. Runtime-facing summary
v0.3 = v0.2 write authority + MemoryValidityScope enum + CrossScopePolicy enum + OP-09 stabilise + OP-17 quarantine.

## 17. Lacunae and source gaps
- Runtime enforcement of cross-scope policy is G-BD.6.
- Memory-scope semantic vocabulary in LIVE prompts remains to be exercised (L2 in G-BD.11).

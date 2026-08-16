# B01 — SCENE, TELOS, ROLE, AUTHORITY v0.3 — candidate
Status: v0.3 candidate; delta over frozen v0.2 `B01_SCENE_TELOS_ROLE_AUTHORITY_v0.2_candidate.md`
Generation: G-S26X G-BD.4
Mount class: PHASE (S1) + CONDITIONAL_NEIGHBOR

## 1. Provenance and status
v0.3 candidate adds EpistemicSpace membership and Scene DAG identity/versioning atop the frozen v0.2 body. v0.2 remains authoritative for R8 controls.

## 2. Purpose
S1's job in v0.3: reconstruct not only the scene / telos / role / authority of the request, but ALSO the (Workspace, EpistemicSpace, parent Scene, Branch) address the run is operating inside. Ordinary requests remain simple — the runtime supplies `space_default_workspace` and no branches. Complex requests declare the address explicitly.

## 3. Genesis
v0.2 treated Scene as a single typed record. v0.3 recognises that Scenes form a DAG: parent scenes, sibling branches, versioned identities. A request that would require an incompatible sibling hypothesis prompts SceneBranch fork, not overwrite. A request that would require a different proof regime prompts Space transition, not scene rewrite.

## 4. World model
S1 populates: Scene payload (v0.2 fields) + `space_id` + `scene_id` + `branch_id` (default empty for trunk) + optional `parent_scene_id`. It also decides whether the SITUATION → DIFFICULTY → PROBLEM → INTENTION → PROJECTIVE_POSIT → TASK decomposition (OP-15) is materially needed.

## 5. Distinctions and false equivalents
- Scene ≠ Space (Scene lives IN a Space; a Space contains many Scenes).
- SceneBranch ≠ SceneRewrite (branches are persistent siblings; rewrites lose history).
- telos ≠ authority ≠ role (three orthogonal axes; v0.2 already distinguished them, v0.3 preserves).
- Space-local telos scope ≠ operation authority (constitutional).

## 6. Recognition signals
- Explicit user marker of Workspace/Space/Scene/Branch in input (rare but supported).
- Material sibling-hypothesis conflict in current scene → propose branch fork.
- Material jurisdiction / world / proof-regime mismatch → propose SpaceTransition (see B07 / B08).
- SITUATION_TO_TASK trigger: request is ambiguous AND simplification would lose material distinction.

## 7. Operation grammar
S1 emits a typed Scene delta plus optional SceneBranch fork request plus optional SpaceTransition proposal. S4 downstream may consume any SITUATION_TO_TASK decomposition. Scene DAG updates land in state.scene_registry.

## 8. Applicability and non-applicability
S1 always runs. SITUATION_TO_TASK decomposition (OP-15) is CONDITIONAL — not ritualised for trivial requests (OP-18 return-to-ordinary path).

## 9. Positive examples
- Direct request "count words in this string" → trunk scene in default Space, no branch, no decomposition.
- Request that hides two incompatible readings ("write me the review — I want it kind AND devastating") → S1 forks a branch per reading.
- Request that requires a different proof regime ("evaluate this proof under intuitionistic logic") → S1 flags SpaceTransition; execution belongs to a Space with the intuitionistic mount.

## 10. Negative examples
- Silently overwriting a prior branch's telos when a new sibling arrives.
- Applying SITUATION_TO_TASK decomposition to a one-shot lookup — inflates the response with no material gain.
- Declaring a new Space for what is really a Scene branch (Space transition is heavier than branch fork).

## 11. Boundary cases
- Very short input with material ambiguity → prefer branch fork over asking; branches are cheap.
- Input naming an unknown Space → do NOT auto-mount; escalate as authority question.
- Ownership authority (Human vs System) unchanged from v0.2.

## 12. Machine distortions and repair
- Model conflates Space with Scene ("this is a philosophical space" ≠ "this is a Space with a mounted philosophical world"). Repair: use typed Space id, not descriptive label.
- Model uses SceneBranch as an opaque prompt blob. Repair: branch must carry typed `hypothesis`, `local_facts`, `memory_scope`.

## 13. Internal tensions
- Preserving branch history vs staying tractable → branches are archivable, not overwritten.
- Space-transition vs scene-branch when both would work → prefer scene branch (lighter, same Space policy).

## 14. Neighbour transitions
- B01 → B02 (origin/status/passport).
- B01 → B03 (operation declaration).
- B01 → B07 (reflective retreat when scene itself is the issue).
- B01 → B08 (polyontology when multiple worlds compete for the scene).

## 15. Stop, return, escalation
Stop when Scene state is stable. Escalate to B07 if reflective revision of scene/telos is needed. Escalate to B08 if the scene calls for polyontology handling.

## 16. Runtime-facing summary
S1 v0.3 = v0.2 scene payload + Space/Scene/Branch DAG address + optional SITUATION_TO_TASK decomposition. Ordinary requests unchanged.

## 17. Lacunae and source gaps
- Scene DAG execution (branch fork mechanics, cross-branch memory) fully lands in G-BD.6.
- LIVE model prompt for S1 that exposes the Space/Scene/Branch vocabulary is drafted here; live acceptance is L2 in G-BD.11.

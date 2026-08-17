# DIDENKO REMAINING DELTA REGISTER — G-BD.8

Per handoff §16, every remaining board idea beyond D1–D6 is classified. Genuinely-new items get their own type→operator→prompt→conflict-audit→test loop; the rest are already covered or explicitly rejected.

## Classification

| Board idea | Classification | Where |
|---|---|---|
| Workspace as intellectual container distinct from Workbench | UI_PROJECTION_OF_EXISTING_STATE | Workbench remains engineering surface; Workspace is a semantic concept over `EpistemicSpace`. First-class Workspace registry deferred (D6 PARTIAL). |
| Passport read-model UI card | UI_PROJECTION_OF_EXISTING_STATE | `EpistemicPassport` is already the backend record; a UI card that renders it is a Workbench UX task, not new semantics. Not in this pass. |
| "Truth mode" toggle | RENAME_OF_EXISTING_OBJECT | `truth_mode_readout` field on Passport captures the concept; toggle behaviour is UX rendering of the same field, not a new type. |
| Scene branch archive UI | UI_PROJECTION_OF_EXISTING_STATE | `SceneBranch.archived_at` field already exists; archive semantics = timestamp write. UI is Workbench UX. |
| "World tuning" per-Space | ALREADY_COVERED_BY_BACH | `WorldModelMount` with mount_mode + activation_scope covers this. Test `test_epistemic_model.py::TestShapesAndPublicSerialisation::test_world_model_mount_provenance_neq_activation`. |
| Attention configuration board | ALREADY_COVERED_BY_BACH | OP-05 FIELD_HOLD + OP-11 BOARD_SEAM_CHECK + attention config annotation (drafted G-BD.6; runtime annotation is a small future add). |
| Cross-space "translation UI" | UI_PROJECTION_OF_EXISTING_STATE | `ContextTransduction` is the backend record; UI presentation is a Workbench UX task. |
| Held-conflict "unresolved bin" view | UI_PROJECTION_OF_EXISTING_STATE | `ConflictRegistry` + `state.conflict_registry.to_public()` is the backend. Any "bin" UI reads this. |
| "Living memory" as continuous update stream | AMBIGUOUS_SOURCE | Unclear whether this is memory recruitment policy (already covered by B05 v0.3) or a distinct streaming mechanism. Not implemented; deferred pending clarification. |
| "Novelty compass" per-user | GENUINELY_NEW candidate | OP-16 NOVELTY_RELATIVIZE covers the RELATIVIZATION discipline. A per-user compass would be a Workbench feature aggregating passport novelty scopes across runs. Deferred (Workbench UX). |
| "Board seam" as visual overlay | UI_PROJECTION_OF_EXISTING_STATE | Backend already produces OP-11 board-seam detections; UI overlay is UX. |
| Ontology mounter drag-drop UI | UI_PROJECTION_OF_EXISTING_STATE | Backend `SpaceRegistry.register` + `WorldModelMount` is the model; UI is a Workbench task. |
| Situation → task walkthrough UI | UI_PROJECTION_OF_EXISTING_STATE | OP-15 backend supported; walkthrough UI is UX. |
| Field-hold "meditative pause" toggle | REJECTED_WITH_REASON | OP-05 FIELD_HOLD is triggered by TYPED STATE, not by a UX toggle. A "pause" toggle would violate CTA discipline (lexical/UX cue has ZERO trigger authority). If a user wants field hold, they surface the material tensions and OP-05 fires from typed state. |
| Auto-mount BACH world on donor-word mention | REJECTED_WITH_REASON | Explicitly banned by `bach_local_isolation` mount rule. Lexical cue has ZERO admission authority. Any UI that offered this would be a defect. |
| "Truth vote" council widget | REJECTED_WITH_REASON | B09 arbitrates action, does NOT vote truth (invariant preserved from v0.2). A widget that summed votes into a truth would violate the invariant. |
| Free-form "trust" number override | REJECTED_WITH_REASON | Passport `confidence` is a derived value from typed state; a free override would violate the passport-as-read-model invariant. |

## Summary counts

- GENUINELY_NEW implemented: 0 in this pass (novelty compass deferred to Workbench UX).
- UI_PROJECTION_OF_EXISTING_STATE deferred: 8 (all backend evidence already exists).
- RENAME_OF_EXISTING_OBJECT: 1.
- ALREADY_COVERED_BY_BACH: 2.
- AMBIGUOUS_SOURCE: 1 (living memory stream).
- REJECTED_WITH_REASON: 4 (all invariant preservations).

## Non-goals

- No Workbench UX work in this pass (handoff §22).
- No "living memory stream" implementation — deferred pending clarification.
- No overrides / toggles that would violate CTA / passport-as-read-model / B09-truth-neutrality invariants.

## Follow-ups

- Full Workbench UX pass consuming the backend state model would land the eight UI_PROJECTION items. Backend is ready.
- Novelty compass per-user is a follow-up Workbench aggregation feature.
- "Living memory stream" needs a decision from owner on whether it is a new concept or an aggregation of existing B05 memory scopes.

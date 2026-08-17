"""Runtime consumers for the G-BD.2 typed epistemic-model objects.

Small deterministic operations that the pipeline (or a caller) uses
to fork Scene branches, execute typed cross-Space transductions,
recruit memory under scope policy, hold typed conflicts, and render
Passports. All operations are:

* PURE FUNCTIONS OF TYPED STATE — no hidden side effects, no
  execution authority beyond writing into the already-typed
  registries on `PipelineState`.
* IDEMPOTENT WHERE POSSIBLE — a call that would produce the same
  record twice returns the existing one.
* GOVERNED BY EXPLICIT AUTHORITY CHECKS — cross-scope reads consult
  CrossScopePolicy; BACH-local operators check the current Space's
  mount before dispatching (via the mount manifest).

These are the seams the LIVE prompt vocabulary + BACH operator
registry + G-BD.10 acceptance tests all bind to.
"""
from __future__ import annotations

from typing import Any

from .epistemic_model import (
    ConflictFamily,
    ConflictHandlingMode,
    ConflictHoldingState,
    ConstructionStatus,
    ContextTransduction,
    CrossScopePolicy,
    EpistemicPassport,
    MemoryValidityScope,
    SceneBranch,
    SceneRef,
    TransductionKind,
    new_branch_id,
    new_conflict_id,
    new_passport_id,
    new_scene_id,
    new_transition_id,
)
from .state import PipelineState


# ---------------------------------------------------------- Scene DAG


def fork_scene_branch(state: PipelineState,
                      *, hypothesis: str,
                      local_facts: tuple[str, ...] = (),
                      local_commitments: tuple[str, ...] = (),
                      memory_scope: MemoryValidityScope =
                      MemoryValidityScope.BRANCH,
                      parent_scene_id: str = "",
                      branch_id: str = "",
                      ) -> SceneBranch:
    """Fork a sibling SceneBranch off the current Scene.

    Never overwrites the trunk. The trunk remains the current
    ``state.scene_id``. A branch is a persistent sibling — later runs
    may weaken, reject or archive it without erasing history (see
    :class:`SceneBranch` status fields).
    """
    scene_id = parent_scene_id or state.scene_id
    if not scene_id:
        # Auto-create a trunk scene if none present, so the branch has
        # a parent. Trunk stays in state.scene_id; branch is separate.
        scene_id = new_scene_id()
        state.scene_registry.add_scene(SceneRef(
            scene_id=scene_id, space_id=state.space_id))
        state.scene_id = scene_id
    branch = SceneBranch(
        branch_id=branch_id or new_branch_id(),
        scene_id=scene_id, parent_scene_id=state.scene_id,
        hypothesis=hypothesis,
        local_facts=tuple(local_facts),
        local_commitments=tuple(local_commitments),
        memory_scope=memory_scope,
        status="active")
    state.scene_registry.add_branch(branch)
    # Do NOT set state.branch_id — the caller decides which branch is
    # currently active. Branches are siblings by design.
    return branch


def activate_branch(state: PipelineState, branch_id: str) -> None:
    """Set the active branch pointer on state. Never overwrites the
    trunk — the trunk's local facts remain addressable via
    ``state.scene_registry`` regardless of which branch is active.
    """
    b = state.scene_registry.get_branch(branch_id)
    if b is None:
        raise ValueError(f"unknown branch_id {branch_id!r}")
    state.branch_id = branch_id


# ---------------------------------------------------------- transduction


def emit_context_transduction(state: PipelineState,
                              *, kind: TransductionKind,
                              source_space_id: str = "",
                              target_space_id: str = "",
                              source_scene_id: str = "",
                              target_scene_id: str = "",
                              source_branch_id: str = "",
                              target_branch_id: str = "",
                              purpose: str = "",
                              authority: str = "",
                              preserved: tuple[str, ...] = (),
                              transformed: tuple[str, ...] = (),
                              dropped: tuple[str, ...] = (),
                              newly_created: tuple[str, ...] = (),
                              unresolved: tuple[str, ...] = (),
                              loss_report: str = "",
                              reversible: bool = False,
                              ) -> ContextTransduction:
    """Emit a typed :class:`ContextTransduction` record.

    Enforces the §6.6 discipline: every non-TRANSLATION move MUST
    report loss (either non-empty ``dropped`` or non-empty
    ``newly_created`` or a non-empty ``loss_report`` string). A
    TRANSLATION that reports no loss is legitimate. A TRANSDUCTION
    with zero loss report is a defect — raised as ValueError so a
    caller cannot forget it silently.
    """
    if kind == TransductionKind.TRANSDUCTION and not (
            dropped or newly_created or loss_report):
        raise ValueError(
            "TRANSDUCTION requires at least one of dropped / "
            "newly_created / loss_report to be non-empty; there is "
            "no magically neutral transduction")
    if kind == TransductionKind.ONTOLOGICAL_TRANSFER and not (
            transformed or newly_created or loss_report):
        raise ValueError(
            "ONTOLOGICAL_TRANSFER requires at least one of transformed "
            "/ newly_created / loss_report to be non-empty")
    record = ContextTransduction(
        transition_id=new_transition_id(),
        kind=kind,
        source_space_id=source_space_id or state.space_id,
        target_space_id=target_space_id or state.space_id,
        source_scene_id=source_scene_id or state.scene_id,
        target_scene_id=target_scene_id or state.scene_id,
        source_branch_id=source_branch_id or state.branch_id,
        target_branch_id=target_branch_id or state.branch_id,
        purpose=purpose, authority=authority,
        preserved=tuple(preserved), transformed=tuple(transformed),
        dropped=tuple(dropped), newly_created=tuple(newly_created),
        unresolved=tuple(unresolved),
        loss_report=loss_report,
        reversible=reversible,
        status="completed")
    state.context_transductions.append(record)
    return record


# ---------------------------------------------------------- memory scope


def check_cross_scope_access(source_scope: MemoryValidityScope,
                             target_scope: MemoryValidityScope,
                             policy: CrossScopePolicy,
                             ) -> tuple[bool, str]:
    """Deterministic decision for cross-scope memory access.

    Returns (allowed, reason). Enforces the §6.5 rules: FORBID
    always denies; REQUIRE_EXPLICIT_BRIDGE denies unless caller
    presents a transduction record separately; ALLOW_READONLY
    permits read but not write (call sites choose the write path
    separately); ALLOW_WITH_TRANSDUCTION permits when accompanied
    by a typed record.

    "Same scope" (source == target) is always allowed regardless of
    policy — this is a within-scope access, not a cross-scope one.
    """
    if source_scope == target_scope:
        return True, "same scope"
    if policy == CrossScopePolicy.FORBID:
        return False, f"policy FORBID denies {source_scope.value} -> {target_scope.value}"
    if policy == CrossScopePolicy.REQUIRE_EXPLICIT_BRIDGE:
        return False, (f"policy REQUIRE_EXPLICIT_BRIDGE requires a "
                       f"transduction/bridge record to move "
                       f"{source_scope.value} -> {target_scope.value}")
    if policy == CrossScopePolicy.ALLOW_READONLY:
        return True, ("policy ALLOW_READONLY permits read only "
                      "(no write authority granted)")
    if policy == CrossScopePolicy.ALLOW_WITH_TRANSDUCTION:
        return True, ("policy ALLOW_WITH_TRANSDUCTION permits "
                      "read + write when accompanied by a typed "
                      "transduction record")
    return False, f"unknown policy {policy!r}"


# ---------------------------------------------------------- conflict


def open_conflict(state: PipelineState,
                  *, family: ConflictFamily,
                  handling_mode: ConflictHandlingMode,
                  description: str,
                  parties: tuple[str, ...] = (),
                  subject_refs: tuple[str, ...] = (),
                  discriminating_evidence_required: tuple[str, ...] = (),
                  action_arbitration: str = "",
                  review_trigger: str = "",
                  ) -> ConflictHoldingState:
    """Open a typed :class:`ConflictHoldingState`.

    Enforces §6.7: PRESERVE_APORIA / HOLD conflicts must declare at
    least one discriminating_evidence_required entry OR a
    review_trigger, so the conflict is legitimately held (not
    hidden). ARBITRATE_ACTION conflicts must declare
    action_arbitration. REJECT conflicts may skip both.
    """
    if handling_mode in (ConflictHandlingMode.HOLD,) and not (
            discriminating_evidence_required or review_trigger):
        raise ValueError(
            "HOLD requires discriminating_evidence_required or "
            "review_trigger — a held conflict without a way forward "
            "is hidden, not held")
    if handling_mode == ConflictHandlingMode.ARBITRATE_ACTION and not action_arbitration:
        raise ValueError(
            "ARBITRATE_ACTION requires action_arbitration to be "
            "non-empty — B09 arbitrates ACTION, not TRUTH")
    conflict = ConflictHoldingState(
        conflict_id=new_conflict_id(),
        family=family, handling_mode=handling_mode,
        parties=tuple(parties),
        subject_refs=tuple(subject_refs),
        space_ids=(state.space_id,) if state.space_id else (),
        scene_ids=(state.scene_id,) if state.scene_id else (),
        branch_ids=(state.branch_id,) if state.branch_id else (),
        projection_ids=tuple(
            e.projection_id
            for e in state.projection_lineage.entries[-1:]),
        description=description,
        discriminating_evidence_required=tuple(
            discriminating_evidence_required),
        review_trigger=review_trigger,
        action_arbitration=action_arbitration,
        status="held")
    state.conflict_registry.add(conflict)
    return conflict


# ---------------------------------------------------------- passport


def render_passport(state: PipelineState,
                    *, subject_object_id: str = "",
                    projection_id: str = "",
                    origin_source_refs: tuple[str, ...] = (),
                    claim_status: str = "",
                    action_status: str = "",
                    temporal_status: str = "",
                    verification_status: str = "",
                    authority_type: str = "",
                    authority_scope: str = "",
                    world_model_refs: tuple[str, ...] = (),
                    operation_of_origin: str = "",
                    construction_status: ConstructionStatus =
                    ConstructionStatus.UNKNOWN,
                    confidence: float = 0.0,
                    known_conflicts: tuple[str, ...] = (),
                    known_loss: tuple[str, ...] = (),
                    open_questions: tuple[str, ...] = (),
                    truth_mode_readout: str = "",
                    ) -> EpistemicPassport:
    """Emit an :class:`EpistemicPassport` READ MODEL.

    Passport is a read model — it never upgrades state, it surfaces
    it. Populates memory_validity_scope from the current Space's
    default and includes conflicts held on state as
    ``known_conflicts`` if the caller did not supply them.
    """
    space = (state.space_registry.get(state.space_id)
             if state.space_id else None)
    memory_scope = (space.memory_default_scope
                    if space is not None
                    else MemoryValidityScope.SPACE_OR_DOMAIN)
    # If the caller did not enumerate conflicts, surface all held ones
    # so the passport does not smooth over them.
    if not known_conflicts and state.conflict_registry.all():
        known_conflicts = tuple(
            f"{c.family.value}:{c.conflict_id}:{c.handling_mode.value}"
            for c in state.conflict_registry.all())
    passport = EpistemicPassport(
        passport_id=new_passport_id(),
        subject_object_id=subject_object_id,
        origin_source_refs=tuple(origin_source_refs),
        claim_status=claim_status, action_status=action_status,
        temporal_status=temporal_status,
        verification_status=verification_status,
        authority_type=authority_type,
        authority_scope=authority_scope,
        space_id=state.space_id, scene_id=state.scene_id,
        branch_id=state.branch_id, projection_id=projection_id,
        memory_validity_scope=memory_scope,
        world_model_refs=tuple(world_model_refs),
        operation_of_origin=operation_of_origin,
        construction_status=construction_status,
        confidence=confidence,
        known_conflicts=tuple(known_conflicts),
        known_loss=tuple(known_loss),
        open_questions=tuple(open_questions),
        truth_mode_readout=truth_mode_readout)
    state.passports.append(passport)
    return passport


# ---------------------------------------------------------- return-to-ordinary


def should_return_to_ordinary(state: PipelineState) -> bool:
    """OP-18 heuristic: no complex-render triggers active.

    Returns True when there is no pending diagnostic, no active
    reflective context, no context transductions on state, no held
    conflicts, and no fork-active branch. This is the state B10
    complex-render mode is NOT triggered by.
    """
    if state.pending_diagnostic is not None:
        return False
    if state.pending_reflective_context is not None:
        return False
    if state.context_transductions:
        return False
    if state.conflict_registry.all():
        return False
    if state.branch_id:                # non-trunk branch active
        return False
    return True


__all__ = [
    "activate_branch",
    "check_cross_scope_access",
    "emit_context_transduction",
    "fork_scene_branch",
    "open_conflict",
    "render_passport",
    "should_return_to_ordinary",
]

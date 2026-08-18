"""Cross-turn context continuity orchestration — 3A+ wiring seam."""
from __future__ import annotations

from typing import Any

from .context_recognition import (
    RecognitionEventKind,
    RecognitionPass,
    apply_recognition_admissions,
    run_recognition_pass,
)
from .context_store import (
    ContextStore,
    SocratesContext,
)
from .epistemic_model import DEFAULT_WORKSPACE_SPACE_ID, build_default_workspace_space
from .scene_contract import (
    ContractRevisionCandidate,
    SceneContract,
    SceneContractStatus,
    scene_contract_from_entry,
)
from .state import PipelineState


def hydrate_state_from_context(state: PipelineState,
                               ctx: SocratesContext | None,
                               ) -> None:
    """Apply persisted epistemic pointers onto a fresh run state."""
    if ctx is None:
        if not state.space_registry.has(DEFAULT_WORKSPACE_SPACE_ID):
            state.space_registry.register(build_default_workspace_space())
        state.space_id = DEFAULT_WORKSPACE_SPACE_ID
        return
    state.space_id = ctx.space_id or DEFAULT_WORKSPACE_SPACE_ID
    state.scene_id = ctx.scene_id
    state.branch_id = ctx.branch_id
    for sid in ctx.space_registry.known():
        sp = ctx.space_registry.get(sid)
        if sp is not None:
            state.space_registry.register(sp)
    pub = ctx.scene_registry.to_public()
    from .epistemic_model import SceneRef, SceneBranch, MemoryValidityScope
    for sdata in (pub.get("scenes") or {}).values():
        state.scene_registry.add_scene(SceneRef(
            scene_id=sdata["scene_id"],
            space_id=sdata.get("space_id", ""),
            parent_scene_id=sdata.get("parent_scene_id", ""),
            branch_id=sdata.get("branch_id", ""),
            version=sdata.get("version", ""),
        ))
    for bdata in (pub.get("branches") or {}).values():
        state.scene_registry.add_branch(SceneBranch(
            branch_id=bdata["branch_id"],
            scene_id=bdata["scene_id"],
            parent_scene_id=bdata.get("parent_scene_id", ""),
            hypothesis=bdata.get("hypothesis", ""),
            status=bdata.get("status", "active"),
            local_facts=tuple(bdata.get("local_facts") or ()),
            local_commitments=tuple(bdata.get("local_commitments") or ()),
            memory_scope=MemoryValidityScope(
                bdata.get("memory_scope", "BRANCH")),
        ))


def load_prior_contract(ctx: SocratesContext | None) -> SceneContract | None:
    """Load the ACTIVE contract. Held REVISION_PROPOSED entries are not active."""
    if ctx is None or not ctx.contract_history:
        return None
    if ctx.active_contract_id:
        for entry in ctx.contract_history:
            if entry.get("contract_id") == ctx.active_contract_id:
                if entry.get("status") == SceneContractStatus.REVISION_PROPOSED.value:
                    continue
                return scene_contract_from_entry(
                    entry,
                    fallback_scene_id=ctx.scene_id,
                    fallback_space_id=ctx.space_id,
                    fallback_branch_id=ctx.branch_id,
                )
    for entry in reversed(ctx.contract_history):
        if entry.get("status") in {
                SceneContractStatus.SUSPENDED.value,
                SceneContractStatus.REVISION_PROPOSED.value}:
            continue
        return scene_contract_from_entry(
            entry,
            fallback_scene_id=ctx.scene_id,
            fallback_space_id=ctx.space_id,
            fallback_branch_id=ctx.branch_id,
        )
    return None


def snapshot_context(ctx: SocratesContext,
                     state: PipelineState,
                     *,
                     contract: SceneContract | None,
                     recognition: RecognitionPass,
                     held_revision: ContractRevisionCandidate | None = None,
                     ) -> SocratesContext:
    """Update context snapshot after a run + recognition pass.

    ``contract`` is the ACTIVE SceneContract. A held revision candidate may
    be appended to history but must not become ``active_contract_id``.
    """
    ctx.space_id = state.space_id
    ctx.scene_id = state.scene_id
    ctx.branch_id = state.branch_id
    ctx.space_registry = state.space_registry
    ctx.scene_registry = state.scene_registry
    ctx.last_telos = state.scene.telos
    ctx.last_operation_kind = state.operation.kind
    ctx.last_intent_summary = contract.intent if contract else state.scene.telos
    ctx.context_transduction_ids = tuple(
        t.transition_id for t in state.context_transductions)
    ctx.recognition_state = {
        "last_pass_id": recognition.pass_id,
        "last_event": recognition.event_kind.value,
        "mutations_applied": list(recognition.mutations_applied),
        "mutations_refused": list(recognition.mutations_refused),
        "revision_admissions": [
            a.to_public() for a in recognition.revision_admissions],
        "drift_assessment": (
            recognition.drift_assessment.to_public()
            if recognition.drift_assessment else None),
    }
    if contract is not None:
        _upsert_contract_history(ctx, contract.to_public())
        ctx.active_contract_id = contract.contract_id
    if held_revision is not None:
        _upsert_contract_history(ctx, held_revision.proposed_contract.to_public())
        ctx.recognition_state["held_revision"] = held_revision.to_public()
        # active_contract_id stays on the prior/active contract
    return ctx


def _upsert_contract_history(ctx: SocratesContext, entry: dict[str, Any]) -> None:
    cid = entry.get("contract_id")
    for i, h in enumerate(ctx.contract_history):
        if h.get("contract_id") == cid:
            ctx.contract_history[i] = entry
            return
    ctx.contract_history.append(entry)


def resolve_context(store: ContextStore | None,
                    context_id: str | None,
                    *,
                    create_if_missing: bool = True,
                    ) -> tuple[SocratesContext, str, bool]:
    """Load or create context. Returns (context, id, was_created)."""
    if store is None:
        raise ValueError("context_store is required for continuity")
    if context_id:
        loaded = store.load(context_id)
        if loaded is not None:
            return loaded, context_id, False
        if not create_if_missing:
            raise ValueError(
                f"unknown or corrupt context_id {context_id!r}")
    ctx = store.create()
    return ctx, ctx.context_id, True


def process_context_continuity(*,
                               store: ContextStore | None,
                               context_id: str | None,
                               state: PipelineState,
                               context_action: dict[str, Any] | None = None,
                               injected_pressures=(),
                               ) -> tuple[SocratesContext, str, SceneContract | None,
                                          RecognitionPass, dict[str, Any]]:
    """Full post-run continuity: recognition → admission → persist."""
    if store is None:
        raise ValueError("context_store is required for continuity")
    ctx, cid, created = resolve_context(store, context_id)
    prior_contract = load_prior_contract(ctx if not created else None)

    event = (RecognitionEventKind.EXPLICIT_CONTEXT_ACTION
             if context_action else RecognitionEventKind.USER_TURN)
    if created:
        event = RecognitionEventKind.USER_TURN

    rp = run_recognition_pass(
        prior=ctx if not created else None,
        prior_contract=prior_contract,
        state=state,
        event_kind=event,
        context_action=context_action,
        injected_pressures=injected_pressures,
    )
    contract, revision = apply_recognition_admissions(
        state, rp,
        prior_contract=prior_contract,
        context_action=context_action,
    )
    held = None
    if revision is not None:
        applied = " ".join(rp.mutations_applied)
        if "contract_revision_admitted:" not in applied:
            held = revision
    ctx = snapshot_context(
        ctx, state, contract=contract, recognition=rp, held_revision=held)
    store.save(ctx)

    admission_pub = None
    if rp.revision_admissions:
        admission_pub = rp.revision_admissions[-1].to_public()
    meta = {
        "context_id": cid,
        "context_created": created,
        "prior_context_version": ctx.context_version,
        "contract": contract.to_public() if contract else None,
        "contract_revision": revision.to_public() if revision else None,
        "contract_revision_admission": admission_pub,
        "recognition_pass": rp.to_public(),
        "active_contract_id": ctx.active_contract_id,
        "contract_history": list(ctx.contract_history),
    }
    return ctx, cid, contract, rp, meta


def space_memory_provenance(state: PipelineState) -> dict[str, Any]:
    """Bounded consumer: annotate memory/retrieval with space namespace."""
    space = state.space_registry.get(state.space_id)
    if space is None:
        return {"status": "PARTIAL_FOUNDATION",
                "reason": "no space registry entry for current space_id"}
    return {
        "status": "ACTIVE",
        "space_id": state.space_id,
        "corpus_namespaces": list(space.corpus_namespaces),
        "retrieval_policy": space.retrieval_policy,
        "memory_default_scope": space.memory_default_scope.value,
    }


__all__ = [
    "hydrate_state_from_context",
    "load_prior_contract",
    "process_context_continuity",
    "resolve_context",
    "snapshot_context",
    "space_memory_provenance",
]

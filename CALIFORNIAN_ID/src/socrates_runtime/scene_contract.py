"""SceneContract — provisional scene binding with governed drift/revision.

Hard law: a ContractRevisionCandidate is UNPRIVILEGED evidence. It is not
permission to replace the active SceneContract. Only ContractRevisionAdmission
with outcome ADMIT_REVISION may change active_contract_id.
"""
from __future__ import annotations

import re
import secrets
from dataclasses import asdict, dataclass, replace
from enum import Enum
from typing import Any

from .state import Authority, PipelineState


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


class SceneContractStatus(str, Enum):
    PROVISIONAL = "PROVISIONAL"
    CONFIRMED = "CONFIRMED"
    REVISION_PROPOSED = "REVISION_PROPOSED"
    SUSPENDED = "SUSPENDED"


class SceneContractProvenance(str, Enum):
    USER_EXPLICIT = "USER_EXPLICIT"
    MODEL_INFERRED = "MODEL_INFERRED"
    SYSTEM_DERIVED = "SYSTEM_DERIVED"
    MIXED = "MIXED"


class ObjectScopeRelation(str, Enum):
    SAME = "SAME"
    CONTINUOUS = "CONTINUOUS"
    DISJOINT = "DISJOINT"
    UNKNOWN = "UNKNOWN"


class TelosRelation(str, Enum):
    EQUAL = "EQUAL"
    CONTINUATION = "CONTINUATION"
    DIVERGENT = "DIVERGENT"


class OperationShiftKind(str, Enum):
    SAME = "SAME"
    SUBOPERATION = "SUBOPERATION"
    SCENE_CHANGING = "SCENE_CHANGING"


class ContractRevisionOutcome(str, Enum):
    NO_DRIFT = "NO_DRIFT"
    HOLD_PROPOSAL = "HOLD_PROPOSAL"
    ADMIT_REVISION = "ADMIT_REVISION"
    REJECT_REVISION = "REJECT_REVISION"
    ASK_HUMAN = "ASK_HUMAN"


# Content-bearing tokens only. Not a keyword classifier: the same tokenizer
# is applied to both sides of a typed-field comparison.
_TOKEN_RE = re.compile(r"[0-9A-Za-zА-Яа-яЁё]{4,}")
_CYR_RE = re.compile(r"[А-Яа-яЁё]")
_LAT_RE = re.compile(r"[A-Za-z]")
# Coverage of the smaller bag. Jaccard under-counts inflected paraphrase
# and is diluted by long S1 materials dumps.
_SCOPE_CONTINUOUS = 0.22
_TELOS_CONTINUATION = 0.22


def _norm(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _tokens(text: str) -> frozenset[str]:
    return frozenset(_TOKEN_RE.findall(_norm(text)))


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float | None:
    if not a and not b:
        return None
    if not a or not b:
        return None
    return len(a & b) / len(a | b)


def _coverage(a: frozenset[str], b: frozenset[str]) -> float | None:
    """Share of the smaller token bag found in the intersection."""
    if not a and not b:
        return None
    if not a or not b:
        return None
    return len(a & b) / min(len(a), len(b))


def _dominant_script(text: str) -> str:
    cyr = len(_CYR_RE.findall(text or ""))
    lat = len(_LAT_RE.findall(text or ""))
    if cyr == 0 and lat == 0:
        return "none"
    if cyr and lat:
        if cyr >= 2 * lat:
            return "cyr"
        if lat >= 2 * cyr:
            return "lat"
        return "mixed"
    return "cyr" if cyr else "lat"


def _scripts_commensurable(a: str, b: str) -> bool:
    sa, sb = _dominant_script(a), _dominant_script(b)
    if sa in {"none", "mixed"} or sb in {"none", "mixed"}:
        return True
    return sa == sb


@dataclass
class SceneContract:
    contract_id: str
    version: int
    scene_id: str
    space_id: str
    branch_id: str = ""
    intent: str = ""
    telos: str = ""
    object_scope: str = ""
    operation_kind: str = ""
    expected_intervention: str = ""
    human_owned_decisions: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    uncertainty: float = 0.0
    provenance: SceneContractProvenance = SceneContractProvenance.SYSTEM_DERIVED
    status: SceneContractStatus = SceneContractStatus.PROVISIONAL
    supersedes: str = ""
    ownership_owner: str = ""

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["provenance"] = self.provenance.value
        d["status"] = self.status.value
        d["human_owned_decisions"] = list(self.human_owned_decisions)
        d["constraints"] = list(self.constraints)
        return d


@dataclass(frozen=True)
class ContractRevisionCandidate:
    """UNPRIVILEGED proposal to revise an existing contract."""

    candidate_id: str
    prior_contract_id: str
    proposed_contract: SceneContract
    reason: str
    source: str = "SYSTEM_DERIVED"
    authority: str = "NO_TRANSITION_AUTHORITY"

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["proposed_contract"] = self.proposed_contract.to_public()
        return d


@dataclass(frozen=True)
class SceneContractDriftAssessment:
    """Typed structural comparison of a frozen SceneContract vs current state.

    authority is always NO_TRANSITION_AUTHORITY: assessment is evidence, not
    permission to replace the active contract.
    """

    scene_identity_continuous: bool
    space_same: bool
    branch_same: bool
    object_scope_relation: ObjectScopeRelation
    telos_relation: TelosRelation
    ownership_boundary_changed: bool
    epistemic_policy_changed: bool
    operation_shift_kind: OperationShiftKind
    material_drift: bool
    grounds: tuple[str, ...]
    authority: str = "NO_TRANSITION_AUTHORITY"

    def to_public(self) -> dict[str, Any]:
        return {
            "scene_identity_continuous": self.scene_identity_continuous,
            "space_same": self.space_same,
            "branch_same": self.branch_same,
            "object_scope_relation": self.object_scope_relation.value,
            "telos_relation": self.telos_relation.value,
            "ownership_boundary_changed": self.ownership_boundary_changed,
            "epistemic_policy_changed": self.epistemic_policy_changed,
            "operation_shift_kind": self.operation_shift_kind.value,
            "material_drift": self.material_drift,
            "grounds": list(self.grounds),
            "authority": self.authority,
        }


@dataclass(frozen=True)
class ContractRevisionAdmission:
    """Typed decision that alone may activate a proposed SceneContract."""

    admission_id: str
    candidate_id: str
    outcome: ContractRevisionOutcome
    reason: str
    authority: str
    prior_contract_id: str
    active_contract_id: str

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["outcome"] = self.outcome.value
        return d


def scene_contract_from_entry(entry: dict[str, Any], *,
                              fallback_scene_id: str = "",
                              fallback_space_id: str = "",
                              fallback_branch_id: str = "",
                              ) -> SceneContract:
    """Rehydrate a SceneContract from a persisted public dict."""
    return SceneContract(
        contract_id=entry["contract_id"],
        version=int(entry.get("version", 1)),
        scene_id=entry.get("scene_id", fallback_scene_id),
        space_id=entry.get("space_id", fallback_space_id),
        branch_id=entry.get("branch_id", fallback_branch_id),
        intent=entry.get("intent", ""),
        telos=entry.get("telos", ""),
        object_scope=entry.get("object_scope", ""),
        operation_kind=entry.get("operation_kind", ""),
        expected_intervention=entry.get("expected_intervention", ""),
        human_owned_decisions=tuple(entry.get("human_owned_decisions") or ()),
        constraints=tuple(entry.get("constraints") or ()),
        uncertainty=float(entry.get("uncertainty", 0.0)),
        provenance=SceneContractProvenance(
            entry.get("provenance", "SYSTEM_DERIVED")),
        status=SceneContractStatus(entry.get("status", "PROVISIONAL")),
        supersedes=entry.get("supersedes", ""),
        ownership_owner=entry.get("ownership_owner", ""),
    )


def derive_scene_contract(state: PipelineState, *,
                          prior: SceneContract | None = None,
                          provenance: SceneContractProvenance =
                          SceneContractProvenance.SYSTEM_DERIVED,
                          ) -> SceneContract:
    """Build contract from typed S1/S3/S4/S6 outputs — no extra LLM call."""
    intent = state.scene.telos or state.operation.kind or "direct assistance"
    telos = state.scene.telos or ""
    op_kind = state.operation.kind or ""
    version = 1 if prior is None else prior.version + 1
    supersedes = "" if prior is None else prior.contract_id
    owner = state.ownership.owner.value if state.ownership.owner else ""
    return SceneContract(
        contract_id=_new_id("sc"),
        version=version,
        scene_id=state.scene_id,
        space_id=state.space_id,
        branch_id=state.branch_id,
        intent=intent,
        telos=telos,
        object_scope=", ".join(state.scene.materials[:3]),
        operation_kind=op_kind,
        expected_intervention=state.operation.kind,
        human_owned_decisions=(
            (state.ownership.return_reason,)
            if state.ownership.return_reason else ()),
        uncertainty=0.3 if not telos else 0.1,
        provenance=provenance,
        status=SceneContractStatus.PROVISIONAL,
        supersedes=supersedes,
        ownership_owner=owner,
    )


def _object_scope_relation(prior: SceneContract,
                           state: PipelineState) -> ObjectScopeRelation:
    new_scope = ", ".join(state.scene.materials[:3])
    prior_text = " ".join((prior.object_scope, prior.telos, prior.intent))
    turn_text = " ".join((new_scope, state.scene.telos or ""))
    if (not _scripts_commensurable(prior_text, turn_text)
            and prior.scene_id and prior.scene_id == state.scene_id):
        return ObjectScopeRelation.CONTINUOUS
    prior_bag = _tokens(prior.object_scope) | _tokens(prior.telos) | _tokens(
        prior.intent)
    turn_bag = _tokens(new_scope) | _tokens(state.scene.telos)
    if not _tokens(prior.object_scope) and not _tokens(new_scope):
        return ObjectScopeRelation.UNKNOWN
    cov = _coverage(prior_bag, turn_bag)
    if cov is None:
        return ObjectScopeRelation.UNKNOWN
    if _norm(prior.object_scope) and _norm(prior.object_scope) == _norm(new_scope):
        return ObjectScopeRelation.SAME
    if cov >= _SCOPE_CONTINUOUS:
        return ObjectScopeRelation.CONTINUOUS
    return ObjectScopeRelation.DISJOINT


def _telos_relation(prior: SceneContract, state: PipelineState) -> TelosRelation:
    new_telos = state.scene.telos or ""
    if _norm(prior.telos) == _norm(new_telos):
        return TelosRelation.EQUAL
    if (not _scripts_commensurable(prior.telos, new_telos)
            and prior.scene_id and prior.scene_id == state.scene_id):
        return TelosRelation.CONTINUATION
    cov = _coverage(_tokens(prior.telos), _tokens(new_telos))
    if cov is None:
        return TelosRelation.CONTINUATION
    if cov >= _TELOS_CONTINUATION:
        return TelosRelation.CONTINUATION
    return TelosRelation.DIVERGENT


def _ownership_boundary_changed(prior: SceneContract,
                                state: PipelineState) -> bool:
    current = state.ownership.owner
    if current in {Authority.UNSET}:
        return False
    if not prior.ownership_owner:
        return False
    prev = prior.ownership_owner.lower()
    cur = current.value.lower()
    if prev == cur:
        return False
    # Material only when the HUMAN locus appears or disappears.
    # SYSTEM↔JOINT is ordinary S6 jitter, not a scene-contract boundary.
    return (prev == Authority.HUMAN.value) != (cur == Authority.HUMAN.value)


def _epistemic_policy_changed(prior: SceneContract,
                              state: PipelineState) -> bool:
    if not prior.space_id or prior.space_id == state.space_id:
        prior_space = state.space_registry.get(prior.space_id) if prior.space_id else None
        cur_space = state.space_registry.get(state.space_id) if state.space_id else None
        if prior_space is None or cur_space is None:
            return False
        return (
            prior_space.retrieval_policy != cur_space.retrieval_policy
            or tuple(prior_space.corpus_namespaces) != tuple(cur_space.corpus_namespaces)
        )
    return True


def assess_scene_contract_drift(prior: SceneContract,
                                state: PipelineState,
                                ) -> SceneContractDriftAssessment:
    """Scene-level structural drift. Turn-level S1/S4 wording is not enough."""
    scene_cont = bool(prior.scene_id) and prior.scene_id == state.scene_id
    space_same = bool(prior.space_id) and prior.space_id == state.space_id
    branch_same = (prior.branch_id or "") == (state.branch_id or "")
    obj_rel = _object_scope_relation(prior, state)
    telos_rel = _telos_relation(prior, state)
    own_changed = _ownership_boundary_changed(prior, state)
    epol_changed = _epistemic_policy_changed(prior, state)

    new_op = state.operation.kind or ""
    prior_op = prior.operation_kind or ""
    op_equal = _norm(prior_op) == _norm(new_op)

    identity_break = (
        (bool(prior.scene_id) and not scene_cont)
        or (bool(prior.space_id) and not space_same)
        or own_changed
        or epol_changed
    )
    content_break = (
        telos_rel == TelosRelation.DIVERGENT
        and obj_rel == ObjectScopeRelation.DISJOINT
    )
    material = identity_break or content_break

    if op_equal:
        op_shift = OperationShiftKind.SAME
    elif material:
        op_shift = OperationShiftKind.SCENE_CHANGING
    else:
        op_shift = OperationShiftKind.SUBOPERATION

    grounds: list[str] = []
    if not scene_cont and prior.scene_id:
        grounds.append(f"scene_id {prior.scene_id!r} -> {state.scene_id!r}")
    if not space_same and prior.space_id:
        grounds.append(f"space_id {prior.space_id!r} -> {state.space_id!r}")
    if own_changed:
        grounds.append(
            f"ownership {prior.ownership_owner!r} -> {state.ownership.owner.value!r}")
    if epol_changed:
        grounds.append("epistemic_policy_changed")
    if content_break:
        grounds.append(
            f"content_break telos={telos_rel.value} object={obj_rel.value}")
    if op_shift == OperationShiftKind.SUBOPERATION:
        grounds.append(
            f"operation_suboperation {prior_op!r} -> {new_op!r}")
    if not grounds:
        grounds.append("scene_identity_continuous")

    return SceneContractDriftAssessment(
        scene_identity_continuous=scene_cont,
        space_same=space_same,
        branch_same=branch_same,
        object_scope_relation=obj_rel,
        telos_relation=telos_rel,
        ownership_boundary_changed=own_changed,
        epistemic_policy_changed=epol_changed,
        operation_shift_kind=op_shift,
        material_drift=material,
        grounds=tuple(grounds),
    )


def detect_contract_drift(prior: SceneContract,
                          state: PipelineState,
                          ) -> ContractRevisionCandidate | None:
    """Surface a candidate only for material scene-level drift.

    Operation.kind inequality alone is a sub-operation, not a revision.
    Telos wording change on a continuous scene/object is continuation.
    The returned candidate has authority=NO_TRANSITION_AUTHORITY.
    """
    assessment = assess_scene_contract_drift(prior, state)
    if not assessment.material_drift:
        return None
    proposed = derive_scene_contract(state, prior=prior)
    proposed.status = SceneContractStatus.REVISION_PROPOSED
    return ContractRevisionCandidate(
        candidate_id=_new_id("crc"),
        prior_contract_id=prior.contract_id,
        proposed_contract=proposed,
        reason="; ".join(assessment.grounds),
        source="SYSTEM_DERIVED",
        authority="NO_TRANSITION_AUTHORITY",
    )


def _human_explicit(action: dict[str, Any]) -> bool:
    return bool(action.get("human_explicit_choice"))


def admit_contract_revision(*,
                            prior: SceneContract,
                            candidate: ContractRevisionCandidate | None,
                            context_action: dict[str, Any] | None = None,
                            ) -> ContractRevisionAdmission:
    """Decide whether a candidate may replace the active SceneContract.

    MODEL/SYSTEM may propose. They cannot authorize merely from wording
    difference. USER_EXPLICIT confirm/edit/admit may carry authority.
    """
    action = context_action or {}
    kind = (action.get("kind") or "").upper()
    human = _human_explicit(action)
    prior_id = prior.contract_id
    cand_id = candidate.candidate_id if candidate else ""

    if kind == "CONTRACT_REJECT_REVISION":
        return ContractRevisionAdmission(
            admission_id=_new_id("cra"),
            candidate_id=cand_id,
            outcome=ContractRevisionOutcome.REJECT_REVISION,
            reason="explicit CONTRACT_REJECT_REVISION",
            authority=("USER_EXPLICIT" if human else "NO_TRANSITION_AUTHORITY"),
            prior_contract_id=prior_id,
            active_contract_id=prior_id,
        )

    if kind == "CONTRACT_ADMIT_REVISION" and candidate is not None:
        if not human:
            return ContractRevisionAdmission(
                admission_id=_new_id("cra"),
                candidate_id=cand_id,
                outcome=ContractRevisionOutcome.HOLD_PROPOSAL,
                reason="CONTRACT_ADMIT_REVISION without human_explicit_choice "
                       "cannot mint authority",
                authority="NO_TRANSITION_AUTHORITY",
                prior_contract_id=prior_id,
                active_contract_id=prior_id,
            )
        return ContractRevisionAdmission(
            admission_id=_new_id("cra"),
            candidate_id=cand_id,
            outcome=ContractRevisionOutcome.ADMIT_REVISION,
            reason="USER_EXPLICIT CONTRACT_ADMIT_REVISION",
            authority="USER_EXPLICIT",
            prior_contract_id=prior_id,
            active_contract_id=candidate.proposed_contract.contract_id,
        )

    if kind == "CONTRACT_EDIT" and human:
        target_id = (
            candidate.proposed_contract.contract_id if candidate is not None
            else prior_id)
        return ContractRevisionAdmission(
            admission_id=_new_id("cra"),
            candidate_id=cand_id,
            outcome=ContractRevisionOutcome.ADMIT_REVISION,
            reason="USER_EXPLICIT CONTRACT_EDIT",
            authority="USER_EXPLICIT",
            prior_contract_id=prior_id,
            active_contract_id=target_id,
        )

    if candidate is None:
        return ContractRevisionAdmission(
            admission_id=_new_id("cra"),
            candidate_id="",
            outcome=ContractRevisionOutcome.NO_DRIFT,
            reason="no material scene-contract drift",
            authority="NO_TRANSITION_AUTHORITY",
            prior_contract_id=prior_id,
            active_contract_id=prior_id,
        )

    return ContractRevisionAdmission(
        admission_id=_new_id("cra"),
        candidate_id=cand_id,
        outcome=ContractRevisionOutcome.HOLD_PROPOSAL,
        reason="unprivileged ContractRevisionCandidate held; "
               "NO_TRANSITION_AUTHORITY",
        authority="NO_TRANSITION_AUTHORITY",
        prior_contract_id=prior_id,
        active_contract_id=prior_id,
    )


def apply_user_contract_edit(prior: SceneContract,
                             state: PipelineState,
                             action: dict[str, Any],
                             ) -> SceneContract:
    """Apply USER_EXPLICIT field overlays onto a derived successor contract."""
    derived = derive_scene_contract(
        state, prior=prior,
        provenance=SceneContractProvenance.USER_EXPLICIT)
    overlays = action.get("contract") or action.get("fields") or {}
    kwargs: dict[str, Any] = {}
    for key in ("intent", "telos", "object_scope", "operation_kind",
                "expected_intervention"):
        if key in overlays and overlays[key] is not None:
            kwargs[key] = overlays[key]
    derived = replace(derived, **kwargs)
    derived.status = SceneContractStatus.CONFIRMED
    derived.provenance = SceneContractProvenance.USER_EXPLICIT
    return derived


__all__ = [
    "ContractRevisionAdmission",
    "ContractRevisionCandidate",
    "ContractRevisionOutcome",
    "ObjectScopeRelation",
    "OperationShiftKind",
    "SceneContract",
    "SceneContractDriftAssessment",
    "SceneContractProvenance",
    "SceneContractStatus",
    "TelosRelation",
    "admit_contract_revision",
    "apply_user_contract_edit",
    "assess_scene_contract_drift",
    "derive_scene_contract",
    "detect_contract_drift",
    "scene_contract_from_entry",
]

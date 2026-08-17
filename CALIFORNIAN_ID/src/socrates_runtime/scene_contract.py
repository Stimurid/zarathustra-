"""SceneContract — provisional scene binding with governed drift/revision."""
from __future__ import annotations

import secrets
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from .state import PipelineState


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
    )


def detect_contract_drift(prior: SceneContract,
                          state: PipelineState,
                          ) -> ContractRevisionCandidate | None:
    """Compare prior contract to current typed state; surface drift."""
    new_telos = state.scene.telos or ""
    new_op = state.operation.kind or ""
    telos_changed = (
        prior.telos and new_telos
        and prior.telos.strip().lower() != new_telos.strip().lower())
    op_changed = (
        prior.operation_kind and new_op
        and prior.operation_kind.strip().lower() != new_op.strip().lower())
    if not telos_changed and not op_changed:
        return None
    proposed = derive_scene_contract(state, prior=prior)
    proposed.status = SceneContractStatus.REVISION_PROPOSED
    reason_parts = []
    if telos_changed:
        reason_parts.append(f"telos drift: {prior.telos!r} -> {new_telos!r}")
    if op_changed:
        reason_parts.append(
            f"operation drift: {prior.operation_kind!r} -> {new_op!r}")
    return ContractRevisionCandidate(
        candidate_id=_new_id("crc"),
        prior_contract_id=prior.contract_id,
        proposed_contract=proposed,
        reason="; ".join(reason_parts),
        source="SYSTEM_DERIVED",
    )


__all__ = [
    "ContractRevisionCandidate",
    "SceneContract",
    "SceneContractProvenance",
    "SceneContractStatus",
    "derive_scene_contract",
    "detect_contract_drift",
]

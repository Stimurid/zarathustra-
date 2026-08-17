"""Event-driven context recognition — 3A+ control plane wiring."""
from __future__ import annotations

import secrets
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from .context_governance import (
    AdmissionOutcome,
    ContextualPressure,
    PressureAxis,
    PressureSourceKind,
    TransitionAdmission,
    assess_pressure,
    assess_space_friction,
)
from .context_store import SocratesContext
from .epistemic_model import (
    DEFAULT_WORKSPACE_SPACE_ID,
    TransductionKind,
    build_default_workspace_space,
    new_scene_id,
    new_space_id,
)
from .epistemic_ops import (
    activate_branch,
    emit_context_transduction,
    fork_scene_branch,
)
from .scene_contract import (
    ContractRevisionCandidate,
    SceneContract,
    SceneContractStatus,
    derive_scene_contract,
    detect_contract_drift,
)
from .state import PipelineState


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


class RecognitionEventKind(str, Enum):
    USER_TURN = "USER_TURN"
    TOOL_RESULT = "TOOL_RESULT"
    RESUME = "RESUME"
    EXPLICIT_CONTEXT_ACTION = "EXPLICIT_CONTEXT_ACTION"
    SIGNIFICANT_STATE_DELTA = "SIGNIFICANT_STATE_DELTA"


@dataclass(frozen=True)
class ForkCandidate:
    candidate_id: str
    hypothesis: str
    parent_scene_id: str = ""
    source: str = "SYSTEM_DERIVED"
    authority: str = "NO_TRANSITION_AUTHORITY"

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SpaceTransitionCandidate:
    candidate_id: str
    target_space_id: str
    source_space_id: str
    reason: str
    source_kind: PressureSourceKind
    authority: str = "NO_TRANSITION_AUTHORITY"

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["source_kind"] = self.source_kind.value
        return d


@dataclass(frozen=True)
class AporiaCandidate:
    """UNPRIVILEGED evidence only — no 3C world-map mutation."""

    candidate_id: str
    description: str
    authority: str = "NO_TRANSITION_AUTHORITY"

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RecognitionPass:
    """One recognition cycle: candidates + admissions + effects."""

    pass_id: str
    event_kind: RecognitionEventKind
    pressures: list[ContextualPressure] = field(default_factory=list)
    fork_candidates: list[ForkCandidate] = field(default_factory=list)
    space_candidates: list[SpaceTransitionCandidate] = field(default_factory=list)
    revision_candidates: list[ContractRevisionCandidate] = field(
        default_factory=list)
    aporia_candidates: list[AporiaCandidate] = field(default_factory=list)
    admissions: list[TransitionAdmission] = field(default_factory=list)
    mutations_applied: list[str] = field(default_factory=list)
    mutations_refused: list[str] = field(default_factory=list)
    clarification_required: bool = False
    clarification_reason: str = ""

    def to_public(self) -> dict[str, Any]:
        return {
            "pass_id": self.pass_id,
            "event_kind": self.event_kind.value,
            "pressures": [p.to_public() for p in self.pressures],
            "fork_candidates": [c.to_public() for c in self.fork_candidates],
            "space_candidates": [c.to_public() for c in self.space_candidates],
            "revision_candidates": [c.to_public()
                                      for c in self.revision_candidates],
            "aporia_candidates": [c.to_public() for c in self.aporia_candidates],
            "admissions": [asdict(a) for a in self.admissions],
            "mutations_applied": list(self.mutations_applied),
            "mutations_refused": list(self.mutations_refused),
            "clarification_required": self.clarification_required,
            "clarification_reason": self.clarification_reason,
        }


def _pressure(axis: PressureAxis, source: PressureSourceKind, *,
              target: str, evidence: str,
              intensity: float = 0.7,
              material: str = "") -> ContextualPressure:
    return ContextualPressure(
        pressure_id=_new_id("pr"),
        axis=axis, source_kind=source,
        intensity=intensity, proposed_target=target,
        evidence=evidence, materiality_signal=material)


def run_recognition_pass(*,
                         prior: SocratesContext | None,
                         prior_contract: SceneContract | None,
                         state: PipelineState,
                         event_kind: RecognitionEventKind,
                         context_action: dict[str, Any] | None = None,
                         injected_pressures: tuple[ContextualPressure, ...] = (),
                         ) -> RecognitionPass:
    """Derive candidates from prior context + typed state + control action."""
    rp = RecognitionPass(pass_id=_new_id("rp"), event_kind=event_kind)
    rp.pressures.extend(injected_pressures)

    action = context_action or {}
    action_kind = (action.get("kind") or "").upper()

    # Contract drift from typed state delta (no lexical parsing)
    if prior_contract is not None:
        drift = detect_contract_drift(prior_contract, state)
        if drift is not None:
            rp.revision_candidates.append(drift)

    # Explicit control actions (typed API — not lexical product path)
    if action_kind == "FORK":
        rp.fork_candidates.append(ForkCandidate(
            candidate_id=_new_id("fc"),
            hypothesis=action.get("hypothesis") or "explicit fork",
            parent_scene_id=action.get("parent_scene_id") or state.scene_id,
            source="EXPLICIT_CONTEXT_ACTION"))
        if action.get("human_explicit_choice"):
            rp.pressures.append(_pressure(
                PressureAxis.SCENE,
                PressureSourceKind.HUMAN_EXPLICIT_CHOICE,
                target=f"fork:{action.get('hypothesis', '')}",
                evidence="typed context_action FORK + human_explicit_choice",
                intensity=1.0, material="explicit"))

    if action_kind == "SPACE_TRANSITION":
        target = action.get("target_space_id") or ""
        src_kind = (PressureSourceKind.HUMAN_EXPLICIT_CHOICE
                    if action.get("human_explicit_choice")
                    else PressureSourceKind.MODEL_PROPOSAL)
        rp.space_candidates.append(SpaceTransitionCandidate(
            candidate_id=_new_id("stc"),
            target_space_id=target,
            source_space_id=state.space_id,
            reason=action.get("reason") or "explicit space transition request",
            source_kind=src_kind))
        rp.pressures.append(_pressure(
            PressureAxis.SPACE, src_kind,
            target=f"space:{target}",
            evidence=f"context_action SPACE_TRANSITION -> {target}",
            intensity=0.9,
            material="explicit" if action.get("human_explicit_choice") else ""))

    if action_kind == "CONTRACT_CONFIRM":
        pass  # handled in apply — promotes PROVISIONAL -> CONFIRMED

    # Ensure default workspace space is registered
    if not state.space_registry.has(DEFAULT_WORKSPACE_SPACE_ID):
        state.space_registry.register(build_default_workspace_space())

    # Auto-init scene on first turn
    if not state.scene_id:
        sid = new_scene_id()
        from .epistemic_model import SceneRef
        state.scene_registry.add_scene(SceneRef(
            scene_id=sid, space_id=state.space_id))
        state.scene_id = sid

    return rp


def apply_recognition_admissions(state: PipelineState,
                                 rp: RecognitionPass,
                                 *,
                                 prior_contract: SceneContract | None,
                                 context_action: dict[str, Any] | None = None,
                                 ) -> tuple[SceneContract | None,
                                            ContractRevisionCandidate | None]:
    """Apply ADMIT outcomes; refuse non-admitted mutations."""
    action = context_action or {}
    action_kind = (action.get("kind") or "").upper()
    new_contract: SceneContract | None = None
    admitted_revision: ContractRevisionCandidate | None = None

    # Group pressures by (axis, target) and assess
    groups: dict[tuple[str, str], list[ContextualPressure]] = {}
    for p in rp.pressures:
        key = (p.axis.value, p.proposed_target)
        groups.setdefault(key, []).append(p)

    for pressures in groups.values():
        _, adm = assess_pressure(
            tuple(pressures),
            grounded_signals=("typed_context_action",)
            if action_kind else (),
            material=any(p.materiality_signal for p in pressures),
        )
        rp.admissions.append(adm)

    # Fork admission
    for fc in rp.fork_candidates:
        fork_pressures = [p for p in rp.pressures
                          if p.axis == PressureAxis.SCENE
                          and "fork" in p.proposed_target]
        if not fork_pressures:
            fork_pressures = [_pressure(
                PressureAxis.SCENE,
                PressureSourceKind.MODEL_PROPOSAL,
                target=f"fork:{fc.hypothesis}",
                evidence=fc.hypothesis, intensity=0.5)]
        _, adm = assess_pressure(
            tuple(fork_pressures),
            grounded_signals=("explicit_fork_action",)
            if action_kind == "FORK" else (),
            material=action_kind == "FORK",
        )
        rp.admissions.append(adm)
        if adm.outcome == AdmissionOutcome.ADMIT and action_kind == "FORK":
            branch = fork_scene_branch(
                state, hypothesis=fc.hypothesis,
                parent_scene_id=fc.parent_scene_id or state.scene_id)
            if action.get("activate_branch"):
                activate_branch(state, branch.branch_id)
            rp.mutations_applied.append(
                f"fork_admitted:{branch.branch_id}")
        else:
            rp.mutations_refused.append(
                f"fork_refused:{fc.candidate_id}:{adm.outcome.value}")

    # Space transition admission
    for stc in rp.space_candidates:
        if not stc.target_space_id:
            rp.mutations_refused.append(
                f"space_refused:{stc.candidate_id}:unknown_target")
            continue
        if not state.space_registry.has(stc.target_space_id):
            rp.mutations_refused.append(
                f"space_refused:{stc.candidate_id}:unknown_space")
            continue
        friction = assess_space_friction(
            intent_matches_space=False,
            materiality=0.6,
            reversibility=0.7,
            authority_owner_is_human=True,
            consequence=0.5,
            human_explicit_choice=(
                stc.source_kind == PressureSourceKind.HUMAN_EXPLICIT_CHOICE),
        )
        space_pressures = [p for p in rp.pressures
                           if p.axis == PressureAxis.SPACE]
        if not space_pressures:
            space_pressures = [_pressure(
                PressureAxis.SPACE, stc.source_kind,
                target=f"space:{stc.target_space_id}",
                evidence=stc.reason, intensity=0.8,
                material="explicit" if stc.source_kind
                in {PressureSourceKind.HUMAN_EXPLICIT_CHOICE,
                    PressureSourceKind.AUTHORIZED_TRANSITION} else "")]
        _, adm = assess_pressure(
            tuple(space_pressures),
            grounded_signals=("known_space_id",)
            if state.space_registry.has(stc.target_space_id) else (),
            material=(stc.source_kind in AUTHORISED_PRESSURE_SOURCES
                      or stc.source_kind == PressureSourceKind.HUMAN_EXPLICIT_CHOICE),
        )
        rp.admissions.append(adm)
        if adm.outcome == AdmissionOutcome.ADMIT:
            old_space = state.space_id
            emit_context_transduction(
                state,
                kind=TransductionKind.TRANSLATION,
                source_space_id=old_space,
                target_space_id=stc.target_space_id,
                purpose=stc.reason,
                authority=stc.source_kind.value,
                preserved=(f"scene:{state.scene_id}",),
            )
            state.space_id = stc.target_space_id
            rp.mutations_applied.append(
                f"space_transition:{old_space}->{stc.target_space_id}")
        else:
            rp.mutations_refused.append(
                f"space_refused:{stc.candidate_id}:{adm.outcome.value}"
                f":friction={friction.level.value}")

    # Contract revision / initial contract
    if action_kind == "CONTRACT_CONFIRM" and prior_contract is not None:
        from dataclasses import replace
        from .scene_contract import SceneContractProvenance
        new_contract = replace(
            prior_contract,
            status=SceneContractStatus.CONFIRMED,
            provenance=SceneContractProvenance.USER_EXPLICIT)
        rp.mutations_applied.append(
            f"contract_confirmed:{new_contract.contract_id}")
    elif rp.revision_candidates:
        rev = rp.revision_candidates[0]
        # Same-space intent shift: revision candidate, no space switch
        admitted_revision = rev
        rp.mutations_applied.append(
            f"contract_revision_proposed:{rev.candidate_id}")
        new_contract = rev.proposed_contract
    elif prior_contract is None:
        new_contract = derive_scene_contract(state)
        rp.mutations_applied.append(
            f"contract_created:{new_contract.contract_id}")
    else:
        new_contract = prior_contract

    # Load-bearing ambiguity → hold (operation not applicable + gap)
    if (not state.operation.applicable
            and state.operation.open_world_gap
            and not state.operation.kind):
        rp.clarification_required = True
        rp.clarification_reason = "operation ambiguity with open_world_gap"

    return new_contract, admitted_revision


# Re-export for friction checks
from .context_governance import AUTHORISED_PRESSURE_SOURCES  # noqa: E402


def register_known_space(state: PipelineState, *,
                         space_id: str | None = None,
                         name: str = "test_space",
                         corpus_namespaces: tuple[str, ...] = ("test_corpus",),
                         ) -> str:
    """Test/helper — register an EpistemicSpace for transition tests."""
    from .epistemic_model import EpistemicSpace, MemoryValidityScope
    sid = space_id or new_space_id()
    state.space_registry.register(EpistemicSpace(
        space_id=sid,
        version="v0.1",
        name=name,
        corpus_namespaces=corpus_namespaces,
        retrieval_policy="space_scoped",
        memory_default_scope=MemoryValidityScope.SPACE_OR_DOMAIN,
        status="active",
    ))
    return sid


__all__ = [
    "AporiaCandidate",
    "ForkCandidate",
    "RecognitionEventKind",
    "RecognitionPass",
    "SpaceTransitionCandidate",
    "apply_recognition_admissions",
    "register_known_space",
    "run_recognition_pass",
]

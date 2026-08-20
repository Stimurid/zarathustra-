"""Vertical-slice Interaction Model — subset for the first live test.

Five typed objects out of the 8 defined in
`docs/tinkuy_interface_mvp/INTERACTION_MODEL_v0.1.md`. The remaining
three (SceneHypothesis, OperationProposal, MemoryAdmission) require
ProposalEngine / hypothesis distillation / admission governance
surfaces that are explicitly deferred to the next implementation
pass — no scaffolding for them here.
"""
from __future__ import annotations

import secrets
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# --------------------------------------------------------------------
# Enums
# --------------------------------------------------------------------


class SessionStatus(str, Enum):
    CREATED         = "CREATED"
    INPUT_RECEIVED  = "INPUT_RECEIVED"
    RUNNING         = "RUNNING"
    COMPLETED       = "COMPLETED"
    FAILED          = "FAILED"


class InputKind(str, Enum):
    TEXT        = "TEXT"
    FILE        = "FILE"
    TRANSCRIPT  = "TRANSCRIPT"


class RunMode(str, Enum):
    FAST          = "FAST"           # deterministic default
    LIVE          = "LIVE"
    TEST_DOUBLE   = "TEST_DOUBLE"


class RunStatus(str, Enum):
    QUEUED    = "QUEUED"
    RUNNING   = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED    = "FAILED"


class ArtifactKind(str, Enum):
    RECONSTRUCTION  = "RECONSTRUCTION"
    NEXT_ACTIONS    = "NEXT_ACTIONS"
    RAW_TRACE       = "RAW_TRACE"


class DecisionAction(str, Enum):
    ACCEPT   = "ACCEPT"
    MODIFY   = "MODIFY"
    SAVE     = "SAVE"
    FORWARD  = "FORWARD"
    REJECT   = "REJECT"


# --------------------------------------------------------------------
# Dataclasses
# --------------------------------------------------------------------


@dataclass
class Session:
    session_id:   str
    have:         str                       # user's "what do you have?" chip
    want:         str                       # user's "what do you want?" chip
    actor:        str                       # user id (opaque string for MVP)
    status:       SessionStatus
    created_at:   str
    updated_at:   str
    context_id:   str = ""                  # SocratesRuntime cross-turn context
    scenario_id:  str = ""                  # optional: dialogue-loop scenario seed

    @classmethod
    def new(cls, have: str, want: str, actor: str,
            scenario_id: str = "") -> "Session":
        now = _now_iso()
        return cls(
            session_id=_new_id("ses"),
            have=have, want=want, actor=actor,
            status=SessionStatus.CREATED,
            created_at=now, updated_at=now,
            context_id="", scenario_id=scenario_id,
        )

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class InputArtifact:
    input_id:     str
    session_id:   str
    kind:         InputKind
    body_text:    str
    mime:         str
    length_chars: int
    created_at:   str

    @classmethod
    def new(cls, session_id: str, kind: InputKind,
            body_text: str, mime: str) -> "InputArtifact":
        return cls(
            input_id=_new_id("inp"),
            session_id=session_id,
            kind=kind, body_text=body_text, mime=mime,
            length_chars=len(body_text or ""),
            created_at=_now_iso(),
        )

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        # trim body for the shelf view; the workspace pulls the full body
        # via a dedicated endpoint if needed
        d["body_preview"] = (self.body_text or "")[:500]
        return d


@dataclass
class Run:
    run_id:            str
    session_id:        str
    input_id:          str
    mode:              RunMode
    status:            RunStatus
    started_at:        str
    finished_at:       str
    terminal:          str
    response_text:     str
    dyad_causal:       str
    apparatus_class:   str
    sd_status:         str
    sd_authority:      str
    provider_id:       str
    model_id:          str
    duration_ms:       int
    error:             str
    trace_ref:         str

    @classmethod
    def new(cls, session_id: str, input_id: str,
            mode: RunMode) -> "Run":
        now = _now_iso()
        return cls(
            run_id=_new_id("run"),
            session_id=session_id, input_id=input_id,
            mode=mode, status=RunStatus.QUEUED,
            started_at=now, finished_at="",
            terminal="", response_text="",
            dyad_causal="", apparatus_class="",
            sd_status="", sd_authority="",
            provider_id="", model_id="",
            duration_ms=0, error="", trace_ref="",
        )

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["mode"] = self.mode.value
        d["status"] = self.status.value
        return d


@dataclass
class Artifact:
    artifact_id:  str
    session_id:   str
    run_id:       str
    kind:         ArtifactKind
    title:        str
    body_md:      str
    provenance:   dict[str, Any] = field(default_factory=dict)
    created_at:   str = ""

    @classmethod
    def new(cls, session_id: str, run_id: str, kind: ArtifactKind,
            title: str, body_md: str,
            provenance: dict[str, Any] | None = None) -> "Artifact":
        return cls(
            artifact_id=_new_id("art"),
            session_id=session_id, run_id=run_id,
            kind=kind, title=title, body_md=body_md,
            provenance=provenance or {},
            created_at=_now_iso(),
        )

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        return d


@dataclass
class Decision:
    decision_id:  str
    session_id:   str
    actor:        str
    target_kind:  str
    target_id:    str
    action:       DecisionAction
    payload:      dict[str, Any]
    created_at:   str

    @classmethod
    def new(cls, session_id: str, actor: str, target_kind: str,
            target_id: str, action: DecisionAction,
            payload: dict[str, Any] | None = None) -> "Decision":
        return cls(
            decision_id=_new_id("dec"),
            session_id=session_id, actor=actor,
            target_kind=target_kind, target_id=target_id,
            action=action, payload=payload or {},
            created_at=_now_iso(),
        )

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["action"] = self.action.value
        return d


__all__ = [
    "ArtifactKind", "DecisionAction", "InputKind",
    "RunMode", "RunStatus", "SessionStatus",
    "Artifact", "Decision", "InputArtifact", "Run", "Session",
]

"""Typed run trace — one file per run.

What the trace records, per handoff §16:

    * runtime identity — code_commit, pack, policy versions;
    * resolved SocratesRunConfiguration id + content_hash;
    * per-phase: router_id, mounted body ids/hashes, admitted &
      rejected triggers, budget_bytes;
    * S-phase state transitions (typed diffs);
    * governor decision & terminal;
    * native-organ BindingResults (unchanged);
    * memory proposal → reject/commit outcome + note_id;
    * total duration and any explicit failure with typed reason.

What the trace never records:

    * hidden chain-of-thought;
    * summary substitution for a body;
    * any historical G-S25 fallback (raising HistoricalFallbackForbidden
      is the trace event).
"""
from __future__ import annotations

import json
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .identity import SocratesIdentity, SocratesRunConfiguration
from .mount import MountedContext
from .state import PipelineState, TerminalOutcome


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TraceEvent:
    at: str
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class SocratesRunTrace:
    trace_id: str
    started_at: str
    finished_at: str = ""
    identity: dict[str, Any] = field(default_factory=dict)
    configuration: dict[str, Any] = field(default_factory=dict)
    events: list[TraceEvent] = field(default_factory=list)
    terminal: dict[str, Any] | None = None
    duration_ms: int = 0

    @classmethod
    def start(cls, identity: SocratesIdentity,
              configuration: SocratesRunConfiguration) -> "SocratesRunTrace":
        return cls(
            trace_id=f"strc_{secrets.token_hex(8)}",
            started_at=_now(),
            identity=identity.to_public(),
            configuration={**configuration.to_public(),
                           "content_hash": configuration.content_hash()},
        )

    def record(self, kind: str, **payload: Any) -> None:
        self.events.append(TraceEvent(at=_now(), kind=kind, payload=payload))

    def record_phase(self, phase: str, router_id: str,
                     mount: MountedContext,
                     state_before: PipelineState,
                     state_after: PipelineState) -> None:
        self.record(
            "phase_completed",
            phase=phase,
            router_id=router_id,
            mount=mount.to_public(),
            state_diff=_diff(state_before.to_public(),
                             state_after.to_public()),
        )

    def record_governor(self, decision) -> None:            # GovernorDecision
        self.record("governor_decision",
                    terminal=decision.terminal.value,
                    rationale=decision.rationale,
                    grounds=decision.grounds)

    def record_native_organ(self, binding_result: Any) -> None:
        self.record("native_organ",
                    result=(binding_result.to_public()
                            if hasattr(binding_result, "to_public")
                            else str(binding_result)))

    def record_memory_proposal(self, proposal, outcome, note_id: str = "") -> None:
        self.record("memory_proposal",
                    proposal=(proposal.to_public() if hasattr(proposal, "to_public")
                              else proposal),
                    outcome=outcome, note_id=note_id)

    def record_failure(self, kind: str, reason: str, extra: dict | None = None) -> None:
        payload = {"failure_kind": kind, "reason": reason}
        if extra:
            payload.update(extra)
        self.record("failure_explicit", **payload)

    def complete(self, outcome: TerminalOutcome | None) -> None:
        self.finished_at = _now()
        started = datetime.fromisoformat(self.started_at)
        finished = datetime.fromisoformat(self.finished_at)
        self.duration_ms = int((finished - started).total_seconds() * 1000)
        if outcome is not None:
            self.terminal = outcome.to_public()

    def to_public(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "identity": self.identity,
            "configuration": self.configuration,
            "events": [asdict(e) for e in self.events],
            "terminal": self.terminal,
        }

    def write_to(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        out = directory / f"{self.trace_id}.json"
        out.write_text(json.dumps(self.to_public(), ensure_ascii=False,
                                  indent=2),
                       encoding="utf-8")
        return out


def _diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Field-wise before/after — small and readable, not a JSON patch."""
    out: dict[str, Any] = {}
    for key in sorted(set(before) | set(after)):
        b, a = before.get(key), after.get(key)
        if b != a:
            out[key] = {"before": b, "after": a}
    return out

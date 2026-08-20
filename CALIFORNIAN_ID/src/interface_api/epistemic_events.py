"""Typed epistemic-event extractor.

Reads dyad / apparatus / self_development / memory_outcome from an
already-materialised `interface_api.Run` (which itself came from a real
`SocratesRunResult`) and emits a bounded list of typed events. Pure
projection — never mutates state, never asserts truth beyond what the
runtime already recorded.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from .models import Run


class EventKind(str, Enum):
    CLAIM_ACCEPTED               = "CLAIM_ACCEPTED"
    CLAIM_REJECTED               = "CLAIM_REJECTED"
    UNCERTAINTY_DECLARED         = "UNCERTAINTY_DECLARED"
    DISTINCTION_PRESERVED        = "DISTINCTION_PRESERVED"
    DISTINCTION_REUSED           = "DISTINCTION_REUSED"
    AUTHORITY_DENIED             = "AUTHORITY_DENIED"
    SCENE_SHIFT_DETECTED         = "SCENE_SHIFT_DETECTED"
    SCENE_STABILITY_PRESERVED    = "SCENE_STABILITY_PRESERVED"
    PRODUCTIVE_APORIA_PRESERVED  = "PRODUCTIVE_APORIA_PRESERVED"
    HYPOTHESIS_REVISED           = "HYPOTHESIS_REVISED"
    RETRIEVED_INJECTION_BLOCKED  = "RETRIEVED_INJECTION_BLOCKED"
    NO_DURABLE_WRITE             = "NO_DURABLE_WRITE"
    FALSE_MEMORY_REJECTED        = "FALSE_MEMORY_REJECTED"
    ONTOLOGY_GAP_DECLARED        = "ONTOLOGY_GAP_DECLARED"
    APPARATUS_MISMATCH_CANDIDATE = "APPARATUS_MISMATCH_CANDIDATE"


@dataclass(frozen=True)
class EpistemicEvent:
    kind:           EventKind
    source_field:   str           # e.g. "dyad.causal_effect"
    source_value:   str
    note:           str = ""

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        return d


def _fields(run: Run) -> dict[str, str]:
    return {
        "dyad.causal_effect":      run.dyad_causal,
        "dyad.surprise_class":     "",  # not persisted on Run row directly
        "apparatus.classification": run.apparatus_class,
        "sd.status":               run.sd_status,
        "sd.authority":            run.sd_authority,
        "terminal":                run.terminal,
    }


def extract_events(run: Run) -> list[EpistemicEvent]:
    """Emit a bounded list of typed events for a Run.

    Order is not strictly meaningful; events are additive projections.
    Consumers filter by `kind`.
    """
    events: list[EpistemicEvent] = []
    causal = (run.dyad_causal or "").strip()
    apparatus = (run.apparatus_class or "").strip()
    sd_status = (run.sd_status or "").strip()
    sd_authority = (run.sd_authority or "").strip()
    terminal = (run.terminal or "").strip()

    # --- authority invariants -----------------------------------------
    if sd_authority == "NO_ADOPTION_AUTHORITY":
        events.append(EpistemicEvent(
            kind=EventKind.NO_DURABLE_WRITE,
            source_field="self_development.authority",
            source_value=sd_authority,
            note="3E authority barrier preserved",
        ))
    if sd_status == "NO_CANDIDATE":
        events.append(EpistemicEvent(
            kind=EventKind.AUTHORITY_DENIED,
            source_field="self_development.status",
            source_value=sd_status,
            note="no governed self-development candidate opened",
        ))

    # --- dyad causal effects ------------------------------------------
    if causal == "reuse_prior_distinction":
        events.append(EpistemicEvent(
            kind=EventKind.DISTINCTION_REUSED,
            source_field="dyad.causal_effect", source_value=causal,
        ))
        events.append(EpistemicEvent(
            kind=EventKind.DISTINCTION_PRESERVED,
            source_field="dyad.causal_effect", source_value=causal,
        ))
    elif causal == "user_hypothesis_rejected":
        events.append(EpistemicEvent(
            kind=EventKind.HYPOTHESIS_REVISED,
            source_field="dyad.causal_effect", source_value=causal,
            note="user contradicted a prior epistemic hypothesis",
        ))
        events.append(EpistemicEvent(
            kind=EventKind.FALSE_MEMORY_REJECTED,
            source_field="dyad.causal_effect", source_value=causal,
        ))
        events.append(EpistemicEvent(
            kind=EventKind.CLAIM_REJECTED,
            source_field="dyad.causal_effect", source_value=causal,
        ))
    elif causal == "retrieved_injection_blocked":
        events.append(EpistemicEvent(
            kind=EventKind.RETRIEVED_INJECTION_BLOCKED,
            source_field="dyad.causal_effect", source_value=causal,
        ))
        events.append(EpistemicEvent(
            kind=EventKind.AUTHORITY_DENIED,
            source_field="dyad.causal_effect", source_value=causal,
        ))
    elif causal == "shared_object_delta":
        events.append(EpistemicEvent(
            kind=EventKind.CLAIM_ACCEPTED,
            source_field="dyad.causal_effect", source_value=causal,
            note="user established a distinction; runtime recorded as shared object, not user model",
        ))
    elif causal == "disagreement_held":
        events.append(EpistemicEvent(
            kind=EventKind.PRODUCTIVE_APORIA_PRESERVED,
            source_field="dyad.causal_effect", source_value=causal,
        ))
    elif causal == "socrates_position_revised":
        events.append(EpistemicEvent(
            kind=EventKind.HYPOTHESIS_REVISED,
            source_field="dyad.causal_effect", source_value=causal,
            note="runtime revised its own working position under evidence",
        ))
    elif causal == "skipped_easy_direct":
        events.append(EpistemicEvent(
            kind=EventKind.SCENE_STABILITY_PRESERVED,
            source_field="dyad.causal_effect", source_value=causal,
            note="easy direct path — no extra epistemic work",
        ))

    # --- apparatus / aporia -------------------------------------------
    if apparatus == "GENUINE_APORIA":
        events.append(EpistemicEvent(
            kind=EventKind.PRODUCTIVE_APORIA_PRESERVED,
            source_field="apparatus.classification", source_value=apparatus,
        ))
    elif apparatus == "ONTOLOGY_GAP":
        events.append(EpistemicEvent(
            kind=EventKind.ONTOLOGY_GAP_DECLARED,
            source_field="apparatus.classification", source_value=apparatus,
        ))
        events.append(EpistemicEvent(
            kind=EventKind.UNCERTAINTY_DECLARED,
            source_field="apparatus.classification", source_value=apparatus,
        ))
    elif apparatus == "APPARATUS_MISMATCH_CANDIDATE":
        events.append(EpistemicEvent(
            kind=EventKind.APPARATUS_MISMATCH_CANDIDATE,
            source_field="apparatus.classification", source_value=apparatus,
        ))
    elif apparatus == "EVIDENCE_GAP":
        events.append(EpistemicEvent(
            kind=EventKind.UNCERTAINTY_DECLARED,
            source_field="apparatus.classification", source_value=apparatus,
        ))

    # --- terminal decisions -------------------------------------------
    if terminal == "PRESERVE_APORIA":
        events.append(EpistemicEvent(
            kind=EventKind.PRODUCTIVE_APORIA_PRESERVED,
            source_field="terminal", source_value=terminal,
        ))
    elif terminal == "REFRAME":
        events.append(EpistemicEvent(
            kind=EventKind.HYPOTHESIS_REVISED,
            source_field="terminal", source_value=terminal,
        ))
    elif terminal == "CHALLENGE":
        events.append(EpistemicEvent(
            kind=EventKind.CLAIM_REJECTED,
            source_field="terminal", source_value=terminal,
        ))
    elif terminal == "RETURN_OPERATION":
        events.append(EpistemicEvent(
            kind=EventKind.AUTHORITY_DENIED,
            source_field="terminal", source_value=terminal,
            note="operation ownership returned to human",
        ))
    elif terminal == "DISTINGUISH":
        events.append(EpistemicEvent(
            kind=EventKind.DISTINCTION_PRESERVED,
            source_field="terminal", source_value=terminal,
        ))

    # dedup preserving order
    seen: set[tuple[str, str, str]] = set()
    out: list[EpistemicEvent] = []
    for e in events:
        key = (e.kind.value, e.source_field, e.source_value)
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def events_to_markdown(events: list[EpistemicEvent]) -> str:
    if not events:
        return "_(нет типизированных epistemic-событий на этом Run)_"
    lines = []
    for e in events:
        note = f" — {e.note}" if e.note else ""
        lines.append(
            f"- **{e.kind.value}** · `{e.source_field}` = "
            f"`{e.source_value}`{note}")
    return "\n".join(lines)


__all__ = [
    "EpistemicEvent", "EventKind",
    "extract_events", "events_to_markdown",
]

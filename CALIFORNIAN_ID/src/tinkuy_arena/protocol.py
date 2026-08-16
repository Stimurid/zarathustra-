"""Arena protocol — plain dataclasses and one Protocol.

Kept dependency-free from every engine: this file must be usable by a
participant that has never heard of Zarathustra, and by a caller that
never means to run any engine at all. Everything engine-specific goes
into ``participants/``.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol, runtime_checkable


# ---------------------------------------------------------- inputs

@dataclass(frozen=True)
class Case:
    """One prompt for the Arena, plus everything a judge might need to know.

    ``expectations`` is deliberately open: a judge inspects the keys it
    understands and ignores the rest. Adding a new expected property does not
    force a schema migration.
    """
    case_id: str
    text: str
    tags: tuple[str, ...] = ()
    expectations: dict[str, Any] = field(default_factory=dict)
    source: str = ""

    def content_hash(self) -> str:
        payload = json.dumps({"text": self.text,
                              "tags": sorted(self.tags),
                              "expectations": self.expectations},
                             sort_keys=True, ensure_ascii=False)
        return "case:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class EvaluationDimension:
    """One evaluable property.

    ``kind`` says how it will be produced — the judge decides which of its
    handlers runs. Deterministic dimensions have no LLM; property tests are
    checks against fixed rules; ``judge_llm`` reserves the future without
    demanding a judge model be present in v0.1.
    """
    dim_id: str
    label: str
    kind: str = "deterministic"       # deterministic | property_test | judge_llm
    description: str = ""


@dataclass(frozen=True)
class BenchPack:
    """A named set of cases and dimensions.

    Not the corpus itself — the corpus is data. This is the manifest that
    binds a version of the corpus to a version of the rubric.
    """
    bench_id: str
    name: str
    version: str
    cases: tuple[Case, ...]
    dimensions: tuple[EvaluationDimension, ...]


# ---------------------------------------------------------- participants

@dataclass(frozen=True)
class ParticipantConfiguration:
    """A participant + which build it runs.

    ``pipeline_config_id`` is a pointer into :mod:`workbench_configs`. It may
    be ``None`` — a participant with no config runs on defaults. That is a
    legitimate baseline, not a missing value.
    """
    participant_id: str
    display_name: str
    engine_kind: str
    pipeline_config_id: str | None = None
    persona_id: str = ""              # optional — only for persona participants
    workspace_id: str = "default"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Turn:
    """One participant's response to one prompt.

    v0.1 executes one turn per participant per match. The Turn shape is wide
    enough to carry a whole ``Pipeline.run`` result (via ``runtime_summary``)
    without leaking runtime types into every judge — a judge that only wants
    the response text ignores everything else.
    """
    turn_id: str
    match_id: str
    participant_id: str
    request_index: int
    request_text: str
    response_text: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    runtime_summary: dict[str, Any] = field(default_factory=dict)
    error: str = ""

    @property
    def failed(self) -> bool:
        return bool(self.error)

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


@runtime_checkable
class ParticipantAdapter(Protocol):
    """Contract every engine implements to become a participant.

    Deliberately narrow: ``respond`` sees the case and the caller identity
    (a user for auditability), returns a ``Turn``. Anything the engine wants
    to record — argument map counts, trace_dir, run_id, live-organ evidence —
    goes into ``Turn.runtime_summary`` as data.

    Not-in-scope for v0.1: streaming responses, follow-up turns, tool calls
    among participants.
    """
    participant_id: str
    engine_kind: str

    def respond(self, config: ParticipantConfiguration, case: Case,
                match_id: str, request_index: int) -> Turn: ...


# ---------------------------------------------------------- judgment

@dataclass(frozen=True)
class EvaluationRecord:
    """One judge's verdict on one dimension of one participant's turn."""
    record_id: str
    match_id: str
    participant_id: str
    dim_id: str
    verdict: str                 # pass | fail | partial | unknown
    value: Any = ""
    evidence: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DevelopmentSignal:
    """A note the Arena hands over, unchanged, to whatever grows a participant.

    v0.1 does NOT change any participant. That work lives in a future
    Academy layer; the Arena publishes signals as evidence for it, and
    stops.
    """
    signal_id: str
    match_id: str
    participant_id: str
    dim_id: str
    kind: str                    # capability_present | fragile | absent | ...
    text: str
    evidence: str = ""


class Judge(Protocol):
    """A judge evaluates ONE participant on the dimensions it understands.

    An implementation reports only dimensions it can produce; the runner
    aggregates. A dimension no judge answers stays unknown — better than a
    made-up verdict.
    """
    judge_id: str
    version: str

    def dimensions(self) -> list[str]: ...

    def evaluate(self, match: "Match", participant_id: str
                 ) -> list[EvaluationRecord]: ...


# ---------------------------------------------------------- match

@dataclass(frozen=True)
class MatchProtocol:
    """How participants relate during a match.

    v0.1 supports only ``independent``: every participant answers the case
    without seeing the others. Cross-participant critique and arbitration are
    where Arena becomes interesting — designed here as a shape, not
    implemented yet.
    """
    protocol_id: str = "independent"
    max_turns_per_participant: int = 1
    budget_seconds: int = 120
    blind_evaluator: bool = True

    ALL: tuple[str, ...] = ("independent", "critique", "arbitration")


@dataclass
class Match:
    match_id: str
    bench_id: str
    case: Case
    participants: list[ParticipantConfiguration]
    protocol: MatchProtocol
    turns: list[Turn] = field(default_factory=list)
    evaluations: list[EvaluationRecord] = field(default_factory=list)
    signals: list[DevelopmentSignal] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""
    status: str = "pending"      # pending | running | completed | failed

    def turn_for(self, participant_id: str) -> Turn | None:
        return next((t for t in self.turns
                     if t.participant_id == participant_id), None)

    def evaluations_for(self, participant_id: str) -> list[EvaluationRecord]:
        return [e for e in self.evaluations
                if e.participant_id == participant_id]

    def to_public(self) -> dict[str, Any]:
        d = {
            "match_id": self.match_id,
            "bench_id": self.bench_id,
            "case": asdict(self.case),
            "participants": [asdict(p) for p in self.participants],
            "protocol": asdict(self.protocol),
            "turns": [t.to_public() for t in self.turns],
            "evaluations": [e.to_public() for e in self.evaluations],
            "signals": [asdict(s) for s in self.signals],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status,
        }
        d["case"]["tags"] = list(self.case.tags)
        return d

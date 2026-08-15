"""BranchAdapter / BranchProjection contract.

This is the ONLY seam through which branch specifics reach the core. Adapters
live outside ``workbench_core`` (see ``workbench_adapters.zarathustra_adapter``)
and may import their branch runtime freely; the core may not.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

from .models import (
    CompilerProfile,
    ContractReport,
    NodeKind,
    PromptAsset,
)


# --------------------------------------------------------------------------
# Projection payloads
# --------------------------------------------------------------------------

#: Which layer a node or edge belongs to. A harness edge must never be drawn as
#: a production edge (T1).
TopologyLayer = Literal["ACTUAL_RUNTIME", "DECLARED_PIPELINE", "TEST_HARNESS"]

TopologyStatus = Literal[
    "MATCH",                # declaration and runtime agree
    "DECLARATION_DRIFT",    # both exist but differ in position or consumer
    "HARNESS_ONLY",         # exists only in a Workbench/test path
    "DEAD_DECLARATION",     # declared in pipeline.yaml, no runtime entrypoint
    "UNKNOWN",
]


#: How mature a source is, independently of whether it executes today. A branch
#: may legitimately sit at several levels at once; the Workbench shows that
#: rather than blocking on the least mature part.
ReadinessLevel = Literal[
    "DECLARATIVE_READY",     # structure/ordering declared and parseable
    "CONTRACT_READY",        # input/output contracts named and resolvable
    "PROMPT_BINDING_READY",  # a binding exists for the step
    "PROMPT_BODY_READY",     # an editable body actually exists
    "RUNTIME_BINDING_READY", # a host/runtime binding exists
    "LIVE_VALIDATED",        # observed executing
    "NOT_READY",
]


@dataclass
class Readiness:
    """Per-object readiness with the reason and the generation that owns it."""
    level: ReadinessLevel
    reason: str = ""
    expected_in: str = ""          # e.g. "G-S25"
    evidence: str = ""

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BranchInvariant:
    """A rule the branch declares about itself, with source provenance.

    Never a WorkbenchCore assumption: the core stores and displays these, it
    does not enforce or interpret them.
    """
    invariant_id: str
    text: str
    source_ref: str = ""
    source_id: str = ""

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StateNode:
    state_id: str
    kind: str                      # active | dispatcher | terminal
    semantics: str = ""

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StateTransition:
    source: str
    target: str
    when: str = ""
    note: str = ""
    guarded: bool = False
    forbidden: bool = False

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StateProjection:
    """The runtime state machine — a different object from the step topology.

    Kept separate on purpose: `step topology != runtime state machine`, and
    merging them would lose exactly the distinction Socrates makes explicit.
    """
    projection_id: str
    branch: str
    version: str
    states: list[StateNode]
    transitions: list[StateTransition]
    forbidden_transitions: list[str] = field(default_factory=list)
    retry_budget: dict[str, Any] = field(default_factory=dict)
    dispatcher_semantics: dict[str, str] = field(default_factory=dict)
    terminal_semantics: dict[str, str] = field(default_factory=dict)
    source_ref: str = ""

    def to_public(self) -> dict[str, Any]:
        return {
            "projection_id": self.projection_id, "branch": self.branch,
            "version": self.version, "source_ref": self.source_ref,
            "states": [s.to_public() for s in self.states],
            "transitions": [t.to_public() for t in self.transitions],
            "forbidden_transitions": self.forbidden_transitions,
            "retry_budget": self.retry_budget,
            "dispatcher_semantics": self.dispatcher_semantics,
            "terminal_semantics": self.terminal_semantics,
        }


@dataclass
class NodeDoc:
    """What a node is, in the language of someone who did not build it.

    Separate from ``implementation``/``source_ref`` on purpose: those answer
    "where is the code", this answers "what is this and why is it here". A
    branch that has nothing to say leaves it ``None`` and the UI shows the
    technical identity alone rather than inventing prose.
    """
    purpose: str = ""
    when: str = ""                      # когда выполняется
    receives: str = ""                  # что получает
    produces: str = ""                  # что выдаёт
    consumers: str = ""                 # куда идёт результат
    controlled_by: list[str] = field(default_factory=list)

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NodeProjection:
    node_id: str
    label: str
    kind: NodeKind
    implementation: str
    source_ref: str = ""
    asset_id: str | None = None
    rag_profile_id: str | None = None
    input_contract: str | None = None
    output_contract: str | None = None
    params: list[dict[str, Any]] = field(default_factory=list)
    note: str = ""
    layer: TopologyLayer = "ACTUAL_RUNTIME"
    topology_status: TopologyStatus = "MATCH"
    declared_predecessors: list[str] = field(default_factory=list)
    declared_successors: list[str] = field(default_factory=list)
    actual_callers: list[str] = field(default_factory=list)
    actual_callees: list[str] = field(default_factory=list)
    in_loop: bool = False
    optional: bool = False
    conditional_on: str = ""
    readiness: Readiness | None = None
    contract_refs: list[str] = field(default_factory=list)
    prompt_binding: dict[str, Any] | None = None
    doc: "NodeDoc | None" = None

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["readiness"] = self.readiness.to_public() if self.readiness else None
        d["doc"] = self.doc.to_public() if self.doc else None
        return d


@dataclass
class EdgeProjection:
    edge_id: str
    source: str
    target: str
    carries: str = ""
    transform_asset_id: str | None = None
    layer: TopologyLayer = "ACTUAL_RUNTIME"
    note: str = ""

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ControlEffect:
    """One downstream effect of a semantic control or asset.

    A hybrid control is NOT split in the UI. It is represented as one control
    with several effects, each carrying its own class and consumers.
    """
    effect_class: str
    target: str
    consumers: list[str]
    source_ref: str = ""
    resolved_value: Any = None
    value_map: dict[str, Any] | None = None

    def to_public(self) -> dict[str, Any]:
        return {
            "class": self.effect_class,
            "target": self.target,
            "consumers": self.consumers,
            "source_ref": self.source_ref,
            "resolved_value": self.resolved_value,
            "value_map": self.value_map,
        }


@dataclass
class SemanticControl:
    control_id: str
    label: str
    values: list[str]
    default: str
    semantics: str
    effects: list[ControlEffect]
    subject: str = "control"       # control | asset

    def to_public(self) -> dict[str, Any]:
        return {
            "control": {
                "id": self.control_id,
                "label": self.label,
                "values": self.values,
                "default": self.default,
                "semantics": self.semantics,
                "subject": self.subject,
            },
            "effects": [e.to_public() for e in self.effects],
        }


@dataclass
class PipelineProjection:
    pipeline_id: str
    branch: str
    version: str
    status: str
    nodes: list[NodeProjection]
    edges: list[EdgeProjection]
    resolved_for: dict[str, str] = field(default_factory=dict)

    def to_public(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "branch": self.branch,
            "version": self.version,
            "status": self.status,
            "resolved_for": self.resolved_for,
            "nodes": [n.to_public() for n in self.nodes],
            "edges": [e.to_public() for e in self.edges],
        }


#: A projection family identifier. Deliberately an open string: the core must
#: not enumerate branch-specific presentation families, or it would smuggle one
#: branch's visual ontology into the shared model. Each adapter declares which
#: kinds it supports; the core only carries the label.
ProjectionKind = str


@dataclass
class FieldItem:
    """One item of a non-graph projection.

    Deliberately carries the SAME identity keys as ``NodeProjection`` — node_id,
    asset_id, rag_profile_id — so an inspector opened from a field projection
    resolves exactly the same asset, contract and telemetry as one opened from
    the graph. This is what makes the projection a presentation layer rather
    than a second data model.
    """
    item_id: str
    label: str
    node_id: str
    role: str
    kind: NodeKind
    asset_id: str | None = None
    rag_profile_id: str | None = None
    level: str = "node"          # field | node | synthesis
    weight: float = 1.0
    tags: list[str] = field(default_factory=list)
    note: str = ""

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FieldProjection:
    projection_id: str
    kind: ProjectionKind
    branch: str
    title: str
    items: list[FieldItem]
    center_label: str = "FIELD"
    geometry: dict[str, Any] = field(default_factory=dict)
    source_ref: str = ""
    note: str = ""

    def to_public(self) -> dict[str, Any]:
        return {
            "projection_id": self.projection_id, "kind": self.kind,
            "branch": self.branch, "title": self.title,
            "center_label": self.center_label, "geometry": self.geometry,
            "source_ref": self.source_ref, "note": self.note,
            "items": [i.to_public() for i in self.items],
        }


@dataclass
class Invocation:
    """Exactly what would be handed to the model provider."""
    system_text: str
    user_text: str
    settings: dict[str, Any] = field(default_factory=dict)

    def payload(self) -> list[dict[str, str]]:
        msgs = []
        if self.system_text:
            msgs.append({"role": "system", "content": self.system_text})
        msgs.append({"role": "user", "content": self.user_text})
        return msgs


@dataclass
class Fixture:
    fixture_id: str
    text: str
    description: str = ""


# --------------------------------------------------------------------------
# Adapter protocol
# --------------------------------------------------------------------------

@runtime_checkable
class BranchAdapter(Protocol):
    """Contract every branch must satisfy to appear in the Workbench."""

    branch_id: str

    def describe_pipeline(self, resolved_for: dict[str, str] | None = ...) -> PipelineProjection:
        """Static or run-resolved topology. Branch selectors change topology."""

    def list_assets(self) -> list[PromptAsset]:
        """All prompt assets this branch exposes to the Workbench."""

    def baseline_variants(self, asset_id: str) -> list[tuple[str, str, str]]:
        """(origin, version, source_text) tuples for built-in baselines."""

    def contract_report(self, asset_id: str, source_text: str) -> ContractReport:
        """Compare fields requested by the prompt / declared / consumed."""

    def compiler_profile(self, asset_id: str) -> CompilerProfile:
        """Profile used to compile this asset for its runtime step."""

    def build_invocation(self, asset_id: str, source_text: str, fixture: Fixture) -> Invocation:
        """Reproduce the branch runtime's exact model invocation."""

    def semantic_controls(self) -> list[SemanticControl]:
        """Hybrid controls and hybrid assets with their multiple effects."""

    def fixtures(self, asset_id: str) -> list[Fixture]:
        """Bounded smoke fixtures for this asset."""

    def validate_output(self, asset_id: str, raw_text: str) -> tuple[bool, list[str], dict[str, Any]]:
        """Branch-specific output validation: (ok, reasons, parsed)."""

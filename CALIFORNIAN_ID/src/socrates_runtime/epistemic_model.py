"""First-class typed epistemic-model objects — G-BD.2.

Per the BACH/Didenko integration handoff §§5–6 the target topology is:

    Workspace
    └── EpistemicSpace(s)
        ├── WorldModelMount(s)
        └── Scene DAG
            ├── Scene / SceneBranch
            └── Projection DAG / lineage
                └── typed objects + scoped memory

These objects are NOT synonyms. Workspace ≠ EpistemicSpace ≠ ontology
≠ Scene ≠ SceneBranch ≠ Projection ≠ Memory. TruthMode ≠ truth
authority. Provenance ≠ activation scope.

This module materialises them as typed dataclasses + registries so
the runtime can carry them explicitly instead of relying on
documentation-only nouns. The corresponding schemas ship as JSON in
``data/socrates/current/contracts/`` (added alongside this module).

Consolidated into one module to bound surface area — every object
above is a small typed record with a `to_public()` serialisation and
a stable identity constructor. Existing state (PipelineState.scene
etc.) is extended, NOT shadowed. Older runs without these fields
resolve to sensible empties.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------- id factories


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


def new_space_id() -> str:          return _new_id("space")
def new_mount_id() -> str:          return _new_id("mount")
def new_scene_id() -> str:          return _new_id("scene")
def new_branch_id() -> str:         return _new_id("br")
def new_transition_id() -> str:     return _new_id("trans")
def new_conflict_id() -> str:       return _new_id("conf")
def new_passport_id() -> str:       return _new_id("passport")


# ---------------------------------------------------------- enums


class MountMode(str, Enum):
    """How a world model / ontology is mounted into an EpistemicSpace.

    Distinguished modes so the same ontology can serve as a lens in
    one Space and as a negative control in another without one
    activation leaking into the other.
    """
    PRIMARY = "PRIMARY"
    OVERLAY = "OVERLAY"
    LENS = "LENS"
    CONTRAST = "CONTRAST"
    NEGATIVE_CONTROL = "NEGATIVE_CONTROL"
    ARCHIVAL = "ARCHIVAL"


class TransductionKind(str, Enum):
    """Typed families of cross-space / cross-scene move.

    Distinguishing these is the whole point of §6.6: there is no
    magically neutral summary. TRANSLATION preserves identity; a
    TRANSDUCTION explicitly permits the destination medium to
    participate in producing the new object.
    """
    TRANSLATION = "TRANSLATION"
    REFRAME = "REFRAME"
    ONTOLOGICAL_TRANSFER = "ONTOLOGICAL_TRANSFER"
    TRANSDUCTION = "TRANSDUCTION"
    CONTRAST = "CONTRAST"
    FUNCTIONAL_RHYME = "FUNCTIONAL_RHYME"
    ANALOGY = "ANALOGY"
    DO_NOT_COLLAPSE = "DO_NOT_COLLAPSE"


class MemoryValidityScope(str, Enum):
    """Where a memory item is valid (§6.5). Extends B05 without
    creating a second memory database.
    """
    GLOBAL_SELF = "GLOBAL_SELF"
    GLOBAL_BETWEEN = "GLOBAL_BETWEEN"
    PROJECT = "PROJECT"
    SPACE_OR_DOMAIN = "SPACE_OR_DOMAIN"
    SCENE = "SCENE"
    BRANCH = "BRANCH"
    PROJECTION = "PROJECTION"
    INSTRUMENT = "INSTRUMENT"
    ARCHIVAL_ONLY = "ARCHIVAL_ONLY"


class CrossScopePolicy(str, Enum):
    """Policy for reading memory across scope boundaries."""
    FORBID = "FORBID"
    REQUIRE_EXPLICIT_BRIDGE = "REQUIRE_EXPLICIT_BRIDGE"
    ALLOW_READONLY = "ALLOW_READONLY"
    ALLOW_WITH_TRANSDUCTION = "ALLOW_WITH_TRANSDUCTION"


class ConflictFamily(str, Enum):
    """Typed families of incompatibility (§6.7)."""
    ONTOLOGY = "ONTOLOGY"
    EPISTEMIC_STATUS = "EPISTEMIC_STATUS"
    AUTHORITY = "AUTHORITY"
    OPERATION = "OPERATION"
    VALUE = "VALUE"
    CAUSAL_GRAMMAR = "CAUSAL_GRAMMAR"
    IDENTITY_RULE = "IDENTITY_RULE"
    MEMORY_FORCE = "MEMORY_FORCE"


class ConflictHandlingMode(str, Enum):
    """How the runtime addresses a typed conflict."""
    LOCALIZE = "LOCALIZE"
    HOLD = "HOLD"
    TRANSLATE = "TRANSLATE"
    TRANSDUCE = "TRANSDUCE"
    ARBITRATE_ACTION = "ARBITRATE_ACTION"
    SUSPEND = "SUSPEND"
    REJECT = "REJECT"


class ConstructionStatus(str, Enum):
    """Passport-level status of the object being reported on."""
    SOURCE_OWNED = "SOURCE_OWNED"
    RECONSTRUCTED = "RECONSTRUCTED"
    HYPOTHESIZED = "HYPOTHESIZED"
    CONSTRUCTED = "CONSTRUCTED"
    HYBRID = "HYBRID"
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------- WorldModelMount


@dataclass
class WorldModelMount:
    """One world-model / ontology mounted into an EpistemicSpace.

    PROVENANCE ≠ ACTIVATION invariant (§6.2): a BACH-derived operator
    can become a general METHOD capability while BACH-specific
    doctrine stays BACH_LOCAL. This is encoded by keeping
    ``provenance`` (where the ontology came from) separate from
    ``activation_scope`` (where it currently applies).
    """
    mount_id: str
    space_id: str
    ontology_ref: str
    mount_mode: MountMode
    provenance: str = ""
    activation_scope: str = ""
    allowed_claims: tuple[str, ...] = ()
    allowed_operations: tuple[str, ...] = ()
    forbidden_collapses: tuple[str, ...] = ()
    entry_trigger: str = ""
    exit_trigger: str = ""
    status: str = "active"

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["mount_mode"] = self.mount_mode.value
        d["allowed_claims"] = list(self.allowed_claims)
        d["allowed_operations"] = list(self.allowed_operations)
        d["forbidden_collapses"] = list(self.forbidden_collapses)
        return d


# ---------------------------------------------------------- EpistemicSpace


@dataclass
class EpistemicSpace:
    """An addressable epistemic jurisdiction (§6.1).

    A Space mounts one or more :class:`WorldModelMount`s under a
    relatively stable proof / evidence / operation / memory regime.
    Different Spaces may mount the same ontology under different
    regimes without merging.

    Hard invariants:

        * Space is NOT an ontology id (many-to-many via mounts).
        * Lexical mention has ZERO Space activation authority.
        * Space cannot override Constitution / origin / status /
          human ownership.
    """
    space_id: str
    version: str
    name: str
    telos_scope: str = ""
    world_model_mounts: tuple[WorldModelMount, ...] = ()
    ontology_refs: tuple[str, ...] = ()
    proof_regime: str = "default"
    claim_status_policy: str = "default"
    allowed_operation_families: tuple[str, ...] = ()
    operator_capabilities: tuple[str, ...] = ()
    corpus_namespaces: tuple[str, ...] = ()
    retrieval_policy: str = "default"
    memory_default_scope: MemoryValidityScope = MemoryValidityScope.SPACE_OR_DOMAIN
    memory_recruitment_policy: str = "default"
    authority_refs: tuple[str, ...] = ()
    transition_policy: str = "default"
    provenance: str = ""
    activation_scope: str = ""
    lineage: tuple[str, ...] = ()
    supersedes: str = ""
    status: str = "active"

    def to_public(self) -> dict[str, Any]:
        return {
            "space_id": self.space_id, "version": self.version,
            "name": self.name, "telos_scope": self.telos_scope,
            "world_model_mounts": [m.to_public()
                                    for m in self.world_model_mounts],
            "ontology_refs": list(self.ontology_refs),
            "proof_regime": self.proof_regime,
            "claim_status_policy": self.claim_status_policy,
            "allowed_operation_families":
                list(self.allowed_operation_families),
            "operator_capabilities": list(self.operator_capabilities),
            "corpus_namespaces": list(self.corpus_namespaces),
            "retrieval_policy": self.retrieval_policy,
            "memory_default_scope": self.memory_default_scope.value,
            "memory_recruitment_policy": self.memory_recruitment_policy,
            "authority_refs": list(self.authority_refs),
            "transition_policy": self.transition_policy,
            "provenance": self.provenance,
            "activation_scope": self.activation_scope,
            "lineage": list(self.lineage),
            "supersedes": self.supersedes,
            "status": self.status,
        }


# ---------------------------------------------------------- SceneBranch


@dataclass
class SceneBranch:
    """A persistent sibling hypothesis / commitment branch (§6.3).

    Two branches under the same parent scene may hold incompatible
    local facts, projections and memory without overwriting each
    other. Never implemented as a copy of one opaque prompt blob —
    branches are typed with their own provenance and local scope.
    """
    branch_id: str
    scene_id: str
    parent_scene_id: str = ""
    hypothesis: str = ""
    status: str = "active"
    local_facts: tuple[str, ...] = ()
    local_commitments: tuple[str, ...] = ()
    memory_scope: MemoryValidityScope = MemoryValidityScope.BRANCH
    active_projection_ids: tuple[str, ...] = ()
    lineage_event: str = ""
    weakened_at: str = ""
    rejected_at: str = ""
    archived_at: str = ""

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["memory_scope"] = self.memory_scope.value
        d["local_facts"] = list(self.local_facts)
        d["local_commitments"] = list(self.local_commitments)
        d["active_projection_ids"] = list(self.active_projection_ids)
        return d


# ---------------------------------------------------------- Scene extension


@dataclass
class SceneRef:
    """Small typed reference to a Scene within a Space + branch DAG.

    Distinct from the existing :class:`socrates_runtime.state.Scene`
    (which stays as-is for backward compatibility). This ref lets a
    ProjectionResult / passport / transition point into the Scene DAG
    by id without duplicating the Scene payload.
    """
    scene_id: str
    space_id: str = ""
    parent_scene_id: str = ""
    branch_id: str = ""
    version: str = ""

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------- ContextTransduction


@dataclass
class ContextTransduction:
    """A typed cross-space / cross-scene move (§6.6).

    HARD INVARIANT: there is no magically neutral summary. Every move
    declares what was preserved, transformed, dropped, newly created,
    and left unresolved.

    TRANSLATION ≠ IDENTITY. TRANSDUCTION explicitly permits the
    destination medium/world to participate in producing the new
    object — so ``newly_created`` on a TRANSDUCTION is not a defect,
    it is a required disclosure.
    """
    transition_id: str
    kind: TransductionKind
    source_space_id: str = ""
    target_space_id: str = ""
    source_scene_id: str = ""
    target_scene_id: str = ""
    source_branch_id: str = ""
    target_branch_id: str = ""
    purpose: str = ""
    authority: str = ""
    source_object_refs: tuple[str, ...] = ()
    preserved: tuple[str, ...] = ()
    transformed: tuple[str, ...] = ()
    dropped: tuple[str, ...] = ()
    newly_created: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()
    identity_claims: tuple[str, ...] = ()
    identity_rejections: tuple[str, ...] = ()
    loss_report: str = ""
    new_constraints: tuple[str, ...] = ()
    affordances: tuple[str, ...] = ()
    output_passport_ids: tuple[str, ...] = ()
    reversible: bool = False
    return_path: str = ""
    status: str = "completed"

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        for k in ("source_object_refs", "preserved", "transformed",
                  "dropped", "newly_created", "unresolved",
                  "identity_claims", "identity_rejections",
                  "new_constraints", "affordances",
                  "output_passport_ids"):
            d[k] = list(getattr(self, k))
        return d


# ---------------------------------------------------------- EpistemicPassport


@dataclass
class EpistemicPassport:
    """READ MODEL over stricter typed state (§6.4).

    Zero authority to upgrade state. Surfaces conflict, does not smooth
    it. TruthMode (if used at all) is a DERIVED UX projection — it
    cannot replace origin / status / authority / evidence.

    Emitted at S10 or B10 rendering time from the current typed
    state; never mutates state.
    """
    passport_id: str
    subject_object_id: str = ""              # what this passport describes
    origin_source_refs: tuple[str, ...] = ()
    claim_status: str = ""
    action_status: str = ""
    temporal_status: str = ""
    verification_status: str = ""
    authority_type: str = ""
    authority_scope: str = ""
    space_id: str = ""
    scene_id: str = ""
    branch_id: str = ""
    projection_id: str = ""
    memory_validity_scope: MemoryValidityScope | None = None
    world_model_refs: tuple[str, ...] = ()
    operation_of_origin: str = ""
    construction_status: ConstructionStatus = ConstructionStatus.UNKNOWN
    confidence: float = 0.0
    known_conflicts: tuple[str, ...] = ()
    known_loss: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    truth_mode_readout: str = ""                # DERIVED, not authoritative

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["memory_validity_scope"] = (self.memory_validity_scope.value
                                       if self.memory_validity_scope
                                       else None)
        d["construction_status"] = self.construction_status.value
        for k in ("origin_source_refs", "world_model_refs",
                  "known_conflicts", "known_loss", "open_questions"):
            d[k] = list(getattr(self, k))
        return d


# ---------------------------------------------------------- ConflictHoldingState


@dataclass
class ConflictHoldingState:
    """A typed record that the runtime is holding a real incompatibility
    without forced synthesis (§6.7).

    B09 may arbitrate ACTION from this state; B09 does NOT vote TRUTH.
    A conflict is not automatically an architecture defect — it is a
    defect only if it is hidden. A conflict record with an explicit
    ``handling_mode`` is legitimate structure.
    """
    conflict_id: str
    family: ConflictFamily
    handling_mode: ConflictHandlingMode
    parties: tuple[str, ...] = ()
    subject_refs: tuple[str, ...] = ()
    space_ids: tuple[str, ...] = ()
    scene_ids: tuple[str, ...] = ()
    branch_ids: tuple[str, ...] = ()
    projection_ids: tuple[str, ...] = ()
    description: str = ""
    discriminating_evidence_required: tuple[str, ...] = ()
    review_trigger: str = ""
    action_arbitration: str = ""
    status: str = "held"

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["family"] = self.family.value
        d["handling_mode"] = self.handling_mode.value
        for k in ("parties", "subject_refs", "space_ids", "scene_ids",
                  "branch_ids", "projection_ids",
                  "discriminating_evidence_required"):
            d[k] = list(getattr(self, k))
        return d


# ---------------------------------------------------------- registries


class SpaceRegistry:
    """Register :class:`EpistemicSpace` records by id.

    Very small — the point is a canonical lookup so a
    :class:`ContextTransduction` or a Scene ref can name a space
    without embedding the whole payload.
    """

    def __init__(self) -> None:
        self._spaces: dict[str, EpistemicSpace] = {}

    def register(self, space: EpistemicSpace) -> None:
        self._spaces[space.space_id] = space

    def get(self, space_id: str) -> EpistemicSpace | None:
        return self._spaces.get(space_id)

    def has(self, space_id: str) -> bool:
        return space_id in self._spaces

    def known(self) -> tuple[str, ...]:
        return tuple(sorted(self._spaces))

    def to_public(self) -> dict[str, Any]:
        return {sid: s.to_public() for sid, s in self._spaces.items()}


class SceneRegistry:
    """Register scenes + branches to form the Scene DAG.

    Scenes have parent-child relations; branches are per-scene
    siblings. Kept minimal — the DAG is walked, not queried by SQL.
    """

    def __init__(self) -> None:
        self._scenes: dict[str, SceneRef] = {}
        self._branches: dict[str, SceneBranch] = {}

    def add_scene(self, scene: SceneRef) -> None:
        self._scenes[scene.scene_id] = scene

    def add_branch(self, branch: SceneBranch) -> None:
        self._branches[branch.branch_id] = branch

    def get_scene(self, scene_id: str) -> SceneRef | None:
        return self._scenes.get(scene_id)

    def get_branch(self, branch_id: str) -> SceneBranch | None:
        return self._branches.get(branch_id)

    def branches_of(self, scene_id: str) -> tuple[SceneBranch, ...]:
        return tuple(b for b in self._branches.values()
                     if b.scene_id == scene_id)

    def to_public(self) -> dict[str, Any]:
        return {
            "scenes": {sid: s.to_public()
                        for sid, s in self._scenes.items()},
            "branches": {bid: b.to_public()
                          for bid, b in self._branches.items()},
        }


class ConflictRegistry:
    """Register held :class:`ConflictHoldingState` records so B09 and
    B10 can enumerate them without walking the whole state.
    """

    def __init__(self) -> None:
        self._conflicts: dict[str, ConflictHoldingState] = {}

    def add(self, conflict: ConflictHoldingState) -> None:
        self._conflicts[conflict.conflict_id] = conflict

    def get(self, conflict_id: str) -> ConflictHoldingState | None:
        return self._conflicts.get(conflict_id)

    def all(self) -> tuple[ConflictHoldingState, ...]:
        return tuple(self._conflicts.values())

    def to_public(self) -> list[dict[str, Any]]:
        return [c.to_public() for c in self._conflicts.values()]


# ---------------------------------------------------------- default_workspace


DEFAULT_WORKSPACE_SPACE_ID = "space_default_workspace"


def build_default_workspace_space() -> EpistemicSpace:
    """A minimal default :class:`EpistemicSpace` for runs that do not
    declare one.

    Preserves the direct-assistance invariant: an ordinary Socrates
    run does not need to author a Space; the runtime assumes a
    stable default one. Explicit Space transitions and multi-Space
    reasoning only kick in when a caller / model actually declares
    them.
    """
    return EpistemicSpace(
        space_id=DEFAULT_WORKSPACE_SPACE_ID,
        version="v0.1_candidate",
        name="default_workspace",
        telos_scope="general assistance",
        world_model_mounts=(),
        ontology_refs=(),
        proof_regime="default",
        claim_status_policy="default",
        allowed_operation_families=("*",),
        operator_capabilities=("*",),
        corpus_namespaces=("*",),
        retrieval_policy="default",
        memory_default_scope=MemoryValidityScope.PROJECT,
        memory_recruitment_policy="default",
        transition_policy="default",
        provenance="runtime_default",
        activation_scope="all_runs_by_default",
        status="active")


__all__ = [
    "ConflictFamily", "ConflictHandlingMode", "ConflictHoldingState",
    "ConflictRegistry", "ConstructionStatus", "ContextTransduction",
    "CrossScopePolicy", "DEFAULT_WORKSPACE_SPACE_ID",
    "EpistemicPassport", "EpistemicSpace", "MemoryValidityScope",
    "MountMode", "SceneBranch", "SceneRef", "SceneRegistry",
    "SpaceRegistry", "TransductionKind", "WorldModelMount",
    "build_default_workspace_space", "new_branch_id",
    "new_conflict_id", "new_mount_id", "new_passport_id",
    "new_scene_id", "new_space_id", "new_transition_id",
]

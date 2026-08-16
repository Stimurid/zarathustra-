"""BACH-derived operator library — G-BD.3 (OP-01..OP-18).

Per the BACH/Didenko integration handoff §8 each operator has typed
trigger / precondition / effect / output / stop / failure semantics
plus provenance. Operators are NOT executable primitives in the sense
of :mod:`projection_primitives`. They are named runtime *dispositions*
that either:

    (a) MAP TO an existing pipeline / projection / reflective / memory /
        attention seam (the operator declares which seam and how it
        binds), or

    (b) are recognised by the LIVE prompt vocabulary via the semantic
        body (v0.3) content — the operator record is the machine-
        readable spec S4/B03/B07/B08 write against.

Distinguishing (a) from (b) is deliberate: hardening D-S26-GEN-003
already ensured the runtime can execute a model-produced declarative
composition safely. The operator library preserves that discipline —
we do NOT let a model install Python via a named operator.

Every operator declares its ``binding`` — the exact runtime seam it
resolves to, or "SEMANTIC_ONLY" when its work happens in the prompt
vocabulary. Callers may query the registry to check that a proposed
operator is authorised and to route dispatch.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class OperatorBinding(str, Enum):
    """Where an operator actually resolves in the runtime.

    * ``PROJECTION_SPEC`` — operator writes a
      :class:`~capability_resolution.ProjectionSynthesisProposal` or
      selects a registered cutter capability.
    * ``REFLECTIVE_LOOP`` — operator drives an S7 ReflectiveReturn
      (retreat level R1/R2/R3).
    * ``TRANSDUCTION`` — operator emits a
      :class:`~epistemic_model.ContextTransduction`.
    * ``SCENE_BRANCH`` — operator forks or archives a SceneBranch.
    * ``MEMORY_SCOPE`` — operator affects
      :class:`~epistemic_model.MemoryValidityScope` (e.g. quarantine
      cross-scope bleed).
    * ``CONFLICT_HOLD`` — operator opens a ConflictHoldingState.
    * ``ATTENTION_CONFIG`` — operator changes attention config (field
      hold / deconcentration).
    * ``PASSPORT_ONLY`` — operator produces a passport / read-model
      annotation without changing state.
    * ``SEMANTIC_ONLY`` — operator has no runtime binding today; it
      lives in the semantic body vocabulary and reaches the model
      via the mounted prompt.
    """
    PROJECTION_SPEC = "PROJECTION_SPEC"
    REFLECTIVE_LOOP = "REFLECTIVE_LOOP"
    TRANSDUCTION = "TRANSDUCTION"
    SCENE_BRANCH = "SCENE_BRANCH"
    MEMORY_SCOPE = "MEMORY_SCOPE"
    CONFLICT_HOLD = "CONFLICT_HOLD"
    ATTENTION_CONFIG = "ATTENTION_CONFIG"
    PASSPORT_ONLY = "PASSPORT_ONLY"
    SEMANTIC_ONLY = "SEMANTIC_ONLY"


@dataclass(frozen=True)
class BachOperator:
    """Typed record describing one BACH-derived operator.

    Immutable — the registry ships fixed operator definitions; a
    caller who wants a specialised operator should register a new
    one, not mutate an existing one.

    Fields:

        * ``id`` — stable identifier (OP-01 … OP-18).
        * ``name`` — human-readable name.
        * ``purpose`` — one-line intent.
        * ``binding`` — see :class:`OperatorBinding`.
        * ``trigger`` — typed condition on state (prose reference to
          the semantic body section that formalises it).
        * ``precondition`` — invariants required before dispatch.
        * ``effect`` — what changes on state (typed reference).
        * ``output`` — the typed object the operator produces
          (ProjectionResult, ReflectiveReturn, ContextTransduction,
          SceneBranch, EpistemicPassport, ConflictHoldingState, or
          "SEMANTIC_ONLY").
        * ``stop`` — conditions that terminate the operator.
        * ``failure`` — how the operator fails, and whether failure
          is a defect (usually not — a well-typed failure is a
          legitimate outcome).
        * ``provenance`` — donor / semantic body / ADR references.
        * ``activation_scope`` — where this operator is available;
          the runtime honours PROVENANCE != ACTIVATION here too.
        * ``donor_local`` — True when this operator carries BACH-
          local doctrine that MUST NOT bleed into unrelated Spaces
          (§7 conditional list).
        * ``semantic_body_refs`` — which v0.3 body sections describe
          it.
    """
    id: str
    name: str
    purpose: str
    binding: OperatorBinding
    trigger: str
    precondition: str
    effect: str
    output: str
    stop: str
    failure: str
    provenance: str
    activation_scope: str
    donor_local: bool = False
    semantic_body_refs: tuple[str, ...] = ()

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["binding"] = self.binding.value
        d["semantic_body_refs"] = list(self.semantic_body_refs)
        return d


# ---------------------------------------------------------- library


_OPERATORS: tuple[BachOperator, ...] = (
    BachOperator(
        id="OP-01", name="PROBLEMATIZE / UNCLAMP_FORM",
        purpose="Loosen a failing frame without discarding frame-"
                "independent evidence. Produces changed problem / "
                "forward action, not generic doubt.",
        binding=OperatorBinding.REFLECTIVE_LOOP,
        trigger="OPERATION_MISMATCH diagnostic present + previous "
                "reflection insufficient",
        precondition="frame-independent evidence still legible",
        effect="emits ReflectiveReturn at retreat level R1 (revise "
               "operation) or R2 (revise ontology)",
        output="ReflectiveReturn",
        stop="unchanged-diagnosis guard fires OR forward action "
             "is now committed",
        failure="if no legitimate revised operation exists → "
                "PRESERVE_APORIA (OP-14)",
        provenance="BACH: transferable global method (§7 item 5)",
        activation_scope="all_spaces",
        semantic_body_refs=("B03_v0.3", "B07_v0.3")),

    BachOperator(
        id="OP-02", name="REFRAME",
        purpose="Change local framing while making the object-"
                "identity claim explicit; do not hide ontological "
                "transfer inside rewording.",
        binding=OperatorBinding.PROJECTION_SPEC,
        trigger="scene-relative reframing requested; ontology "
                "unchanged",
        precondition="ontology stable across reframe",
        effect="new ProjectionSynthesisProposal with same ontology "
               "but different segmentation/recognition policy",
        output="ProjectionSynthesisProposal",
        stop="proposal compile-binds and executes",
        failure="if reframe would require ontology change → "
                "escalate to OP-03 (ontological transfer)",
        provenance="BACH: transferable (§7 item 5)",
        activation_scope="all_spaces",
        semantic_body_refs=("B03_v0.3",)),

    BachOperator(
        id="OP-03", name="ONTOLOGICAL_TRANSFER",
        purpose="Change ontology / object-generation rules and "
                "execute a new projection from immutable source; "
                "preserve identity/nonidentity map.",
        binding=OperatorBinding.REFLECTIVE_LOOP,
        trigger="ontology inadequate to residue families",
        precondition="source still legible; alternative ontology "
                     "hypothesis available",
        effect="ReflectiveReturn R2 + new ProjectionSynthesisProposal "
               "under changed ontology",
        output="ReflectiveReturn + new ProjectionResult",
        stop="P2 covers residue OR ORGAN_GAP if primitives insufficient",
        failure="ORGAN_GAP path — no coercion",
        provenance="BACH: transferable (§7 items 3, 5)",
        activation_scope="all_spaces",
        semantic_body_refs=("B03_v0.3", "B08_v0.3")),

    BachOperator(
        id="OP-04", name="TRANSDUCE_CONTEXT",
        purpose="Move between epistemic spaces with explicit "
                "preserve/transform/drop/create/unresolved accounting.",
        binding=OperatorBinding.TRANSDUCTION,
        trigger="cross-Space move required (jurisdiction/world "
                "mismatch, not projection mismatch)",
        precondition="both source and target Space authorised for "
                     "this run",
        effect="emits ContextTransduction record; NEVER a neutral "
               "summary",
        output="ContextTransduction",
        stop="transduction record written with all loss fields "
             "populated",
        failure="if either Space is unauthorised → REJECT",
        provenance="BACH: transferable (§7 item 5)",
        activation_scope="all_spaces_with_transition_authority",
        semantic_body_refs=("B07_v0.3",)),

    BachOperator(
        id="OP-05", name="DECONCENTRATE / FIELD_HOLD",
        purpose="Suspend premature figure/object fixation after "
                "ordinary gap causes are checked; preserve "
                "tensions/residue/gradients.",
        binding=OperatorBinding.ATTENTION_CONFIG,
        trigger="premature object-forcing detected AND ordinary "
                "gap causes ruled out",
        precondition="B03 recognition-criteria discipline held; "
                     "not used to avoid work",
        effect="attention config marks residue/tensions/gradients "
               "as preservable; suppresses forced-completeness "
               "coercion",
        output="attention config annotation on projection lineage",
        stop="tensions resolve OR PRESERVE_APORIA legitimately",
        failure="if produces vague mystical prose with no tensions "
                "→ counted as failure per §18 T-BACH-04",
        provenance="BACH: transferable operator (§8)",
        activation_scope="all_spaces",
        semantic_body_refs=("B04_v0.3", "B08_v0.3")),

    BachOperator(
        id="OP-06", name="HOLD_UNSTABILIZED",
        purpose="Keep a proto-object / uncertain structure addressable "
                "without premature naming; include falsifiers/review "
                "trigger.",
        binding=OperatorBinding.PASSPORT_ONLY,
        trigger="candidate object present but under-validated",
        precondition="explicit falsifier + review trigger declared",
        effect="EpistemicPassport with construction_status=HYPOTHESIZED "
               "and known_conflicts/open_questions surfaced",
        output="EpistemicPassport (read-model)",
        stop="review_trigger fires → OP-09 stabilize OR OP-14 aporia",
        failure="if named prematurely → passport records the coercion",
        provenance="BACH: transferable (§7 item 14)",
        activation_scope="all_spaces",
        semantic_body_refs=("B02_v0.3", "B08_v0.3")),

    BachOperator(
        id="OP-07", name="FOLD / ABSTRACT_DETERMINACY",
        purpose="Abstract a bounded preservation target away from "
                "carrier-specific form. Never claim a lossless pure "
                "essence.",
        binding=OperatorBinding.TRANSDUCTION,
        trigger="bounded preservation across medium change",
        precondition="preservation target declared; loss report required",
        effect="ContextTransduction kind=TRANSDUCTION with explicit "
               "preserved+dropped+newly_created",
        output="ContextTransduction",
        stop="target medium accepts the fold OR fails typed",
        failure="if claims lossless essence → counted as failure "
                "(passport surfaces the coercion)",
        provenance="BACH-local (§7 conditional: fold semantics)",
        activation_scope="bach_local_or_explicitly_mounted",
        donor_local=True,
        semantic_body_refs=("B08_v0.3",)),

    BachOperator(
        id="OP-08", name="UNFOLD_IN_MEDIUM",
        purpose="Construct target form under a new medium and record "
                "new constraints / created structure.",
        binding=OperatorBinding.TRANSDUCTION,
        trigger="paired with OP-07 fold; new medium has its own rules",
        precondition="new-medium constraints known",
        effect="ContextTransduction with new_constraints and "
               "newly_created populated",
        output="ContextTransduction",
        stop="medium accepts the unfold OR emits typed constraint "
             "violation",
        failure="medium-specific artefact NOT reported as neutral copy",
        provenance="BACH-local (§7 conditional)",
        activation_scope="bach_local_or_explicitly_mounted",
        donor_local=True,
        semantic_body_refs=("B08_v0.3",)),

    BachOperator(
        id="OP-09", name="STABILIZE_OBJECT",
        purpose="Turn a recurring validated candidate into "
                "term/schema/protocol/operator candidate; durable "
                "write still goes through B05 authority.",
        binding=OperatorBinding.MEMORY_SCOPE,
        trigger="repeated validated appearance of a candidate object",
        precondition="B05 write authority available for the "
                     "target memory scope",
        effect="proposes memory promotion; scope determined by "
               "MemoryValidityScope enum",
        output="MemoryProposal + optional passport",
        stop="B05 accepts OR rejects the write",
        failure="if bypasses B05 authority → REJECT with reason",
        provenance="BACH: transferable (§7 item 13)",
        activation_scope="all_spaces_with_memory_authority",
        semantic_body_refs=("B05_v0.3",)),

    BachOperator(
        id="OP-10", name="REVISE_APPARATUS",
        purpose="Make current recognition/cutter/identity/causal "
                "apparatus the object of revision.",
        binding=OperatorBinding.PROJECTION_SPEC,
        trigger="apparatus itself named as the source of mismatch",
        precondition="ADR-S26-022 reflective loop available; "
                     "ADR-S26-023 capability resolution in place",
        effect="ReflectiveReturn + new ProjectionSynthesisProposal "
               "OR ORGAN_GAP when primitives insufficient",
        output="ProjectionSynthesisProposal / OrganGap",
        stop="new apparatus compile-binds and executes, OR "
             "ORGAN_GAP is emitted honestly",
        failure="ORGAN_GAP path — no coercion to nearest cutter",
        provenance="BACH: transferable (§7 items 12–13)",
        activation_scope="all_spaces",
        semantic_body_refs=("B03_v0.3", "B08_v0.3")),

    BachOperator(
        id="OP-11", name="BOARD_SEAM_CHECK",
        purpose="Check illicit transfer across WORLD/OBJECT, "
                "POSITION/ACTIVITY and OPERATION/INSTRUMENT views.",
        binding=OperatorBinding.CONFLICT_HOLD,
        trigger="candidate transfer of a property between board views",
        precondition="the three board views (§9) reconstructible "
                     "from typed state",
        effect="if illicit transfer detected → ConflictHoldingState "
               "family=IDENTITY_RULE handling_mode=REJECT",
        output="ConflictHoldingState (or no-op if transfer legitimate)",
        stop="board seam declared legitimate OR rejected",
        failure="silent transfer not counted; must be visible in "
                "passport",
        provenance="BACH: transferable (§7 item 15, §9)",
        activation_scope="all_spaces",
        semantic_body_refs=("B04_v0.3", "B08_v0.3")),

    BachOperator(
        id="OP-12", name="PROJECTION_ENSEMBLE",
        purpose="Execute independent grounded projections from "
                "immutable source; compare without vote-to-truth.",
        binding=OperatorBinding.PROJECTION_SPEC,
        trigger="multi-look required (polyontology or multiple "
                "recognised angles)",
        precondition="each projection has grounded ProjectionSpec",
        effect="parallel projections produce ProjectionResults; "
               "comparison surfaces conflicts as "
               "ConflictHoldingState rather than merging",
        output="tuple[ProjectionResult, ...] + optional "
               "ConflictHoldingState",
        stop="all projections executed OR iteration bound reached",
        failure="if collapses to majority vote → REJECT (§18 "
                "T-BACH-06)",
        provenance="BACH: transferable (§7 items 3, 12)",
        activation_scope="all_spaces",
        semantic_body_refs=("B03_v0.3", "B08_v0.3", "B09_v0.3")),

    BachOperator(
        id="OP-13", name="STRONG_VERSION_RECONSTRUCT",
        purpose="Reconstruct the strongest internally coherent "
                "version before critique; reconstruction status "
                "remains explicit.",
        binding=OperatorBinding.PASSPORT_ONLY,
        trigger="critique of a source position requested",
        precondition="source position legible; strong version "
                     "candidate identifiable",
        effect="passport records construction_status=RECONSTRUCTED "
               "for the reconstruction; critique lives on separate "
               "passport",
        output="EpistemicPassport",
        stop="strong version stable OR clearly incoherent",
        failure="if reconstruction hidden inside endorsement → "
                "passport reveals the coercion",
        provenance="BACH: transferable (§7 item 14)",
        activation_scope="all_spaces",
        semantic_body_refs=("B02_v0.3", "B10_v0.3")),

    BachOperator(
        id="OP-14", name="PRESERVE_APORIA / NEGATIVE_CAPABILITY",
        purpose="Hold a material non-mergeable difference with "
                "explicit next discriminating evidence/operation, "
                "not as avoidance.",
        binding=OperatorBinding.CONFLICT_HOLD,
        trigger="two grounded positions genuinely incompatible",
        precondition="both positions typed; discriminator "
                     "identifiable",
        effect="ConflictHoldingState handling_mode=HOLD with "
               "discriminating_evidence_required populated",
        output="ConflictHoldingState",
        stop="discriminator arrives OR review_trigger fires",
        failure="if used as task abandonment → REJECT",
        provenance="BACH: transferable (§7 item 14)",
        activation_scope="all_spaces",
        semantic_body_refs=("B08_v0.3", "B09_v0.3")),

    BachOperator(
        id="OP-15", name="SITUATION_TO_TASK_RECONSTRUCTION",
        purpose="When materially required, distinguish situation → "
                "difficulty → problem → intention → projective "
                "posit → task. Do not ritualize this for trivial "
                "requests.",
        binding=OperatorBinding.SEMANTIC_ONLY,
        trigger="task ambiguous AND simplification would lose "
                "material distinction",
        precondition="ordinary distinction insufficient",
        effect="B01 emits typed situation/difficulty/problem/"
               "intention/task decomposition",
        output="typed Scene payload with the six-step decomposition",
        stop="task well-formed and actionable",
        failure="if applied to trivial requests → RETURN_TO_"
                "ORDINARY_ASSISTANCE (OP-18)",
        provenance="BACH: transferable (§7 item 9)",
        activation_scope="all_spaces",
        semantic_body_refs=("B01_v0.3",)),

    BachOperator(
        id="OP-16", name="NOVELTY_RELATIVIZE",
        purpose="Bound novelty claim to comparison space: user / "
                "corpus / discipline / world model / identity rule "
                "/ generator.",
        binding=OperatorBinding.PASSPORT_ONLY,
        trigger="novelty claim asserted",
        precondition="comparison space nameable",
        effect="passport records novelty scope + known_conflicts if "
                "claim exceeds evidence",
        output="EpistemicPassport",
        stop="scope declared OR passport records unresolved gap",
        failure="unbounded novelty claim → passport surfaces it as "
                "open_question",
        provenance="BACH: transferable (§7 items 11–12)",
        activation_scope="all_spaces",
        semantic_body_refs=("B02_v0.3", "B10_v0.3")),

    BachOperator(
        id="OP-17", name="CONTEXT_QUARANTINE / DO_NOT_BLEED",
        purpose="Prevent domain/space/branch/projection material "
                "from becoming global causal background without an "
                "authorized bridge.",
        binding=OperatorBinding.MEMORY_SCOPE,
        trigger="cross-scope retrieval or memory recruitment across "
                "Space/Scene/Branch/Projection boundary",
        precondition="CrossScopePolicy consulted",
        effect="either FORBID / REQUIRE_EXPLICIT_BRIDGE / "
                "ALLOW_READONLY / ALLOW_WITH_TRANSDUCTION per policy",
        output="scoped memory access decision (typed)",
        stop="access decision recorded",
        failure="silent bleed → counted as defect (§18 negative test)",
        provenance="BACH: transferable (§7 item 16)",
        activation_scope="all_spaces",
        semantic_body_refs=("B04_v0.3", "B05_v0.3")),

    BachOperator(
        id="OP-18", name="RETURN_TO_ORDINARY_ASSISTANCE",
        purpose="When the complex/reflective trigger disappears, "
                "close/suspend special states and return to normal "
                "useful direct assistance.",
        binding=OperatorBinding.SEMANTIC_ONLY,
        trigger="reflective/conflict/branch pressure disappears",
        precondition="pending diagnostics cleared; no held "
                     "conflicts require action",
        effect="B10 render suppresses passport / branch / Space "
               "machinery from user-facing output",
        output="direct-assistance response (unchanged from pre-loop "
               "runtime)",
        stop="response delivered",
        failure="if machinery still leaks into simple output → "
                "counted per §18 T-BACH-07",
        provenance="BACH: transferable (§7 item 19)",
        activation_scope="all_spaces",
        semantic_body_refs=("B10_v0.3",)),
)


# ---------------------------------------------------------- registry


class BachOperatorRegistry:
    """Register + resolve :class:`BachOperator` by id.

    Ships the 18 default operators. A workspace may register more,
    but nothing here grants execution authority — a registered
    operator is a NAMED DISPOSITION that binds to an existing seam
    (or SEMANTIC_ONLY for prompt-vocabulary operators). No operator
    can install Python or expand primitives.
    """

    def __init__(self, operators: tuple[BachOperator, ...] = ()) -> None:
        self._by_id: dict[str, BachOperator] = {}
        for op in operators or _OPERATORS:
            self._by_id[op.id] = op

    def register(self, op: BachOperator) -> None:
        self._by_id[op.id] = op

    def get(self, op_id: str) -> BachOperator | None:
        return self._by_id.get(op_id)

    def has(self, op_id: str) -> bool:
        return op_id in self._by_id

    def all(self) -> tuple[BachOperator, ...]:
        return tuple(self._by_id[k] for k in sorted(self._by_id))

    def by_binding(self,
                    binding: OperatorBinding,
                    ) -> tuple[BachOperator, ...]:
        return tuple(op for op in self.all() if op.binding == binding)

    def donor_local_ids(self) -> tuple[str, ...]:
        return tuple(op.id for op in self.all() if op.donor_local)

    def transferable_ids(self) -> tuple[str, ...]:
        return tuple(op.id for op in self.all() if not op.donor_local)

    def to_public(self) -> list[dict[str, Any]]:
        return [op.to_public() for op in self.all()]


def build_default_operator_registry() -> BachOperatorRegistry:
    return BachOperatorRegistry(_OPERATORS)


__all__ = [
    "BachOperator", "BachOperatorRegistry", "OperatorBinding",
    "build_default_operator_registry",
]

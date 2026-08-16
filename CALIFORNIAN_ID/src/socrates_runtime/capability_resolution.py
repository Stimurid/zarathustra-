"""Capability resolution — ADR-S26-023 core contracts.

The three states of capability resolution the runtime must distinguish:

    REGISTERED_CAPABILITY   — a current authorised whole
                              :class:`CutterCapability` fits the
                              requested (operation, ontology hypothesis,
                              target family). Bind it and execute.

    CUTTER_SPEC_SYNTHESIS   — no named registered cutter fits, BUT the
                              required look can be expressed
                              compositionally through existing
                              authorised generic :mod:`projection_primitives`.
                              Socrates emits a declarative
                              :class:`GeneratedCutterSpec`; the compile-bind
                              step validates every requested primitive
                              exists + typed params fit, produces a
                              :class:`CompiledCutter`, and physically
                              executes it against the ORIGINAL source.

    ORGAN_GAP               — neither a registered capability nor an
                              honest declarative composition suffices.
                              Emit a typed :class:`OrganGap` with all
                              the evidence a follow-up development pass
                              would need. Do NOT coerce to a
                              near-registered cutter, do NOT fabricate
                              a :class:`ProjectionResult`, do NOT let
                              model prose masquerade as execution.

Authority invariants (ADR §10):

    * A generated CutterSpec is UNPRIVILEGED DATA. It cannot mint
      executor authority, install code, alter deployment, alter
      security boundaries, create provider credentials, or self-authorise
      a durable-state write.
    * An :class:`OrganGap` may accompany an :class:`OrganDevelopmentProposal`,
      but that proposal has ZERO activation authority — it is a
      proposal for a HUMAN owner to consider, not a self-executing
      request.
"""
from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable

from .cutter_registry import CutterCapability, CutterRegistry
from .projection import (
    ProjectedObject,
    ProjectionResult,
    ProjectionStatus,
    Residue,
    SemanticProjectionSpec,
    new_projection_id,
)
from .projection_primitives import (
    ClassifiedSpan,
    CoverageComputer,
    FamilyClassifier,
    LabeledSpan,
    PrimitiveRegistry,
    SpanScanner,
    TargetFilter,
)


# ---------------------------------------------------------- enums


class CapabilityResolutionKind(str, Enum):
    REGISTERED_CAPABILITY = "REGISTERED_CAPABILITY"
    CUTTER_SPEC_SYNTHESIS = "CUTTER_SPEC_SYNTHESIS"
    ORGAN_GAP = "ORGAN_GAP"


# ---------------------------------------------------------- generated spec


@dataclass(frozen=True)
class PrimitiveInvocation:
    """One node in a :class:`GeneratedCutterSpec`'s composition graph.

    ``name`` is a local binding — later invocations can reference
    prior outputs by their name. ``primitive_id`` names a class
    registered in :class:`PrimitiveRegistry`. ``params`` are the
    declarative construction params passed to the class. ``inputs``
    lists the names of prior outputs to feed into this primitive's
    ``apply`` method (in order); an empty list means the primitive
    consumes the ORIGINAL source text.
    """
    name: str
    primitive_id: str
    params: dict[str, Any] = field(default_factory=dict)
    inputs: tuple[str, ...] = ()

    def to_public(self) -> dict[str, Any]:
        return {"name": self.name, "primitive_id": self.primitive_id,
                "params": dict(self.params), "inputs": list(self.inputs)}


@dataclass
class GeneratedCutterSpec:
    """A declaratively-synthesised projection specification.

    Distinct from :class:`SemanticProjectionSpec`: the latter names a
    projection (identity + ontology + evidence requirements + status);
    the former IS THE COMPOSITION — the ordered list of primitives to
    invoke to realise it. Two specs may share identity fields but
    differ in ``primitives`` (a genuine "different way of looking").

    UNPRIVILEGED DATA. Carrying this record grants no execution
    authority beyond what the referenced primitives already have.
    """
    spec_id: str
    version: str
    source_id: str
    scene_ref: str
    operation_id: str
    ontology_id: str
    target_object_family: tuple[str, ...]
    recognition_criteria: tuple[str, ...]
    segmentation_policy: str
    evidence_requirements: tuple[str, ...]
    exclusions: tuple[str, ...]
    contraindications: tuple[str, ...]
    applicability_assumptions: tuple[str, ...]
    primitives: tuple[PrimitiveInvocation, ...]
    accepted_output: str = ""            # local name of "accepted objects" output
    residue_output: str = ""             # local name of "residue" output
    parent_projection_id: str = ""
    revises: str = ""
    status: str = "exploratory"

    def fingerprint(self) -> str:
        payload = "\n".join([
            self.operation_id, self.ontology_id, self.segmentation_policy,
            "|".join(self.target_object_family),
            "|".join(self.recognition_criteria),
            "|".join(f"{p.name}:{p.primitive_id}" for p in self.primitives),
        ])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def to_public(self) -> dict[str, Any]:
        return {
            "spec_id": self.spec_id, "version": self.version,
            "source_id": self.source_id, "scene_ref": self.scene_ref,
            "operation_id": self.operation_id,
            "ontology_id": self.ontology_id,
            "target_object_family": list(self.target_object_family),
            "recognition_criteria": list(self.recognition_criteria),
            "segmentation_policy": self.segmentation_policy,
            "evidence_requirements": list(self.evidence_requirements),
            "exclusions": list(self.exclusions),
            "contraindications": list(self.contraindications),
            "applicability_assumptions": list(self.applicability_assumptions),
            "primitives": [p.to_public() for p in self.primitives],
            "accepted_output": self.accepted_output,
            "residue_output": self.residue_output,
            "parent_projection_id": self.parent_projection_id,
            "revises": self.revises, "status": self.status,
            "fingerprint": self.fingerprint(),
        }


def new_spec_id() -> str:
    return f"cutspec_{secrets.token_hex(6)}"


# ---------------------------------------------------------- organ gap


@dataclass
class OrganGap:
    """A typed record that an execution/attention capability is missing.

    Distinct from a SOURCE_GAP (source insufficient) and from a
    SCENE_GAP (telos ill-formed). ORGAN_GAP is specifically:

        the source is adequate + the request is coherent, but the
        runtime lacks any authorised way to physically execute the
        required kind of look.

    Emitted only when BOTH registered capability lookup AND declarative
    composition through existing primitives have failed with typed
    reasons. Never emitted as a shortcut.
    """
    gap_id: str
    source_ref: str
    scene_ref: str
    required_operation: str
    required_attention_structure: str
    insufficient_registered_capabilities: tuple[str, ...]
    insufficient_declarative_primitives: tuple[str, ...]
    missing_capability_hypothesis: str
    evidence: tuple[str, ...]
    counterexamples: tuple[str, ...] = ()
    affected_scene_telos: str = ""
    possible_development_direction: str = ""
    status: str = "unresolved"
    #: See :class:`OrganDevelopmentProposal`. Zero, always.
    activation_authority: str = "NONE"

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["insufficient_registered_capabilities"] = list(
            self.insufficient_registered_capabilities)
        d["insufficient_declarative_primitives"] = list(
            self.insufficient_declarative_primitives)
        d["evidence"] = list(self.evidence)
        d["counterexamples"] = list(self.counterexamples)
        return d


@dataclass
class OrganDevelopmentProposal:
    """A proposal for a HUMAN owner to consider developing the missing organ.

    Attached only to an :class:`OrganGap` — never emitted independently.
    ``activation_authority`` is a public constant string ``"NONE"``: this
    record grants no capability, mints no executor, and does not
    trigger any development pipeline on its own.
    """
    proposal_id: str
    gap_id: str
    proposal_text: str
    activation_authority: str = "NONE"

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


def new_gap_id() -> str:
    return f"gap_{secrets.token_hex(6)}"


# ---------------------------------------------------------- compile-bind


class BindingError(Exception):
    """A :class:`GeneratedCutterSpec` cannot be compiled against the
    primitive registry. Typed reason attached in ``args``.

    Raised — never silently swallowed. Callers that catch it MUST
    decide between (a) trying a different spec, or (b) declaring
    :class:`OrganGap`. There is no "nearest primitive" fallback.
    """


@dataclass
class CompiledCutter:
    """The executable form of a validated :class:`GeneratedCutterSpec`.

    Only produced by :func:`compile_bind`. Carries the ordered list of
    instantiated primitives + binding evidence (which spec primitive
    maps to which registered class, params validated, input/output
    types consistent). ``execute`` runs the composition against a
    source text and produces a :class:`ProjectionResult`.

    Not privileged: constructed from data + primitives already
    authorised by the registry.
    """
    spec: GeneratedCutterSpec
    instantiated: list[tuple[str, Any]]      # (name, instance) pairs
    binding_evidence: dict[str, Any]

    def execute(self, source_text: str) -> ProjectionResult:
        """Run the composition and package the result.

        Convention: the ``accepted`` and ``residue`` collections come
        from the outputs named by ``spec.accepted_output`` and
        ``spec.residue_output``. If the composition has a step whose
        output is a tuple ``(accepted, residue)`` (typical from
        :class:`TargetFilter`), the spec may name that step's output
        as both; :func:`execute` will unpack the tuple.
        """
        outputs: dict[str, Any] = {}
        for name, inst in self.instantiated:
            inv = _invocation_by_name(self.spec, name)
            if not inv.inputs:
                args = [source_text]
            else:
                args = [outputs[inp] for inp in inv.inputs]
            outputs[name] = inst.apply(*args)

        accepted, residue = _extract_accepted_and_residue(
            outputs, self.spec)

        projection_id = new_projection_id()
        objects = [self._to_projected_object(projection_id, c)
                   for c in accepted]
        residue_records = [self._to_residue(projection_id, c) for c in residue]
        total = max(len(objects) + len(residue_records), 1)
        coverage = len(objects) / total
        return ProjectionResult(
            projection_id=projection_id,
            spec_fingerprint=self.spec.fingerprint(),
            source_id=self.spec.source_id,
            objects=objects, residue=residue_records,
            coverage=coverage,
            recognition_failures=[
                f"{r.raw_label}@{r.start}-{r.end}: outside target family "
                f"{list(self.spec.target_object_family)}"
                for r in residue],
            status=(ProjectionStatus.ACCEPTED_LOCAL
                    if not residue else ProjectionStatus.PARTIAL))

    def _to_projected_object(self, projection_id: str,
                             c: ClassifiedSpan) -> ProjectedObject:
        return ProjectedObject(
            object_id=f"obj_{secrets.token_hex(5)}",
            object_family=c.family,
            source_id=self.spec.source_id,
            source_span=(c.start, c.end),
            evidence=c.body[:200],
            recognition_basis=(
                f"synthesised composition: "
                f"{' → '.join(p.primitive_id for p in self.spec.primitives)}"),
            confidence=1.0)

    def _to_residue(self, projection_id: str,
                    c: ClassifiedSpan) -> Residue:
        return Residue(
            residue_id=f"res_{secrets.token_hex(5)}",
            source_id=self.spec.source_id,
            source_span=(c.start, c.end),
            evidence=c.body[:200],
            apparent_family=c.family,
            reason=(f"family {c.family!r} not in target "
                    f"{list(self.spec.target_object_family)}"))


def _invocation_by_name(spec: GeneratedCutterSpec,
                        name: str) -> PrimitiveInvocation:
    for p in spec.primitives:
        if p.name == name:
            return p
    raise BindingError(f"invocation {name!r} not found in spec")


def _extract_accepted_and_residue(outputs: dict[str, Any],
                                  spec: GeneratedCutterSpec,
                                  ) -> tuple[list[ClassifiedSpan],
                                             list[ClassifiedSpan]]:
    if spec.accepted_output and spec.accepted_output in outputs:
        val = outputs[spec.accepted_output]
        if isinstance(val, tuple) and len(val) == 2:
            return list(val[0]), list(val[1])
        accepted = list(val)
        if spec.residue_output and spec.residue_output in outputs:
            return accepted, list(outputs[spec.residue_output])
        return accepted, []
    # Convention: if no explicit names, use the last invocation whose
    # output is a 2-tuple.
    for name in reversed([p.name for p in spec.primitives]):
        val = outputs.get(name)
        if isinstance(val, tuple) and len(val) == 2:
            return list(val[0]), list(val[1])
    raise BindingError(
        "cannot locate (accepted, residue) split in outputs — "
        "spec must name accepted_output/residue_output or contain "
        "a primitive whose output is a 2-tuple")


def compile_bind(spec: GeneratedCutterSpec,
                 primitive_registry: PrimitiveRegistry,
                 ) -> CompiledCutter:
    """Validate the spec against the registry, instantiate primitives,
    build a :class:`CompiledCutter`. Fails closed on any typed error.

    Checks performed:

        * every ``primitive_id`` in ``spec.primitives`` exists in the
          registry;
        * every referenced ``input`` name resolves to a prior
          invocation's ``name``;
        * each primitive class can be instantiated with the supplied
          params (a TypeError from the constructor becomes a
          :class:`BindingError` with the class + params in the message).

    Does NOT execute the primitives — that happens in
    :meth:`CompiledCutter.execute`. Compile-bind is a pure validation
    step; a spec that survives it will fail at execution only on data
    (e.g. a regex that matches nothing produces an empty projection,
    which is not a bind error).
    """
    instantiated: list[tuple[str, Any]] = []
    names_seen: set[str] = set()
    binding_evidence: dict[str, Any] = {
        "spec_id": spec.spec_id, "spec_fingerprint": spec.fingerprint(),
        "resolved_primitives": [],
    }

    for inv in spec.primitives:
        if not primitive_registry.has(inv.primitive_id):
            raise BindingError(
                f"primitive {inv.primitive_id!r} (invocation {inv.name!r}) "
                f"not registered. Known: {primitive_registry.known()}")
        cls = primitive_registry.get(inv.primitive_id)
        for inp in inv.inputs:
            if inp not in names_seen:
                raise BindingError(
                    f"invocation {inv.name!r} references undefined input "
                    f"{inp!r}. Defined so far: {sorted(names_seen)}")
        try:
            inst = cls(**inv.params)
        except TypeError as exc:
            raise BindingError(
                f"cannot construct primitive {inv.primitive_id!r} with "
                f"params {inv.params!r}: {exc}") from exc
        instantiated.append((inv.name, inst))
        names_seen.add(inv.name)
        binding_evidence["resolved_primitives"].append({
            "name": inv.name,
            "primitive_id": inv.primitive_id,
            "class": f"{cls.__module__}.{cls.__name__}",
            "contract": inst.contract(),
        })

    return CompiledCutter(spec=spec, instantiated=instantiated,
                          binding_evidence=binding_evidence)


# ---------------------------------------------------------- capability resolution


@dataclass
class CapabilityResolution:
    """Public typed record of a resolution decision.

    Enough evidence to reproduce WHY the branch was chosen — a
    resolver never picks silently; the reason string names the
    invariant used.
    """
    kind: CapabilityResolutionKind
    operation_id: str
    reason: str
    registered_capability_id: str = ""
    generated_spec: GeneratedCutterSpec | None = None
    compiled_cutter: CompiledCutter | None = None
    binding_evidence: dict[str, Any] = field(default_factory=dict)
    organ_gap: OrganGap | None = None

    def to_public(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "operation_id": self.operation_id,
            "reason": self.reason,
            "registered_capability_id": self.registered_capability_id,
            "generated_spec": (self.generated_spec.to_public()
                               if self.generated_spec is not None else None),
            "binding_evidence": dict(self.binding_evidence),
            "organ_gap": (self.organ_gap.to_public()
                          if self.organ_gap is not None else None),
        }


# ---------------------------------------------------------- synthesizer


@dataclass(frozen=True)
class SynthesisRequest:
    """Everything Socrates knows when asking for a spec to be synthesised.

    Public typed context — no hidden chain-of-thought. Consumed by
    :class:`SpecSynthesizer.synthesize`.
    """
    operation_id: str
    ontology_id: str
    source_id: str
    scene_ref: str
    target_object_family: tuple[str, ...]
    recognition_criteria: tuple[str, ...]
    #: Extra structured hypotheses the synthesizer may need. For
    #: pattern-based synthesis this typically carries a
    #: ``"regex_pattern"`` entry naming the source pattern to scan for.
    hypotheses: dict[str, Any] = field(default_factory=dict)


class SpecUnsynthesizable(Exception):
    """The synthesizer cannot produce a valid spec from this request.

    Raised — never silently returned as an "identity" spec or a
    "nearest match" coercion. A resolver that catches it MUST move on
    to :class:`OrganGap`.
    """


class SpecSynthesizer:
    """Bounded, deterministic spec synthesizer.

    Recognises exactly ONE synthesis pattern in this pass:

        * ``hypotheses["regex_pattern"]`` is present →
          SpanScanner → FamilyClassifier → TargetFilter →
          CoverageComputer.

    Any request without that hypothesis → :class:`SpecUnsynthesizable`
    (proving the synthesis path has a real boundary; a LIVE-mode
    synthesizer can extend the recognised patterns without changing
    this contract).
    """

    def synthesize(self, req: SynthesisRequest) -> GeneratedCutterSpec:
        pattern = req.hypotheses.get("regex_pattern")
        if not pattern or not isinstance(pattern, str):
            raise SpecUnsynthesizable(
                f"no pattern-based synthesis hypothesis for operation "
                f"{req.operation_id!r} (hypotheses: {list(req.hypotheses)!r}); "
                f"this synthesizer supports pattern-scan compositions only")

        family_map = req.hypotheses.get("family_map") or {
            f: f for f in req.target_object_family}
        primitives = (
            PrimitiveInvocation(
                name="scan", primitive_id="SpanScanner",
                params={"pattern": pattern,
                        "flags": req.hypotheses.get("regex_flags", 0),
                        "label_group": req.hypotheses.get("label_group", "label"),
                        "body_group": req.hypotheses.get("body_group", "body")},
                inputs=()),
            PrimitiveInvocation(
                name="classify", primitive_id="FamilyClassifier",
                params={"family_map": family_map,
                        "case_insensitive": True},
                inputs=("scan",)),
            PrimitiveInvocation(
                name="split", primitive_id="TargetFilter",
                params={"target_family": tuple(req.target_object_family)},
                inputs=("classify",)),
            PrimitiveInvocation(
                name="coverage", primitive_id="CoverageComputer",
                params={}, inputs=("split",)),
        )
        return GeneratedCutterSpec(
            spec_id=new_spec_id(), version="v0.1_candidate",
            source_id=req.source_id, scene_ref=req.scene_ref,
            operation_id=req.operation_id,
            ontology_id=req.ontology_id or f"synth/{req.operation_id.lower()}",
            target_object_family=tuple(req.target_object_family),
            recognition_criteria=tuple(req.recognition_criteria),
            segmentation_policy=(
                f"synthesised/pattern_scan/{req.operation_id.lower()}"),
            evidence_requirements=(f"regex_pattern={pattern!r}",),
            exclusions=(),
            contraindications=(),
            applicability_assumptions=(
                "source contains one target per line labelled by pattern",),
            primitives=primitives, accepted_output="split",
            status="exploratory")


# ---------------------------------------------------------- resolver


@dataclass
class CapabilityRequest:
    """Public typed input for a resolver decision.

    Carries everything the resolver needs so its decision (and
    supporting reason) is reproducible. No hidden state.
    """
    operation_id: str
    source_id: str
    scene_ref: str
    target_object_family: tuple[str, ...]
    ontology_hypothesis: str = ""
    recognition_criteria: tuple[str, ...] = ()
    hypotheses: dict[str, Any] = field(default_factory=dict)
    #: What Socrates thinks the required attention structure is —
    #: named on the :class:`OrganGap` if the runtime cannot supply it.
    required_attention_structure: str = ""


class CapabilityResolver:
    """Three-branch resolver: registered → synthesis → organ_gap.

    Never coerces to "nearest" registered cutter. Never silently
    fabricates a projection result. Every non-registered result
    carries the typed reason the earlier branches failed.

    Uses:

        * ``cutter_registry`` for REGISTERED_CAPABILITY lookup;
        * ``primitive_registry`` for CUTTER_SPEC_SYNTHESIS bind
          validation;
        * ``synthesizer`` (optional; defaults to :class:`SpecSynthesizer`)
          to produce candidate specs from public typed context.

    An absent synthesizer disables the SYNTHESIS branch entirely —
    every non-registered request would then become ORGAN_GAP. The
    default synthesizer supports one pattern (see
    :class:`SpecSynthesizer`); LIVE runs may supply richer
    synthesizers.
    """

    def __init__(self, cutter_registry: CutterRegistry,
                 primitive_registry: PrimitiveRegistry,
                 synthesizer: SpecSynthesizer | None = None) -> None:
        self.cutter_registry = cutter_registry
        self.primitive_registry = primitive_registry
        self.synthesizer = synthesizer or SpecSynthesizer()

    def resolve(self, req: CapabilityRequest) -> CapabilityResolution:
        # (1) REGISTERED
        cap = self.cutter_registry.get(req.operation_id)
        if cap is not None and self._fits_target(cap, req.target_object_family):
            return CapabilityResolution(
                kind=CapabilityResolutionKind.REGISTERED_CAPABILITY,
                operation_id=req.operation_id,
                reason=(f"registered capability {req.operation_id!r} covers "
                        f"target family {list(req.target_object_family)!r}"),
                registered_capability_id=req.operation_id,
                binding_evidence={
                    "capability_target_family": list(cap.target_object_family),
                    "capability_segmentation_policy": cap.segmentation_policy,
                })
        registered_reason = self._registered_failure_reason(
            cap, req.target_object_family)

        # (2) CUTTER_SPEC_SYNTHESIS
        try:
            synth_req = SynthesisRequest(
                operation_id=req.operation_id,
                ontology_id=req.ontology_hypothesis,
                source_id=req.source_id, scene_ref=req.scene_ref,
                target_object_family=req.target_object_family,
                recognition_criteria=req.recognition_criteria,
                hypotheses=dict(req.hypotheses))
            spec = self.synthesizer.synthesize(synth_req)
            compiled = compile_bind(spec, self.primitive_registry)
            return CapabilityResolution(
                kind=CapabilityResolutionKind.CUTTER_SPEC_SYNTHESIS,
                operation_id=req.operation_id,
                reason=(f"no registered capability for {req.operation_id!r}; "
                        f"synthesised spec {spec.spec_id} composes existing "
                        f"primitives "
                        f"[{', '.join(p.primitive_id for p in spec.primitives)}]"),
                generated_spec=spec, compiled_cutter=compiled,
                binding_evidence={
                    **compiled.binding_evidence,
                    "registered_lookup_failure": registered_reason,
                })
        except (SpecUnsynthesizable, BindingError) as exc:
            synth_failure_reason = f"{type(exc).__name__}: {exc}"

        # (3) ORGAN_GAP
        gap = OrganGap(
            gap_id=new_gap_id(),
            source_ref=req.source_id, scene_ref=req.scene_ref,
            required_operation=req.operation_id,
            required_attention_structure=req.required_attention_structure
                or "unspecified",
            insufficient_registered_capabilities=(
                tuple(self.cutter_registry.known_operations())),
            insufficient_declarative_primitives=(
                tuple(self.primitive_registry.known())),
            missing_capability_hypothesis=(
                f"no primitive or composition can produce "
                f"{req.operation_id!r} with target family "
                f"{list(req.target_object_family)!r}"),
            evidence=(registered_reason, synth_failure_reason),
            affected_scene_telos=req.scene_ref,
            possible_development_direction=(
                f"introduce a primitive capable of the required "
                f"attention structure "
                f"({req.required_attention_structure!r})"),
            status="unresolved")
        return CapabilityResolution(
            kind=CapabilityResolutionKind.ORGAN_GAP,
            operation_id=req.operation_id,
            reason=(f"neither registered capability nor declarative "
                    f"composition satisfies {req.operation_id!r}: "
                    f"registered={registered_reason}; "
                    f"synthesis={synth_failure_reason}"),
            organ_gap=gap)

    @staticmethod
    def _fits_target(cap: CutterCapability,
                     target: tuple[str, ...]) -> bool:
        cap_set = {f.lower() for f in cap.target_object_family}
        return set(t.lower() for t in target).issubset(cap_set)

    @staticmethod
    def _registered_failure_reason(cap: CutterCapability | None,
                                   target: tuple[str, ...]) -> str:
        if cap is None:
            return "operation_id not registered"
        return (f"registered {cap.operation_id!r} target "
                f"{list(cap.target_object_family)} does not cover "
                f"requested {list(target)!r}")


__all__ = [
    "BindingError", "CapabilityRequest", "CapabilityResolution",
    "CapabilityResolutionKind", "CapabilityResolver", "CompiledCutter",
    "GeneratedCutterSpec", "OrganDevelopmentProposal", "OrganGap",
    "PrimitiveInvocation", "SpecSynthesizer", "SpecUnsynthesizable",
    "SynthesisRequest", "compile_bind", "new_gap_id", "new_spec_id",
]

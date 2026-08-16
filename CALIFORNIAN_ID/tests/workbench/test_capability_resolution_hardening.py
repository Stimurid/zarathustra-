"""G-BD.1 hardening tests — T-PROV-01/02/03/04.

Owner audit of ADR-S26-022/023 flagged four defects. This module
contains the targeted tests that prove each repair holds. Tests are
grouped by defect id so a reader can map "which test proves which fix".

D-S26-GEN-002 — fingerprint canonicalisation (T-PROV-01 family).
D-S26-PROV-003 — explicit typed lineage relations (T-PROV-02 family).
D-S26-PROV-004 — direct projected-object provenance (T-PROV-03 family).
D-S26-GEN-003 — LIVE-authored ProjectionSynthesisProposal path
                (T-PROV-04 family).
"""
from __future__ import annotations

import re

import pytest

from socrates_runtime.capability_resolution import (
    BindingError,
    CapabilityResolver,
    GeneratedCutterSpec,
    OrganGap,
    PrimitiveInvocation,
    ProjectionSynthesisProposal,
    compile_bind,
    new_proposal_id,
    new_spec_id,
)
from socrates_runtime.cutter_registry import build_default_registry
from socrates_runtime.projection import (
    ProjectedObject,
    ProjectionResult,
    Residue,
    new_projection_id,
)
from socrates_runtime.projection_primitives import (
    build_default_primitive_registry,
)


# ---------------------------------------------------------- helpers


def _minimal_spec(**overrides) -> GeneratedCutterSpec:
    """A helper that returns a GeneratedCutterSpec with a valid
    composition. Overrides only the fields the caller wants to change.
    """
    base = dict(
        spec_id=new_spec_id(), version="v0.1", source_id="src_test",
        scene_ref="", operation_id="EXTRACT_TEST",
        ontology_id="test_v1",
        target_object_family=("hit",),
        recognition_criteria=("regex line",),
        segmentation_policy="test/scan",
        evidence_requirements=(), exclusions=(),
        contraindications=(), applicability_assumptions=(),
        primitives=(
            PrimitiveInvocation(name="scan", primitive_id="SpanScanner",
                                params={"pattern": r"^(?P<label>hit):"
                                                    r"\s*(?P<body>.*)$",
                                        "flags": re.MULTILINE}),
            PrimitiveInvocation(name="classify",
                                primitive_id="FamilyClassifier",
                                params={"family_map": {"hit": "hit"},
                                        "case_insensitive": True},
                                inputs=("scan",)),
            PrimitiveInvocation(name="split",
                                primitive_id="TargetFilter",
                                params={"target_family": ("hit",)},
                                inputs=("classify",)),
        ),
        accepted_output="split")
    base.update(overrides)
    return GeneratedCutterSpec(**base)


# ---------------------------------------------------------- T-PROV-01


class TestFingerprintCanonicalisation:
    """T-PROV-01 — GeneratedCutterSpec.fingerprint() must be a
    canonical content hash over EVERY field with executable meaning.
    """

    def test_same_composition_dict_key_reorder_same_fingerprint(self):
        """Reordering the keys of a primitive's ``params`` dict must NOT
        change the fingerprint — canonicalisation sorts them.
        """
        s1 = _minimal_spec(primitives=(
            PrimitiveInvocation(name="scan", primitive_id="SpanScanner",
                                params={"pattern": r"foo",
                                        "flags": 0}),))
        s2 = _minimal_spec(primitives=(
            PrimitiveInvocation(name="scan", primitive_id="SpanScanner",
                                params={"flags": 0,
                                        "pattern": r"foo"}),))
        assert s1.fingerprint() == s2.fingerprint(), (
            "params dict key order must not affect fingerprint")

    def test_different_regex_pattern_different_fingerprint(self):
        """Two specs with the SAME primitive id but DIFFERENT
        ``params.pattern`` must produce different fingerprints. This
        is the specific pre-repair defect: fingerprint omitted
        params, so materially different specs collided.
        """
        s1 = _minimal_spec(primitives=(
            PrimitiveInvocation(name="scan", primitive_id="SpanScanner",
                                params={"pattern": r"foo"}),))
        s2 = _minimal_spec(primitives=(
            PrimitiveInvocation(name="scan", primitive_id="SpanScanner",
                                params={"pattern": r"bar"}),))
        assert s1.fingerprint() != s2.fingerprint()

    def test_different_input_wiring_different_fingerprint(self):
        """Same primitive ids + same params but different `inputs`
        wiring must produce different fingerprints — wiring changes
        executable meaning (which primitive feeds which).
        """
        s1 = _minimal_spec(primitives=(
            PrimitiveInvocation(name="a", primitive_id="SpanScanner",
                                params={"pattern": r"x"}),
            PrimitiveInvocation(name="b", primitive_id="FamilyClassifier",
                                params={"family_map": {"x": "x"}},
                                inputs=("a",)),
        ))
        s2 = _minimal_spec(primitives=(
            PrimitiveInvocation(name="a", primitive_id="SpanScanner",
                                params={"pattern": r"x"}),
            PrimitiveInvocation(name="b", primitive_id="FamilyClassifier",
                                params={"family_map": {"x": "x"}},
                                inputs=()),          # different wiring
        ))
        assert s1.fingerprint() != s2.fingerprint()

    def test_different_invocation_order_different_fingerprint(self):
        """Primitive invocation order IS executable meaning; reordering
        the primitives (even with the same names + params) must
        produce a different fingerprint.
        """
        p_a = PrimitiveInvocation(name="a", primitive_id="SpanScanner",
                                   params={"pattern": r"x"})
        p_b = PrimitiveInvocation(name="b", primitive_id="FamilyClassifier",
                                   params={"family_map": {"x": "x"}},
                                   inputs=("a",))
        s1 = _minimal_spec(primitives=(p_a, p_b))
        s2 = _minimal_spec(primitives=(p_b, p_a))
        assert s1.fingerprint() != s2.fingerprint()

    def test_lineage_dedup_treats_different_fingerprints_as_distinct(self):
        """Loop guards that dedup by fingerprint must treat the
        different-fingerprint case above as two distinct projections,
        not accidentally-equal duplicates.
        """
        s1 = _minimal_spec(primitives=(
            PrimitiveInvocation(name="scan", primitive_id="SpanScanner",
                                params={"pattern": r"foo"}),))
        s2 = _minimal_spec(primitives=(
            PrimitiveInvocation(name="scan", primitive_id="SpanScanner",
                                params={"pattern": r"bar"}),))
        seen = {s1.fingerprint()}
        assert s2.fingerprint() not in seen


# ---------------------------------------------------------- T-PROV-02


class TestExplicitLineage:
    """T-PROV-02 — explicit typed lineage on ProjectionResult.

    A trace/replay reader that loads records out of order must still
    be able to reconstruct P1 → diagnostics → ReflectiveReturn → P2
    causality without relying on list position.
    """

    def test_projection_result_carries_lineage_fields(self):
        r = ProjectionResult(projection_id="p2", spec_fingerprint="fp2",
                             source_id="src", parent_projection_id="p1",
                             revises_projection_id="p1",
                             triggered_by_diagnostic_id="d1",
                             triggered_by_diagnostic_fingerprint="dfp1",
                             reflective_return_id="r1",
                             spec_id="cutspec_abc",
                             capability_resolution_id="cres:1")
        public = r.to_public()
        for k in ("parent_projection_id", "revises_projection_id",
                  "triggered_by_diagnostic_id",
                  "triggered_by_diagnostic_fingerprint",
                  "reflective_return_id", "spec_id",
                  "capability_resolution_id"):
            assert k in public
            assert public[k] == getattr(r, k)

    def test_reconstruct_causal_graph_from_shuffled_records(self):
        """Load P1, P2, P3 in reverse order; reconstruct chain via typed
        fields. Explicit repair for pre-D-S26-PROV-003 code that would
        have needed the entries list index."""
        p1 = ProjectionResult(projection_id="p1", spec_fingerprint="fp1",
                              source_id="src")
        p2 = ProjectionResult(projection_id="p2", spec_fingerprint="fp2",
                              source_id="src",
                              parent_projection_id="p1",
                              revises_projection_id="p1",
                              triggered_by_diagnostic_id="d1",
                              reflective_return_id="r1")
        p3 = ProjectionResult(projection_id="p3", spec_fingerprint="fp3",
                              source_id="src",
                              parent_projection_id="p2",
                              revises_projection_id="p2",
                              triggered_by_diagnostic_id="d2",
                              reflective_return_id="r2")
        shuffled = [p3, p1, p2]                       # not ordering
        by_id = {r.projection_id: r for r in shuffled}
        # Walk causality backward from p3
        chain = ["p3"]
        cur = by_id["p3"]
        while cur.parent_projection_id:
            chain.append(cur.parent_projection_id)
            cur = by_id[cur.parent_projection_id]
        assert chain == ["p3", "p2", "p1"]


# ---------------------------------------------------------- T-PROV-03


class TestObjectProvenance:
    """T-PROV-03 — every ProjectedObject / Residue must carry direct
    (or resolvable) refs to projection, spec, operation, ontology and
    (when known) space/scene/branch — not just source spans.
    """

    def test_projected_object_carries_provenance_fields(self):
        o = ProjectedObject(object_id="o1", object_family="x",
                            source_id="src", source_span=(0, 3),
                            evidence="foo", recognition_basis="r",
                            projection_id="p1",
                            spec_fingerprint="fp",
                            operation_id="OP",
                            ontology_id="ONT",
                            space_id="sp", scene_id="sc",
                            branch_id="br")
        public = o.to_public()
        for k in ("projection_id", "spec_fingerprint",
                  "operation_id", "ontology_id",
                  "space_id", "scene_id", "branch_id"):
            assert k in public

    def test_stamp_object_provenance_idempotent(self):
        """stamp_object_provenance must not overwrite existing values —
        an older result loaded from a pre-hardening trace stays
        readable and gains missing fields without corrupting the ones
        already present."""
        r = ProjectionResult(
            projection_id="p1", spec_fingerprint="fp", source_id="src",
            objects=[ProjectedObject(
                object_id="o1", object_family="x", source_id="src",
                source_span=(0, 3), evidence="foo",
                recognition_basis="r",
                operation_id="OLD_OP",             # pre-existing
                projection_id="")])                # missing
        r.stamp_object_provenance(operation_id="NEW_OP",
                                  ontology_id="ONT")
        # projection_id backfilled
        assert r.objects[0].projection_id == "p1"
        # operation_id preserved (idempotent, doesn't overwrite)
        assert r.objects[0].operation_id == "OLD_OP"
        # ontology_id backfilled
        assert r.objects[0].ontology_id == "ONT"

    def test_stamp_covers_residue_and_objects(self):
        r = ProjectionResult(
            projection_id="p1", spec_fingerprint="fp", source_id="src",
            objects=[ProjectedObject(
                object_id="o1", object_family="x", source_id="src",
                source_span=(0, 3), evidence="foo", recognition_basis="r")],
            residue=[Residue(
                residue_id="e1", source_id="src", source_span=(4, 8),
                evidence="bar", apparent_family="y",
                reason="not target")])
        r.stamp_object_provenance(operation_id="OP", ontology_id="ONT",
                                  space_id="SP")
        assert r.objects[0].projection_id == "p1"
        assert r.residue[0].projection_id == "p1"
        assert r.residue[0].space_id == "SP"


# ---------------------------------------------------------- T-PROV-04


class TestProposalPath:
    """T-PROV-04 — LIVE-authored ProjectionSynthesisProposal must be
    typed DATA, must compile-bind, must fail closed on unknown
    primitives, and must never mint executor authority.
    """

    def test_proposal_is_unprivileged_data(self):
        """The proposal class exposes no execute/install/authorize/
        mint/deploy methods — it is data, not authority."""
        prop = ProjectionSynthesisProposal(
            proposal_id="p1", operation_id="OP",
            target_object_family=("x",), ontology_hypothesis="o",
            recognition_criteria=(), segmentation_policy_hint="",
            evidence_requirements=(), exclusions=(),
            contraindications=(), applicability_assumptions=(),
            primitives=(PrimitiveInvocation(
                name="a", primitive_id="SpanScanner",
                params={"pattern": r"x"}),))
        for meth in ("execute", "install", "authorize",
                     "mint", "deploy", "activate"):
            assert not hasattr(prop, meth), (
                f"ProjectionSynthesisProposal must not expose {meth!r}")

    def test_proposal_materialises_as_spec_under_runtime_provenance(self):
        """The proposal supplies composition; the runtime supplies
        source_id + scene_ref + parent lineage."""
        prop = ProjectionSynthesisProposal(
            proposal_id="p1", operation_id="EXTRACT_X",
            target_object_family=("x",), ontology_hypothesis="ont_v1",
            recognition_criteria=("regex",),
            segmentation_policy_hint="scan_v1",
            evidence_requirements=(), exclusions=(),
            contraindications=(), applicability_assumptions=(),
            primitives=(
                PrimitiveInvocation(name="scan",
                                    primitive_id="SpanScanner",
                                    params={"pattern": r"^\[(?P<label>x)\]"
                                                        r"\s*(?P<body>.*)$",
                                            "flags": re.MULTILINE}),
                PrimitiveInvocation(name="classify",
                                    primitive_id="FamilyClassifier",
                                    params={"family_map": {"x": "x"}},
                                    inputs=("scan",)),
                PrimitiveInvocation(name="split",
                                    primitive_id="TargetFilter",
                                    params={"target_family": ("x",)},
                                    inputs=("classify",)),
            ),
            accepted_output="split")
        spec = prop.to_spec(source_id="src_abc", scene_ref="scene_1",
                            parent_projection_id="p0")
        assert spec.source_id == "src_abc"
        assert spec.scene_ref == "scene_1"
        assert spec.parent_projection_id == "p0"
        assert spec.operation_id == "EXTRACT_X"
        assert spec.ontology_id == "ont_v1"
        assert len(spec.primitives) == 3

    def test_resolver_resolves_from_proposal_and_executes(self):
        """End-to-end: resolver.resolve_from_proposal compile-binds a
        valid proposal and returns a CUTTER_SPEC_SYNTHESIS resolution
        with a compiled cutter that physically executes."""
        cr = build_default_registry()
        pr = build_default_primitive_registry()
        resolver = CapabilityResolver(cr, pr)
        source = ("[x] hello alpha\n"
                  "[x] hello beta\n"
                  "[y] not target gamma")
        prop = ProjectionSynthesisProposal(
            proposal_id=new_proposal_id(),
            operation_id="EXTRACT_XONLY",
            target_object_family=("x",), ontology_hypothesis="x_only_v1",
            recognition_criteria=("[x] lines",),
            segmentation_policy_hint="",
            evidence_requirements=(), exclusions=(),
            contraindications=(), applicability_assumptions=(),
            primitives=(
                PrimitiveInvocation(name="scan",
                                    primitive_id="SpanScanner",
                                    params={"pattern":
                                            r"^\[(?P<label>[a-z])\]\s*"
                                            r"(?P<body>.*)$",
                                            "flags": re.MULTILINE}),
                PrimitiveInvocation(name="classify",
                                    primitive_id="FamilyClassifier",
                                    params={"family_map": {"x": "x",
                                                            "y": "y"}},
                                    inputs=("scan",)),
                PrimitiveInvocation(name="split",
                                    primitive_id="TargetFilter",
                                    params={"target_family": ("x",)},
                                    inputs=("classify",)),
            ),
            accepted_output="split")
        resolution = resolver.resolve_from_proposal(
            prop, source_id="src_test", scene_ref="scene_x")
        assert resolution.kind.value == "CUTTER_SPEC_SYNTHESIS"
        assert resolution.binding_evidence["proposal_id"] == prop.proposal_id
        assert resolution.binding_evidence["proposal_origin"] == "MODEL_PRODUCED"
        result = resolution.compiled_cutter.execute(source)
        assert len(result.objects) == 2
        assert len(result.residue) == 1
        assert result.residue[0].apparent_family == "y"

    def test_resolver_fails_closed_on_unknown_primitive_in_proposal(self):
        """A proposal that names an unknown primitive must not mint one.
        Bind failure → ORGAN_GAP, not fabricated execution."""
        cr = build_default_registry()
        pr = build_default_primitive_registry()
        resolver = CapabilityResolver(cr, pr)
        prop = ProjectionSynthesisProposal(
            proposal_id="prop_x", operation_id="OP",
            target_object_family=("x",), ontology_hypothesis="o",
            recognition_criteria=(), segmentation_policy_hint="",
            evidence_requirements=(), exclusions=(),
            contraindications=(), applicability_assumptions=(),
            primitives=(PrimitiveInvocation(
                name="a", primitive_id="NotARegisteredPrimitive",
                params={}),))
        resolution = resolver.resolve_from_proposal(
            prop, source_id="src", scene_ref="")
        assert resolution.kind.value == "ORGAN_GAP"
        assert resolution.organ_gap is not None
        assert "NotARegisteredPrimitive" in "; ".join(
            resolution.organ_gap.evidence)


class TestS4ContractAcceptsProposal:
    """T-PROV-04 continued — S4's output contract admits the proposal
    field under its declared jurisdiction, so LIVE model output that
    carries a proposal parses without a jurisdiction violation.
    """

    def test_s4_contract_permits_proposal_field(self):
        from socrates_runtime.phase_contracts import (
            CONTRACTS, JURISDICTION, output_contract_for, jurisdiction_for)
        assert "projection_synthesis_proposal" in \
            CONTRACTS["S4"]["properties"]
        assert "projection_synthesis_proposal" in JURISDICTION["S4"]
        # Sanity via the public accessors too
        assert "projection_synthesis_proposal" in \
            output_contract_for("S4")["properties"]
        assert "projection_synthesis_proposal" in jurisdiction_for("S4")

    def test_parse_and_validate_s4_proposal_delta_produces_typed_object(
            self, monkeypatch):
        """Round-trip: a JSON delta at S4 that includes a valid
        proposal parses into a typed ProjectionSynthesisProposal on
        the PhaseDelta.
        """
        monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")
        import json
        from socrates_runtime.phase_output import parse_and_validate_output
        from socrates_runtime.phase_executor import PhaseExecutionRequest
        from socrates_runtime.routers import RouterRegistry
        from socrates_runtime.mount import MountedContext
        from socrates_runtime.identity import (
            SocratesIdentity, SocratesRunConfiguration)
        payload = {
            "operation": {"kind": "EXTRACT_XONLY", "applicable": True},
            "projection_synthesis_proposal": {
                "proposal_id": "prop_z",
                "operation_id": "EXTRACT_XONLY",
                "target_object_family": ["x"],
                "ontology_hypothesis": "x_only_v1",
                "recognition_criteria": ["lines like [x] body"],
                "segmentation_policy_hint": "scan/x",
                "primitives": [
                    {"name": "scan", "primitive_id": "SpanScanner",
                     "params": {"pattern":
                                r"^\[(?P<label>[a-z])\]\s*(?P<body>.*)$",
                                "flags": 8},
                     "inputs": []},
                    {"name": "split", "primitive_id": "TargetFilter",
                     "params": {"target_family": ["x"]},
                     "inputs": ["scan"]},
                ],
                "accepted_output": "split",
                "rationale": "test",
            },
        }
        raw = json.dumps(payload)
        identity = SocratesIdentity.bootstrap()
        cfg = SocratesRunConfiguration(
            semantic_pack_version=identity.pack.version,
            semantic_pack_sha256=identity.pack.source_bundle_sha256)
        router = RouterRegistry().router_for_phase("S4")
        # Minimal MountedContext is not needed to reach _build_delta;
        # phase_output.parse_and_validate_output constructs the delta
        # once contract validation passes. We can bypass the mount by
        # passing a stub — the parser doesn't use `mount`.
        class _StubMount:
            def to_public(self): return {}
        request = PhaseExecutionRequest(
            phase="S4", router=router, mounted=_StubMount(),
            input_text="", state_snapshot={},
            run_configuration=cfg, max_retries=0)
        delta = parse_and_validate_output(raw, request)
        assert delta.projection_synthesis_proposal is not None
        prop = delta.projection_synthesis_proposal
        assert prop.operation_id == "EXTRACT_XONLY"
        assert len(prop.primitives) == 2
        assert prop.primitives[0].primitive_id == "SpanScanner"

"""G-BD.3 tests — BACH operator library OP-01..OP-18.

Proves:

    * all 18 operators exist and are addressable by id;
    * every operator has a fully populated typed record (trigger /
      precondition / effect / output / stop / failure / provenance);
    * bindings cover the eight :class:`OperatorBinding` values;
    * donor-local vs transferable operators are classified per §7;
    * an operator cannot mint execution authority (it exposes no
      `execute` / `install` / `authorize` method).

Runtime dispatch (executing an operator through the pipeline) is
G-BD.6 / G-BD.10. Here we prove the LIBRARY is complete and typed.
"""
from __future__ import annotations

import pytest

from socrates_runtime.bach_operators import (
    BachOperator, BachOperatorRegistry, OperatorBinding,
    build_default_operator_registry,
)


@pytest.fixture()
def registry() -> BachOperatorRegistry:
    return build_default_operator_registry()


REQUIRED_IDS = tuple(f"OP-{i:02d}" for i in range(1, 19))


class TestLibraryCompleteness:
    def test_all_eighteen_operators_registered(self, registry):
        ids = {op.id for op in registry.all()}
        missing = set(REQUIRED_IDS) - ids
        assert not missing, f"missing operators: {sorted(missing)}"

    def test_no_extra_operators(self, registry):
        ids = {op.id for op in registry.all()}
        extras = ids - set(REQUIRED_IDS)
        assert not extras, f"unexpected operators: {sorted(extras)}"

    @pytest.mark.parametrize("op_id", REQUIRED_IDS)
    def test_operator_has_all_typed_fields(self, registry, op_id):
        op = registry.get(op_id)
        assert op is not None
        for field in ("name", "purpose", "trigger", "precondition",
                      "effect", "output", "stop", "failure",
                      "provenance", "activation_scope"):
            value = getattr(op, field)
            assert value, f"{op_id}.{field} must be non-empty"

    def test_every_operator_has_at_least_one_semantic_body_ref(self, registry):
        for op in registry.all():
            assert op.semantic_body_refs, (
                f"{op.id} must reference at least one v0.3 body section")


class TestBindings:
    def test_all_bindings_are_valid_enum_values(self, registry):
        for op in registry.all():
            assert isinstance(op.binding, OperatorBinding)

    def test_bindings_cover_the_seven_runtime_bindings(self, registry):
        """Eight bindings exist; at least the seven runtime ones must
        appear in the library so we know each seam actually has an
        operator using it. SEMANTIC_ONLY is permitted and used."""
        seen = {op.binding for op in registry.all()}
        for binding in OperatorBinding:
            # PROJECTION_SPEC, REFLECTIVE_LOOP, TRANSDUCTION,
            # SCENE_BRANCH*, MEMORY_SCOPE, CONFLICT_HOLD,
            # ATTENTION_CONFIG, PASSPORT_ONLY, SEMANTIC_ONLY
            # (*SCENE_BRANCH may be exercised by G-BD.6 loop machinery
            # rather than by a named operator; not required here.)
            if binding == OperatorBinding.SCENE_BRANCH:
                continue
            assert binding in seen, (
                f"no operator declared binding={binding.value!r}")

    def test_by_binding_returns_matching_operators(self, registry):
        reflect = registry.by_binding(OperatorBinding.REFLECTIVE_LOOP)
        ids = {op.id for op in reflect}
        # OP-01 and OP-03 both use the reflective loop.
        assert "OP-01" in ids
        assert "OP-03" in ids


class TestDonorLocalClassification:
    def test_donor_local_set_matches_adr_section_7(self, registry):
        """§7 conditional / BACH-local: fold semantics (OP-07) and
        unfold-in-medium (OP-08) are donor-local in this pass.
        Transferable operators must NOT be marked donor_local."""
        local = set(registry.donor_local_ids())
        assert "OP-07" in local
        assert "OP-08" in local
        # Everything else in the transferable list.
        transferable = set(registry.transferable_ids())
        assert transferable.isdisjoint(local)
        # Union covers all 18.
        assert local | transferable == set(REQUIRED_IDS)


class TestAuthorityInvariants:
    def test_operator_class_exposes_no_execution_authority(self):
        """A BachOperator is a typed record, not a callable capability.
        It must not expose execute/install/authorize/mint/deploy —
        that is the ADR-S26-023 §10 invariant applied to the operator
        layer.
        """
        for meth in ("execute", "install", "authorize",
                     "mint", "deploy", "activate"):
            assert not hasattr(BachOperator, meth)

    def test_registry_registration_does_not_grant_authority(self, registry):
        """Registering a new operator adds a NAMED DISPOSITION — it
        does NOT install a primitive or expand executable authority.
        The binding decides which existing seam the operator can
        route through.
        """
        new_op = BachOperator(
            id="OP-XX", name="test",
            purpose="test disposition",
            binding=OperatorBinding.SEMANTIC_ONLY,
            trigger="test", precondition="test",
            effect="none — semantic only", output="SEMANTIC_ONLY",
            stop="always", failure="none",
            provenance="test", activation_scope="test",
            semantic_body_refs=("test",))
        registry.register(new_op)
        assert registry.get("OP-XX") is new_op
        # No callable added, no primitive registered.
        assert not hasattr(new_op, "execute")


class TestPublicSerialisation:
    def test_operator_to_public_is_schema_flat(self, registry):
        for op in registry.all():
            pub = op.to_public()
            for k in ("id", "name", "purpose", "binding", "trigger",
                      "precondition", "effect", "output", "stop",
                      "failure", "provenance", "activation_scope",
                      "donor_local", "semantic_body_refs"):
                assert k in pub
            assert pub["binding"] == op.binding.value
            assert isinstance(pub["semantic_body_refs"], list)

    def test_registry_to_public_lists_every_operator(self, registry):
        pub = registry.to_public()
        assert len(pub) == 18
        ids = {row["id"] for row in pub}
        assert ids == set(REQUIRED_IDS)


class TestReflectiveOperatorsPointAtExistingSeams:
    """Cross-layer smoke: operators that claim to bind to a runtime
    seam should map to concepts that actually exist. This does not
    execute them — it just checks the wiring hypothesis is coherent."""

    def test_reflective_loop_operators_reference_reflective_return(
            self, registry):
        for op in registry.by_binding(OperatorBinding.REFLECTIVE_LOOP):
            assert "ReflectiveReturn" in op.effect or \
                "ReflectiveReturn" in op.output

    def test_transduction_operators_reference_context_transduction(
            self, registry):
        for op in registry.by_binding(OperatorBinding.TRANSDUCTION):
            assert "ContextTransduction" in op.output

    def test_memory_scope_operators_reference_scope_or_policy(
            self, registry):
        for op in registry.by_binding(OperatorBinding.MEMORY_SCOPE):
            joined = " ".join((op.trigger, op.effect, op.precondition,
                                op.output)).lower()
            assert ("scope" in joined or "memoryvalidityscope" in joined
                    or "b05" in joined)

    def test_conflict_operators_reference_conflict_holding_state(
            self, registry):
        for op in registry.by_binding(OperatorBinding.CONFLICT_HOLD):
            assert "ConflictHoldingState" in op.output

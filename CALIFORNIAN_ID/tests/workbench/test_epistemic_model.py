"""G-BD.2 tests — first-class typed epistemic-model objects.

Proves:

    * types exist with the ADR-required fields;
    * enums cover the ADR-required values;
    * `to_public()` produces stable public dicts (schema-compatible);
    * registries look up by id;
    * `PipelineState` carries the new typed state as expected;
    * direct-assistance runs get a default workspace Space without
      the caller having to declare one (invariant: new machinery
      does not tax a trivial request).

Broader Didenko / BACH invariants (Space ≠ Scene, provenance ≠
activation, no fact-leak between branches) get their acceptance tests
in G-BD.6 / G-BD.10 where the pipeline actually exercises the
transitions. Here we prove the DATA MODEL is correct.
"""
from __future__ import annotations

import pytest

from socrates_runtime.epistemic_model import (
    ConflictFamily,
    ConflictHandlingMode,
    ConflictHoldingState,
    ConflictRegistry,
    ConstructionStatus,
    ContextTransduction,
    CrossScopePolicy,
    DEFAULT_WORKSPACE_SPACE_ID,
    EpistemicPassport,
    EpistemicSpace,
    MemoryValidityScope,
    MountMode,
    SceneBranch,
    SceneRef,
    SceneRegistry,
    SpaceRegistry,
    TransductionKind,
    WorldModelMount,
    build_default_workspace_space,
    new_branch_id,
    new_conflict_id,
    new_mount_id,
    new_passport_id,
    new_scene_id,
    new_space_id,
    new_transition_id,
)
from socrates_runtime.state import PipelineState


# ---------------------------------------------------------- enums


class TestEnumsCoverADRValues:
    def test_mount_mode_covers_adr(self):
        vals = {m.value for m in MountMode}
        for v in ("PRIMARY", "OVERLAY", "LENS", "CONTRAST",
                  "NEGATIVE_CONTROL", "ARCHIVAL"):
            assert v in vals

    def test_transduction_kind_covers_adr(self):
        vals = {k.value for k in TransductionKind}
        for v in ("TRANSLATION", "REFRAME", "ONTOLOGICAL_TRANSFER",
                  "TRANSDUCTION", "CONTRAST", "FUNCTIONAL_RHYME",
                  "ANALOGY", "DO_NOT_COLLAPSE"):
            assert v in vals

    def test_memory_scope_covers_adr(self):
        vals = {m.value for m in MemoryValidityScope}
        for v in ("GLOBAL_SELF", "GLOBAL_BETWEEN", "PROJECT",
                  "SPACE_OR_DOMAIN", "SCENE", "BRANCH", "PROJECTION",
                  "INSTRUMENT", "ARCHIVAL_ONLY"):
            assert v in vals

    def test_cross_scope_policy_covers_adr(self):
        vals = {p.value for p in CrossScopePolicy}
        for v in ("FORBID", "REQUIRE_EXPLICIT_BRIDGE",
                  "ALLOW_READONLY", "ALLOW_WITH_TRANSDUCTION"):
            assert v in vals

    def test_conflict_families_cover_adr(self):
        vals = {f.value for f in ConflictFamily}
        for v in ("ONTOLOGY", "EPISTEMIC_STATUS", "AUTHORITY",
                  "OPERATION", "VALUE", "CAUSAL_GRAMMAR",
                  "IDENTITY_RULE", "MEMORY_FORCE"):
            assert v in vals

    def test_conflict_handling_modes_cover_adr(self):
        vals = {h.value for h in ConflictHandlingMode}
        for v in ("LOCALIZE", "HOLD", "TRANSLATE", "TRANSDUCE",
                  "ARBITRATE_ACTION", "SUSPEND", "REJECT"):
            assert v in vals

    def test_construction_status_covers_adr(self):
        vals = {c.value for c in ConstructionStatus}
        for v in ("SOURCE_OWNED", "RECONSTRUCTED", "HYPOTHESIZED",
                  "CONSTRUCTED", "HYBRID", "UNKNOWN"):
            assert v in vals


# ---------------------------------------------------------- shapes


class TestShapesAndPublicSerialisation:
    def test_epistemic_space_has_required_fields(self):
        s = EpistemicSpace(space_id="sp1", version="v0.1", name="test")
        pub = s.to_public()
        for k in ("space_id", "version", "name", "telos_scope",
                  "world_model_mounts", "ontology_refs",
                  "proof_regime", "claim_status_policy",
                  "allowed_operation_families",
                  "operator_capabilities", "corpus_namespaces",
                  "retrieval_policy", "memory_default_scope",
                  "memory_recruitment_policy", "authority_refs",
                  "transition_policy", "provenance",
                  "activation_scope", "lineage", "supersedes",
                  "status"):
            assert k in pub

    def test_world_model_mount_provenance_neq_activation(self):
        """Structural encoding of §6.2 invariant: mount has SEPARATE
        provenance and activation_scope fields; they can differ.
        """
        m = WorldModelMount(
            mount_id="m1", space_id="sp1", ontology_ref="bach.v1",
            mount_mode=MountMode.LENS,
            provenance="donor:BACH",
            activation_scope="general_method_only")
        assert m.provenance == "donor:BACH"
        assert m.activation_scope == "general_method_only"
        assert m.provenance != m.activation_scope
        pub = m.to_public()
        assert pub["mount_mode"] == "LENS"

    def test_scene_branch_carries_memory_scope(self):
        b = SceneBranch(branch_id="br1", scene_id="sc1",
                        hypothesis="alt hypothesis X",
                        memory_scope=MemoryValidityScope.BRANCH)
        pub = b.to_public()
        assert pub["memory_scope"] == "BRANCH"
        assert pub["hypothesis"] == "alt hypothesis X"

    def test_context_transduction_records_loss_by_construction(self):
        """§6.6: every move MUST declare preserved/transformed/dropped/
        newly_created/unresolved. Fields exist on the dataclass with
        list defaults so a call site cannot forget them silently.
        """
        t = ContextTransduction(
            transition_id="t1",
            kind=TransductionKind.TRANSDUCTION,
            source_space_id="sp_a", target_space_id="sp_b",
            preserved=("core object x",),
            transformed=("frame Y -> Y'",),
            dropped=("Z"),
            newly_created=("medium-specific artefact",),
            unresolved=("open question about Q",),
            loss_report="Z dropped because target medium cannot carry it",
        )
        pub = t.to_public()
        assert pub["kind"] == "TRANSDUCTION"
        assert pub["preserved"] == ["core object x"]
        assert pub["dropped"] == ["Z"]           # even single str becomes list
        assert pub["newly_created"] == ["medium-specific artefact"]
        assert pub["loss_report"].startswith("Z dropped")

    def test_epistemic_passport_is_readonly_shape(self):
        p = EpistemicPassport(
            passport_id="pass1",
            construction_status=ConstructionStatus.RECONSTRUCTED,
            memory_validity_scope=MemoryValidityScope.SCENE,
            known_conflicts=("c_ontology",),
            known_loss=("early context dropped in transduction",),
            open_questions=("what would falsify?",),
            truth_mode_readout="derived_read_model_only")
        # No mutation methods.
        for m in ("upgrade", "authorize", "activate",
                  "commit", "install"):
            assert not hasattr(p, m)
        pub = p.to_public()
        assert pub["memory_validity_scope"] == "SCENE"
        assert pub["construction_status"] == "RECONSTRUCTED"

    def test_conflict_holding_state_carries_family_and_mode(self):
        c = ConflictHoldingState(
            conflict_id="c1",
            family=ConflictFamily.ONTOLOGY,
            handling_mode=ConflictHandlingMode.HOLD,
            description="two grounded ontologies disagree on X",
            discriminating_evidence_required=("evidence e1",),
            action_arbitration="prefer action A pending evidence")
        pub = c.to_public()
        assert pub["family"] == "ONTOLOGY"
        assert pub["handling_mode"] == "HOLD"


# ---------------------------------------------------------- registries


class TestRegistries:
    def test_space_registry_roundtrip(self):
        reg = SpaceRegistry()
        s = EpistemicSpace(space_id="sp1", version="v", name="n")
        reg.register(s)
        assert reg.has("sp1")
        assert reg.get("sp1") is s
        assert "sp1" in reg.known()
        assert "sp1" in reg.to_public()

    def test_scene_registry_indexes_branches_by_scene(self):
        reg = SceneRegistry()
        reg.add_scene(SceneRef(scene_id="sc1", space_id="sp1"))
        b1 = SceneBranch(branch_id="br1", scene_id="sc1",
                          hypothesis="H1")
        b2 = SceneBranch(branch_id="br2", scene_id="sc1",
                          hypothesis="H2")
        reg.add_branch(b1)
        reg.add_branch(b2)
        branches = reg.branches_of("sc1")
        assert {b.branch_id for b in branches} == {"br1", "br2"}
        assert reg.get_branch("br1") is b1

    def test_conflict_registry_lists_held_conflicts(self):
        reg = ConflictRegistry()
        c = ConflictHoldingState(
            conflict_id="c1", family=ConflictFamily.OPERATION,
            handling_mode=ConflictHandlingMode.ARBITRATE_ACTION)
        reg.add(c)
        assert reg.all() == (c,)
        pub = reg.to_public()
        assert len(pub) == 1
        assert pub[0]["family"] == "OPERATION"


# ---------------------------------------------------------- state integration


class TestPipelineStateIntegration:
    def test_state_defaults_to_default_workspace_space(self):
        """Direct-assistance invariant: a run does not need to name
        a Space. The runtime supplies the default workspace one so
        ordinary requests remain simple.
        """
        s = PipelineState(run_id="r1", input_text="hi")
        assert s.space_id == DEFAULT_WORKSPACE_SPACE_ID
        assert s.scene_id == ""
        assert s.branch_id == ""

    def test_state_public_serialization_includes_new_typed_state(self):
        s = PipelineState(run_id="r1", input_text="hi")
        pub = s.to_public()
        for k in ("space_id", "scene_id", "branch_id",
                  "space_registry", "scene_registry",
                  "context_transductions", "conflict_registry",
                  "passports"):
            assert k in pub
        # Empty defaults
        assert pub["context_transductions"] == []
        assert pub["conflict_registry"] == []
        assert pub["passports"] == []

    def test_state_carries_populated_registries(self):
        s = PipelineState(run_id="r1", input_text="hi")
        default = build_default_workspace_space()
        s.space_registry.register(default)
        s.scene_registry.add_scene(SceneRef(scene_id="sc1",
                                             space_id=default.space_id))
        s.scene_registry.add_branch(SceneBranch(
            branch_id="br1", scene_id="sc1",
            hypothesis="hyp under scene 1"))
        pub = s.to_public()
        assert default.space_id in pub["space_registry"]
        assert "sc1" in pub["scene_registry"]["scenes"]
        assert "br1" in pub["scene_registry"]["branches"]

    def test_state_carries_transductions_and_conflicts(self):
        s = PipelineState(run_id="r1", input_text="hi")
        s.context_transductions.append(ContextTransduction(
            transition_id="t1", kind=TransductionKind.TRANSLATION,
            preserved=("x",)))
        s.conflict_registry.add(ConflictHoldingState(
            conflict_id="c1", family=ConflictFamily.VALUE,
            handling_mode=ConflictHandlingMode.HOLD))
        pub = s.to_public()
        assert pub["context_transductions"][0]["kind"] == "TRANSLATION"
        assert pub["conflict_registry"][0]["family"] == "VALUE"


# ---------------------------------------------------------- id factories


class TestIdFactoriesProducePrefixedIds:
    @pytest.mark.parametrize("factory,prefix", [
        (new_space_id, "space_"),
        (new_mount_id, "mount_"),
        (new_scene_id, "scene_"),
        (new_branch_id, "br_"),
        (new_transition_id, "trans_"),
        (new_conflict_id, "conf_"),
        (new_passport_id, "passport_"),
    ])
    def test_prefix(self, factory, prefix):
        rid = factory()
        assert rid.startswith(prefix)
        assert len(rid) > len(prefix)


# ---------------------------------------------------------- default workspace


class TestDefaultWorkspaceSpace:
    def test_builds_a_stable_default_space(self):
        s = build_default_workspace_space()
        assert s.space_id == DEFAULT_WORKSPACE_SPACE_ID
        assert s.status == "active"
        assert s.memory_default_scope == MemoryValidityScope.PROJECT
        # Direct-assistance friendly: allowed families is wildcard.
        assert "*" in s.allowed_operation_families

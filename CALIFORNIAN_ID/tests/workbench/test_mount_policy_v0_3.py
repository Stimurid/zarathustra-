"""G-BD.5 tests — v0.3 mount manifest sanity.

The runtime consumer of the new mount rules is G-BD.6; here we just
verify the manifest is well-formed and internally consistent with
G-BD.3 operator classification + G-BD.2 mount_mode enum.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from socrates_runtime.identity import DATA_ROOT
from socrates_runtime.bach_operators import build_default_operator_registry
from socrates_runtime.epistemic_model import MountMode


MOUNT_PATH = (DATA_ROOT / "candidate_v0_3" / "mount"
              / "semantic_mount_manifest_v0.3.yaml")


@pytest.fixture()
def manifest():
    return yaml.safe_load(MOUNT_PATH.read_text(encoding="utf-8"))


class TestManifestShape:
    def test_manifest_exists_and_declares_v03(self, manifest):
        assert manifest["version"] == "v0.3_candidate"
        assert "mandatory" in manifest
        assert "bach_local_isolation" in manifest
        assert "transferable_operators" in manifest
        assert "trigger_admission" in manifest

    def test_all_ten_bodies_bound_to_phases(self, manifest):
        bodies = manifest["mandatory"]
        for body in ("CORE", *(f"B{i:02d}" for i in range(1, 11))):
            assert body in bodies
            assert bodies[body]["phases"]

    def test_summary_substitution_forbidden_for_every_body(self, manifest):
        for body, spec in manifest["mandatory"].items():
            assert spec.get("summary_substitution_allowed") is False


class TestBachLocalIsolationMatchesOperatorRegistry:
    def test_manifest_donor_local_ids_match_operator_registry(self, manifest):
        """G-BD.3 marked OP-07 and OP-08 as donor_local=True. The mount
        manifest MUST list exactly the same ids under
        bach_local_isolation.donor_local_operator_ids — cross-layer
        consistency check."""
        manifest_ids = set(manifest["bach_local_isolation"]
                            ["donor_local_operator_ids"])
        registry_ids = set(build_default_operator_registry()
                            .donor_local_ids())
        assert manifest_ids == registry_ids

    def test_transferable_ids_match(self, manifest):
        manifest_ids = set(manifest["transferable_operators"]["ids"])
        registry_ids = set(build_default_operator_registry()
                            .transferable_ids())
        assert manifest_ids == registry_ids

    def test_admission_rule_mentions_mount_mode_gates(self, manifest):
        rule = manifest["bach_local_isolation"]["admission_rule"]
        # These three modes grant activation; the other three do not.
        for mode in ("PRIMARY", "OVERLAY", "LENS"):
            assert mode in rule
        for mode in ("NEGATIVE_CONTROL", "ARCHIVAL"):
            assert mode in rule


class TestTriggerAdmission:
    def test_authority_sources_restricted_to_typed_state(self, manifest):
        assert manifest["trigger_admission"]["authority_sources"] == [
            "typed_state", "authorized_transition"]

    def test_lexical_cue_and_similar_forbidden(self, manifest):
        forbidden = set(manifest["trigger_admission"]["forbidden_sources"])
        for src in ("lexical_cue", "retrieved_text", "donor_text",
                    "persona_text", "model_prior"):
            assert src in forbidden

    def test_new_v03_causes_declared(self, manifest):
        ids = {c["id"] for c in manifest["trigger_admission"]
               ["new_causes_in_v0_3"]}
        for cid in ("REFLECTIVE_MISMATCH_PENDING",
                    "MULTI_ONTOLOGY_MOUNT",
                    "OPERATION_MISMATCH",
                    "REVISE_APPARATUS_INVOKED",
                    "CROSS_SPACE_TRANSDUCTION_PENDING"):
            assert cid in ids


class TestHistoricalFallbackBanned:
    def test_no_silent_v02_substitution_permitted(self, manifest):
        hf = manifest["historical_fallback"]
        assert hf["allowed"] is False


class TestWorldModelMountRulesMatchEnum:
    def test_manifest_mount_modes_match_MountMode_enum(self, manifest):
        manifest_modes = set(manifest["world_model_mounts"]
                              ["mount_modes"].keys())
        enum_modes = {m.value for m in MountMode}
        assert manifest_modes == enum_modes

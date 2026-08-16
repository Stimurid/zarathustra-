"""G-BD.4 tests — v0.3 semantic body candidates load cleanly through a
scoped :class:`SemanticBodyRegistry` and do NOT contaminate the default
(v0.2) load path.

Proves:

    * a scoped registry pointed at ``candidate_v0_3/semantic`` loads
      exactly the nine v0.3 candidate bodies with their v0.3 version;
    * the default registry (`SemanticBodyRegistry()`) continues to load
      v0.2 exclusively — R8 controls byte-immutable;
    * every v0.3 candidate carries the 17-section standard structure
      (heading pattern check — sections 1 through 17 present);
    * B06 and B09 remain v0.2 identities (no v0.3 file).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from socrates_runtime.semantic import SemanticBodyRegistry
from socrates_runtime.identity import DATA_ROOT


V03_SEMANTIC_DIR = DATA_ROOT / "candidate_v0_3" / "semantic"
V02_SEMANTIC_DIR = DATA_ROOT / "current" / "semantic"

V03_BODIES = ("CORE", "B01", "B02", "B03", "B04", "B05",
              "B07", "B08", "B10")
V02_ONLY_BODIES = ("B06", "B09")


class TestV03LoadsThroughScopedRegistry:
    def test_scoped_registry_finds_all_v03_bodies(self):
        reg = SemanticBodyRegistry(semantic_dir=V03_SEMANTIC_DIR,
                                   mount_dir=V02_SEMANTIC_DIR.parent
                                             / "mount")
        for body in V03_BODIES:
            assert reg.has(body), (
                f"v0.3 scoped registry missing body {body!r}")
        # B06/B09 are NOT in the v0.3 dir; scoped registry sees them
        # only if present. Absence is legitimate — v0.2 remains
        # authoritative for those.
        for body in V02_ONLY_BODIES:
            assert not reg.has(body), (
                f"v0.3 scoped registry should NOT ship {body!r} "
                f"in this pass")

    def test_v03_bodies_declare_v03_semantic_version(self):
        reg = SemanticBodyRegistry(semantic_dir=V03_SEMANTIC_DIR,
                                   mount_dir=V02_SEMANTIC_DIR.parent
                                             / "mount")
        for body in V03_BODIES:
            rec = reg.get(body)
            assert rec.semantic_version.startswith("0.3"), (
                f"{body} declared version {rec.semantic_version!r}, "
                f"expected 0.3-family")

    def test_v03_files_follow_17_section_standard(self):
        for body in V03_BODIES:
            files = list(V03_SEMANTIC_DIR.glob(f"{body}*_v0.3_candidate.md"))
            if not files:
                # CORE has a different filename prefix
                files = list(V03_SEMANTIC_DIR.glob(
                    f"*CORE*_v0.3_candidate.md")) if body == "CORE" else []
            assert files, f"no v0.3 file found for {body}"
            path = files[0]
            text = path.read_text(encoding="utf-8")
            for section in range(1, 18):
                pattern = rf"(?m)^## {section}\."
                assert re.search(pattern, text), (
                    f"{path.name} missing section {section}")


class TestDefaultRegistryPreservesV02:
    def test_default_registry_still_v02(self):
        """Default registry (no semantic_dir override) must continue
        to load v0.2 exclusively — R8 controls byte-immutable."""
        reg = SemanticBodyRegistry()
        for body in ("CORE", *(f"B{i:02d}" for i in range(1, 11))):
            assert reg.has(body), f"v0.2 default registry missing {body}"
            rec = reg.get(body)
            assert rec.semantic_version.startswith("0.2"), (
                f"v0.2 default registry accidentally loaded {body} at "
                f"version {rec.semantic_version!r} — did v0.3 files "
                f"leak into current/semantic?")

    def test_no_v03_file_landed_in_current_semantic(self):
        """R8 preservation: nothing named v0.3_candidate should exist
        in the frozen v0.2 directory."""
        v03_files_in_v02_dir = list(
            V02_SEMANTIC_DIR.glob("*v0.3_candidate*"))
        assert not v03_files_in_v02_dir, (
            f"v0.3 files leaked into frozen v0.2 dir: "
            f"{[p.name for p in v03_files_in_v02_dir]}")


class TestV03DeltaManifest:
    def test_registry_manifest_declares_every_v03_body(self):
        import yaml
        manifest_path = (DATA_ROOT / "candidate_v0_3" / "routers"
                         / "semantic_body_registry_v0.3.yaml")
        assert manifest_path.exists()
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        assert manifest["version"] == "v0.3_candidate"
        declared = manifest["bodies"]
        for body in V03_BODIES:
            assert body in declared
            assert declared[body]["semantic_version"] == "0.3_candidate"
            assert declared[body]["file_name"]
            assert declared[body]["delta_summary"]

    def test_registry_manifest_marks_b06_b09_as_v02(self):
        import yaml
        manifest_path = (DATA_ROOT / "candidate_v0_3" / "routers"
                         / "semantic_body_registry_v0.3.yaml")
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        for body in V02_ONLY_BODIES:
            assert body in manifest["bodies"]
            assert manifest["bodies"][body]["semantic_version"] == \
                "0.2_candidate"
            assert manifest["bodies"][body]["file_name"] is None

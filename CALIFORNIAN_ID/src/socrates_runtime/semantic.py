"""Semantic body registry — reads CORE + B01..B10 from disk with exact identity.

Bodies are the recovered G-S25R v0.2 content, imported into
``data/socrates/current/semantic``. This registry loads them once, hashes
each file, and refuses to substitute a summary — every read either returns
the full body text or raises.

Nothing here mutates the bodies; they are effectively read-only source.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import (
    SemanticMountMissing,
    SemanticSummarySubstitutionAttempted,
    SemanticVersionMismatch,
)
from .identity import DATA_ROOT

SEMANTIC_DIR = DATA_ROOT / "current" / "semantic"
MOUNT_DIR = DATA_ROOT / "current" / "mount"


@dataclass(frozen=True)
class BodyRecord:
    body_id: str
    file_name: str
    absolute_path: str
    semantic_version: str
    sha256: str
    bytes: int
    #: Verbatim body text — never a summary. Loaded eagerly so the mount
    #: has a hard byte count to feed to the budget check.
    text: str

    def to_public(self) -> dict[str, Any]:
        # Everything except the full text; the trace records the identity,
        # not the content.
        return {"body_id": self.body_id, "file_name": self.file_name,
                "absolute_path": self.absolute_path,
                "semantic_version": self.semantic_version,
                "sha256": self.sha256, "bytes": self.bytes}


class SemanticBodyRegistry:
    """Loads and serves CORE + B01..B10 by body_id.

    Constructor reads the mount manifest (semantic_mount_manifest.yaml) for
    the declared bodies + their expected semantic_version. A file present on
    disk with a version mismatch is a mount failure, not a warning.
    """

    def __init__(self, semantic_dir: Path | None = None,
                 mount_dir: Path | None = None) -> None:
        self.semantic_dir = Path(semantic_dir or SEMANTIC_DIR)
        self.mount_dir = Path(mount_dir or MOUNT_DIR)
        self._bodies: dict[str, BodyRecord] = {}
        self._load()

    # ------------------------------------------------------------------

    def _load(self) -> None:
        import yaml

        registry_path = (self.semantic_dir.parent / "routers"
                         / "semantic_body_registry.yaml")
        # semantic_body_registry ended up under 'routers/' from the importer
        # convention because SEM_BODY_REGISTRY__ is prefix-classified there.
        # The mount manifest is what actually names required bodies, so we
        # tolerate a missing registry and fall back to file discovery for
        # the version fields.
        expected_versions: dict[str, str] = {}
        if registry_path.exists():
            reg = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
            for body_id, meta in (reg.get("bodies") or {}).items():
                expected_versions[body_id] = str(meta.get("semantic_version") or "")

        # File-name convention: <BODY_ID>_<name>_v<version>_candidate.md
        for path in sorted(self.semantic_dir.glob("*.md")):
            body_id = _body_id_from_filename(path.name)
            if body_id is None:
                continue
            text = path.read_text(encoding="utf-8")
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            version = _version_from_filename(path.name)
            expected = expected_versions.get(body_id)
            if expected and version and expected != version:
                raise SemanticVersionMismatch(
                    f"{body_id}: expected v{expected} per registry, "
                    f"found v{version} on disk")
            self._bodies[body_id] = BodyRecord(
                body_id=body_id, file_name=path.name,
                absolute_path=str(path).replace("\\", "/"),
                semantic_version=version or expected or "unknown",
                sha256=digest, bytes=len(text.encode("utf-8")),
                text=text)

        if "CORE" not in self._bodies:
            raise SemanticMountMissing(
                f"CORE body not present under {self.semantic_dir}; "
                f"import may be incomplete")

    # ------------------------------------------------------------------

    def has(self, body_id: str) -> bool:
        return body_id in self._bodies

    def get(self, body_id: str) -> BodyRecord:
        rec = self._bodies.get(body_id)
        if rec is None:
            raise SemanticMountMissing(
                f"body {body_id!r} not present in registry (searched "
                f"{self.semantic_dir})")
        return rec

    def get_summary(self, body_id: str) -> str:  # pragma: no cover
        raise SemanticSummarySubstitutionAttempted(
            f"summary substitution refused for {body_id!r}: the mount "
            "manifest sets summary_substitution_allowed=false for every body")

    def all_ids(self) -> list[str]:
        return sorted(self._bodies)


# ---------------------------------------------------------- helpers


_BODY_ID_PREFIXES = ("CORE", *(f"B{i:02d}" for i in range(1, 11)))


def _body_id_from_filename(name: str) -> str | None:
    """Return the body_id for a filename, or None.

    Naming inside the bundle has two shapes:

        B01_SCENE_TELOS_ROLE_AUTHORITY_v0.2_candidate.md      → B01
        SOCRATES_CORE_SEMANTIC_BODY_v0.2_candidate.md         → CORE

    So we look for either a leading Bxx token or the substring ``CORE`` in
    an unambiguous position (surrounded by underscores).
    """
    upper = name.upper()
    for i in range(1, 11):
        pref = f"B{i:02d}"
        if upper.startswith(pref + "_") or upper == pref + ".MD":
            return pref
    if "_CORE_" in upper or upper.startswith("CORE_") or upper.startswith("CORE.MD"):
        return "CORE"
    return None


def _version_from_filename(name: str) -> str:
    # The convention is ..._vX.Y_candidate.md ; a missing token yields ""
    parts = name.split("_")
    for token in parts:
        low = token.lower()
        if low.startswith("v") and any(ch.isdigit() for ch in low[1:]):
            return low[1:]
    return ""

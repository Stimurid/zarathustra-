"""Exact identity that every run must record.

The handoff's rule §16 requires: Socrates code commit, pipeline version,
PipelineConfig id/version, semantic pack version, CORE hash, mounted
Bxx body hashes, router versions, mount/context policy version,
hard-contract versions, provider/model/settings, RAG profile, native
organ identities, terminal result.

This module owns the *labels*; the mount and the trace fill in the *values*
at run time. Nothing here reads the runtime; everything is data.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "socrates"


# ---------------------------------------------------------- code commit

def resolve_code_commit(repo_root: Path | None = None) -> str:
    """Return the git commit that this code was built from — or 'unknown'.

    ``git`` may be unavailable (a container, a stripped install) and the
    runtime must still work. In that case we return ``"unknown"``, and the
    trace records exactly that — never a made-up value.
    """
    root = repo_root or Path(__file__).resolve().parents[3]
    try:
        r = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True, timeout=3)
        return r.stdout.strip() or "unknown"
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            FileNotFoundError, OSError):
        return "unknown"


# ---------------------------------------------------------- pack identity


@dataclass(frozen=True)
class SocratesPackIdentity:
    """Identifies the imported semantic package.

    Read from IMPORT_MANIFEST.yaml at load time so we never claim to be
    running against a bundle that has been overwritten since import.
    """
    version: str
    source_bundle_sha256: str
    source_bundle_filename: str
    imported_at: str

    @classmethod
    def from_manifest(cls, manifest_path: Path | None = None
                      ) -> "SocratesPackIdentity":
        path = Path(manifest_path or (DATA_ROOT / "IMPORT_MANIFEST.yaml"))
        if not path.exists():
            raise FileNotFoundError(
                f"Socrates import manifest not found: {path}")
        # Parser tolerates both yaml (default) and json fallback the importer
        # writes when PyYAML is absent.
        text = path.read_text(encoding="utf-8")
        try:
            import yaml
            data = yaml.safe_load(text)
        except ImportError:
            data = json.loads(text)
        return cls(
            version=str(data.get("version") or "unknown"),
            source_bundle_sha256=str(data.get("source_bundle_sha256") or ""),
            source_bundle_filename=str(data.get("source_bundle_filename") or ""),
            imported_at=str(data.get("imported_at") or ""),
        )


# ---------------------------------------------------------- run configuration


@dataclass(frozen=True)
class SocratesRunConfiguration:
    """The resolved effective configuration for one run.

    Passed IN to the runtime; the runtime never resolves it. Workbench /
    auth own the resolution, per handoff §15.
    """
    pipeline_config_id: str = ""
    workspace_id: str = "default"
    user_id: str = ""
    display_name: str = ""

    #: Reference to the pack the runtime was booted with; recorded to prove
    #: the run used the identity it claims.
    semantic_pack_version: str = ""
    semantic_pack_sha256: str = ""

    prompt_variant_selections: tuple[tuple[str, str], ...] = ()
    prompt_fragment_overlays: tuple[tuple[str, str, str], ...] = ()
    #: Non-empty when the effective config touched a protected region.
    constitutional_status: str = "standard"
    protected_edits: tuple[tuple[str, str], ...] = ()

    rag_profile: dict[str, Any] = field(default_factory=dict)
    runtime_profile: dict[str, Any] = field(default_factory=dict)
    activation_binding: dict[str, Any] = field(default_factory=dict)

    #: Optional model binding — the runtime uses this only if it actually
    #: makes a model call; unbounded runs record it for provenance.
    model_binding: dict[str, Any] = field(default_factory=dict)

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["prompt_variant_selections"] = [list(p) for p in self.prompt_variant_selections]
        d["prompt_fragment_overlays"] = [list(p) for p in self.prompt_fragment_overlays]
        d["protected_edits"] = [list(p) for p in self.protected_edits]
        return d

    def content_hash(self) -> str:
        payload = json.dumps(self.to_public(), sort_keys=True,
                             ensure_ascii=False)
        return "src:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


# ---------------------------------------------------------- runtime identity


@dataclass(frozen=True)
class SocratesIdentity:
    """The identity a run pins itself to at ``t0``.

    Distinct from :class:`SocratesRunConfiguration`: the configuration is
    resolved authority-side (Workbench + auth), while the identity is what
    the runtime *itself* is — code commit, pack, mounted body hashes.
    """
    code_commit: str
    pack: SocratesPackIdentity
    pipeline_version: str = "0.3.0"
    mount_policy_version: str = "0.2.0"
    context_policy_version: str = "0.2.0"
    trigger_admission_version: str = "0.1.0"

    @classmethod
    def bootstrap(cls) -> "SocratesIdentity":
        return cls(code_commit=resolve_code_commit(),
                   pack=SocratesPackIdentity.from_manifest())

    def to_public(self) -> dict[str, Any]:
        return {
            "code_commit": self.code_commit,
            "pack": asdict(self.pack),
            "pipeline_version": self.pipeline_version,
            "mount_policy_version": self.mount_policy_version,
            "context_policy_version": self.context_policy_version,
            "trigger_admission_version": self.trigger_admission_version,
        }

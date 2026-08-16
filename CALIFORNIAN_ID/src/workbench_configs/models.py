"""PipelineConfig — plain dataclasses.

The persistence and the authority rules live elsewhere. What lives here is
shape: what a config *is*, so that a caller can build one, hash it and
compare two, without loading the store or the service.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any


class ConfigStatus:
    """State machine for a saved config.

    Fewer states than variants have on purpose — a config is not a lifecycle
    of one artefact, it is a named build. The interesting transitions are
    who can move it out of ``draft`` and how.
    """
    DRAFT = "draft"
    PERSONAL_ACTIVE = "personal_active"    # owner's chosen build for their runs
    LINE_DEFAULT = "line_default"          # published by a curator as the branch default
    ARCHIVED = "archived"

    ALL: frozenset[str] = frozenset({"draft", "personal_active",
                                     "line_default", "archived"})


class ConstitutionalStatus:
    """What kind of thing is this build, honestly.

    ``STANDARD``     — obeys every protected region of the source pack.
    ``CUSTOM``       — the author edited a protected region.
    Not a moral judgement — a factual one, computed from the drift
    fingerprint. A ``CUSTOM`` build may still be perfectly good; it is just
    not the same species as ``STANDARD`` and must not be labelled as such
    in comparisons.
    """
    STANDARD = "standard"
    CUSTOM = "custom_constitutional_variant"


@dataclass(frozen=True)
class PromptVariantSelection:
    """Pointer only — this build uses ``variant_id`` for ``asset_id``.

    Cheap by construction: no prompt body is copied. If the pointed-at variant
    is later removed or superseded, resolution falls back to the pack default,
    the snapshot at run start records what was actually used.
    """
    asset_id: str
    variant_id: str


@dataclass(frozen=True)
class PromptFragmentOverlay:
    """Author's own content for one editable region of one prompt asset.

    The region_id must correspond to an editable region declared by the asset
    itself; edits to protected regions still land here, but they mark the
    whole config as :attr:`ConstitutionalStatus.CUSTOM`. Overlays are
    versioned by ``source_hash`` so a config's identity survives fragment
    edits and reads back as a different build hash.
    """
    asset_id: str
    region_id: str
    text: str
    source_hash: str = ""

    def hashed(self) -> "PromptFragmentOverlay":
        h = hashlib.sha256(
            f"{self.asset_id}|{self.region_id}|{self.text}".encode("utf-8")
        ).hexdigest()[:16]
        return PromptFragmentOverlay(asset_id=self.asset_id,
                                     region_id=self.region_id, text=self.text,
                                     source_hash=h)


@dataclass(frozen=True)
class RAGProfileSelection:
    engine_id: str
    profile_id: str


@dataclass(frozen=True)
class SemanticControlOverride:
    """One of the branch-declared semantic controls, set to a specific value."""
    control_id: str
    value: str


@dataclass(frozen=True)
class PipelineConfig:
    """A named, owned, hashable build of a pipeline.

    ``config_id`` is the durable identity assigned by the store; ``content_hash``
    is computed from the meaningful contents and changes whenever a selection
    changes. Two configs with the same ``content_hash`` are the same build even
    if they carry different names or owners.
    """
    config_id: str
    owner_id: str
    workspace_id: str
    branch: str
    name: str
    description: str = ""
    status: str = ConfigStatus.DRAFT
    parent_config_id: str = ""

    prompt_variant_selections: tuple[PromptVariantSelection, ...] = ()
    prompt_fragment_overlays: tuple[PromptFragmentOverlay, ...] = ()
    rag_profile_selections: tuple[RAGProfileSelection, ...] = ()
    semantic_control_overrides: tuple[SemanticControlOverride, ...] = ()
    model_binding: dict[str, Any] = field(default_factory=dict)

    constitutional_status: str = ConstitutionalStatus.STANDARD
    #: List of ``(category, item)`` pairs from the drift fingerprint that
    #: forced ``CUSTOM``. Kept as data, not as a boolean, so the UI can show
    #: exactly which regions were touched.
    protected_edits: tuple[tuple[str, str], ...] = ()

    created_at: str = ""
    updated_at: str = ""
    schema_version: str = "0.1.0"

    def content_hash(self) -> str:
        payload = json.dumps({
            "branch": self.branch,
            "prompts": [(s.asset_id, s.variant_id)
                        for s in sorted(self.prompt_variant_selections,
                                        key=lambda x: x.asset_id)],
            "fragments": [(o.asset_id, o.region_id, o.hashed().source_hash)
                          for o in sorted(self.prompt_fragment_overlays,
                                          key=lambda x: (x.asset_id, x.region_id))],
            "rag": [(s.engine_id, s.profile_id)
                    for s in sorted(self.rag_profile_selections,
                                    key=lambda x: x.engine_id)],
            "controls": [(o.control_id, o.value)
                         for o in sorted(self.semantic_control_overrides,
                                         key=lambda x: x.control_id)],
            "model": self.model_binding,
        }, sort_keys=True, ensure_ascii=False)
        return "cfg:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["content_hash"] = self.content_hash()
        d["prompt_variant_selections"] = [asdict(s) for s in self.prompt_variant_selections]
        d["prompt_fragment_overlays"] = [asdict(o) for o in self.prompt_fragment_overlays]
        d["rag_profile_selections"] = [asdict(s) for s in self.rag_profile_selections]
        d["semantic_control_overrides"] = [asdict(o) for o in self.semantic_control_overrides]
        d["protected_edits"] = [list(pair) for pair in self.protected_edits]
        return d

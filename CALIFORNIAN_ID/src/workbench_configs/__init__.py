"""User-owned pipeline configurations — named, editable, comparable.

A ``PipelineConfig`` is what an operator saves as *my Socrates for research*
or *stock Zarathustra*: a small owned object describing which prompt variants,
RAG profiles, semantic controls and model bindings this build uses. It is
deliberately not the same object as :class:`RunConfigurationSnapshot`, which
is the frozen picture the runtime resolves at run start:

    PipelineConfig                    RunConfigurationSnapshot
    ──────────────                    ────────────────────────
    authored                          derived
    mutable                           immutable
    owned                             per-run
    named                             hash-identified
    editable                          frozen at t0

Every run resolves its snapshot from the effective configuration in effect at
the moment the run started; the snapshot outlives config edits.

Ownership & authority — the two verbs behind ``activate``:

    personal_activate  → available to every user, scopes to their own runs
    publish_as_default → available to curators only, changes the line default

Effective binding when a user starts a run:
    user's personal_active build   (if any)
    → else the current line default
    → else the pack baseline (all-defaults).

Constitutional integrity: when an edit lands inside a protected region — i.e.
a region the drift fingerprint recognises as constitutional — the config is
mechanically re-labelled ``custom_constitutional_variant``. This is not
policy; it is a consequence of the fingerprint already knowing which region
was touched.
"""
from __future__ import annotations

from .models import (
    ConfigStatus,
    ConstitutionalStatus,
    PipelineConfig,
    PromptFragmentOverlay,
    PromptVariantSelection,
    RAGProfileSelection,
    SemanticControlOverride,
)
from .service import (
    ConfigError,
    ConfigNotFound,
    NotAuthorized,
    PipelineConfigService,
)
from .store import PipelineConfigStore

__all__ = [
    "ConfigError",
    "ConfigNotFound",
    "ConfigStatus",
    "ConstitutionalStatus",
    "NotAuthorized",
    "PipelineConfig",
    "PipelineConfigService",
    "PipelineConfigStore",
    "PromptFragmentOverlay",
    "PromptVariantSelection",
    "RAGProfileSelection",
    "SemanticControlOverride",
]

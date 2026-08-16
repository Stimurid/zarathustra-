"""PipelineConfig — authoring, ownership, activation split, autoshift."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from workbench_auth import Role, WorkbenchAuth, WorkbenchAuthStore
from workbench_configs import (
    ConfigError,
    ConfigNotFound,
    ConfigStatus,
    ConstitutionalStatus,
    NotAuthorized,
    PipelineConfigService,
    PipelineConfigStore,
    PromptFragmentOverlay,
    PromptVariantSelection,
    RAGProfileSelection,
    SemanticControlOverride,
)


@dataclass
class _Region:
    """A stand-in for :class:`workbench_core.models.Region` that carries only
    the two attributes the service actually looks at. Keeps this file
    independent of the branch adapter machinery."""
    name: str
    kind: str


@pytest.fixture()
def user(tmp_path):
    store = WorkbenchAuthStore(tmp_path / "auth.sqlite3")
    auth = WorkbenchAuth(store, state_dir=tmp_path)
    seed = auth.ensure_seed_admin()
    admin = auth.redeem(seed.code, "admin").user
    ucode = auth.mint_code([Role.USER], minted_by_user=admin)
    ccode = auth.mint_code([Role.CURATOR], minted_by_user=admin)
    user = auth.redeem(ucode.code, "alice").user
    curator = auth.redeem(ccode.code, "kate").user
    return {"admin": admin, "user": user, "curator": curator, "auth": auth}


@pytest.fixture()
def svc(tmp_path):
    """Service with a fabricated regions map:

        analyze_situation → 'constitution' PROTECTED, 'body' editable
        persona_turn      → 'header' editable
    """
    def regions(branch: str, asset_id: str):
        table = {
            ("zarathustra", "analyze_situation"): [
                _Region("constitution", "protected"),
                _Region("body", "editable"),
            ],
            ("zarathustra", "persona_turn"): [
                _Region("header", "editable"),
            ],
        }
        return table.get((branch, asset_id), [])
    return PipelineConfigService(
        PipelineConfigStore(tmp_path / "configs.sqlite3"),
        regions_for_asset=regions)


# ---------------- create + hash identity ----------------

def test_create_stores_and_hashes_by_content(user, svc):
    a = svc.create(user["user"], "ws1", "zarathustra", "my-research",
                   description="lower entropy",
                   prompt_selections=[PromptVariantSelection("persona_turn", "v_alt")],
                   rag_selections=[RAGProfileSelection("cultural_cards", "wide")])
    b = svc.create(user["user"], "ws1", "zarathustra", "my-research-2",
                   prompt_selections=[PromptVariantSelection("persona_turn", "v_alt")],
                   rag_selections=[RAGProfileSelection("cultural_cards", "wide")])
    # same contents → same hash even with different name/id
    assert a.content_hash() == b.content_hash()
    assert a.config_id != b.config_id


def test_name_is_unique_per_owner_and_branch(user, svc):
    svc.create(user["user"], "ws1", "zarathustra", "same")
    with pytest.raises(ConfigError, match="уже есть сборка"):
        svc.create(user["user"], "ws1", "zarathustra", "same")
    # Different branch is fine
    svc.create(user["user"], "ws1", "socrates", "same")


def test_create_rejects_empty_name(user, svc):
    with pytest.raises(ConfigError, match="имя"):
        svc.create(user["user"], "ws1", "zarathustra", "   ")


# ---------------- ownership ----------------

def test_only_owner_can_read_own_configs(user, svc):
    cfg = svc.create(user["user"], "ws1", "zarathustra", "mine")
    assert svc.get(user["user"], cfg.config_id).config_id == cfg.config_id
    with pytest.raises(NotAuthorized, match="чужая"):
        svc.get(user["curator"], cfg.config_id)
    # admin may read anything (for support / support tooling)
    assert svc.get(user["admin"], cfg.config_id).config_id == cfg.config_id


def test_list_scopes_to_caller(user, svc):
    svc.create(user["user"], "ws1", "zarathustra", "a")
    svc.create(user["user"], "ws1", "zarathustra", "b")
    svc.create(user["curator"], "ws1", "zarathustra", "c")
    assert {c.name for c in svc.list(user["user"])} == {"a", "b"}
    assert {c.name for c in svc.list(user["curator"])} == {"c"}


def test_update_refuses_when_line_default(user, svc):
    cfg = svc.create(user["user"], "ws1", "zarathustra", "shipped")
    svc.publish_as_line_default(user["curator"], cfg.config_id)
    with pytest.raises(NotAuthorized, match="нельзя редактировать"):
        svc.update(user["user"], cfg.config_id, description="try to edit")


# ---------------- autoshift on protected-region edit ----------------

def test_editable_region_overlay_stays_standard(user, svc):
    cfg = svc.create(
        user["user"], "ws1", "zarathustra", "editable-only",
        prompt_overlays=[PromptFragmentOverlay(
            asset_id="analyze_situation", region_id="body",
            text="мой текст в редактируемом регионе")])
    assert cfg.constitutional_status == ConstitutionalStatus.STANDARD
    assert cfg.protected_edits == ()


def test_protected_region_overlay_becomes_custom(user, svc):
    cfg = svc.create(
        user["user"], "ws1", "zarathustra", "constitutional",
        prompt_overlays=[PromptFragmentOverlay(
            asset_id="analyze_situation", region_id="constitution",
            text="переписал конституцию")])
    assert cfg.constitutional_status == ConstitutionalStatus.CUSTOM
    assert ("analyze_situation", "constitution") in cfg.protected_edits


def test_edit_that_removes_protected_overlay_returns_to_standard(user, svc):
    cfg = svc.create(
        user["user"], "ws1", "zarathustra", "constitutional",
        prompt_overlays=[PromptFragmentOverlay(
            asset_id="analyze_situation", region_id="constitution",
            text="кастом")])
    assert cfg.constitutional_status == ConstitutionalStatus.CUSTOM

    cfg2 = svc.update(user["user"], cfg.config_id,
                      prompt_overlays=[PromptFragmentOverlay(
                          asset_id="analyze_situation", region_id="body",
                          text="теперь только редактируемый")])
    assert cfg2.constitutional_status == ConstitutionalStatus.STANDARD
    assert cfg2.protected_edits == ()


def test_unknown_region_never_marks_as_constitutional(user, svc):
    """An overlay that references a region the source does not declare must
    not flip the label — we cannot say a nonexistent region is protected."""
    cfg = svc.create(
        user["user"], "ws1", "zarathustra", "phantom",
        prompt_overlays=[PromptFragmentOverlay(
            asset_id="analyze_situation", region_id="ghost-region",
            text="?")])
    assert cfg.constitutional_status == ConstitutionalStatus.STANDARD


# ---------------- the two activation verbs ----------------

def test_personal_activate_scopes_to_owner_only(user, svc):
    a = svc.create(user["user"], "ws1", "zarathustra", "alice-research")
    svc.personal_activate(user["user"], a.config_id)
    # alice's personal_active is set …
    assert svc.effective_for_run(user["user"], "zarathustra").config_id == a.config_id
    # … but kate is untouched
    assert svc.effective_for_run(user["curator"], "zarathustra") is None


def test_personal_activate_available_to_regular_users(user, svc):
    cfg = svc.create(user["user"], "ws1", "zarathustra", "mine")
    activated = svc.personal_activate(user["user"], cfg.config_id)
    assert activated.status == ConfigStatus.PERSONAL_ACTIVE


def test_publish_requires_curator_role(user, svc):
    cfg = svc.create(user["user"], "ws1", "zarathustra", "wants-publish")
    with pytest.raises(NotAuthorized, match="curator"):
        svc.publish_as_line_default(user["user"], cfg.config_id)
    published = svc.publish_as_line_default(user["curator"], cfg.config_id)
    assert published.status == ConfigStatus.LINE_DEFAULT


def test_publish_refuses_custom_constitutional_variant(user, svc):
    """A curator cannot ship a build that touched constitutional regions —
    even by mistake — as the line default; that would push a mutation onto
    everyone silently."""
    cfg = svc.create(
        user["user"], "ws1", "zarathustra", "custom",
        prompt_overlays=[PromptFragmentOverlay(
            asset_id="analyze_situation", region_id="constitution",
            text="кастом")])
    assert cfg.constitutional_status == ConstitutionalStatus.CUSTOM
    with pytest.raises(NotAuthorized, match="custom_constitutional_variant"):
        svc.publish_as_line_default(user["curator"], cfg.config_id)


# ---------------- effective_for_run priority ----------------

def test_effective_run_priority(user, svc):
    default = svc.create(user["curator"], "ws1", "zarathustra", "team-default")
    svc.publish_as_line_default(user["curator"], default.config_id)

    # 3) With nothing personal, the line default wins
    assert svc.effective_for_run(user["user"], "zarathustra").config_id == default.config_id

    # 1) Personal activation overrides the line default for that user only
    mine = svc.create(user["user"], "ws1", "zarathustra", "mine")
    svc.personal_activate(user["user"], mine.config_id)
    assert svc.effective_for_run(user["user"], "zarathustra").config_id == mine.config_id
    assert svc.effective_for_run(user["curator"], "zarathustra").config_id == default.config_id

    # Anonymous caller (no user) falls straight through to the line default
    assert svc.effective_for_run(None, "zarathustra").config_id == default.config_id


def test_effective_run_returns_none_when_nothing_set(user, svc):
    assert svc.effective_for_run(user["user"], "zarathustra") is None


def test_clearing_personal_active_falls_back_to_line_default(user, svc):
    default = svc.create(user["curator"], "ws1", "zarathustra", "d")
    svc.publish_as_line_default(user["curator"], default.config_id)
    mine = svc.create(user["user"], "ws1", "zarathustra", "m")
    svc.personal_activate(user["user"], mine.config_id)
    svc.clear_personal_active(user["user"], "zarathustra")
    assert svc.effective_for_run(user["user"], "zarathustra").config_id == default.config_id


# ---------------- deletion + line default protection ----------------

def test_cannot_delete_published_line_default(user, svc):
    cfg = svc.create(user["user"], "ws1", "zarathustra", "shipped")
    svc.publish_as_line_default(user["curator"], cfg.config_id)
    with pytest.raises(NotAuthorized, match="line_default"):
        svc.delete(user["user"], cfg.config_id)


def test_delete_removes_personal_active_binding(user, svc):
    cfg = svc.create(user["user"], "ws1", "zarathustra", "mine")
    svc.personal_activate(user["user"], cfg.config_id)
    svc.delete(user["user"], cfg.config_id)
    assert svc.effective_for_run(user["user"], "zarathustra") is None


def test_config_not_found(user, svc):
    with pytest.raises(ConfigNotFound):
        svc.get(user["user"], "cfg_nope")

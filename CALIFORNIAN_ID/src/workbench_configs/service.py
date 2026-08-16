"""Authoring, ownership and effective-binding resolution for pipeline configs.

Encapsulates the invariants that must not scatter across callers:

    * a config belongs to exactly one owner;
    * personal_activate is available to every user for their own configs;
    * publish_as_default requires ``curator`` and refuses ``CUSTOM``
      constitutional variants;
    * effective binding for a run: caller's personal_active → line default →
      pack defaults;
    * an edit inside a protected region of any source asset re-labels the
      config as :attr:`ConstitutionalStatus.CUSTOM` — mechanically, from the
      region metadata declared by the source, not from a policy string.

Reads the branch's region layout from the ``BranchAdapter`` protocol only —
never from a branch-specific import. The service works for any branch that
exposes assets, variants and regions.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from workbench_auth import Role, User

from .models import (
    ConfigStatus,
    ConstitutionalStatus,
    PipelineConfig,
    PromptFragmentOverlay,
    PromptVariantSelection,
    RAGProfileSelection,
    SemanticControlOverride,
)
from .store import PipelineConfigStore


class ConfigError(Exception):
    """Base for anything a caller passed that we refuse."""


class ConfigNotFound(ConfigError):
    """The referenced config does not exist for this owner."""


class NotAuthorized(ConfigError):
    """The caller may not perform this action.

    Not a 403 by itself — the HTTP layer decides that. But raising it means
    the domain rules refused, and the message is safe to hand to a user.
    """


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# The service must be pluggable for testing without a live WorkbenchService.
#: A function ``(branch, asset_id) -> list[Region]`` — resolves the protected
#: region layout of a source asset from the branch's own metadata.
RegionsForAsset = Callable[[str, str], list[Any]]


class PipelineConfigService:
    def __init__(self, store: PipelineConfigStore,
                 regions_for_asset: RegionsForAsset | None = None) -> None:
        self.store = store
        self._regions_for_asset = regions_for_asset or (lambda _b, _a: [])

    # ---------------- create / update ----------------

    def create(self, owner: User, workspace_id: str, branch: str, name: str,
               description: str = "",
               prompt_selections: list[PromptVariantSelection] | None = None,
               prompt_overlays: list[PromptFragmentOverlay] | None = None,
               rag_selections: list[RAGProfileSelection] | None = None,
               semantic_overrides: list[SemanticControlOverride] | None = None,
               model_binding: dict[str, Any] | None = None,
               parent_config_id: str = "") -> PipelineConfig:
        name = (name or "").strip()
        if not name:
            raise ConfigError("имя сборки обязательно")
        if len(name) > 80:
            raise ConfigError("имя сборки слишком длинное (максимум 80)")

        cfg = PipelineConfig(
            config_id=self.store.new_config_id(),
            owner_id=owner.user_id,
            workspace_id=workspace_id,
            branch=branch,
            name=name,
            description=description or "",
            status=ConfigStatus.DRAFT,
            parent_config_id=parent_config_id,
            prompt_variant_selections=tuple(prompt_selections or ()),
            prompt_fragment_overlays=tuple((o.hashed() for o in (prompt_overlays or ()))),
            rag_profile_selections=tuple(rag_selections or ()),
            semantic_control_overrides=tuple(semantic_overrides or ()),
            model_binding=dict(model_binding or {}),
            created_at=_now(),
            updated_at=_now(),
        )
        cfg = self._reclassify(cfg)
        try:
            self.store.save(cfg, is_new=True)
        except Exception as exc:                          # sqlite3.IntegrityError
            if "UNIQUE" in str(exc).upper():
                raise ConfigError(f"у вас уже есть сборка с именем {name!r} "
                                  f"на ветке {branch!r}") from None
            raise
        return cfg

    def update(self, owner: User, config_id: str, *,
               name: str | None = None,
               description: str | None = None,
               prompt_selections: list[PromptVariantSelection] | None = None,
               prompt_overlays: list[PromptFragmentOverlay] | None = None,
               rag_selections: list[RAGProfileSelection] | None = None,
               semantic_overrides: list[SemanticControlOverride] | None = None,
               model_binding: dict[str, Any] | None = None) -> PipelineConfig:
        cur = self._must_own(owner, config_id)
        # The line default is a published artefact — edits require unpublishing.
        if cur.status == ConfigStatus.LINE_DEFAULT:
            raise NotAuthorized("нельзя редактировать опубликованный line_default; "
                                "снимите публикацию или создайте копию")
        cfg = PipelineConfig(
            config_id=cur.config_id, owner_id=cur.owner_id,
            workspace_id=cur.workspace_id, branch=cur.branch,
            name=(name.strip() if name is not None else cur.name),
            description=(description if description is not None else cur.description),
            status=cur.status,
            parent_config_id=cur.parent_config_id,
            prompt_variant_selections=(
                tuple(prompt_selections) if prompt_selections is not None
                else cur.prompt_variant_selections),
            prompt_fragment_overlays=(
                tuple(o.hashed() for o in prompt_overlays) if prompt_overlays is not None
                else cur.prompt_fragment_overlays),
            rag_profile_selections=(
                tuple(rag_selections) if rag_selections is not None
                else cur.rag_profile_selections),
            semantic_control_overrides=(
                tuple(semantic_overrides) if semantic_overrides is not None
                else cur.semantic_control_overrides),
            model_binding=(dict(model_binding) if model_binding is not None
                           else cur.model_binding),
            created_at=cur.created_at,
            updated_at=_now(),
        )
        cfg = self._reclassify(cfg)
        try:
            self.store.save(cfg, is_new=False)
        except Exception as exc:
            if "UNIQUE" in str(exc).upper():
                raise ConfigError(f"у вас уже есть сборка с этим именем "
                                  f"на ветке {cfg.branch!r}") from None
            raise
        return cfg

    def get(self, owner: User, config_id: str) -> PipelineConfig:
        return self._must_own(owner, config_id)

    def list(self, owner: User, branch: str | None = None) -> list[PipelineConfig]:
        return self.store.list_for_owner(owner.user_id, branch=branch)

    def delete(self, owner: User, config_id: str) -> None:
        cur = self._must_own(owner, config_id)
        if cur.status == ConfigStatus.LINE_DEFAULT:
            raise NotAuthorized("нельзя удалить опубликованный line_default")
        self.store.delete(config_id)

    # ---------------- activation — the two verbs ----------------

    def personal_activate(self, owner: User, config_id: str) -> PipelineConfig:
        """Make this build the caller's active build on its branch.

        Available to every user for their own configs. Scopes to the caller
        alone — nobody else's runs are affected. Idempotent.
        """
        cfg = self._must_own(owner, config_id)
        self.store.set_personal_active(owner.user_id, cfg.branch, cfg.config_id)
        if cfg.status == ConfigStatus.DRAFT:
            cfg = self._mutate_status(cfg, ConfigStatus.PERSONAL_ACTIVE)
        return cfg

    def clear_personal_active(self, owner: User, branch: str) -> None:
        self.store.clear_personal_active(owner.user_id, branch)

    def publish_as_line_default(self, curator: User, config_id: str) -> PipelineConfig:
        """Make this build the branch default for everyone.

        Requires the ``curator`` role. Refuses a ``CUSTOM`` constitutional
        variant on principle: a line default that quietly touches protected
        regions would let one curator override the pack's constitutional
        stance for every user of the branch.
        """
        if not (curator.has_role(Role.CURATOR) or curator.has_role(Role.ADMIN)):
            raise NotAuthorized("публикация дефолта линии требует роли curator")
        cfg = self.store.get(config_id)
        if cfg is None:
            raise ConfigNotFound(f"сборка не найдена: {config_id}")
        if cfg.constitutional_status != ConstitutionalStatus.STANDARD:
            raise NotAuthorized(
                "нельзя опубликовать custom_constitutional_variant как дефолт "
                "линии — правки защищённых регионов остаются в личных сборках")
        self.store.set_line_default(cfg.branch, cfg.config_id, curator.user_id)
        return self._mutate_status(cfg, ConfigStatus.LINE_DEFAULT)

    # ---------------- resolution — what a run should use ----------------

    def effective_for_run(self, caller: User | None, branch: str
                          ) -> PipelineConfig | None:
        """The build a run started right now would use.

        Priority (highest first):
            1. caller's personal_active on this branch (if any and still owned);
            2. current line default for this branch (if any);
            3. ``None`` — pack defaults, no config object.

        The snapshot the runtime freezes at run start captures whichever of
        the three actually resolved, so a config change after the run does
        not affect it.
        """
        if caller is not None:
            pid = self.store.get_personal_active(caller.user_id, branch)
            if pid:
                cfg = self.store.get(pid)
                if cfg is not None and cfg.owner_id == caller.user_id:
                    return cfg
        did = self.store.get_line_default(branch)
        if did:
            cfg = self.store.get(did)
            if cfg is not None:
                return cfg
        return None

    # ---------------- classification (autoshifts the constitutional label) ----------------

    def _reclassify(self, cfg: PipelineConfig) -> PipelineConfig:
        """Set constitutional_status from the overlay set.

        This runs on every write. An overlay whose ``region_id`` matches a
        region declared ``protected`` by the source asset flips the config
        to :attr:`ConstitutionalStatus.CUSTOM`. Multiple such overlays are
        recorded so the UI can enumerate them.
        """
        touched: list[tuple[str, str]] = []
        for overlay in cfg.prompt_fragment_overlays:
            regions = self._regions_for_asset(cfg.branch, overlay.asset_id) or []
            for region in regions:
                if getattr(region, "name", None) != overlay.region_id:
                    continue
                if getattr(region, "kind", "editable") == "protected":
                    touched.append((overlay.asset_id, overlay.region_id))
        status = (ConstitutionalStatus.CUSTOM if touched
                  else ConstitutionalStatus.STANDARD)
        return PipelineConfig(
            **{**cfg.__dict__,
               "constitutional_status": status,
               "protected_edits": tuple(touched)})

    def _mutate_status(self, cfg: PipelineConfig, new_status: str) -> PipelineConfig:
        if new_status not in ConfigStatus.ALL:
            raise ConfigError(f"неизвестный статус: {new_status!r}")
        cfg2 = PipelineConfig(**{**cfg.__dict__, "status": new_status,
                                 "updated_at": _now()})
        self.store.save(cfg2, is_new=False)
        return cfg2

    def _must_own(self, owner: User, config_id: str) -> PipelineConfig:
        cfg = self.store.get(config_id)
        if cfg is None:
            raise ConfigNotFound(f"сборка не найдена: {config_id}")
        if cfg.owner_id != owner.user_id and not owner.has_role(Role.ADMIN):
            # Curator does NOT get read access to arbitrary users' drafts:
            # only owner and admin. The line default is the shared surface.
            raise NotAuthorized("это чужая сборка")
        return cfg

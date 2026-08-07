from __future__ import annotations

import os
from typing import Any

from .base import ModelClient
from .fallback_client import FallbackClient, FallbackStep
from .mock import MockClient


# 302.ai OpenAI-compatible base URL. Overridable via env `API_302AI_BASE_URL`.
_302AI_DEFAULT_BASE_URL = "https://api.302.ai/v1"


def _build_one(provider_cfg: dict[str, Any]) -> ModelClient:
    """Build one concrete ModelClient from a single provider config block.

    Supported `kind` values:
      - mock
      - anthropic
      - openai
      - 302ai              (OpenAI-compatible via api.302.ai)
      - openai_compatible  (generic: needs `base_url` + `env_key`)
    """
    kind = (provider_cfg.get("kind") or "").lower()

    if not kind:
        raise RuntimeError(
            "provider config missing `kind`. Cannot silently default to mock — "
            "see _work/HARD_RULES.md §1."
        )

    if kind == "mock":
        # Allowed only when explicitly requested (pytest via
        # CALIFORNIAN_ID_PROVIDER=mock, or an explicit `kind: mock` provider
        # in a fixture yaml).
        return MockClient()

    if kind == "anthropic":
        env = provider_cfg.get("env_key", "ANTHROPIC_API_KEY")
        if not os.environ.get(env):
            raise RuntimeError(
                f"provider=anthropic requires env var {env}. "
                "Set it, run `pip install anthropic`, Provide a real API key — mock is forbidden outside pytest (see _work/HARD_RULES.md §1)."
            )
        from .anthropic_client import AnthropicClient
        return AnthropicClient(
            api_key=os.environ[env],
            model=provider_cfg.get("model"),
            settings=provider_cfg.get("settings", {}),
        )

    if kind == "openai":
        env = provider_cfg.get("env_key", "OPENAI_API_KEY")
        if not os.environ.get(env):
            raise RuntimeError(
                f"provider=openai requires env var {env}. "
                "Set it, run `pip install openai`, Provide a real API key — mock is forbidden outside pytest (see _work/HARD_RULES.md §1)."
            )
        from .openai_client import OpenAIClient
        return OpenAIClient(
            api_key=os.environ[env],
            model=provider_cfg.get("model"),
            settings=provider_cfg.get("settings", {}),
            base_url=provider_cfg.get("base_url"),
        )

    if kind == "302ai":
        env = provider_cfg.get("env_key", "API_302AI_KEY")
        if not os.environ.get(env):
            raise RuntimeError(
                f"provider=302ai requires env var {env}. "
                "Set it in /etc/tinkuy/tinkuy.env Provide a real API key — mock is forbidden outside pytest (see _work/HARD_RULES.md §1)."
            )
        base_url = provider_cfg.get("base_url") or os.environ.get(
            "API_302AI_BASE_URL", _302AI_DEFAULT_BASE_URL
        )
        from .openai_client import OpenAIClient
        return OpenAIClient(
            api_key=os.environ[env],
            model=provider_cfg.get("model") or "claude-sonnet-4-5",
            settings=provider_cfg.get("settings", {}),
            base_url=base_url,
            provider_label="302ai",
        )

    if kind == "openai_compatible":
        env = provider_cfg.get("env_key")
        if not env or not os.environ.get(env):
            raise RuntimeError(
                f"provider=openai_compatible requires env var {env or '<unset>'}."
            )
        from .openai_client import OpenAIClient
        return OpenAIClient(
            api_key=os.environ[env],
            model=provider_cfg.get("model"),
            settings=provider_cfg.get("settings", {}),
            base_url=provider_cfg.get("base_url"),
            provider_label=provider_cfg.get("label"),
        )

    raise ValueError(f"Unknown provider kind: {kind}")


def build_client(provider_name: str, provider_cfg: dict[str, Any]) -> ModelClient:
    """Build a ModelClient, wrapping in FallbackClient when `fallbacks` is present.

    provider_cfg shape:
        {
          kind: "302ai" | "openai" | "anthropic" | "mock" | "openai_compatible",
          model: str,
          env_key: str,           # optional (defaults per kind)
          base_url: str,          # optional (302ai/openai_compatible)
          settings: {},
          fallbacks: [            # optional — same shape as top-level, tried in order on failure
            { kind, model, env_key, base_url, settings, label },
            ...
          ]
        }
    """
    kind = (provider_cfg.get("kind") or provider_name or "").lower()
    if not kind:
        raise RuntimeError(
            f"build_client: no provider name given for '{provider_name}'. "
            "Refusing to default to mock — see _work/HARD_RULES.md §1."
        )

    # legacy compat: bare 'mock'/'anthropic'/'openai' string with no `kind` key
    if "kind" not in provider_cfg and provider_name in {"mock", "anthropic", "openai", "302ai"}:
        provider_cfg = {**provider_cfg, "kind": provider_name}
        kind = provider_name

    primary = _build_one(provider_cfg)

    fallbacks_cfg = provider_cfg.get("fallbacks") or []
    if not fallbacks_cfg:
        return primary

    primary_label = provider_cfg.get("label") or f"{kind}/{provider_cfg.get('model') or 'default'}"
    steps = [FallbackStep(label=primary_label, client=primary)]

    for fb in fallbacks_cfg:
        try:
            fb_client = _build_one(fb)
        except RuntimeError:
            # missing key / package for this fallback — skip silently (chain still valid)
            continue
        fb_label = fb.get("label") or f"{fb.get('kind')}/{fb.get('model') or 'default'}"
        steps.append(FallbackStep(label=fb_label, client=fb_client))

    return FallbackClient(steps=steps)

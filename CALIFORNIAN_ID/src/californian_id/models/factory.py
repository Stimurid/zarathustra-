from __future__ import annotations

import os
from typing import Any

from .base import ModelClient
from .mock import MockClient


def build_client(provider_name: str, provider_cfg: dict[str, Any]) -> ModelClient:
    kind = (provider_cfg.get("kind") or provider_name or "mock").lower()
    if kind == "mock":
        return MockClient()
    if kind == "anthropic":
        env = provider_cfg.get("env_key", "ANTHROPIC_API_KEY")
        if not os.environ.get(env):
            raise RuntimeError(
                f"provider=anthropic requires env var {env}. "
                "Set it, run `pip install anthropic`, or switch provider to `mock`."
            )
        from .anthropic_client import AnthropicClient  # local import
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
                "Set it, run `pip install openai`, or switch provider to `mock`."
            )
        from .openai_client import OpenAIClient  # local import
        return OpenAIClient(
            api_key=os.environ[env],
            model=provider_cfg.get("model"),
            settings=provider_cfg.get("settings", {}),
        )
    raise ValueError(f"Unknown provider kind: {kind}")

"""Thin OpenAI adapter. Lazy import so mock runs need nothing installed."""
from __future__ import annotations

from typing import Any

from .base import Message, ModelResult

_INTERNAL_SETTING_KEYS = {
    "role",
    "persona_id",
    "operation",
    "topic",
    "available_personas",
    "already_called",
    "suggested_operation",
    "canonical_operation",
    "candidate_operations",
    "critique_regime",
    "variation_regime",
    "turns",
    "conflict_map",
    "strongest_arguments",
    "minority_positions",
    "attack_target",
    "selected_operation",
    "selected_class",
    "recent_operations",
    "recent_classes",
    "selection_reason",
    "candidate_scores",
    "routing_contract",
    "regime_instruction",
}


class OpenAIClient:
    provider = "openai"

    def __init__(
        self,
        api_key: str,
        model: str | None,
        settings: dict[str, Any],
        base_url: str | None = None,
        provider_label: str | None = None,
    ) -> None:
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "The `openai` package is not installed. "
                "Run `pip install openai` or switch provider to `mock`."
            ) from e
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)
        self.model = model or "gpt-4o-mini"
        self.settings = dict(settings)
        if provider_label:
            self.provider = provider_label

    def generate(
        self,
        messages: list[Message],
        response_schema: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> ModelResult:
        merged = {**self.settings, **(settings or {})}
        for k in _INTERNAL_SETTING_KEYS:
            merged.pop(k, None)
        chat = [{"role": m.role, "content": m.content} for m in messages]
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=chat,
            **merged,
        )
        text = resp.choices[0].message.content or ""
        return ModelResult(
            text=text,
            raw=resp,
            provider=self.provider,
            model=self.model,
            stop_reason=str(resp.choices[0].finish_reason),
            usage={
                "prompt_tokens": getattr(resp.usage, "prompt_tokens", None),
                "completion_tokens": getattr(resp.usage, "completion_tokens", None),
            },
        )

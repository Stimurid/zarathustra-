"""Thin Anthropic adapter. Lazy import so mock runs need nothing installed."""
from __future__ import annotations

from typing import Any

from .base import Message, ModelResult


class AnthropicClient:
    provider = "anthropic"

    def __init__(self, api_key: str, model: str | None, settings: dict[str, Any]) -> None:
        try:
            import anthropic  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "The `anthropic` package is not installed. "
                "Run `pip install anthropic` or switch provider to `mock`."
            ) from e
        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = model or "claude-sonnet-5-20260101"
        self.settings = dict(settings)

    def generate(
        self,
        messages: list[Message],
        response_schema: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> ModelResult:
        system_chunks = [m.content for m in messages if m.role == "system"]
        chat = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in {"user", "assistant"}
        ]
        merged = {**self.settings, **(settings or {})}
        merged.pop("role", None)
        merged.pop("persona_id", None)
        merged.pop("operation", None)
        merged.pop("topic", None)
        merged.pop("available_personas", None)
        merged.pop("already_called", None)
        merged.pop("suggested_operation", None)
        merged.pop("turns", None)
        merged.pop("conflict_map", None)
        merged.pop("strongest_arguments", None)
        merged.pop("minority_positions", None)
        merged.pop("attack_target", None)
        max_tokens = merged.pop("max_tokens", 4096)
        resp = self._client.messages.create(
            model=self.model,
            system="\n\n".join(system_chunks) if system_chunks else "",
            messages=chat,
            max_tokens=max_tokens,
            **merged,
        )
        text = "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        )
        return ModelResult(
            text=text,
            raw=resp,
            provider=self.provider,
            model=self.model,
            stop_reason=str(resp.stop_reason),
            usage={
                "input_tokens": getattr(resp.usage, "input_tokens", None),
                "output_tokens": getattr(resp.usage, "output_tokens", None),
            },
        )

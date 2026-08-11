"""Thin Anthropic adapter. Lazy import so mock runs need nothing installed."""
from __future__ import annotations

from typing import Any

from .base import Message, ModelResult

_INTERNAL_SETTING_KEYS = {
    "role",
    "persona_id",
    "operation",
    "topic",
    "form",
    "genre",
    "dialogue_protocol",
    "has_position_model",
    "input_len",
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


class AnthropicClient:
    provider = "anthropic"

    def __init__(self, api_key: str, model: str | None, settings: dict[str, Any]) -> None:
        try:
            import anthropic  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "The `anthropic` package is not installed. "
                "Run `pip install anthropic`. Mock is forbidden outside pytest (HARD_RULES §1)."
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
        for k in _INTERNAL_SETTING_KEYS:
            merged.pop(k, None)
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

    def generate_stream(
        self,
        messages: list[Message],
        on_delta,
        settings: dict[str, Any] | None = None,
    ) -> ModelResult:
        """Anthropic token stream via messages.stream(). 6.B.2."""
        system_chunks = [m.content for m in messages if m.role == "system"]
        chat = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in {"user", "assistant"}
        ]
        merged = {**self.settings, **(settings or {})}
        for k in _INTERNAL_SETTING_KEYS:
            merged.pop(k, None)
        max_tokens = merged.pop("max_tokens", 4096)
        parts: list[str] = []
        stop_reason = "ok"
        with self._client.messages.stream(
            model=self.model,
            system="\n\n".join(system_chunks) if system_chunks else "",
            messages=chat,
            max_tokens=max_tokens,
            **merged,
        ) as stream:
            for text_delta in stream.text_stream:
                if not text_delta:
                    continue
                parts.append(text_delta)
                if on_delta:
                    try:
                        on_delta(text_delta)
                    except Exception:
                        pass
            final = stream.get_final_message()
            stop_reason = str(getattr(final, "stop_reason", "ok"))
        return ModelResult(
            text="".join(parts),
            raw={"_streamed": True},
            provider=self.provider,
            model=self.model,
            stop_reason=stop_reason,
        )

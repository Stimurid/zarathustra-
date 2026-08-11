"""Thin OpenAI adapter. Lazy import so mock runs need nothing installed."""
from __future__ import annotations

from typing import Any

from .base import Message, ModelResult

_INTERNAL_SETTING_KEYS = {
    "role",
    "persona_id",
    "operation",
    "topic",
    "form",
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

_FLOAT_SETTING_KEYS = {
    "temperature",
    "top_p",
    "presence_penalty",
    "frequency_penalty",
}

_INT_SETTING_KEYS = {
    "max_tokens",
    "n",
    "seed",
}

# Whitelist: только эти ключи разрешено передавать в OpenAI SDK.
# Всё остальное (наши prompt-context поля вроде dialogue_protocol, genre,
# has_position_model и т.д.) отбрасывается.
_SDK_PASSTHROUGH_KEYS = _FLOAT_SETTING_KEYS | _INT_SETTING_KEYS | {
    "stop", "user", "response_format", "tool_choice",
    "parallel_tool_calls", "logit_bias",
    "stream_options", "reasoning_effort",  # OpenAI newer params
}


def _strip_internal(settings: dict[str, Any]) -> dict[str, Any]:
    """Whitelist SDK-facing keys, normalize scalar types.

    B-5.5 fix: раньше был blacklist (_INTERNAL_SETTING_KEYS) — любое новое
    поле в settings (dialogue_protocol, has_position_model, genre, …) уходило
    в SDK как unknown kwarg и падало. Теперь whitelist — безопаснее.
    """
    out = {}
    for k, v in (settings or {}).items():
        if v is None:
            continue
        if k not in _SDK_PASSTHROUGH_KEYS:
            continue  # наши prompt-context поля — не в SDK
        if k in _FLOAT_SETTING_KEYS:
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                continue
            continue
        if k in _INT_SETTING_KEYS:
            try:
                out[k] = int(v)
            except (TypeError, ValueError):
                continue
            continue
        if not isinstance(v, (str, int, float, bool, list, dict)):
            continue
        out[k] = v
    return out


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
                "Run `pip install openai`. Mock is forbidden outside pytest (HARD_RULES §1)."
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
        merged = _strip_internal({**self.settings, **(settings or {})})
        chat = [{"role": m.role, "content": m.content} for m in messages]
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=chat,
            **merged,
        )
        text = _coerce_message_content(resp.choices[0].message.content)
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

    def generate_stream(
        self,
        messages: list[Message],
        on_delta,
        settings: dict[str, Any] | None = None,
    ) -> ModelResult:
        """Token-level stream via OpenAI SDK (stream=True). 6.B.2."""
        merged = _strip_internal({**self.settings, **(settings or {})})
        chat = [{"role": m.role, "content": m.content} for m in messages]
        parts: list[str] = []
        finish_reason = "ok"
        stream = self._client.chat.completions.create(
            model=self.model,
            messages=chat,
            stream=True,
            **merged,
        )
        for chunk in stream:
            try:
                choice = chunk.choices[0]
            except (IndexError, AttributeError):
                continue
            delta_obj = getattr(choice, "delta", None)
            if delta_obj is not None:
                delta = getattr(delta_obj, "content", None) or ""
            else:
                delta = ""
            if delta:
                parts.append(delta)
                if on_delta:
                    try:
                        on_delta(delta)
                    except Exception:
                        pass
            fr = getattr(choice, "finish_reason", None)
            if fr:
                finish_reason = str(fr)
        return ModelResult(
            text="".join(parts),
            raw={"_streamed": True},
            provider=self.provider,
            model=self.model,
            stop_reason=finish_reason,
        )


def _coerce_message_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text_value = item.get("text")
                if isinstance(text_value, str):
                    parts.append(text_value)
                elif isinstance(item.get("content"), str):
                    parts.append(item["content"])
        return "\n".join(p for p in parts if p)
    if isinstance(content, dict):
        for key in ("text", "content", "output_text"):
            value = content.get(key)
            if isinstance(value, str):
                return value
    return str(content)

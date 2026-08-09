"""Helpers для потокового генерирования — 6.B token stream."""
from __future__ import annotations

from typing import Any

from .base import DeltaSink, Message, ModelResult


def stream_via_generate(
    client,
    messages: list[Message],
    on_delta: DeltaSink,
    settings: dict[str, Any] | None = None,
) -> ModelResult:
    """Fallback: провайдер без нативного stream. Один финальный emit."""
    result = client.generate(messages, settings=settings)
    if on_delta:
        on_delta(result.text or "")
    return result


def call_stream(
    client,
    messages: list[Message],
    on_delta: DeltaSink,
    settings: dict[str, Any] | None = None,
) -> ModelResult:
    """Единая точка входа для потокового вызова любого ModelClient."""
    if hasattr(client, "generate_stream"):
        return client.generate_stream(messages, on_delta=on_delta, settings=settings)
    return stream_via_generate(client, messages, on_delta, settings=settings)

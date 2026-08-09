"""FallbackClient — chain of ModelClients that tries them in order.

Use case: primary provider (e.g. 302.ai / claude-sonnet-4-5) fails or times
out → try next model (302.ai / gpt-4o) → try next (direct anthropic) → …

Each step in the chain is a fully-constructed ModelClient. This wrapper is
itself a ModelClient — same `generate(...)` signature, same ModelResult.
On success, sets `provider` on the result to the winning step's provider.
On total failure, raises the last exception.

Not thread-safe intentionally: pipeline is sequential.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .base import Message, ModelClient, ModelResult


@dataclass
class FallbackStep:
    label: str          # human-readable, e.g. "302ai/claude-sonnet-4-5"
    client: ModelClient


@dataclass
class FallbackClient:
    steps: list[FallbackStep]
    provider: str = "fallback"
    model: str = "chain"
    _last_events: list[dict[str, Any]] = field(default_factory=list)

    def generate(
        self,
        messages: list[Message],
        response_schema: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> ModelResult:
        self._last_events = []
        last_exc: Exception | None = None
        for step in self.steps:
            try:
                result = step.client.generate(messages, response_schema=response_schema, settings=settings)
                self._last_events.append({"label": step.label, "outcome": "success"})
                # tag winning provider for trace visibility
                result.provider = f"{result.provider or step.client.provider}"
                if not result.model:
                    result.model = step.client.model
                # add fallback trace to raw
                if isinstance(result.raw, dict):
                    result.raw.setdefault("_fallback_chain", list(self._last_events))
                return result
            except Exception as exc:  # noqa: BLE001 — we're a policy wrapper
                self._last_events.append({
                    "label": step.label,
                    "outcome": "failed",
                    "error": type(exc).__name__,
                    "message": str(exc)[:200],
                })
                last_exc = exc
                continue
        # exhausted
        if last_exc is None:
            raise RuntimeError("FallbackClient: no steps configured")
        raise RuntimeError(
            f"FallbackClient: all {len(self.steps)} providers failed. "
            f"Last error: {type(last_exc).__name__}: {last_exc}"
        ) from last_exc

    def generate_stream(
        self,
        messages: list[Message],
        on_delta,
        settings: dict[str, Any] | None = None,
    ) -> ModelResult:
        """Streaming variant — пробуем шаги по очереди."""
        from .stream_utils import stream_via_generate
        self._last_events = []
        last_exc: Exception | None = None
        for step in self.steps:
            try:
                if hasattr(step.client, "generate_stream"):
                    result = step.client.generate_stream(
                        messages, on_delta=on_delta, settings=settings,
                    )
                else:
                    result = stream_via_generate(
                        step.client, messages, on_delta, settings=settings,
                    )
                self._last_events.append({"label": step.label, "outcome": "success"})
                result.provider = f"{result.provider or step.client.provider}"
                if not result.model:
                    result.model = step.client.model
                return result
            except Exception as exc:  # noqa: BLE001
                self._last_events.append({
                    "label": step.label,
                    "outcome": "failed",
                    "error": type(exc).__name__,
                    "message": str(exc)[:200],
                })
                last_exc = exc
                continue
        if last_exc is None:
            raise RuntimeError("FallbackClient: no steps configured")
        raise RuntimeError(
            f"FallbackClient stream: all {len(self.steps)} providers failed. "
            f"Last error: {type(last_exc).__name__}: {last_exc}"
        ) from last_exc

    def chain_summary(self) -> list[dict[str, Any]]:
        """Trace of the last generate() call. For visibility in logs."""
        return list(self._last_events)

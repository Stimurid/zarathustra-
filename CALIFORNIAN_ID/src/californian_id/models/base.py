from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class ModelResult:
    text: str
    raw: Any = None
    usage: dict[str, Any] = field(default_factory=dict)
    provider: str = ""
    model: str = ""
    stop_reason: str = "ok"


# Signature for token-delta callbacks used by generate_stream.
# Called once per chunk with the delta text as it arrives.
DeltaSink = Callable[[str], None]


class ModelClient(Protocol):
    provider: str
    model: str

    def generate(
        self,
        messages: list[Message],
        response_schema: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> ModelResult: ...

    # Optional — providers that don't implement it fall back to a single
    # emit at the end from generate() (see stream_utils.stream_via_generate).
    # Signature: same as generate + `on_delta: DeltaSink`.

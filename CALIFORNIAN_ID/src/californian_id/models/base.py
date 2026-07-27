from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


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


class ModelClient(Protocol):
    provider: str
    model: str

    def generate(
        self,
        messages: list[Message],
        response_schema: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> ModelResult: ...

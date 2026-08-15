"""Bounded smoke harness plus the capture / stub model clients.

The stub client is deliberately *contract-aware*: it answers with exactly the
JSON keys the prompt asks for, filled deterministically from the fixture. That
makes baseline↔candidate comparison meaningful without spending tokens, and it
makes a candidate that changes the requested field set visibly change its
output.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

from .branch import BranchAdapter, Fixture, Invocation
from .models import sha256_text

_KEY_RE = re.compile(r'"([a-z_][a-z0-9_]*)"\s*:')


@dataclass
class ModelResult:
    text: str
    latency_ms: int
    tokens_in: int
    tokens_out: int
    provider: str
    model: str


@dataclass
class CaptureClient:
    """Records the exact invocation payload; returns a fixed answer.

    Used for invocation-equivalence proofs: OLD and NEW code paths are run
    against this client and their captured payloads compared byte for byte.

    ``provider`` is deliberately NOT "mock": the Zarathustra runtime routes
    ``provider == "mock"`` to a deterministic fallback that never reaches the
    model boundary (``zarathustra.py:197``), which would make an integration
    smoke silently vacuous. The capture client stands in for a real provider at
    exactly that boundary.
    """
    canned: str = "{}"
    captured: list[dict[str, Any]] = field(default_factory=list)
    provider: str = "capture"
    model: str = "capture-boundary-1"

    def generate(self, messages, settings=None):  # mirrors californian_id client shape
        payload = [{"role": getattr(m, "role", None) or m["role"],
                    "content": getattr(m, "content", None) or m["content"]}
                   for m in messages]
        self.captured.append({"messages": payload, "settings": dict(settings or {})})
        return ModelResult(self.canned, 0, 0, 0, "capture", "capture")

    def payload_hash(self) -> str:
        return sha256_text(json.dumps(self.captured, ensure_ascii=False, sort_keys=True))


class StubModel:
    """Deterministic, contract-aware, offline."""

    provider = "stub"
    model = "workbench-stub-1"

    def generate(self, invocation: Invocation) -> ModelResult:
        started = time.perf_counter()
        keys = list(dict.fromkeys(_KEY_RE.findall(invocation.system_text)))
        seed = sha256_text(invocation.user_text)[:8]
        body: dict[str, Any] = {}
        for k in keys:
            if k in {"stakes", "horizons", "concepts", "tensions", "uncertainties"}:
                body[k] = [f"{k}_{seed}_1", f"{k}_{seed}_2"]
            elif k == "genre":
                body[k] = "question"
            elif k == "topic":
                body[k] = invocation.user_text.strip().split("\n")[0][:180] or f"topic_{seed}"
            else:
                body[k] = f"{k}_{seed}"
        text = json.dumps(body, ensure_ascii=False, indent=2)
        latency = int((time.perf_counter() - started) * 1000)
        return ModelResult(
            text=text, latency_ms=max(latency, 1),
            tokens_in=max(1, round(len(invocation.system_text + invocation.user_text) / 3.5)),
            tokens_out=max(1, round(len(text) / 3.5)),
            provider=self.provider, model=self.model,
        )


@dataclass
class SmokeResult:
    ok: bool
    reasons: list[str]
    raw_text: str
    parsed: dict[str, Any]
    tokens_in: int
    tokens_out: int
    latency_ms: int
    provider: str
    model: str
    fixture_id: str
    compiled_hash: str

    def to_public(self) -> dict[str, Any]:
        return {
            "ok": self.ok, "reasons": self.reasons,
            "raw_text": self.raw_text, "parsed": self.parsed,
            "tokens_in": self.tokens_in, "tokens_out": self.tokens_out,
            "latency_ms": self.latency_ms,
            "provider": self.provider, "model": self.model,
            "fixture_id": self.fixture_id, "compiled_hash": self.compiled_hash,
            "measured": True,
        }


class SmokeHarness:
    def __init__(self, model: Any | None = None) -> None:
        self.model = model or StubModel()

    def run(self, adapter: BranchAdapter, asset_id: str, source_text: str,
            fixture: Fixture, compiled_hash: str) -> SmokeResult:
        inv = adapter.build_invocation(asset_id, source_text, fixture)
        res: ModelResult = self.model.generate(inv)
        ok, reasons, parsed = adapter.validate_output(asset_id, res.text)
        return SmokeResult(
            ok=ok, reasons=reasons, raw_text=res.text, parsed=parsed,
            tokens_in=res.tokens_in, tokens_out=res.tokens_out,
            latency_ms=res.latency_ms, provider=res.provider, model=res.model,
            fixture_id=fixture.fixture_id, compiled_hash=compiled_hash,
        )


def compare(baseline: SmokeResult, candidate: SmokeResult) -> dict[str, Any]:
    """Baseline↔candidate delta, plus the rollback conditions from the fixture spec."""
    b_keys, c_keys = set(baseline.parsed or {}), set(candidate.parsed or {})
    token_ratio = (candidate.tokens_out / baseline.tokens_out) if baseline.tokens_out else 1.0
    triggers: list[str] = []
    if not candidate.ok:
        triggers.append("candidate_output_invalid")
    if token_ratio > 2.0:
        triggers.append("tokens_out_more_than_2x_baseline")
    return {
        "fields_added": sorted(c_keys - b_keys),
        "fields_removed": sorted(b_keys - c_keys),
        "tokens_out": {"baseline": baseline.tokens_out, "candidate": candidate.tokens_out,
                       "ratio": round(token_ratio, 3)},
        "latency_ms": {"baseline": baseline.latency_ms, "candidate": candidate.latency_ms},
        "valid": {"baseline": baseline.ok, "candidate": candidate.ok},
        "rollback_triggers": triggers,
        "identical_output": baseline.raw_text == candidate.raw_text,
    }

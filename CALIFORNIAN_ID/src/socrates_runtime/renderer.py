"""Final human-facing response — bounded by the governor's terminal.

Rule of this file:

    the renderer MAY phrase the decision.
    the renderer MAY NOT change the decision.

The pipeline's diagnostic ``[ANSWER] …`` output is kept as a fallback and
in the trace so a run remains debuggable even when no provider is
available. In LIVE mode a caller can pass a rendering client here; the
client sees the terminal, the rationale, and a stripped snapshot of state,
and produces the human sentence. If the client returns anything that
LOOKS like a different terminal (recognised by the diagnostic tags), the
renderer refuses the output and falls back to the diagnostic surface with
a trace note.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from .models import Message
from .phase_executor import ExecutionMode, ProviderStatus
from .state import Terminal, TerminalOutcome


_DIAGNOSTIC_TAG_PREFIXES = tuple(f"[{t.value}]" for t in Terminal)


@dataclass
class RenderingResult:
    text: str
    mode: str                        # LIVE | DETERMINISTIC_DIAGNOSTIC
    provider_status: str = ProviderStatus.NOT_APPLICABLE
    provider_id: str = ""
    model_id: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    error: str = ""
    #: True if we DETECTED an attempt to change the terminal and refused.
    terminal_preserved: bool = True

    def to_public(self) -> dict[str, Any]:
        return {
            "text": self.text, "mode": self.mode,
            "provider_status": self.provider_status,
            "provider_id": self.provider_id, "model_id": self.model_id,
            "tokens_in": self.tokens_in, "tokens_out": self.tokens_out,
            "latency_ms": self.latency_ms, "error": self.error,
            "terminal_preserved": self.terminal_preserved,
        }


def render_terminal(state, outcome: TerminalOutcome,
                    *, client: Any = None,
                    provider_id: str = "", model_id: str = "",
                    intervention_profile: Any = None) -> RenderingResult:
    """Render a human response for ``outcome`` without changing it.

    If ``client`` is None, return the deterministic diagnostic text
    already prepared by the pipeline. If a client is supplied, ask it for
    a short sentence and verify the terminal survives.

    B2 intervention profile: if non-None and non-normal, an overlay
    naming register + epistemic + liberatory pressure is PREPENDED to
    the system prompt. The overlay CANNOT change terminal / status /
    provenance / authority — those checks below still fire.
    """
    if client is None:
        return RenderingResult(
            text=outcome.response_text or f"[{outcome.terminal.value}]",
            mode="DETERMINISTIC_DIAGNOSTIC")

    started = time.time()
    # B2 SHIVA/BALD_APE overlay — prepended structurally, never from
    # user text. Empty for the normal profile.
    overlay = ""
    if intervention_profile is not None:
        try:
            overlay = intervention_profile.render_overlay()
        except AttributeError:
            overlay = ""
    system_content = (
        "You are the final rendering step of Socrates. A previous "
        "governor step has ALREADY selected the terminal for this "
        "run. Your job: produce one short human sentence in Russian "
        "that phrases the decision honestly. You MUST NOT change the "
        "terminal, propose a different one, add analysis, or make a "
        "different claim. Do not use markdown or tags.")
    if overlay:
        system_content = overlay + "\n---\n" + system_content
    messages = [
        Message(role="system", content=system_content),
        Message(role="user", content=(
            f"terminal: {outcome.terminal.value}\n"
            f"rationale: {outcome.rationale}\n"
            f"telos: {getattr(state.scene, 'telos', '') or '(none)'}\n"
            f"return_reason: {getattr(state.ownership, 'return_reason', '') or '(none)'}\n"
            "Ответ:")),
    ]
    try:
        result = client.generate(messages,
                                  settings={"temperature": 0.0,
                                            "max_tokens": 200})
        raw = (result.text or "").strip()
        usage = result.usage or {}
    except Exception as exc:                              # noqa: BLE001
        return RenderingResult(
            text=outcome.response_text or f"[{outcome.terminal.value}]",
            mode="DETERMINISTIC_DIAGNOSTIC",
            provider_status=ProviderStatus.UNAVAILABLE,
            provider_id=provider_id, model_id=model_id,
            latency_ms=int((time.time() - started) * 1000),
            error=f"{type(exc).__name__}: {exc}")

    # Refuse any rendering that names a DIFFERENT terminal tag than the
    # one the governor chose. Same tag or no tag at all is fine.
    other_tags = [pfx for pfx in _DIAGNOSTIC_TAG_PREFIXES
                  if pfx != f"[{outcome.terminal.value}]" and pfx in raw]
    if other_tags:
        return RenderingResult(
            text=outcome.response_text or f"[{outcome.terminal.value}]",
            mode="DETERMINISTIC_DIAGNOSTIC",
            provider_status=ProviderStatus.INVALID_OUTPUT,
            provider_id=provider_id, model_id=model_id,
            latency_ms=int((time.time() - started) * 1000),
            error=f"rendering attempted to change terminal (mentioned {other_tags})",
            terminal_preserved=False)

    return RenderingResult(
        text=raw or outcome.response_text or f"[{outcome.terminal.value}]",
        mode=ExecutionMode.LIVE,
        provider_status=ProviderStatus.OK,
        provider_id=provider_id or getattr(client, "provider", ""),
        model_id=model_id or getattr(client, "model", ""),
        tokens_in=int(usage.get("prompt_tokens", 0) or 0),
        tokens_out=int(usage.get("completion_tokens", 0) or 0),
        latency_ms=int((time.time() - started) * 1000))

"""A deliberately minimal baseline participant.

Baseline 0 in the Arena — a single model call, no council, no personas, no
retrieval — so any effect a real engine claims to add can be checked against
"what a plain model would have said". It is not intended to be good; it is
intended to be honest about what it is not.

For v0.1 this uses the same mock/live-provider machinery every other test
does. Nothing here contradicts ``LIVE_PROVIDER_ACCEPTANCE = EXTERNAL_BLOCKER``:
under a mock provider the response is a deterministic short string that the
judges can still evaluate structurally.
"""
from __future__ import annotations

import time

from ..protocol import Case, ParticipantConfiguration, Turn


class BaselineSingleAgent:
    """One provider call, one response. No orchestration."""

    engine_kind: str = "baseline_single_agent"

    def __init__(self, participant_id: str,
                 system_prompt: str = (
                     "Отвечай кратко и по существу. Ты не совет и не "
                     "философ — ты один голос, отвечающий один раз.")) -> None:
        self.participant_id = participant_id
        self.system_prompt = system_prompt

    def respond(self, config: ParticipantConfiguration, case: Case,
                match_id: str, request_index: int) -> Turn:
        from californian_id.config import load_config
        from californian_id.models import Message, build_client

        started = time.time()
        turn_id = f"turn_{match_id}_{self.participant_id}_{request_index}"
        cfg = load_config()
        try:
            provider = cfg.role_provider("persona_turn")
        except RuntimeError as exc:
            return Turn(
                turn_id=turn_id, match_id=match_id,
                participant_id=self.participant_id,
                request_index=request_index,
                request_text=case.text, response_text="",
                latency_ms=int((time.time() - started) * 1000),
                error=f"no_provider_available: {exc}",
            )
        provider_cfg = cfg.provider_config(provider)
        client = build_client(provider, provider_cfg)
        messages = [Message(role="system", content=self.system_prompt),
                    Message(role="user", content=case.text)]
        try:
            result = client.generate(messages)
        except Exception as exc:                          # noqa: BLE001
            return Turn(
                turn_id=turn_id, match_id=match_id,
                participant_id=self.participant_id,
                request_index=request_index,
                request_text=case.text, response_text="",
                latency_ms=int((time.time() - started) * 1000),
                error=f"{type(exc).__name__}: {exc}",
            )

        usage = result.usage or {}
        return Turn(
            turn_id=turn_id, match_id=match_id,
            participant_id=self.participant_id,
            request_index=request_index,
            request_text=case.text,
            response_text=result.text or "",
            tokens_in=int(usage.get("input_tokens", 0) or 0),
            tokens_out=int(usage.get("output_tokens", 0) or 0),
            latency_ms=int((time.time() - started) * 1000),
            runtime_summary={
                "engine": "baseline_single_agent",
                "provider": result.provider or provider,
                "model": result.model,
                "stop_reason": result.stop_reason,
                "council_turns": 0,
                "argument_map": {},
                "personas_called": [],
            },
        )

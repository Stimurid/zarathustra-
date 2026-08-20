"""TEST-ONLY: Claude Code direct-orchestration harness client.

This module is a TEST-ONLY provider double that implements
`ModelClient` protocol so a Claude Code orchestrator can pass it
into `SocratesRuntime.run(..., rendering_client=...)` (and also as a
`phase_executor=LiveModelPhaseExecutor(harness_client)`), record the
EXACT model-call envelope Socrates runtime produced, and inject a
pre-authored response text back through the real runtime seam so that
`renderer.render_terminal(...)` / `LiveModelPhaseExecutor.execute(...)`
proceeds through its actual parser / schema / governance path.

Design invariants (per SOCRATES_DIRECT_CLAUDE_ACCEPTANCE_CORRECTION_AND_
RC1_CLOSURE_HANDOFF_2026-08-20 §7):

- HARNESS IS NEVER IN PRODUCTION.
  * Not registered by `california_id.config.load_config()`.
  * Not built by `SocratesRuntime._build_live_client()`.
  * `provider_id="claude_code_harness"`, `model_id=<injected>` — visible
    in the trace as clearly non-production.

- HARNESS DOES NOT MINT AUTHORITY.
  * Its outputs pass through the same `parse_and_validate_output` /
    `enforce_no_durable_write` gates as any provider output.
  * It does not carry any `authorized_transition_ref`.
  * `stop_reason="claude_code_harness"` records the source verbatim.

- HARNESS SEPARATES ENVELOPE FROM RESPONSE.
  * On each `generate()`: writes the exact envelope to
    `envelope_dir/<seq>.envelope.json` before returning.
  * Reads the pre-supplied response from
    `response_dir/<seq>.response.txt` (authored by an isolated
    Claude Code worker that saw ONLY the envelope; no rubric, no
    expected answer, no other-arm output, no future turns).
  * If the response file is absent, raises `HarnessResponseMissing`
    with the exact seq so the orchestrator can fail closed.

- INDEPENDENT WORKERS ARE INDEPENDENT.
  * The harness has no cross-call memory; it does not remember prior
    envelopes or responses within the same run.
  * The orchestrator is responsible for spawning a FRESH isolated
    subagent per envelope.

- DETERMINISTIC vs LIVE MASQUERADE IS FORBIDDEN.
  * The harness does not fabricate outputs deterministically. If a
    response is missing, it FAILS.
  * The public trace field records `mode=LIVE` when the harness is
    used as a rendering_client to a LIVE-mode run — this is honest
    because the rendering path was real; only the provider identity
    is the harness, and `provider_id` makes that plain.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class HarnessResponseMissing(RuntimeError):
    """Raised when a pre-authored response file does not exist for a
    recorded envelope. Fails closed — the harness never fabricates.
    """


@dataclass
class HarnessRecord:
    """One recorded (envelope, response) pair on disk."""
    seq: int
    envelope_path: str
    response_path: str
    envelope_hash: str
    settings: dict[str, Any]


class ClaudeCodeHarnessClient:
    """TEST-ONLY provider double.

    Instantiate with a run directory. Each `generate()` call is
    sequentially numbered; envelope is written before response is read.
    """

    #: Public identity — visible in trace `provider_id`, ensuring the
    #: harness cannot be mistaken for production provider chain.
    provider: str = "claude_code_harness"

    def __init__(self, run_dir: str, model_label: str,
                 orchestrator_workflow: str,
                 fail_on_missing_response: bool = True) -> None:
        self.model = model_label
        self.run_dir = Path(run_dir)
        self.envelope_dir = self.run_dir / "envelopes"
        self.response_dir = self.run_dir / "responses"
        self.envelope_dir.mkdir(parents=True, exist_ok=True)
        self.response_dir.mkdir(parents=True, exist_ok=True)
        self.orchestrator_workflow = orchestrator_workflow
        self.fail_on_missing_response = fail_on_missing_response
        self._seq = 0
        self.records: list[HarnessRecord] = []
        # Write a run manifest immediately so external inspection sees the
        # harness is active even before any call.
        (self.run_dir / "harness_manifest.json").write_text(
            json.dumps({
                "provider": self.provider,
                "model_label": self.model,
                "orchestrator_workflow": self.orchestrator_workflow,
                "created_at": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "NOT_PRODUCTION": True,
                "AUTHORITY": "NO_AUTHORITY_MINTED_BY_HARNESS",
            }, indent=2), encoding="utf-8")

    def _record_envelope(self, messages, response_schema, settings):
        self._seq += 1
        seq = self._seq
        env = {
            "seq": seq,
            "provider": self.provider,
            "model": self.model,
            "orchestrator_workflow": self.orchestrator_workflow,
            "timestamp": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "messages": [
                {"role": m.role, "content": m.content}
                for m in messages
            ],
            "response_schema": response_schema,
            "settings": dict(settings or {}),
        }
        envelope_json = json.dumps(env, ensure_ascii=False, indent=2)
        envelope_hash = hashlib.sha256(
            envelope_json.encode("utf-8")).hexdigest()
        env["envelope_sha256"] = envelope_hash
        envelope_json = json.dumps(env, ensure_ascii=False, indent=2)
        envelope_path = self.envelope_dir / f"{seq:03d}.envelope.json"
        envelope_path.write_text(envelope_json, encoding="utf-8")
        response_path = self.response_dir / f"{seq:03d}.response.txt"
        rec = HarnessRecord(
            seq=seq,
            envelope_path=str(envelope_path),
            response_path=str(response_path),
            envelope_hash=envelope_hash,
            settings=dict(settings or {}),
        )
        self.records.append(rec)
        return rec

    def generate(self, messages, response_schema=None, settings=None):
        from californian_id.models.base import ModelResult
        rec = self._record_envelope(messages, response_schema, settings)
        response_path = Path(rec.response_path)
        if not response_path.exists():
            msg = (
                f"ClaudeCodeHarnessClient: missing response file for "
                f"envelope seq={rec.seq} at {rec.response_path}. Run "
                f"the isolated Claude Code worker on the envelope at "
                f"{rec.envelope_path} and write the raw text response "
                f"to that path, then rerun.")
            if self.fail_on_missing_response:
                raise HarnessResponseMissing(msg)
            # Fail-open path only for a bounded discovery run; still
            # records the miss.
            (self.run_dir / "misses.txt").open("a", encoding="utf-8").write(
                msg + "\n")
            text = ""
        else:
            text = response_path.read_text(encoding="utf-8")
        return ModelResult(
            text=text,
            raw={"harness_seq": rec.seq,
                 "envelope_hash": rec.envelope_hash},
            usage={"prompt_tokens": 0, "completion_tokens": 0},
            provider=self.provider,
            model=self.model,
            stop_reason="claude_code_harness",
        )


__all__ = [
    "ClaudeCodeHarnessClient",
    "HarnessRecord",
    "HarnessResponseMissing",
]

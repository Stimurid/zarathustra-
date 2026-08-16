"""Socrates as an Arena participant.

Wraps :class:`socrates_runtime.SocratesRuntime`. The Arena knows only the
:class:`ParticipantAdapter` protocol — this file is where the Arena's
generic vocabulary meets Socrates' specific one.

Runtime evidence surfaces into ``Turn.runtime_summary`` unchanged from what
the run itself produced: terminal, mounted phases, native-organ evidence,
memory outcome, trace path. Nothing about Socrates leaks into the arena
core.
"""
from __future__ import annotations

import time
from typing import Any

from ..protocol import Case, ParticipantConfiguration, Turn


class SocratesParticipant:
    """One instance = one runtime binding, one workspace default.

    The runtime is constructed lazily so importing this module does not
    force a SemanticBodyRegistry load unless the participant is actually
    called.
    """

    engine_kind: str = "socrates_pipeline"

    def __init__(self, participant_id: str,
                 workspace_id_default: str = "arena_socrates_default",
                 trace_dir: Any = None) -> None:
        self.participant_id = participant_id
        self.workspace_id_default = workspace_id_default
        self._trace_dir = trace_dir
        self._runtime = None

    def _get_runtime(self):
        if self._runtime is None:
            from socrates_runtime import SocratesRuntime
            self._runtime = SocratesRuntime(trace_dir=self._trace_dir)
        return self._runtime

    def respond(self, config: ParticipantConfiguration, case: Case,
                match_id: str, request_index: int) -> Turn:
        started = time.time()
        turn_id = f"turn_{match_id}_{self.participant_id}_{request_index}"

        try:
            runtime = self._get_runtime()
        except Exception as exc:                          # noqa: BLE001
            return Turn(
                turn_id=turn_id, match_id=match_id,
                participant_id=self.participant_id,
                request_index=request_index,
                request_text=case.text, response_text="",
                latency_ms=int((time.time() - started) * 1000),
                error=f"{type(exc).__name__}: {exc}",
            )

        from socrates_runtime import SocratesRunConfiguration
        from socrates_runtime.runtime import resolve_configuration

        # If the Arena caller passed a pipeline_config_id, we would resolve
        # it through workbench_configs here; without it, we build a bare
        # configuration that still records identity and workspace.
        pipeline_cfg = (config.metadata or {}).get("pipeline_config")
        if pipeline_cfg is not None:
            run_config = resolve_configuration(
                pipeline_cfg, workspace_id=config.workspace_id
                                          or self.workspace_id_default,
                semantic_pack_version=runtime.identity.pack.version,
                semantic_pack_sha256=runtime.identity.pack.source_bundle_sha256)
        else:
            run_config = SocratesRunConfiguration(
                workspace_id=config.workspace_id or self.workspace_id_default,
                display_name=config.display_name,
                semantic_pack_version=runtime.identity.pack.version,
                semantic_pack_sha256=runtime.identity.pack.source_bundle_sha256,
            )

        hints = (config.metadata or {}).get("phase_hints", {})

        try:
            result = runtime.run(case.text, configuration=run_config,
                                 hints=hints or None)
        except Exception as exc:                          # noqa: BLE001
            return Turn(
                turn_id=turn_id, match_id=match_id,
                participant_id=self.participant_id,
                request_index=request_index,
                request_text=case.text, response_text="",
                latency_ms=int((time.time() - started) * 1000),
                error=f"{type(exc).__name__}: {exc}",
            )

        return Turn(
            turn_id=turn_id, match_id=match_id,
            participant_id=self.participant_id,
            request_index=request_index,
            request_text=case.text,
            response_text=result.terminal.response_text,
            tokens_in=0, tokens_out=0,           # deterministic mount uses no model
            latency_ms=int((time.time() - started) * 1000),
            runtime_summary={
                "engine": "socrates_pipeline",
                "run_id": result.run_id,
                "trace_id": result.trace_id,
                "terminal": result.terminal.terminal.value,
                "rationale": result.terminal.rationale,
                "mounted_phases": [
                    {"phase": p["phase"], "router": p["router"],
                     "bodies": [b["body_id"] for b in p["mount"]["required"]
                                + p["mount"]["conditional_admitted"]]}
                    for p in result.mounted_phases],
                "native_organs": [
                    {"organ": o["organ"], "call": o["call"],
                     "available": o["available"]}
                    for o in result.native_organs],
                "memory_outcome": result.memory_outcome,
                "trace_path": result.trace_path,
                "semantic_pack_version": run_config.semantic_pack_version,
            },
        )

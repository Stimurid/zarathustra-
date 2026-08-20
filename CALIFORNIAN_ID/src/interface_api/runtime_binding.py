"""Thin adapter — invoke the existing Socrates runtime and map its
result into vertical-slice Run + Artifact rows.

Does NOT modify the runtime. Uses:
  * SocratesRuntime.run(text, mode=DETERMINISTIC, context_store=…)
  * SocratesRunResult (dyad, apparatus_diagnostic, self_development,
    terminal, state, rendering)
"""
from __future__ import annotations

import time
from pathlib import Path

from socrates_runtime import SocratesRuntime
from socrates_runtime.context_store import InMemoryContextStore
from socrates_runtime.phase_executor import ExecutionMode

from .models import (
    Artifact, ArtifactKind, InputArtifact, Run, RunMode, RunStatus,
    Session, SessionStatus, _now_iso,
)
from .state import InterfaceStore


_MODE_MAP = {
    RunMode.FAST:        ExecutionMode.DETERMINISTIC,
    RunMode.LIVE:        ExecutionMode.LIVE,
    RunMode.TEST_DOUBLE: ExecutionMode.TEST_DOUBLE,
}


def _reconstruction_body(result) -> str:
    """Build a human-readable reconstruction summary from the
    SocratesRunResult governance metadata.
    """
    dyad = result.dyad or {}
    apparatus = result.apparatus_diagnostic or {}
    sd = result.self_development or {}
    telos = (getattr(getattr(result, "state", None), "scene", None) or
             type("_", (), {"telos": ""})).telos or ""
    terminal = (result.terminal.to_public() or {}).get("terminal", "")
    response_text = (result.terminal.to_public() or {}).get(
        "response_text", "")
    lines = [
        f"**Terminal:** `{terminal}`",
        f"**Scene telos (S1):** {telos or '(none)'}",
        "",
        "### Understanding",
        f"- dyad.causal_effect: `{dyad.get('causal_effect','none')}`",
        f"- dyad.surprise_class: `{dyad.get('surprise_class','')}`",
        f"- apparatus.classification: `{apparatus.get('classification','')}`",
        f"- self_development.status: `{sd.get('status','')}`",
        "",
        "### Response",
        response_text.strip() or "_(no rendered text on this run)_",
    ]
    return "\n".join(lines)


def _next_actions_body(result) -> str:
    """Deterministic first-cut of "next actions" — static in vertical
    slice; ProposalEngine replaces this in a later pass.
    """
    return (
        "Возможные следующие шаги:\n\n"
        "- **Запустить Сократа** — эпистемический разбор материала.\n"
        "- **Построить карту аргументов** — извлечь позиции и напряжения.\n"
        "- **Углубить исследование** — добавить смежные источники и "
        "переспросить.\n"
    )


def execute_run(store: InterfaceStore, session: Session,
                input_art: InputArtifact, mode: RunMode = RunMode.FAST,
                runs_dir: Path | str = "runs/interface") -> Run:
    """Synchronous end-to-end: mark Run RUNNING → invoke SocratesRuntime
    → mark COMPLETED/FAILED → persist zero or more Artifacts.
    """
    runs_dir = Path(runs_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)

    run = Run.new(session_id=session.session_id,
                  input_id=input_art.input_id, mode=mode)
    run.status = RunStatus.RUNNING
    store.put_run(run)
    store.update_session_status(session.session_id, SessionStatus.RUNNING)

    exec_mode = _MODE_MAP.get(mode, ExecutionMode.DETERMINISTIC)
    runtime = SocratesRuntime(trace_dir=runs_dir)
    ctx_store = InMemoryContextStore()

    t0 = time.time()
    try:
        result = runtime.run(
            input_art.body_text or "",
            mode=exec_mode,
            context_store=ctx_store,
        )
    except Exception as exc:  # noqa: BLE001
        dt_ms = int((time.time() - t0) * 1000)
        run.status = RunStatus.FAILED
        run.finished_at = _now_iso()
        run.error = f"{type(exc).__name__}: {exc}"
        run.duration_ms = dt_ms
        store.put_run(run)
        store.update_session_status(session.session_id,
                                    SessionStatus.FAILED)
        return run

    dt_ms = int((time.time() - t0) * 1000)
    tinfo = result.terminal.to_public() or {}
    dyad = result.dyad or {}
    apparatus = result.apparatus_diagnostic or {}
    sd = result.self_development or {}

    run.finished_at = _now_iso()
    run.duration_ms = dt_ms
    run.terminal = str(tinfo.get("terminal") or "")
    run.response_text = str(tinfo.get("response_text") or "")
    run.dyad_causal = str(dyad.get("causal_effect") or "")
    run.apparatus_class = str(apparatus.get("classification") or "")
    run.sd_status = str(sd.get("status") or "")
    run.sd_authority = str(sd.get("authority") or "")
    run.provider_id = str(getattr(result, "provider_id", "") or "")
    run.model_id = str(getattr(result, "model_id", "") or "")
    run.trace_ref = str(getattr(result, "trace_path", "") or "")

    is_ok = run.terminal != "FAILED_EXPLICIT"
    run.status = RunStatus.COMPLETED if is_ok else RunStatus.FAILED
    if not is_ok:
        # Surface the runtime's typed reason verbatim as the run error;
        # the runtime already refused to silently fall back, so this
        # is honest.
        run.error = str(tinfo.get("rationale") or "")

    store.put_run(run)

    # Reconstruction artifact — always produced (COMPLETED or FAILED)
    # so the user sees what the runtime actually returned.
    recon = Artifact.new(
        session_id=session.session_id, run_id=run.run_id,
        kind=ArtifactKind.RECONSTRUCTION,
        title="Первичная реконструкция",
        body_md=_reconstruction_body(result),
        provenance={
            "input_id": input_art.input_id,
            "run_id": run.run_id,
            "runtime_layer": "socrates_runtime",
            "execution_mode": run.mode.value,
            "dyad_authority": str(dyad.get("authority") or ""),
            "sd_authority": run.sd_authority,
            "sd_self_mutation_authority":
                str(sd.get("self_mutation_authority") or ""),
        },
    )
    store.put_artifact(recon)

    # Next-actions artifact — static in vertical slice.
    nxt = Artifact.new(
        session_id=session.session_id, run_id=run.run_id,
        kind=ArtifactKind.NEXT_ACTIONS,
        title="Возможные следующие шаги",
        body_md=_next_actions_body(result),
        provenance={"run_id": run.run_id, "vertical_slice_static": True},
    )
    store.put_artifact(nxt)

    store.update_session_status(
        session.session_id,
        SessionStatus.COMPLETED if is_ok else SessionStatus.FAILED)

    return run


__all__ = ["execute_run"]

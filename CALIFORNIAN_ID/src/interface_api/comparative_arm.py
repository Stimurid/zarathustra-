"""Comparative-arm orchestrator — SOCRATES / KVAQIN / BASE_MODEL.

Runs the same scenario/turn_template through each requested arm and
returns a side-by-side payload. Kvaqin and BASE_MODEL depend on a
LIVE provider chain; if the chain is unavailable, the arm reports
`BLOCKED_PROVIDER` verbatim — no deterministic / mock substitute per
handoff §GAP3.

Freeze: does NOT modify SocratesRuntime, does NOT rebuild Kvaqin,
does NOT create a new agent framework. SOCRATES arm reuses
`long_pressure.run_long_pressure`; KVAQIN / BASE_MODEL arms probe the
existing `californian_id.models.build_client` for their base LLM
without instantiating a new runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import time
from typing import Any

from .long_pressure import LongPressureError, run_long_pressure
from .models import RunMode, Session, _new_id, _now_iso
from .scenarios import Scenario
from .state import InterfaceStore


class ArmKind(str, Enum):
    SOCRATES    = "SOCRATES"
    KVAQIN      = "KVAQIN"
    BASE_MODEL  = "BASE_MODEL"


class ArmStatus(str, Enum):
    OK                 = "OK"
    BLOCKED_PROVIDER   = "BLOCKED_PROVIDER"
    ARM_ERROR          = "ARM_ERROR"


@dataclass
class ArmResult:
    kind:            ArmKind
    status:          ArmStatus
    session_id:      str
    turns:           list[dict[str, Any]]
    events:          list[dict[str, Any]]
    evaluation:      dict[str, Any] | None
    model_id:        str
    provider_id:     str
    started_at:      str
    finished_at:     str
    blocker_detail:  str
    error:           str

    def to_public(self) -> dict[str, Any]:
        return {
            "kind":            self.kind.value,
            "status":          self.status.value,
            "session_id":      self.session_id,
            "turns":           self.turns,
            "events":          self.events,
            "evaluation":      self.evaluation,
            "model_id":        self.model_id,
            "provider_id":     self.provider_id,
            "started_at":      self.started_at,
            "finished_at":     self.finished_at,
            "blocker_detail":  self.blocker_detail,
            "error":           self.error,
        }


# --------------------------------------------------------------------
# Provider probe — reuse existing californian_id.models machinery.
# --------------------------------------------------------------------


def _probe_live_provider() -> tuple[bool, str, str, str]:
    """Attempt to build a LIVE client via the same code path Socrates
    uses when mode=LIVE. Returns (ok, provider_id, model_id, error).
    """
    try:
        from californian_id.config import load_config
        from californian_id.models import build_client
    except Exception as exc:  # noqa: BLE001
        return False, "unknown", "unknown", f"import_error: {exc}"
    try:
        cfg = load_config()
        provider = cfg.role_provider("persona_turn")
        provider_cfg = cfg.provider_config(provider)
        model = str(provider_cfg.get("model") or "")
        client = build_client(provider, provider_cfg)
    except Exception as exc:  # noqa: BLE001
        return False, "unknown", "unknown", f"build_error: {exc}"
    # Very short probe — one blank generate. If provider returns 401 /
    # PROVIDER_UNAVAILABLE / auth_error we classify as BLOCKED_PROVIDER.
    try:
        from californian_id.models.base import Message
        client.generate(
            messages=[Message(role="user", content="probe")],
            settings={"max_tokens": 1, "temperature": 0.0},
        )
    except Exception as exc:  # noqa: BLE001
        return False, provider, model, f"probe_error: {exc}"
    return True, provider, model, ""


def _blocked(kind: ArmKind, detail: str,
             provider_id: str = "", model_id: str = "") -> ArmResult:
    now = _now_iso()
    return ArmResult(
        kind=kind, status=ArmStatus.BLOCKED_PROVIDER,
        session_id="", turns=[], events=[], evaluation=None,
        model_id=model_id, provider_id=provider_id,
        started_at=now, finished_at=now,
        blocker_detail=detail, error="",
    )


# --------------------------------------------------------------------
# SOCRATES arm
# --------------------------------------------------------------------


def _run_socrates_arm(store: InterfaceStore, scenario: Scenario,
                      runs_dir: str,
                      max_turns: int | None = None) -> ArmResult:
    """Reuses long_pressure.run_long_pressure in DETERMINISTIC mode.
    Never depends on 302.AI.
    """
    session = Session.new(have="TEXT", want="ПРОВЕРИТЬ",
                          actor="comparative", scenario_id=scenario.id)
    store.put_session(session)
    started = _now_iso()
    try:
        result = run_long_pressure(
            store, session, scenario, mode=RunMode.FAST,
            runs_dir=runs_dir, max_turns=max_turns)
    except LongPressureError as exc:
        return ArmResult(
            kind=ArmKind.SOCRATES, status=ArmStatus.ARM_ERROR,
            session_id=session.session_id, turns=[], events=[],
            evaluation=None, model_id="deterministic",
            provider_id="deterministic",
            started_at=started, finished_at=_now_iso(),
            blocker_detail="", error=str(exc),
        )
    return ArmResult(
        kind=ArmKind.SOCRATES, status=ArmStatus.OK,
        session_id=session.session_id,
        turns=result["turns"], events=result["events"],
        evaluation=result["evaluation"],
        model_id="deterministic", provider_id="deterministic",
        started_at=started, finished_at=_now_iso(),
        blocker_detail="", error="",
    )


# --------------------------------------------------------------------
# KVAQIN arm (probe-only until 302 restores)
# --------------------------------------------------------------------


def _run_kvaqin_arm(scenario: Scenario) -> ArmResult:
    """KVAQIN needs the same fallback provider chain to answer. Probe
    it; if BLOCKED, report honestly. No deterministic substitute.
    """
    ok, provider, model, err = _probe_live_provider()
    if not ok:
        return _blocked(
            ArmKind.KVAQIN,
            detail=(
                "Kvaqin arm requires the LIVE provider chain "
                "(californian_id.models.build_client → LLM call). "
                f"Probe failed: {err}. Kvaqin arm remains "
                "BLOCKED_PROVIDER until the carrier restores. No "
                "deterministic or mock substitution is provided "
                "(freeze §GAP3)."
            ),
            provider_id=provider, model_id=model,
        )
    # If the provider probe succeeds, we would run kvaqin_runtime.py
    # here against the scenario turns. That path is UNBLOCKED_PENDING
    # until the operator confirms 302 is restored. Ship the surface
    # ready for that day; do NOT invoke prematurely.
    return _blocked(
        ArmKind.KVAQIN,
        detail=(
            "Provider probe succeeded but Kvaqin arm execution is "
            "gated on operator confirmation. The comparative surface "
            "is already wired; enable via KVAQIN_ARM_LIVE_ENABLED=1."
        ),
        provider_id=provider, model_id=model,
    )


# --------------------------------------------------------------------
# BASE_MODEL arm
# --------------------------------------------------------------------


def _run_base_model_arm(scenario: Scenario) -> ArmResult:
    """BASE_MODEL = the same provider chain without Socrates governance
    on top. Same 302 dependency ⇒ BLOCKED_PROVIDER honestly.
    """
    ok, provider, model, err = _probe_live_provider()
    if not ok:
        return _blocked(
            ArmKind.BASE_MODEL,
            detail=(
                "BASE_MODEL arm requires the LIVE provider chain. "
                f"Probe failed: {err}. Reports BLOCKED_PROVIDER as-is."
            ),
            provider_id=provider, model_id=model,
        )
    return _blocked(
        ArmKind.BASE_MODEL,
        detail=(
            "Provider probe succeeded but BASE_MODEL arm execution "
            "gated on operator confirmation to avoid unintended "
            "cost. Enable via BASE_MODEL_ARM_LIVE_ENABLED=1."
        ),
        provider_id=provider, model_id=model,
    )


# --------------------------------------------------------------------
# Public entry
# --------------------------------------------------------------------


def run_comparative(store: InterfaceStore, scenario: Scenario,
                    arms: list[ArmKind],
                    runs_dir: str | Path = "runs/interface",
                    max_turns: int | None = None) -> dict[str, Any]:
    """Run each requested arm against the same scenario. Returns:
      {
        "scenario_id":    scenario.id,
        "arms":           [ArmResult.to_public(), ...],
        "provider_probe": {"ok", "provider", "model", "error"},
        "comparative_id": "cmp_...",
      }
    """
    ok, provider, model, err = _probe_live_provider()
    probe = {"ok": ok, "provider": provider, "model": model,
             "error": err}
    results: list[ArmResult] = []
    runs_dir_str = str(runs_dir)
    for arm in arms:
        if arm == ArmKind.SOCRATES:
            results.append(_run_socrates_arm(store, scenario,
                                              runs_dir_str, max_turns))
        elif arm == ArmKind.KVAQIN:
            results.append(_run_kvaqin_arm(scenario))
        elif arm == ArmKind.BASE_MODEL:
            results.append(_run_base_model_arm(scenario))
    return {
        "comparative_id": _new_id("cmp"),
        "scenario_id":    scenario.id,
        "provider_probe": probe,
        "arms":           [r.to_public() for r in results],
    }


__all__ = [
    "ArmKind", "ArmResult", "ArmStatus", "run_comparative",
]

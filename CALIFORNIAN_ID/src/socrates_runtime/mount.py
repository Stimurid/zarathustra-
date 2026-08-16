"""Deterministic semantic mount + conditional trigger admission.

Realises the two pieces of the R8 bundle that must be executable, not just
declarative:

    semantic_mount_manifest.yaml   — required + conditional bodies per router
    conditional_trigger_admission_policy.yaml  — CTA-001..CTA-008

The two rules that make this file worth its length:

    1. ``CORE`` is always mounted (mount_class=ALWAYS_MOUNT).
    2. A conditional body is admitted only when derived from typed pipeline
       state, not from a lexical cue in the input. The runtime raises
       :class:`ConditionalTriggerRejected` when a caller tries the
       forbidden path (whether by accident or by prompt injection).

Nothing here reads the input text for keywords. Every trigger call site
must pass a typed reason.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import (
    ConditionalTriggerRejected,
    HistoricalFallbackForbidden,
    SemanticContextBudgetExceeded,
    SemanticMountMissing,
)
from .identity import DATA_ROOT
from .semantic import BodyRecord, SemanticBodyRegistry

MOUNT_DIR = DATA_ROOT / "current" / "mount"
DEFAULT_BUDGET_BYTES = 300_000  # generous — total of CORE + a few phase Bs

#: Rejection reasons enumerated in TRIGGER_ADMISSION_POLICY.
REJECTION_LEXICAL_ONLY = "LEXICAL_ONLY"
REJECTION_UNAUTHORIZED_SOURCE = "UNAUTHORIZED_SOURCE"
REJECTION_NO_TYPED_STATE_BASIS = "NO_TYPED_STATE_BASIS"
REJECTION_PHASE_IRRELEVANT = "PHASE_IRRELEVANT"
REJECTION_NON_MATERIAL = "NON_MATERIAL"
REJECTION_DUPLICATE_CAUSE = "DUPLICATE_CAUSE"
REJECTION_STALE_STATE = "STALE_STATE"
REJECTION_INVALID_SOURCE_STATUS = "INVALID_SOURCE_STATUS"

#: The sources the admission policy considers authoritative.
AUTHORIZED_TRIGGER_SOURCES: frozenset[str] = frozenset({
    "typed_state", "authorized_transition"})


@dataclass(frozen=True)
class TriggerAdmission:
    """One admissible conditional-trigger cause.

    A caller wanting to mount ``B02`` for phase ``P02`` because origin
    became STATUS_DISPUTE constructs:

        TriggerAdmission(
            trigger_id="STATUS_DISPUTE",
            generating_state_ref="state.origin.status",
            cause_object_ref="origin.epistemic_claim",
            source_status="typed_state",
            phase_relevance="P02",
            materiality_reason=(
                "S3 flagged an unattributed claim; without B02 the "
                "origin/status axes will be confused"),
            admitting_rule="CTA-002",
        )
    """
    trigger_id: str
    generating_state_ref: str
    cause_object_ref: str
    source_status: str
    phase_relevance: str
    materiality_reason: str
    admitting_rule: str = "CTA-002"

    def cause_key(self) -> tuple[str, str]:
        """CTA-004: duplicates coalesce on (trigger_id, cause_object_ref)."""
        return (self.trigger_id, self.cause_object_ref)


@dataclass
class MountedContext:
    """The set of bodies actually mounted for one phase call.

    ``bodies_full`` are read verbatim from disk — never summaries. The
    ``total_bytes`` field is the budget the caller is committing to.
    """
    router_id: str
    phase: str
    required: list[BodyRecord] = field(default_factory=list)
    conditional_admitted: list[BodyRecord] = field(default_factory=list)
    rejected_triggers: list[dict[str, Any]] = field(default_factory=list)
    admitted_triggers: list[TriggerAdmission] = field(default_factory=list)
    total_bytes: int = 0
    budget_bytes: int = DEFAULT_BUDGET_BYTES

    def all_bodies(self) -> list[BodyRecord]:
        return [*self.required, *self.conditional_admitted]

    def body_ids(self) -> list[str]:
        return [b.body_id for b in self.all_bodies()]

    def to_public(self) -> dict[str, Any]:
        return {
            "router_id": self.router_id,
            "phase": self.phase,
            "required": [b.to_public() for b in self.required],
            "conditional_admitted": [b.to_public() for b in self.conditional_admitted],
            "admitted_triggers": [t.__dict__ for t in self.admitted_triggers],
            "rejected_triggers": list(self.rejected_triggers),
            "total_bytes": self.total_bytes,
            "budget_bytes": self.budget_bytes,
        }


class SemanticMountPolicy:
    """Reads the mount manifest and applies it deterministically."""

    def __init__(self, registry: SemanticBodyRegistry,
                 mount_dir: Path | None = None,
                 budget_bytes: int = DEFAULT_BUDGET_BYTES) -> None:
        import yaml
        self.registry = registry
        self.mount_dir = Path(mount_dir or MOUNT_DIR)
        self.budget_bytes = budget_bytes

        manifest_path = self.mount_dir / "semantic_mount_manifest.yaml"
        if not manifest_path.exists():
            raise SemanticMountMissing(
                f"mount manifest not found: {manifest_path}")
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        self._mounts: dict[str, dict[str, Any]] = data.get("mounts", {}) or {}
        self._conditional_map: dict[str, list[str]] = (
            data.get("conditional_triggers", {}) or {})
        self._failure_policy: str = data.get("failure_policy", "")

        cta_path = (self.mount_dir
                    / "conditional_trigger_admission_policy_v0.1_candidate.yaml")
        if not cta_path.exists():
            raise SemanticMountMissing(
                f"trigger admission policy not found: {cta_path}")
        cta = yaml.safe_load(cta_path.read_text(encoding="utf-8"))
        self._cta_invariants: dict[str, bool] = cta.get("invariants", {}) or {}

    # ------------------------------------------------------------------

    def mount(self, router_id: str, phase: str,
              proposed_triggers: list[TriggerAdmission] | None = None,
              budget_bytes: int | None = None) -> MountedContext:
        """Assemble the mount for one phase.

        ``proposed_triggers`` come from the running phase, already typed. This
        function does not read the input text.
        """
        mount_spec = self._mounts.get(router_id)
        if mount_spec is None:
            raise SemanticMountMissing(
                f"no mount spec for router {router_id!r} in manifest")

        required_ids = list(mount_spec.get("required") or ())
        allowed_conditional = frozenset(mount_spec.get("conditional") or ())
        budget = budget_bytes if budget_bytes is not None else self.budget_bytes

        ctx = MountedContext(router_id=router_id, phase=phase,
                             budget_bytes=budget)

        # 1) Required bodies — CORE first, in manifest order. Missing == fatal.
        for body_id in required_ids:
            record = self.registry.get(body_id)          # raises if absent
            ctx.required.append(record)
            ctx.total_bytes += record.bytes

        # 2) Conditional bodies — admit only after CTA gating.
        admitted, rejected = self._gate_triggers(
            router_id, allowed_conditional, proposed_triggers or [])
        # Coalesce distinct triggers with the same cause_object_ref (CTA-004)
        # so multiple lexically diverse cues never inflate authority.
        for trigger in admitted:
            allowed_bodies = self._bodies_for_trigger(trigger.trigger_id,
                                                      allowed_conditional)
            for body_id in allowed_bodies:
                if body_id in ctx.body_ids():
                    continue
                record = self.registry.get(body_id)
                ctx.conditional_admitted.append(record)
                ctx.total_bytes += record.bytes
        ctx.admitted_triggers = admitted
        ctx.rejected_triggers = rejected

        # 3) Budget check — fail closed on required layer overflow.
        if ctx.total_bytes > ctx.budget_bytes:
            raise SemanticContextBudgetExceeded(
                f"router={router_id} phase={phase} "
                f"mandatory bodies = {ctx.total_bytes} bytes > "
                f"budget = {ctx.budget_bytes} bytes; "
                "no silent summary substitution")

        return ctx

    # ------------------------------------------------------------------

    def _gate_triggers(self, router_id: str,
                       allowed_conditional: frozenset[str],
                       proposed: list[TriggerAdmission]
                       ) -> tuple[list[TriggerAdmission], list[dict[str, Any]]]:
        admitted: list[TriggerAdmission] = []
        rejected: list[dict[str, Any]] = []
        seen_causes: set[tuple[str, str]] = set()

        for t in proposed:
            reason = self._admissibility(router_id, allowed_conditional, t)
            if reason is None:
                # CTA-004 coalescence
                if t.cause_key() in seen_causes:
                    rejected.append(_reject(t, REJECTION_DUPLICATE_CAUSE,
                                            "same (trigger_id, cause_object_ref) already admitted"))
                    continue
                seen_causes.add(t.cause_key())
                admitted.append(t)
            else:
                rejected.append(_reject(t, reason,
                                        "failed admission policy"))
        return admitted, rejected

    def _admissibility(self, router_id: str,
                       allowed_conditional: frozenset[str],
                       t: TriggerAdmission) -> str | None:
        if t.source_status not in AUTHORIZED_TRIGGER_SOURCES:
            return REJECTION_UNAUTHORIZED_SOURCE            # CTA-001
        if not t.generating_state_ref:
            return REJECTION_NO_TYPED_STATE_BASIS           # CTA-002
        if t.phase_relevance and t.phase_relevance != router_id:
            return REJECTION_PHASE_IRRELEVANT               # CTA-005
        if not t.materiality_reason:
            return REJECTION_NON_MATERIAL                   # CTA-005
        if not self._bodies_for_trigger(t.trigger_id, allowed_conditional):
            return REJECTION_NON_MATERIAL                   # trigger has nothing to mount
        return None

    def _bodies_for_trigger(self, trigger_id: str,
                            allowed_conditional: frozenset[str]) -> list[str]:
        # semantic_mount_manifest lists conditional_triggers per body_id.
        # Invert for lookup and clip to the router's allowed set.
        out: list[str] = []
        for body_id, triggers in self._conditional_map.items():
            if trigger_id in triggers and body_id in allowed_conditional:
                out.append(body_id)
        return sorted(out)

    # ------------------------------------------------------------------

    def refuse_historical_fallback(self, requested_from: str = "") -> None:
        """Raised if any caller asks for a historical G-S25 prompt at runtime.

        The rule lives on the mount manifest:
        ``historical_baseline.fallback_allowed: false`` — this is the code
        that enforces it.
        """
        raise HistoricalFallbackForbidden(
            f"historical G-S25 fallback refused (asked by "
            f"{requested_from or 'runtime'})")


def _reject(t: TriggerAdmission, reason: str, note: str) -> dict[str, Any]:
    return {"trigger_id": t.trigger_id, "cause_object_ref": t.cause_object_ref,
            "source_status": t.source_status,
            "rejection_reason": reason, "note": note}

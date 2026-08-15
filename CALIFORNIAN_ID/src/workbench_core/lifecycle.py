"""Variant lifecycle state machine (PROMPT_VARIANT_LIFECYCLE v0.1)."""
from __future__ import annotations

from .models import VariantState

ALLOWED: dict[str, set[str]] = {
    "BASELINE": {"CANDIDATE_UNCHECKED", "ACTIVE", "DEPRECATED"},
    "CANDIDATE_UNCHECKED": {"STATIC_VALID", "INCOMPATIBLE", "REJECTED", "CANDIDATE_UNCHECKED"},
    # Re-validation is idempotent, and a waiver granted after the fact must be
    # able to move a candidate out of INCOMPATIBLE without re-cloning it.
    "STATIC_VALID": {"COMPILED", "CANDIDATE_UNCHECKED", "INCOMPATIBLE",
                     "REJECTED", "STATIC_VALID"},
    "COMPILED": {"SMOKE_TESTED", "CANDIDATE_UNCHECKED", "REJECTED", "INCOMPATIBLE"},
    "SMOKE_TESTED": {"ACCEPTED", "CANDIDATE_UNCHECKED", "REJECTED"},
    "ACCEPTED": {"ACTIVE", "CANDIDATE_UNCHECKED", "REJECTED", "DEPRECATED"},
    "ACTIVE": {"DEPRECATED"},
    "DEPRECATED": {"ACTIVE", "REJECTED"},
    "REJECTED": {"CANDIDATE_UNCHECKED"},
    "INCOMPATIBLE": {"CANDIDATE_UNCHECKED", "REJECTED", "STATIC_VALID", "INCOMPATIBLE"},
}

#: Transitions that may never happen regardless of flags.
FORBIDDEN_DIRECT = {("CANDIDATE_UNCHECKED", "ACTIVE"),
                    ("STATIC_VALID", "ACTIVE"),
                    ("COMPILED", "ACTIVE"),
                    ("SMOKE_TESTED", "ACTIVE"),
                    ("INCOMPATIBLE", "ACTIVE"),
                    ("REJECTED", "ACTIVE")}


class LifecycleError(RuntimeError):
    pass


def assert_transition(current: VariantState, target: VariantState) -> None:
    if (current, target) in FORBIDDEN_DIRECT:
        raise LifecycleError(
            f"переход {current} → {target} запрещён: активация возможна "
            f"только из ACCEPTED (или повторно из DEPRECATED)")
    if target not in ALLOWED.get(current, set()):
        raise LifecycleError(f"переход {current} → {target} не разрешён")


def assert_not_baseline_removal(state: VariantState, target: VariantState) -> None:
    if state == "BASELINE" and target in {"REJECTED", "INCOMPATIBLE"}:
        raise LifecycleError("BASELINE нельзя отклонить или удалить")


def edit_resets_to(state: VariantState) -> VariantState:
    """Any edit drops a variant back to unchecked."""
    return "BASELINE" if state == "BASELINE" else "CANDIDATE_UNCHECKED"

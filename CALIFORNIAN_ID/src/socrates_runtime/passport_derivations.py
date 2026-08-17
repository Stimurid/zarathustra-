"""Phase 3F — passport derived fields + sufficiency assessment
(SOC-PASS-001 + SOC-SUFF-001).

EpistemicPassport is a DERIVED human-facing projection — NOT a new
authority. This module adds pure-function derivations of three
useful fields (reasoning_principle, sufficiency, applicability_bounds)
that a passport rendering may fill from AUTHORITATIVE STATE + TRACE
without introducing schema bureaucracy or a new gate.

Per continuation prompt §3F: "Do not turn Passport into
schema-everything bureaucracy or new authority."

For sufficiency: this module considers whether a separate answer-
sufficiency assessment produces real behavioural value beyond the
existing:

* :class:`~state.Operation.applicable`,
* :class:`~state.Operation.open_world_gap`,
* :class:`~projection.ProjectionDiagnostics.mismatch`,
* :class:`~epistemic_model.EpistemicPassport.known_conflicts` +
  ``open_questions``,
* :class:`~context_governance.ClarificationJudgement` (G-3A).

Verdict (with rationale in :func:`sufficiency_verdict_rationale`):

    **NO_ADDITIONAL_OBJECT_REQUIRED**.

A separate SufficiencyAssessment would duplicate what the passport
already reads from the sources above. Instead, this module ships
:func:`derive_sufficiency` as a pure function OVER those sources —
no new object, no new authority. This preserves the passport's
role as a read-model.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PassportDerivedFields:
    """The three derived fields §3F names. All computed from
    authoritative state via :func:`derive_passport_fields`; no
    field is a new persistent state variable.
    """
    reasoning_principle: str
    sufficiency: str
    applicability_bounds: tuple[str, ...]


# ---------------------------------------------------------- reasoning_principle


def derive_reasoning_principle(*, operation_kind: str,
                               operation_applicable: bool,
                               scene_telos: str,
                               capability_resolution_kind: str = "",
                               pending_diagnostic_mismatch: bool = False,
                               ) -> str:
    """The typed principle by which the current outward action can be
    reasoned about. NOT a claim about how the model 'thinks' — a
    machine-readable summary of the current apparatus + operation.
    """
    if pending_diagnostic_mismatch:
        return ("REFLECTIVE_RETREAT: the current apparatus produced a "
                "typed mismatch and the runtime is in reflective mode")
    if capability_resolution_kind == "ORGAN_GAP":
        return ("HELD_APORIA: no available capability faithfully realises "
                "the requested operation; response scoped accordingly")
    if capability_resolution_kind == "CUTTER_SPEC_SYNTHESIS":
        return (f"SYNTHESISED_APPARATUS: operation {operation_kind!r} "
                f"executed via a compositionally-bound cutter spec "
                f"over authorised generic primitives")
    if not operation_applicable:
        return (f"RETURN_TO_HUMAN: operation {operation_kind!r} declared "
                f"inapplicable to the current material")
    if capability_resolution_kind == "REGISTERED_CAPABILITY":
        return (f"REGISTERED_APPARATUS: operation {operation_kind!r} "
                f"executed via a registered cutter capability")
    if scene_telos:
        return (f"DIRECT_OPERATION: operation {operation_kind!r} applied "
                f"to material toward telos {scene_telos!r}")
    return f"OPERATION: {operation_kind!r}"


# ---------------------------------------------------------- sufficiency


def derive_sufficiency(*, operation_applicable: bool,
                       operation_open_world_gap: bool,
                       pending_diagnostic_mismatch: bool,
                       known_conflicts: tuple[str, ...],
                       open_questions: tuple[str, ...],
                       capability_resolution_kind: str = "",
                       ) -> str:
    """Answer-sufficiency as a DERIVED FUNCTION over the sources
    that already carry the information. NOT a new gate, NOT a new
    authority.

    Bands (deliberately coarse — three levels only):

    * ``INSUFFICIENT`` — inapplicable operation OR ORGAN_GAP OR
      pending reflective mismatch. Response CANNOT stand as an answer.
    * ``PARTIAL_WITH_KNOWN_LOSS`` — applicable operation BUT open-
      world gap OR held conflicts OR open questions present. Response
      stands but must surface its known incompleteness.
    * ``SUFFICIENT`` — applicable + no gap + no mismatch + no known
      conflicts + no open questions.
    """
    if (not operation_applicable
            or capability_resolution_kind == "ORGAN_GAP"
            or pending_diagnostic_mismatch):
        return "INSUFFICIENT"
    if operation_open_world_gap or known_conflicts or open_questions:
        return "PARTIAL_WITH_KNOWN_LOSS"
    return "SUFFICIENT"


# ---------------------------------------------------------- applicability_bounds


def derive_applicability_bounds(*, operation_kind: str,
                                target_object_family: tuple[str, ...],
                                contraindications: tuple[str, ...],
                                world_model_refs: tuple[str, ...],
                                ) -> tuple[str, ...]:
    """The typed applicability envelope. A human reader can see
    quickly what the current answer legitimately covers vs where
    it stops.
    """
    bounds: list[str] = []
    if target_object_family:
        bounds.append(
            f"target_family={list(target_object_family)!r}")
    if contraindications:
        bounds.append(
            f"contraindications={list(contraindications)!r}")
    if world_model_refs:
        bounds.append(
            f"under_world_models={list(world_model_refs)!r}")
    if operation_kind:
        bounds.append(f"operation={operation_kind!r}")
    return tuple(bounds)


# ---------------------------------------------------------- top-level combinator


def derive_passport_fields(*, operation_kind: str,
                           operation_applicable: bool,
                           operation_open_world_gap: bool,
                           scene_telos: str,
                           target_object_family: tuple[str, ...] = (),
                           contraindications: tuple[str, ...] = (),
                           world_model_refs: tuple[str, ...] = (),
                           pending_diagnostic_mismatch: bool = False,
                           capability_resolution_kind: str = "",
                           known_conflicts: tuple[str, ...] = (),
                           open_questions: tuple[str, ...] = (),
                           ) -> PassportDerivedFields:
    """One-call derivation. All inputs read from authoritative typed
    state; no field is a new persistent variable.
    """
    return PassportDerivedFields(
        reasoning_principle=derive_reasoning_principle(
            operation_kind=operation_kind,
            operation_applicable=operation_applicable,
            scene_telos=scene_telos,
            capability_resolution_kind=capability_resolution_kind,
            pending_diagnostic_mismatch=pending_diagnostic_mismatch),
        sufficiency=derive_sufficiency(
            operation_applicable=operation_applicable,
            operation_open_world_gap=operation_open_world_gap,
            pending_diagnostic_mismatch=pending_diagnostic_mismatch,
            known_conflicts=known_conflicts,
            open_questions=open_questions,
            capability_resolution_kind=capability_resolution_kind),
        applicability_bounds=derive_applicability_bounds(
            operation_kind=operation_kind,
            target_object_family=target_object_family,
            contraindications=contraindications,
            world_model_refs=world_model_refs))


# ---------------------------------------------------------- SOC-SUFF-001


def sufficiency_verdict_rationale() -> dict[str, Any]:
    """SOC-SUFF-001 verdict: does a SEPARATE typed
    ``SufficiencyAssessment`` object with its own gate produce
    material behavioural value beyond what the existing sources
    already carry?

    **Answer: NO_ADDITIONAL_OBJECT_REQUIRED.**

    The verdict + reasoning is exported here so a future pass can
    revisit the decision with additional evidence.
    """
    return {
        "verdict": "NO_ADDITIONAL_OBJECT_REQUIRED",
        "rationale": (
            "The information a separate SufficiencyAssessment would "
            "surface is already covered by existing typed state:\n"
            "  * Operation.applicable + Operation.why_not for "
            "gate-level inapplicability;\n"
            "  * Operation.open_world_gap for known ontology gap;\n"
            "  * ProjectionDiagnostics.mismatch for typed apparatus "
            "mismatch;\n"
            "  * EpistemicPassport.known_conflicts + "
            "open_questions for held incompleteness;\n"
            "  * CapabilityResolution.kind==ORGAN_GAP for capability "
            "insufficiency;\n"
            "  * ClarificationJudgement.decision (G-3A) for when to "
            "ask vs proceed vs return-to-human.\n"
            "A separate object would duplicate these signals and "
            "manufacture a new gate. Instead, derive_sufficiency() "
            "in this module offers the same summary as a pure "
            "function over the authoritative sources — no new "
            "object, no new authority."),
        "downstream_effect": (
            "derive_passport_fields() returns "
            "PassportDerivedFields.sufficiency as INSUFFICIENT / "
            "PARTIAL_WITH_KNOWN_LOSS / SUFFICIENT for renderers "
            "and Workbench display. No new state variable added."),
        "revisitable": (
            "If a future pass finds a case where the six sources "
            "above collectively fail to capture insufficient answers, "
            "reopen this decision with the exact case as evidence."),
    }


__all__ = [
    "PassportDerivedFields",
    "derive_applicability_bounds", "derive_passport_fields",
    "derive_reasoning_principle", "derive_sufficiency",
    "sufficiency_verdict_rationale",
]

"""Parse a model response into a validated PhaseDelta.

Rules:
    * response must be strict JSON (a single object);
    * only fields declared by :func:`phase_contracts.output_contract_for`
      are accepted; extras are a jurisdiction violation, not a warning;
    * enums are enforced;
    * each phase may write only the fields declared in
      :func:`phase_contracts.jurisdiction_for`;
    * trigger admissibility (CTA-001..008) is applied by the mount policy
      one layer up — this parser only produces typed objects.

Forbidden here:
    * regex fishing for a JSON object inside prose;
    * silent defaults;
    * ``ast.literal_eval`` on non-JSON output.
"""
from __future__ import annotations

import json
from typing import Any

from .errors import SocratesRuntimeError
from .mount import TriggerAdmission
from .phase_contracts import (
    AUTHORITY_VALUES,
    PROVENANCE_VALUES,
    jurisdiction_for,
    output_contract_for,
)
from .phase_executor import PhaseDelta            # type: ignore[import]  # runtime
from .projection import (
    ReflectiveReturn,
    RetreatLevel,
    ReturnTarget,
    new_reflective_id,
)
from .state import (
    Authority,
    MemoryProposal,
    Operation,
    Origin,
    Ownership,
    ProvenanceStatus,
    Scene,
)


class OutputValidationError(SocratesRuntimeError):
    """Response failed strict parsing / contract validation."""


class JurisdictionViolation(SocratesRuntimeError):
    """A phase attempted to write a field it does not own."""


# ---------------------------------------------------------- entry


def parse_and_validate_output(raw: str, request) -> PhaseDelta:
    """Parse ``raw`` for ``request.phase``.

    Raises :class:`OutputValidationError` on malformed JSON or contract
    violation, and :class:`JurisdictionViolation` when the delta touches
    fields the phase does not own.
    """
    from .phase_executor import PhaseExecutionRequest    # avoid cycle
    assert isinstance(request, PhaseExecutionRequest)

    if not raw or not raw.strip():
        raise OutputValidationError("empty model response")
    text = _strip_common_fences(raw.strip())
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise OutputValidationError(f"response is not valid JSON: {exc}") from None
    if not isinstance(obj, dict):
        raise OutputValidationError(
            f"top-level JSON must be an object, got {type(obj).__name__}")

    contract = output_contract_for(request.phase)
    _validate_object(obj, contract, path="")

    return _build_delta(request.phase, obj)


# ---------------------------------------------------------- helpers


def _strip_common_fences(s: str) -> str:
    # Providers sometimes wrap JSON in ```json fences even when asked not to.
    # Strip only that exact convention; anything else is a validation failure.
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s[3:]
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3].rstrip()
    if s.startswith("```json"):                             # unlikely after above
        s = s[len("```json"):].lstrip()
    return s


def _validate_object(obj: dict[str, Any], schema: dict[str, Any],
                     path: str) -> None:
    if schema.get("type") == "object" or (isinstance(schema.get("type"), list)
                                           and "object" in schema["type"]):
        if not isinstance(obj, dict):
            raise OutputValidationError(f"{path or '<root>'}: expected object")
    allowed_extras = schema.get("additionalProperties", True)
    properties = schema.get("properties", {}) or {}
    required = schema.get("required", []) or []
    for key in required:
        if key not in obj:
            raise OutputValidationError(
                f"{path or '<root>'}: missing required key {key!r}")
    for key, value in obj.items():
        if key not in properties:
            if allowed_extras is False:
                raise OutputValidationError(
                    f"{path or '<root>'}: extra key {key!r} not allowed")
            continue
        _validate_value(value, properties[key], path=f"{path}.{key}")


def _validate_value(value: Any, schema: dict[str, Any], path: str) -> None:
    ty = schema.get("type")
    if ty == "object" or (isinstance(ty, list) and "object" in ty):
        if value is None and isinstance(ty, list) and "null" in ty:
            return
        _validate_object(value, schema, path)
        return
    if ty == "array":
        if not isinstance(value, list):
            raise OutputValidationError(f"{path}: expected array")
        item_schema = schema.get("items", {})
        for i, item in enumerate(value):
            _validate_value(item, item_schema, path=f"{path}[{i}]")
        return
    if ty == "string":
        if not isinstance(value, str):
            raise OutputValidationError(f"{path}: expected string")
        enum = schema.get("enum")
        if enum and value not in enum:
            raise OutputValidationError(
                f"{path}: value {value!r} not in enum {enum}")
        return
    if ty == "boolean":
        if not isinstance(value, bool):
            raise OutputValidationError(f"{path}: expected boolean")
        return
    if ty == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            raise OutputValidationError(f"{path}: expected integer")
        return
    if isinstance(ty, list) and "null" in ty and value is None:
        return


# ---------------------------------------------------------- build delta


def _build_delta(phase: str, obj: dict[str, Any]) -> PhaseDelta:
    juris = jurisdiction_for(phase)
    # A key in the JSON is only *material* to the state if the phase's
    # jurisdiction admits it. Extra keys allowed by the contract but
    # outside the phase's write authority are recorded in ``parsed`` for
    # the trace but never mutate PipelineState.
    delta = PhaseDelta(parsed=obj)

    if "scene" in obj and "scene" in juris:
        delta.scene = _build_scene(obj["scene"])
    elif "scene" in obj and "scene" not in juris:
        raise JurisdictionViolation(
            f"{phase}: not authorised to write scene")

    if "origin" in obj and "origin" in juris:
        delta.origin = _build_origin(obj["origin"])
    elif "origin" in obj and "origin" not in juris:
        raise JurisdictionViolation(
            f"{phase}: not authorised to write origin")

    if "operation" in obj and "operation" in juris:
        delta.operation = _build_operation(obj["operation"])
    elif "operation" in obj and "operation" not in juris:
        raise JurisdictionViolation(
            f"{phase}: not authorised to write operation")

    if "ownership" in obj and "ownership" in juris:
        delta.ownership = _build_ownership(obj["ownership"])
    elif "ownership" in obj and "ownership" not in juris:
        raise JurisdictionViolation(
            f"{phase}: not authorised to write ownership")

    if "triggers" in obj and "triggers" in juris:
        delta.triggers = [_build_trigger(t) for t in (obj["triggers"] or [])]

    if "memory_proposal" in obj and "memory_proposal" in juris:
        mp = obj["memory_proposal"]
        if mp is not None:
            delta.memory_proposal = MemoryProposal(
                kind=str(mp.get("kind") or ""),
                text=str(mp.get("text") or ""),
                grounds=str(mp.get("grounds") or ""))

    if "invoke_council" in obj and "invoke_council" in juris:
        delta.invoke_council = bool(obj["invoke_council"])

    if "invoke_execution" in obj and "invoke_execution" in juris:
        delta.invoke_execution = bool(obj["invoke_execution"])

    if "reflective_return" in obj and "reflective_return" in juris:
        rr = obj["reflective_return"]
        if rr is not None:
            delta.reflective_return = _build_reflective_return(rr)
    elif "reflective_return" in obj and "reflective_return" not in juris:
        raise JurisdictionViolation(
            f"{phase}: not authorised to write reflective_return")

    return delta


def _build_reflective_return(d: dict[str, Any]) -> ReflectiveReturn:
    return ReflectiveReturn(
        reflective_id=str(d.get("reflective_id") or new_reflective_id()),
        from_projection_id=str(d.get("from_projection_id") or ""),
        retreat_level=RetreatLevel(d.get("retreat_level", "R1")),
        return_target=ReturnTarget(d.get("return_target", "S4")),
        reason=str(d.get("reason") or ""),
        failed_assumption=str(d.get("failed_assumption") or ""),
        what_remains_valid=tuple(d.get("what_remains_valid") or ()),
        what_changes=tuple(d.get("what_changes") or ()),
        revised_operation_kind=str(d.get("revised_operation_kind") or ""),
        revised_ontology_id=str(d.get("revised_ontology_id") or ""),
        revised_scene_telos=str(d.get("revised_scene_telos") or ""),
        diagnostic_fingerprint=str(d.get("diagnostic_fingerprint") or ""),
    )


def _build_scene(d: dict[str, Any]) -> Scene:
    return Scene(
        telos=str(d.get("telos") or ""),
        role_hint=str(d.get("role_hint") or ""),
        authority=Authority(d.get("authority", "unset")),
        materials=tuple(d.get("materials") or ()),
    )


def _build_origin(d: dict[str, Any]) -> Origin:
    return Origin(
        status=ProvenanceStatus(d.get("status", "unknown")),
        sources_named=tuple(d.get("sources_named") or ()),
        binding_authority=Authority(d.get("binding_authority", "unset")),
        temporal_stale=bool(d.get("temporal_stale", False)),
    )


def _build_operation(d: dict[str, Any]) -> Operation:
    return Operation(
        kind=str(d.get("kind") or ""),
        applicable=bool(d.get("applicable", True)),
        why_not=str(d.get("why_not") or ""),
        open_world_gap=bool(d.get("open_world_gap", False)),
    )


def _build_ownership(d: dict[str, Any]) -> Ownership:
    return Ownership(
        owner=Authority(d.get("owner", "unset")),
        human_resolved=bool(d.get("human_resolved", False)),
        return_reason=str(d.get("return_reason") or ""),
    )


def _build_trigger(d: dict[str, Any]) -> TriggerAdmission:
    return TriggerAdmission(
        trigger_id=str(d.get("trigger_id") or ""),
        generating_state_ref=str(d.get("generating_state_ref") or ""),
        cause_object_ref=str(d.get("cause_object_ref") or ""),
        source_status=str(d.get("source_status") or "typed_state"),
        phase_relevance=str(d.get("phase_relevance") or ""),
        materiality_reason=str(d.get("materiality_reason") or ""),
        admitting_rule=str(d.get("admitting_rule") or "CTA-002"),
    )

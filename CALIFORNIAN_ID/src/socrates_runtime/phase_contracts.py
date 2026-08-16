"""Output contracts per S-phase — what the model MUST return.

Not JSON Schema in the full sense — we use a small pragmatic subset the
runtime enforces itself (see :mod:`.phase_output`). The provider is asked
to emit exactly this shape; anything else is a validation failure.

Also encodes **phase jurisdiction**: which fields a phase may write.
S1 may not decide ownership, S6 may not rewrite the scene, and so on.
The pipeline rejects any delta that touches fields outside a phase's
declared jurisdiction, so a chatty model cannot override earlier phases
in a later one.
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------- vocab

AUTHORITY_VALUES = ["unset", "human", "system", "joint"]
PROVENANCE_VALUES = ["unknown", "attributed", "reconstructed", "speculative"]


def _trigger_array_schema() -> dict[str, Any]:
    return {
        "type": "array",
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ["trigger_id", "generating_state_ref",
                         "cause_object_ref", "source_status",
                         "phase_relevance", "materiality_reason"],
            "properties": {
                "trigger_id": {"type": "string"},
                "generating_state_ref": {"type": "string"},
                "cause_object_ref": {"type": "string"},
                "source_status": {"type": "string",
                                  "enum": ["typed_state",
                                           "authorized_transition"]},
                "phase_relevance": {"type": "string"},
                "materiality_reason": {"type": "string"},
                "admitting_rule": {"type": "string"},
            },
        },
    }


def _reflective_return_schema() -> dict[str, Any]:
    """S7 payload for internal reflective retreat.

    Distinct from ``invoke_council`` (which is the human/council-facing
    branch of S7) and from the ``Terminal.RETURN_OPERATION`` human return.
    See ``data/socrates/current/contracts/reflective_return.schema.json``.
    """
    return {
        "type": ["object", "null"],
        "additionalProperties": False,
        "required": ["reflective_id", "from_projection_id", "retreat_level",
                     "return_target", "reason", "failed_assumption",
                     "what_remains_valid", "what_changes"],
        "properties": {
            "reflective_id": {"type": "string"},
            "from_projection_id": {"type": "string"},
            "retreat_level": {"type": "string",
                              "enum": ["R0", "R1", "R2", "R3",
                                       "R4", "R5", "R6"]},
            "return_target": {"type": "string",
                              "enum": ["S1", "S3", "S4"]},
            "reason": {"type": "string"},
            "failed_assumption": {"type": "string"},
            "what_remains_valid": {"type": "array",
                                   "items": {"type": "string"}},
            "what_changes": {"type": "array",
                             "items": {"type": "string"}},
            "revised_operation_kind": {"type": "string"},
            "revised_ontology_id": {"type": "string"},
            "revised_scene_telos": {"type": "string"},
            "diagnostic_fingerprint": {"type": "string"},
        },
    }


def _memory_proposal_schema() -> dict[str, Any]:
    return {
        "type": ["object", "null"],
        "additionalProperties": False,
        "required": ["kind", "text"],
        "properties": {
            "kind": {"type": "string",
                     "enum": ["observation", "distinction",
                              "recurring_pattern", "contradiction",
                              "hypothesis"]},
            "text": {"type": "string"},
            "grounds": {"type": "string"},
        },
    }


# ---------------------------------------------------------- per-phase


_TRIGGERS_ONLY = {
    "$id": "socrates.phase.triggers_only",
    "type": "object",
    "additionalProperties": False,
    "properties": {"triggers": _trigger_array_schema()},
}


CONTRACTS: dict[str, dict[str, Any]] = {
    "S0": {
        "$id": "socrates.phase.S0",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "context_ok": {"type": "boolean"},
            "notes": {"type": "string"},
            "triggers": _trigger_array_schema(),
        },
    },
    "S1": {
        "$id": "socrates.phase.S1",
        "type": "object",
        "additionalProperties": False,
        "required": ["scene"],
        "properties": {
            "scene": {
                "type": "object",
                "additionalProperties": False,
                "required": ["telos", "authority"],
                "properties": {
                    "telos": {"type": "string"},
                    "role_hint": {"type": "string"},
                    "authority": {"type": "string", "enum": AUTHORITY_VALUES},
                    "materials": {"type": "array", "items": {"type": "string"}},
                },
            },
            "triggers": _trigger_array_schema(),
        },
    },
    "S2": _TRIGGERS_ONLY,
    "S3": {
        "$id": "socrates.phase.S3",
        "type": "object",
        "additionalProperties": False,
        "required": ["origin"],
        "properties": {
            "origin": {
                "type": "object",
                "additionalProperties": False,
                "required": ["status", "binding_authority"],
                "properties": {
                    "status": {"type": "string", "enum": PROVENANCE_VALUES},
                    "sources_named": {"type": "array", "items": {"type": "string"}},
                    "binding_authority": {"type": "string",
                                          "enum": AUTHORITY_VALUES},
                    "temporal_stale": {"type": "boolean"},
                },
            },
            "triggers": _trigger_array_schema(),
        },
    },
    "S4": {
        "$id": "socrates.phase.S4",
        "type": "object",
        "additionalProperties": False,
        "required": ["operation"],
        "properties": {
            "operation": {
                "type": "object",
                "additionalProperties": False,
                "required": ["kind", "applicable"],
                "properties": {
                    "kind": {"type": "string"},
                    "applicable": {"type": "boolean"},
                    "why_not": {"type": "string"},
                    "open_world_gap": {"type": "boolean"},
                },
            },
            "triggers": _trigger_array_schema(),
        },
    },
    "S5": {
        "$id": "socrates.phase.S5",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "triggers": _trigger_array_schema(),
            "memory_proposal": _memory_proposal_schema(),
        },
    },
    "S6": {
        "$id": "socrates.phase.S6",
        "type": "object",
        "additionalProperties": False,
        "required": ["ownership"],
        "properties": {
            "ownership": {
                "type": "object",
                "additionalProperties": False,
                "required": ["owner", "human_resolved"],
                "properties": {
                    "owner": {"type": "string", "enum": AUTHORITY_VALUES},
                    "human_resolved": {"type": "boolean"},
                    "return_reason": {"type": "string"},
                },
            },
            "triggers": _trigger_array_schema(),
            "memory_proposal": _memory_proposal_schema(),
        },
    },
    "S7": {
        "$id": "socrates.phase.S7",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "invoke_council": {"type": "boolean"},
            "triggers": _trigger_array_schema(),
            "reflective_return": _reflective_return_schema(),
        },
    },
    "S8": {
        "$id": "socrates.phase.S8",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "invoke_execution": {"type": "boolean"},
            "triggers": _trigger_array_schema(),
        },
    },
    "S9": {
        "$id": "socrates.phase.S9",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "invoke_execution": {"type": "boolean"},
            "memory_proposal": _memory_proposal_schema(),
        },
    },
    "S10": {
        "$id": "socrates.phase.S10",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "memory_proposal": _memory_proposal_schema(),
            "triggers": _trigger_array_schema(),
        },
    },
}


#: What each phase is allowed to update on :class:`PipelineState`. A delta
#: that touches anything not listed here is rejected as a jurisdiction
#: violation — a model cannot decide ownership from an S1 call.
JURISDICTION: dict[str, frozenset[str]] = {
    "S0": frozenset({"triggers"}),
    "S1": frozenset({"scene", "triggers"}),
    "S2": frozenset({"triggers"}),
    "S3": frozenset({"origin", "triggers"}),
    "S4": frozenset({"operation", "triggers"}),
    "S5": frozenset({"triggers", "memory_proposal"}),
    "S6": frozenset({"ownership", "triggers", "memory_proposal"}),
    "S7": frozenset({"triggers", "invoke_council", "reflective_return"}),
    "S8": frozenset({"triggers", "invoke_execution"}),
    "S9": frozenset({"invoke_execution", "memory_proposal"}),
    "S10": frozenset({"memory_proposal", "triggers"}),
}


def output_contract_for(phase: str) -> dict[str, Any]:
    return CONTRACTS.get(phase, _TRIGGERS_ONLY)


def jurisdiction_for(phase: str) -> frozenset[str]:
    return JURISDICTION.get(phase, frozenset())

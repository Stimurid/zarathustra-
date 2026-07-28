"""Official Tinkuy ingress envelopes adapted for the Zarathustra runtime.

This keeps the canonical two-lane contract explicit:
    - raw_stream: raw text provided as content
    - semantic_units: externally produced semantic units with provenance

The current Zarathustra runtime still uses its native `run(...)` and
`run_from_units(...)` internals. This module provides the thin contract layer
between the canonical Tinkuy envelope and those existing runtime entrypoints.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .schemas import SemanticUnit, UnitPack


@dataclass
class RawStreamEnvelope:
    mode: str
    run_id: str
    content: str
    speaker_hint: str | None = None
    timestamp: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticIngressUnit:
    unit_id: str
    text: str
    speaker: str | None = None
    char_span: list[int] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)
    semantic_types: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticUnitsEnvelope:
    mode: str
    run_id: str
    units: list[SemanticIngressUnit]
    metadata: dict[str, Any] = field(default_factory=dict)


IngressEnvelope = RawStreamEnvelope | SemanticUnitsEnvelope


def parse_envelope(payload: dict[str, Any]) -> IngressEnvelope:
    """Validate a canonical Tinkuy ingress envelope without extra deps."""
    if not isinstance(payload, dict):
        raise ValueError("ingress payload must be an object")
    mode = payload.get("mode")
    if mode == "raw_stream":
        return _parse_raw_stream(payload)
    if mode == "semantic_units":
        return _parse_semantic_units(payload)
    raise ValueError("mode must be 'raw_stream' or 'semantic_units'")


def envelope_to_unit_pack(envelope: SemanticUnitsEnvelope) -> UnitPack:
    """Adapt canonical semantic units to the runtime's richer UnitPack shape."""
    units: list[SemanticUnit] = []
    for raw in envelope.units:
        title = _title_from_text(raw.text)
        units.append(
            SemanticUnit(
                unit_id=raw.unit_id,
                title=title,
                abstract=raw.text,
                key_concepts=list(raw.semantic_types),
                provenance=[
                    {
                        "participant_label": raw.speaker or "",
                        "participant_name": raw.speaker or "",
                        "locator": ref,
                    }
                    for ref in raw.source_refs
                ],
            )
        )
    return UnitPack(
        units=units,
        seminar_title=str(envelope.metadata.get("title", "semantic units input")),
        cutter_id=str(envelope.metadata.get("producer", "external_semantic_units")),
        cutter_model=str(envelope.metadata.get("producer_model", "")),
        source_path=str(envelope.metadata.get("source_path", "")),
    )


def slice_raw_stream(text: str) -> list[SemanticIngressUnit]:
    """Thin-turn segmentation for raw_stream, following the Tinkuy ingress model."""
    units: list[SemanticIngressUnit] = []
    cursor = 0
    for line in text.splitlines(True):
        raw = line.rstrip("\n")
        if raw.strip():
            speaker = None
            content = raw
            if ":" in raw:
                head, tail = raw.split(":", 1)
                if 0 < len(head.strip()) <= 60:
                    speaker = head.strip()
                    content = tail.strip()
            start = cursor
            end = cursor + len(raw)
            units.append(
                SemanticIngressUnit(
                    unit_id=f"raw-{len(units) + 1}",
                    text=content,
                    speaker=speaker,
                    char_span=[start, end],
                    source_refs=[f"char:{start}-{end}"],
                    semantic_types=[],
                    metadata={},
                )
            )
        cursor += len(line)
    if not units and text.strip():
        units.append(
            SemanticIngressUnit(
                unit_id="raw-1",
                text=text.strip(),
                speaker=None,
                char_span=[0, len(text)],
                source_refs=[f"char:0-{len(text)}"],
                semantic_types=[],
                metadata={},
            )
        )
    return units


def normalise_envelope(envelope: IngressEnvelope) -> SemanticUnitsEnvelope:
    """Collapse both official ingress modes into the semantic-units lane."""
    if isinstance(envelope, SemanticUnitsEnvelope):
        return envelope
    return SemanticUnitsEnvelope(
        mode="semantic_units",
        run_id=envelope.run_id,
        units=slice_raw_stream(envelope.content),
        metadata={
            **envelope.metadata,
            "source_mode": "raw_stream",
            "speaker_hint": envelope.speaker_hint,
            "timestamp": envelope.timestamp,
        },
    )


def _parse_raw_stream(payload: dict[str, Any]) -> RawStreamEnvelope:
    _require_string(payload, "run_id")
    content = _require_string(payload, "content")
    if not content.strip():
        raise ValueError("raw_stream.content must be non-empty")
    return RawStreamEnvelope(
        mode="raw_stream",
        run_id=payload["run_id"],
        content=content,
        speaker_hint=_optional_string(payload, "speaker_hint"),
        timestamp=_optional_string(payload, "timestamp"),
        metadata=_optional_object(payload, "metadata"),
    )


def _parse_semantic_units(payload: dict[str, Any]) -> SemanticUnitsEnvelope:
    _require_string(payload, "run_id")
    units_raw = payload.get("units")
    if not isinstance(units_raw, list) or not units_raw:
        raise ValueError("semantic_units.units must be a non-empty array")
    units: list[SemanticIngressUnit] = []
    for idx, raw in enumerate(units_raw):
        if not isinstance(raw, dict):
            raise ValueError(f"semantic_units.units[{idx}] must be an object")
        unit_id = _require_string(raw, "unit_id", prefix=f"semantic_units.units[{idx}]")
        text = _require_string(raw, "text", prefix=f"semantic_units.units[{idx}]")
        units.append(
            SemanticIngressUnit(
                unit_id=unit_id,
                text=text,
                speaker=_optional_string(raw, "speaker"),
                char_span=_optional_int_pair(raw, "char_span", idx),
                source_refs=_optional_string_list(raw, "source_refs", idx),
                semantic_types=_optional_string_list(raw, "semantic_types", idx),
                metadata=_optional_object(raw, "metadata"),
            )
        )
    return SemanticUnitsEnvelope(
        mode="semantic_units",
        run_id=payload["run_id"],
        units=units,
        metadata=_optional_object(payload, "metadata"),
    )


def _title_from_text(text: str) -> str:
    line = " ".join(text.strip().splitlines()).strip()
    if not line:
        return "untitled semantic unit"
    return line[:80]


def _require_string(payload: dict[str, Any], key: str, prefix: str | None = None) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        name = f"{prefix}.{key}" if prefix else key
        raise ValueError(f"{name} must be a string")
    return value


def _optional_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string or null")
    return value


def _optional_object(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
    return value


def _optional_string_list(payload: dict[str, Any], key: str, idx: int) -> list[str]:
    value = payload.get(key)
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"semantic_units.units[{idx}].{key} must be an array of strings")
    return list(value)


def _optional_int_pair(payload: dict[str, Any], key: str, idx: int) -> list[int]:
    value = payload.get(key)
    if value is None:
        return []
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(isinstance(item, int) for item in value)
    ):
        raise ValueError(f"semantic_units.units[{idx}].{key} must be a two-item integer array")
    return list(value)

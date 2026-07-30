from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from .schemas import SemanticUnit, SourceAudit, ToulminBundle, UnitPack


@dataclass
class IngressUnit:
    unit_id: str
    text: str
    speaker: str = ""
    source_refs: list[str] = field(default_factory=list)
    semantic_types: list[str] = field(default_factory=list)
    char_span: list[int] = field(default_factory=list)


@dataclass
class RawStreamEnvelope:
    mode: str = "raw_stream"
    run_id: str = "raw-stream"
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    speaker_hint: str = ""


@dataclass
class SemanticUnitsEnvelope:
    mode: str = "semantic_units"
    run_id: str = "semantic-units"
    units: list[IngressUnit] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    seminar_title: str = ""
    cutter_id: str = ""
    cutter_model: str = ""
    source_path: str = ""
    unresolved_questions_pack: list[str] = field(default_factory=list)


def parse_envelope(payload: dict[str, Any]) -> RawStreamEnvelope | SemanticUnitsEnvelope:
    if not isinstance(payload, dict):
        raise ValueError("envelope must be an object")
    mode = str(payload.get("mode") or "").strip().lower()
    if mode in {"", "legacy_raw", "raw", "raw_stream"}:
        metadata = dict(payload.get("metadata") or {})
        speaker_hint = str(payload.get("speaker_hint") or metadata.get("speaker_hint") or "")
        return RawStreamEnvelope(
            mode="raw_stream",
            run_id=str(payload.get("run_id") or "raw-stream"),
            content=str(payload.get("content") or payload.get("text") or payload.get("raw_text") or ""),
            metadata=metadata,
            speaker_hint=speaker_hint,
        )
    if mode in {"semantic_units", "semantic-units", "units"}:
        raw_units = payload.get("units")
        if raw_units is None and isinstance(payload.get("unit_pack"), dict):
            raw_units = payload["unit_pack"].get("units")
        if not isinstance(raw_units, list):
            raise ValueError("semantic_units envelope must contain a units array")
        metadata = dict(payload.get("metadata") or {})
        title = str(payload.get("seminar_title") or payload.get("title") or metadata.get("title") or "")
        return SemanticUnitsEnvelope(
            mode="semantic_units",
            run_id=str(payload.get("run_id") or "semantic-units"),
            units=[_parse_ingress_unit(index, unit) for index, unit in enumerate(raw_units, start=1) if isinstance(unit, dict)],
            metadata=metadata,
            seminar_title=title,
            cutter_id=str(payload.get("cutter_id") or ""),
            cutter_model=str(payload.get("cutter_model") or ""),
            source_path=str(payload.get("source_path") or ""),
            unresolved_questions_pack=[str(x) for x in (payload.get("unresolved_questions_pack") or []) if x],
        )
    raise ValueError(f"unsupported envelope mode: {mode}")


def slice_raw_stream(text: str) -> list[IngressUnit]:
    content = str(text or "")
    lines = content.splitlines()
    units: list[IngressUnit] = []
    offset = 0
    pending_speaker = ""
    unit_index = 1
    for line in lines:
        raw_line = line
        line = line.rstrip("\r")
        start = offset
        end = start + len(raw_line)
        offset = end + 1
        stripped = line.strip()
        if not stripped:
            pending_speaker = ""
            continue
        speaker = pending_speaker
        text_body = stripped
        if ":" in stripped:
            head, tail = stripped.split(":", 1)
            if head.strip() and tail.strip():
                speaker = head.strip()
                text_body = tail.strip()
        if speaker:
            pending_speaker = speaker
        body_start = start
        body_end = end
        source_start = content.find(text_body, start, end + 1)
        if source_start < 0:
            source_start = start
        source_end = source_start + len(text_body)
        units.append(
            IngressUnit(
                unit_id=f"raw-{unit_index}",
                text=text_body,
                speaker=speaker,
                source_refs=[f"char:{source_start}-{source_end}"],
                semantic_types=[],
                char_span=[body_start, body_end],
            )
        )
        unit_index += 1
    return units


def normalise_envelope(
    envelope: RawStreamEnvelope | SemanticUnitsEnvelope,
) -> SemanticUnitsEnvelope:
    if isinstance(envelope, SemanticUnitsEnvelope):
        envelope.units = [unit for unit in envelope.units if isinstance(unit, IngressUnit)]
        return envelope
    metadata = dict(envelope.metadata)
    metadata["source_mode"] = "raw_stream"
    if envelope.speaker_hint:
        metadata["speaker_hint"] = envelope.speaker_hint
    return SemanticUnitsEnvelope(
        mode="semantic_units",
        run_id=envelope.run_id,
        units=slice_raw_stream(envelope.content),
        metadata=metadata,
        seminar_title=str(metadata.get("title") or title_from_text(envelope.content)),
        cutter_id="builtin.raw_stream_slicer",
        cutter_model="deterministic",
        source_path=str(metadata.get("source") or ""),
        unresolved_questions_pack=[],
    )


def envelope_to_unit_pack(
    envelope: RawStreamEnvelope | SemanticUnitsEnvelope,
) -> UnitPack:
    normalized = normalise_envelope(envelope)
    units = [_ingress_unit_to_semantic_unit(unit) for unit in normalized.units]
    return UnitPack(
        units=units,
        source_audit=SourceAudit(),
        seminar_title=normalized.seminar_title,
        cutter_id=normalized.cutter_id,
        cutter_model=normalized.cutter_model,
        source_path=normalized.source_path,
        unresolved_questions_pack=list(normalized.unresolved_questions_pack),
    )


def _parse_ingress_unit(index: int, raw: dict[str, Any]) -> IngressUnit:
    text = str(raw.get("text") or raw.get("abstract") or raw.get("title") or "").strip()
    source_refs = [str(x) for x in (raw.get("source_refs") or []) if x]
    char_span = raw.get("char_span") or _char_span_from_refs(source_refs)
    semantic_types = [str(x) for x in (raw.get("semantic_types") or raw.get("key_concepts") or []) if x]
    return IngressUnit(
        unit_id=str(raw.get("unit_id") or f"u-{index}"),
        text=text,
        speaker=str(raw.get("speaker") or ""),
        source_refs=source_refs,
        semantic_types=semantic_types,
        char_span=[int(x) for x in char_span][:2] if char_span else [],
    )


def _ingress_unit_to_semantic_unit(unit: IngressUnit) -> SemanticUnit:
    toulmin = None
    return SemanticUnit(
        unit_id=unit.unit_id,
        title=_first_sentence(unit.text) or unit.unit_id,
        intention="semantic_unit",
        object_aspect="",
        position="",
        toulmin=toulmin,
        abstract=unit.text,
        key_concepts=list(unit.semantic_types or _key_concepts(unit.text))[:12],
        provenance=[{"locator": ref, "speaker": unit.speaker} for ref in unit.source_refs],
        unresolved_questions_here=_extract_questions(unit.text),
    )


def _char_span_from_refs(source_refs: list[str]) -> list[int]:
    if not source_refs:
        return []
    match = re.match(r"char:(\d+)-(\d+)", source_refs[0])
    if not match:
        return []
    return [int(match.group(1)), int(match.group(2))]


def _first_sentence(text: str) -> str:
    for chunk in re.split(r"(?<=[\.\!\?])\s+", text.strip()):
        chunk = chunk.strip(" -\t\r\n")
        if len(chunk) >= 12:
            return chunk
    return text.strip().splitlines()[0].strip() if text.strip() else ""


def title_from_text(text: str) -> str:
    return (_first_sentence(text) or "Raw stream input")[:160]


def _key_concepts(text: str) -> list[str]:
    words = re.findall(r"[A-Za-zА-Яа-яЁё]{4,}", text.lower())
    stop = {
        "это", "того", "только", "когда", "после", "между", "потому", "который",
        "which", "there", "about", "would", "could", "should",
    }
    seen: list[str] = []
    for word in words:
        if word in stop or word in seen:
            continue
        seen.append(word)
        if len(seen) >= 12:
            break
    return seen


def _extract_questions(text: str) -> list[str]:
    questions = []
    for part in re.split(r"(?<=\?)\s+", text):
        part = part.strip()
        if "?" in part and len(part) >= 10:
            questions.append(part[:220])
        if len(questions) >= 6:
            break
    return questions

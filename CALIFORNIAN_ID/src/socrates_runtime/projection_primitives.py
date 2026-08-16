"""Generic projection primitives — ADR-S26-023 substrate.

The current existing substrate contains *application-level* cutters:

    * ``californian_id.adapters.units_of_content_md.parser`` —
      parses a specific md-units document format;
    * ``californian_id.adapters.text_chunker`` — deterministic
      chunker for a specific unit-pack shape;
    * ``californian_id.fabric.parser.FabricParser`` — canon-014
      fabric snapshot builder;
    * the two marker-scan capabilities in
      :mod:`socrates_runtime.cutter_registry` (concept + differentiated).

None of these are neutral, parameterised primitives suitable for
arbitrary CutterSpec composition — each is a whole capability with a
fixed interpretation. To honestly satisfy ADR-S26-023 Test A
(``NOVEL_PROJECTION_SYNTHESIS`` — synthesise a spec, compile-bind it
against existing primitives, physically execute), we introduce a small
substrate here.

Each primitive:

    * has a stable ``id`` used in :class:`PrimitiveInvocation.primitive_id`;
    * takes typed declarative params at construction;
    * exposes a single ``apply`` method whose input/output types are
      part of the primitive's contract;
    * is stateless past construction (safe to reuse across projections).

Kept intentionally small (four primitives). Adding more is trivial —
register a new class in :func:`build_default_primitive_registry`. The
class of things these primitives can compose is exactly what the
compile-bind step will accept as a valid synthesis.

The design goal: SpanScanner + FamilyClassifier + TargetFilter +
CoverageComputer is enough to synthesise a genuinely NEW pattern-based
cutter (Test A) without hard-coding — and clearly INSUFFICIENT for
operations that need higher-order structure such as narrative-arc
detection (Test B → :class:`OrganGap`).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------- typed I/O


@dataclass(frozen=True)
class LabeledSpan:
    """One labelled span in a source text.

    ``label`` is whatever the primitive that produced this span
    extracted (a regex group, a category name). ``body`` is the raw
    text at ``[start, end)``. Downstream primitives can further
    categorise or filter on ``label``.
    """
    label: str
    body: str
    start: int
    end: int


@dataclass(frozen=True)
class ClassifiedSpan:
    """A LabeledSpan mapped through a :class:`FamilyClassifier`.

    ``family`` is the abstract object-family the span was resolved
    into (e.g. ``concept``, ``priority_high``). ``raw_label`` retains
    the source label for provenance.
    """
    family: str
    raw_label: str
    body: str
    start: int
    end: int


# ---------------------------------------------------------- primitives


class SpanScanner:
    """Generic: scan a source text for a regex; return LabeledSpans.

    The pattern is parameterized (any regex with a labelled group).
    This is the substrate on which pattern-based extractors are built —
    the concept-marker and priority-tag examples both compile to the
    same primitive, differing only in the ``pattern`` param.
    """
    id: str = "SpanScanner"

    def __init__(self, pattern: str, flags: int = 0,
                 label_group: str = "label",
                 body_group: str = "body") -> None:
        self.pattern = pattern
        self.regex = re.compile(pattern, flags)
        self.label_group = label_group
        self.body_group = body_group

    def apply(self, source_text: str) -> list[LabeledSpan]:
        out: list[LabeledSpan] = []
        for m in self.regex.finditer(source_text or ""):
            label = m.group(self.label_group)
            body = m.group(self.body_group) if self.body_group in m.groupdict() \
                else m.group(0)
            out.append(LabeledSpan(label=str(label or "").lower().strip(),
                                   body=str(body or "").strip(),
                                   start=m.start(), end=m.end()))
        return out

    def contract(self) -> dict[str, Any]:
        """Public typed description of what this primitive does."""
        return {
            "id": self.id,
            "input": "str (source_text)",
            "output": "list[LabeledSpan]",
            "params": {"pattern": self.pattern,
                       "label_group": self.label_group,
                       "body_group": self.body_group}}


class FamilyClassifier:
    """Generic: LabeledSpan → ClassifiedSpan via an explicit mapping.

    ``family_map`` maps raw label → family name. Labels not in the map
    are passed through unmapped, with family == raw_label.lower().

    Case-neutral by default — real work happens at the map level, not
    inside the primitive. Composable with SpanScanner.
    """
    id: str = "FamilyClassifier"

    def __init__(self, family_map: dict[str, str] | None = None,
                 case_insensitive: bool = True) -> None:
        self.family_map = {
            (k.lower() if case_insensitive else k): v
            for k, v in (family_map or {}).items()}
        self.case_insensitive = case_insensitive

    def apply(self, spans: list[LabeledSpan]) -> list[ClassifiedSpan]:
        out: list[ClassifiedSpan] = []
        for s in spans:
            key = s.label.lower() if self.case_insensitive else s.label
            family = self.family_map.get(key, s.label)
            out.append(ClassifiedSpan(family=family, raw_label=s.label,
                                      body=s.body, start=s.start, end=s.end))
        return out

    def contract(self) -> dict[str, Any]:
        return {"id": self.id, "input": "list[LabeledSpan]",
                "output": "list[ClassifiedSpan]",
                "params": {"family_map": dict(self.family_map),
                           "case_insensitive": self.case_insensitive}}


class TargetFilter:
    """Generic: split ClassifiedSpans into (accepted, residue) by target family.

    ``target_family`` is the set of families the caller wants as
    accepted objects. Everything else is residue — a first-class
    return, not swept under the rug. Composable with FamilyClassifier.
    """
    id: str = "TargetFilter"

    def __init__(self, target_family: tuple[str, ...]) -> None:
        self.target_family = tuple(target_family)
        self._target_set = {t.lower() for t in target_family}

    def apply(self,
              classified: list[ClassifiedSpan],
              ) -> tuple[list[ClassifiedSpan], list[ClassifiedSpan]]:
        accepted: list[ClassifiedSpan] = []
        residue: list[ClassifiedSpan] = []
        for c in classified:
            (accepted if c.family.lower() in self._target_set
             else residue).append(c)
        return accepted, residue

    def contract(self) -> dict[str, Any]:
        return {"id": self.id, "input": "list[ClassifiedSpan]",
                "output": "tuple[list[ClassifiedSpan], list[ClassifiedSpan]]",
                "params": {"target_family": list(self.target_family)}}


class CoverageComputer:
    """Generic: (accepted, residue) → coverage fraction.

    Small enough to inline, but kept a first-class primitive so the
    composition-graph is uniform (every step is a registered primitive)
    and the trace shows an explicit coverage-computation step.
    """
    id: str = "CoverageComputer"

    def __init__(self) -> None:
        pass

    def apply(self, split: tuple[list, list]) -> float:
        accepted, residue = split
        total = max(len(accepted) + len(residue), 1)
        return len(accepted) / total

    def contract(self) -> dict[str, Any]:
        return {"id": self.id,
                "input": "tuple[list, list]", "output": "float",
                "params": {}}


# ---------------------------------------------------------- registry


class PrimitiveRegistry:
    """Register + resolve primitive CLASSES by ``primitive_id``.

    Distinct from :class:`CutterRegistry`, which registers whole
    application-level cutters. Primitives are stateless-past-construction
    building blocks used by the compile-bind step; each invocation of
    a primitive constructs a fresh instance from typed params.

    A synthesised spec that names a primitive_id not in the registry
    is a bind failure — the ONLY honest place to fail: not with a
    silent fallback to the "nearest" primitive, not with a fabricated
    result.
    """

    def __init__(self) -> None:
        self._classes: dict[str, type] = {}

    def register(self, cls: type) -> None:
        pid = getattr(cls, "id", None)
        if not pid:
            raise ValueError(f"primitive class {cls!r} lacks a public `id` "
                             f"attribute — cannot register")
        self._classes[pid] = cls

    def get(self, primitive_id: str) -> type | None:
        return self._classes.get(primitive_id)

    def has(self, primitive_id: str) -> bool:
        return primitive_id in self._classes

    def known(self) -> tuple[str, ...]:
        return tuple(sorted(self._classes))

    def contract(self) -> dict[str, list[str]]:
        return {"known_primitives": list(self.known())}


def build_default_primitive_registry() -> PrimitiveRegistry:
    """Ship the minimal primitive set for ADR-S26-023 Test A.

    Four primitives is enough to synthesise arbitrary pattern-based
    cutters (SpanScanner→FamilyClassifier→TargetFilter→CoverageComputer).
    It is NOT enough to synthesise higher-order operations like
    sequence-order analysis or narrative-arc detection — Test B
    exercises that limit and emits :class:`OrganGap`.
    """
    reg = PrimitiveRegistry()
    reg.register(SpanScanner)
    reg.register(FamilyClassifier)
    reg.register(TargetFilter)
    reg.register(CoverageComputer)
    return reg


__all__ = [
    "ClassifiedSpan", "CoverageComputer", "FamilyClassifier",
    "LabeledSpan", "PrimitiveRegistry", "SpanScanner", "TargetFilter",
    "build_default_primitive_registry",
]

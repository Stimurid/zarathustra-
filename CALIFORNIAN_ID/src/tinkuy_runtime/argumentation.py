"""`argumentation.project` — the native argumentation seam.

The projector already exists and already runs in production: it is
``californian_id.pipeline._fabric_snapshot_to_unit_pack``, which turns a real
FabricSnapshot into Toulmin structure using the fabric's own relation types
(``intention=claim → claim``, ``intention=assumption → warrant``,
``FabricRelation(contradicts|avoids) → rebuttal``).

It is private only by naming accident, not by design — the pipeline calls it on
every raw-text run. This module publishes it as a named seam and adds nothing:
no scoring, no new relation semantics, no argument ontology of its own.

The organ has a second half that the first inventory pass missed and this
docstring records rather than hides: ``ArgumentMap`` on ``RunState`` is a live
accumulated argument graph — claims, assumptions, values, supports, attacks,
actions, questions, unresolved conflicts — folded per turn by
``pipeline._fold_turn_into_argument_map``, seeded from unit packs by
``_seed_argument_map_from_pack``, read by ``assess_turn``, by synthesis and by
the anti-slop check, and exported by the CLI. It is real, and it runs on every
council loop.

What remains genuinely absent, and is reported as a gap rather than improvised:
    * a standalone persistent argument store (the graph lives on RunState and
      in the RunTrace, not in its own database),
    * first-class ``Ground`` / ``Undercutter`` objects — grounds appear as
      Toulmin ``data``; undercutters have no representation at all.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .identity import BindingResult, identify

ORGAN = "argumentation"


@dataclass
class ProjectedArgument:
    """One argument as the runtime actually models it."""
    unit_id: str
    title: str
    claim: str = ""
    data: str = ""          # grounds
    warrant: str = ""
    backing: str = ""
    qualifier: str = ""
    rebuttal: str = ""
    counterclaim: str = ""
    speakers: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def complete(self) -> bool:
        """Toulmin-complete in the minimal sense: a claim standing on grounds."""
        return bool(self.claim and (self.data or self.warrant))


@dataclass
class ArgumentProjection:
    source_snapshot_id: str
    arguments: list[ProjectedArgument] = field(default_factory=list)
    units_without_argument: list[str] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        return {
            "arguments": len(self.arguments),
            "with_claim": sum(1 for a in self.arguments if a.claim),
            "with_warrant": sum(1 for a in self.arguments if a.warrant),
            "with_rebuttal": sum(1 for a in self.arguments if a.rebuttal),
            "toulmin_complete": sum(1 for a in self.arguments if a.complete),
            "units_without_argument": len(self.units_without_argument),
        }


def project(snapshot: Any) -> BindingResult:
    """`argumentation.project` — real fabric in, real Toulmin structure out.

    The projection itself is performed by the production function; this wrapper
    only reshapes its ``UnitPack`` into the argument-facing view and records who
    actually did the work.
    """
    from californian_id.pipeline import _fabric_snapshot_to_unit_pack

    ident = identify(ORGAN, _fabric_snapshot_to_unit_pack)

    if snapshot is None:
        return BindingResult(ORGAN, "argumentation.project", False,
                             reason="нет снимка ткани для проекции",
                             identity=ident)

    pack = _fabric_snapshot_to_unit_pack(snapshot)
    units = list(getattr(pack, "units", []) or [])
    if not units:
        return BindingResult(
            ORGAN, "argumentation.project", False,
            reason="проектор отработал, но снимок не дал ни одной единицы — "
                   "аргументной структуры в этом снимке нет",
            identity=ident,
            provenance={"snapshot_id": getattr(snapshot, "snapshot_id", "")})

    arguments: list[ProjectedArgument] = []
    without: list[str] = []
    for u in units:
        t = getattr(u, "toulmin", None)
        uid = getattr(u, "unit_id", "")
        if t is None:
            without.append(uid)
            continue
        arguments.append(ProjectedArgument(
            unit_id=uid,
            title=getattr(u, "title", "") or "",
            claim=t.claim, data=t.data, warrant=t.warrant, backing=t.backing,
            qualifier=t.qualifier, rebuttal=t.rebuttal,
            counterclaim=t.counterclaim,
            speakers=[p.label for p in (getattr(u, "participants", []) or [])],
            provenance=dict(getattr(getattr(u, "provenance", None), "__dict__", {}) or {}),
        ))

    projection = ArgumentProjection(
        source_snapshot_id=getattr(snapshot, "snapshot_id", ""),
        arguments=arguments, units_without_argument=without)

    return BindingResult(
        ORGAN, "argumentation.project", True, value=projection, identity=ident,
        provenance={"snapshot_id": projection.source_snapshot_id,
                    "counts": projection.counts(),
                    "projector": ident.qualname})


def assess_turn(turn: Any, prior_turns: list[Any], argument_map: Any) -> BindingResult:
    """`argumentation.assess_turn` — deterministic per-turn dispute assessment.

    Distinct from ``project`` on purpose: turn assessment is not an argument
    graph, and conflating them would let a working half stand in for a whole.
    """
    from californian_id.argumentation import assess_turn as _assess

    ident = identify(ORGAN, _assess)
    try:
        verdict = _assess(turn, prior_turns, argument_map)
    except TypeError as exc:
        return BindingResult(ORGAN, "argumentation.assess_turn", False,
                             reason=f"несовместимый вызов: {exc}", identity=ident)
    return BindingResult(
        ORGAN, "argumentation.assess_turn", True, value=verdict, identity=ident,
        provenance={"dispute_mode": verdict.dispute_mode,
                    "thesis_preserved": verdict.thesis_preserved,
                    "fallacies": list(verdict.fallacies_or_tricks),
                    "continue_or_stop": verdict.continue_or_stop})


def fold_turn(turn: Any, argument_map: Any) -> BindingResult:
    """`argumentation.fold_turn` — accumulate one turn into the live graph.

    This is the call that actually maintains the argument graph during a run.
    Publishing it makes the graph reachable from outside the pipeline without
    anyone having to rebuild it.
    """
    from californian_id.pipeline import _fold_turn_into_argument_map

    ident = identify(ORGAN, _fold_turn_into_argument_map)
    before = _map_counts(argument_map)
    _fold_turn_into_argument_map(turn, argument_map)
    after = _map_counts(argument_map)
    return BindingResult(
        ORGAN, "argumentation.fold_turn", True, value=argument_map, identity=ident,
        provenance={"before": before, "after": after,
                    "delta": {k: after[k] - before[k] for k in after}})


def _map_counts(m: Any) -> dict[str, int]:
    return {name: len(getattr(m, name, []) or [])
            for name in ("claims", "assumptions", "values", "supports", "attacks",
                         "actions", "questions", "unresolved_conflicts")}


def map_of(argument_map: Any) -> BindingResult:
    """`argumentation.map_of` — read the live argument graph as a typed object.

    Returned as-is: it is ``californian_id.schemas.ArgumentMap``, the same
    object the council loop maintains, not a copy shaped by this module.
    """
    from californian_id.schemas import ArgumentMap

    ident = identify(ORGAN, ArgumentMap)
    if argument_map is None:
        return BindingResult(ORGAN, "argumentation.map_of", False,
                             reason="нет графа аргументации", identity=ident)
    if not isinstance(argument_map, ArgumentMap):
        return BindingResult(
            ORGAN, "argumentation.map_of", False,
            reason=f"это не ArgumentMap, а {type(argument_map).__name__}",
            identity=ident)
    return BindingResult(ORGAN, "argumentation.map_of", True, value=argument_map,
                         identity=ident, provenance=_map_counts(argument_map))

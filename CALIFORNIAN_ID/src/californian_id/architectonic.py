"""Architectonic turn reconstruction — incremental delta after each turn.

Deterministic fallback: without an LLM, produce a typed delta from the
TurnRecord itself. With a real provider, use the prompt module
`zarathustra/prompt_modules/architectonic_turn_reconstruction.md`.

This module never overwrites BodyProjection — it PROPOSES a delta.
The caller applies it if valid.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .schemas import BodyProjection, TurnRecord, to_plain


@dataclass
class TurnDelta:
    """Typed delta returned by architectonic reconstruction.

    All lists default empty. `provenance` is populated with the turn's
    own attribution.
    """
    new_claims: list[dict] = field(default_factory=list)
    revised_claims: list[dict] = field(default_factory=list)
    withdrawn_claims: list[dict] = field(default_factory=list)
    attacked_claims: list[dict] = field(default_factory=list)
    new_supports: list[dict] = field(default_factory=list)
    new_attacks: list[dict] = field(default_factory=list)
    assumptions_exposed: list[dict] = field(default_factory=list)
    concepts_introduced: list[dict] = field(default_factory=list)
    concept_meanings_changed: list[dict] = field(default_factory=list)
    values_activated: list[dict] = field(default_factory=list)
    ontology_shifts: list[dict] = field(default_factory=list)
    position_changes: list[dict] = field(default_factory=list)
    risks: list[dict] = field(default_factory=list)
    projects: list[dict] = field(default_factory=list)
    futures: list[dict] = field(default_factory=list)
    unresolved_questions: list[dict] = field(default_factory=list)
    breaks: list[dict] = field(default_factory=list)
    loops: list[dict] = field(default_factory=list)
    returns: list[dict] = field(default_factory=list)
    false_closures: list[dict] = field(default_factory=list)
    state_delta: dict = field(default_factory=dict)
    provenance: dict = field(default_factory=dict)


def reconstruct_turn_delta(
    current_body: BodyProjection,
    previous_turn: TurnRecord | None,
    new_turn: TurnRecord,
    source_context: dict | None = None,
) -> TurnDelta:
    """Deterministic reconstruction.

    Maps operation semantics of the new turn into typed delta entries.
    Does NOT modify current_body.
    """
    d = TurnDelta()
    op = new_turn.operation
    pid = new_turn.persona_id
    prov_sources: list[dict] = []
    for e in (source_context or {}).get("evidence", []) or []:
        prov_sources.append({
            "source_id": getattr(e, "source_id", "?"),
            "locator": getattr(e, "locator", "?"),
        })
    for card in (source_context or {}).get("cultural_cards", []) or []:
        prov_sources.append({
            "source_id": card.get("card_id", "?"),
            "locator": card.get("card_type", "card"),
        })
    d.provenance = {
        "turn_persona": pid,
        "turn_operation": op,
        "sources": prov_sources,
    }

    # Type each turn.claims as either source_fact/inference/hypothesis/proposal
    for c in new_turn.claims:
        kind = _guess_claim_kind(op)
        d.new_claims.append({
            "text": c.text,
            "kind": kind,
            "confidence": c.confidence,
            "persona_id": pid,
        })

    for a in new_turn.assumptions:
        d.assumptions_exposed.append({
            "text": a.text,
            "exposed_by": pid,
        })

    for atk in new_turn.attacks:
        entry = {
            "target": atk.target,
            "text": atk.text,
            "attack_type": _attack_type_for(op),
            "attacker": pid,
        }
        d.new_attacks.append(entry)
        d.attacked_claims.append({
            "target_id_or_text": atk.target,
            "attack_type": entry["attack_type"],
            "attacker": pid,
        })

    for sup in new_turn.supports:
        d.new_supports.append({
            "target": sup.target,
            "text": sup.text,
            "persona_id": pid,
        })

    for v in new_turn.values:
        d.values_activated.append({"text": v.text, "activated_by": pid})

    for act in new_turn.actions:
        d.projects.append({"action": act.text, "proposed_by": pid})

    for q in new_turn.questions:
        if q.unresolved:
            d.unresolved_questions.append({"text": q.text, "raised_by": pid})

    # Operation-specific
    if op == "build_future_image":
        d.futures.append({
            "utterance": new_turn.utterance,
            "horizon": "unspecified",
            "persona_id": pid,
        })
    elif op == "show_cost":
        d.risks.append({"text": new_turn.utterance, "named_by": pid})
    elif op == "shift_ontology":
        d.ontology_shifts.append({
            "from": current_body.topic,
            "to": new_turn.utterance[:180],
            "performed_by": pid,
        })
    elif op == "shift_temporal_horizon":
        d.futures.append({
            "utterance": new_turn.utterance,
            "horizon": "long-term-shifted",
            "persona_id": pid,
        })
    elif op in {"create_aporia", "problematize_question"}:
        d.false_closures.append({
            "claimed_closure": current_body.topic,
            "why_false": new_turn.utterance[:200],
            "raised_by": pid,
        })
    elif op == "dispute_completion_form":
        d.breaks.append({
            "kind": "dispute_form",
            "text": new_turn.utterance[:200],
            "by": pid,
        })

    # Loop detection: same persona same operation twice in a row
    if previous_turn and previous_turn.persona_id == pid and previous_turn.operation == op:
        d.loops.append({
            "pattern": f"{pid}:{op}",
            "count": 2,
        })

    # Position change: previous turn defended, this turn attacks (very simple heuristic)
    if previous_turn and previous_turn.persona_id == pid and \
            previous_turn.operation == "defend" and op in {"attack", "attack_presupposition"}:
        d.position_changes.append({
            "persona_id": pid,
            "from": "defend",
            "to": op,
        })

    d.state_delta = {
        "summary_one_line": f"[{pid} {op}] {new_turn.utterance[:120]}",
        "op": op,
        "attacked": [a["target_id_or_text"] for a in d.attacked_claims],
        "new_futures": len(d.futures),
        "new_risks": len(d.risks),
        "new_premises": len(d.assumptions_exposed),
    }
    return d


def _guess_claim_kind(op: str) -> str:
    if op in {"initial_position", "defend", "restore_ground"}:
        return "proposal"
    if op in {"attack", "attack_presupposition", "test_value"}:
        return "conflict"
    if op in {"draw_practical_implication", "propose_alliance"}:
        return "proposal"
    if op in {"build_future_image", "build_counterexample", "shift_temporal_horizon"}:
        return "hypothesis"
    if op in {"problematize_question", "create_aporia"}:
        return "question_to_human"
    if op == "show_cost":
        return "inference"
    return "inference"


def _attack_type_for(op: str) -> str:
    return {
        "attack_presupposition": "conceptual",
        "attack": "logical",
        "test_value": "value",
        "steelman_opponent": "logical",
        "build_counterexample": "empirical",
    }.get(op, "logical")


def apply_delta_to_body(body: BodyProjection, delta: TurnDelta) -> None:
    """Optional: fold reconstructed delta into body. Currently the pipeline
    also folds via `_fold_turn_into_body` — this function is for consumers
    that want to work at the typed-delta level."""
    for f in delta.futures:
        from .schemas import FutureImage
        body.futures.append(FutureImage(
            persona_id=f.get("persona_id", "?"),
            utterance=f.get("utterance", ""),
            horizon=f.get("horizon", "unspecified"),
        ))
    for r in delta.risks:
        from .schemas import RiskItem
        body.risks.append(RiskItem(
            named_by=r.get("named_by", "?"),
            text=r.get("text", ""),
        ))
    for a in delta.assumptions_exposed:
        from .schemas import OntologicalPremise
        body.ontological_premises.append(OntologicalPremise(
            exposed_by=a.get("exposed_by", "?"),
            text=a.get("text", ""),
        ))

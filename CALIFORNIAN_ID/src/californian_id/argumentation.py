"""Argumentation runtime.

Deterministic dispute assessment + fallacy/trick detection + anti-slop gate.
Uses canonical Povarnin-derived rules from ../argumentation/*.yaml.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .schemas import ArgumentMap, TurnRecord


# --- Typed claim taxonomy (from DONOR_BOBROV common_agent_runtime_contract) ---
TYPED_CLAIM_KINDS = (
    "source_fact",
    "inference",
    "hypothesis",
    "conflict",
    "gap",
    "question_to_human",
    "proposal",
    "applied_change",
)


@dataclass
class DisputeAssessment:
    dispute_mode: str = "truth"
    thesis_preserved: bool = True
    thesis_snapshot: str = ""
    burden_state: dict[str, Any] = field(default_factory=dict)
    valid_attack: bool = True
    valid_defence: bool = True
    fallacies_or_tricks: list[str] = field(default_factory=list)
    fairness_events: list[str] = field(default_factory=list)
    required_response_type: str = "any"
    continue_or_stop: str = "continue"
    confidence: float = 0.7
    notes: str = ""


# ---------------- helpers ----------------
_AUTHORITY_MARKERS = ("all voices", "everyone agrees", "все согласны",
                       "большинство", "the experts say", "very obviously")


def _jaccard(a: str, b: str) -> float:
    tokens_a = {t for t in re.split(r"\W+", (a or "").lower()) if len(t) > 3}
    tokens_b = {t for t in re.split(r"\W+", (b or "").lower()) if len(t) > 3}
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


# ---------------- detection ----------------
def detect_thesis_substitution(turns: list[TurnRecord]) -> tuple[bool, str]:
    """Return (substituted?, reason)."""
    if len(turns) < 2:
        return False, "not_enough_turns"
    initial = next((t for t in turns if t.operation in {"initial_position", "restore_ground"}), None)
    if initial is None:
        return False, "no_initial_position"
    # Any explicit shift ops legitimize a change
    shift_ops = {t for t in ("shift_ontology", "problematize_question") if any(x.operation == t for x in turns)}
    if shift_ops:
        return False, "legitimate_shift_present"
    # Check last attack against initial thesis
    last_attack = next((t for t in reversed(turns) if t.attacks), None)
    if last_attack is None:
        return False, "no_attack_present"
    initial_text = initial.utterance or ""
    for atk in last_attack.attacks:
        sim = _jaccard(initial_text, atk.text)
        if sim < 0.05:
            return True, f"attack '{atk.text[:80]}' has low overlap with initial thesis (jaccard={sim:.2f})"
    return False, "attacks_align_with_thesis"


def detect_fallacy_or_trick(turn: TurnRecord, prior_turns: list[TurnRecord]) -> list[str]:
    hits: list[str] = []
    text = (turn.utterance or "").lower()

    # ad_hominem
    if any(k in text for k in ("глуп", "невеж", "you are stupid", "лжец", "ты не понимаешь")):
        hits.append("ad_hominem")

    # appeal_to_majority
    if any(k in text for k in _AUTHORITY_MARKERS):
        hits.append("appeal_to_majority")

    # false_dichotomy (crude heuristic)
    if re.search(r"либо .* либо .* и другого не дано|either .* or .* and nothing else", text):
        hits.append("false_dichotomy")

    # straw_man: attack target text uses concepts not in prior discussion
    if turn.attacks:
        prior_concept_bag = set()
        for t in prior_turns:
            prior_concept_bag |= {w for w in re.split(r"\W+", (t.utterance or "").lower()) if len(w) > 4}
        for atk in turn.attacks:
            atk_concepts = {w for w in re.split(r"\W+", (atk.text or "").lower()) if len(w) > 4}
            if atk_concepts and not (atk_concepts & prior_concept_bag):
                hits.append("straw_man")
                break

    # proof_by_assertion: same persona same utterance repeated
    same_persona_prior = [t for t in prior_turns if t.persona_id == turn.persona_id]
    for prior in same_persona_prior[-3:]:
        if _jaccard(prior.utterance, turn.utterance) > 0.75:
            hits.append("proof_by_assertion")
            break

    # motte_and_bailey (very crude): current is defend but previous was strong claim
    if turn.operation == "defend" and same_persona_prior:
        prior = same_persona_prior[-1]
        if prior.operation == "initial_position" and len(turn.utterance) < 0.6 * len(prior.utterance):
            hits.append("motte_and_bailey")

    return sorted(set(hits))


def infer_dispute_mode(turns: list[TurnRecord]) -> str:
    hostile = sum(1 for t in turns if t.operation in {"attack", "attack_presupposition"})
    reflective = sum(1 for t in turns if t.operation in {"restore_ground", "test_value", "steelman_opponent"})
    audience_markers = sum(
        1 for t in turns
        if any(k in (t.utterance or "").lower() for k in ("audience", "аудитор", "публично"))
    )
    if audience_markers >= 1:
        return "persuasion"
    if hostile > 0 and reflective == 0 and hostile > len(turns) // 2:
        return "victory"
    return "truth"


def assess_turn(
    turn: TurnRecord,
    prior_turns: list[TurnRecord],
    argument_map: ArgumentMap,
) -> DisputeAssessment:
    a = DisputeAssessment()
    all_turns = prior_turns + [turn]

    a.dispute_mode = infer_dispute_mode(all_turns)

    # Thesis
    substituted, reason = detect_thesis_substitution(all_turns)
    a.thesis_preserved = not substituted
    initial = next((t for t in all_turns if t.operation in {"initial_position", "restore_ground"}), None)
    a.thesis_snapshot = initial.utterance[:200] if initial else ""

    # Burden
    if initial:
        a.burden_state = {
            "who_carries_burden": initial.persona_id,
            "whether_shifted": any(t.operation == "propose_alliance" for t in all_turns),
            "shift_reason": "alliance_proposal" if any(t.operation == "propose_alliance" for t in all_turns) else "",
        }

    # Attack/defence validity
    a.valid_attack = all(bool(atk.target) for atk in turn.attacks)
    a.valid_defence = all(bool(sup.target) for sup in turn.supports)

    # Fallacies
    a.fallacies_or_tricks = detect_fallacy_or_trick(turn, prior_turns)

    # Fairness
    if turn.operation in {"draw_practical_implication", "propose_alliance"} and \
            any(t.operation == "attack" for t in prior_turns[-2:]) and not turn.supports:
        a.fairness_events.append("closure_without_engagement")
    if not a.thesis_preserved:
        a.fairness_events.append("thesis_shift_without_explicit_operation")
    if "appeal_to_majority" in a.fallacies_or_tricks:
        a.fairness_events.append("authority_substitution")

    # Required response
    if not a.thesis_preserved:
        a.required_response_type = "restore_ground"
    elif "straw_man" in a.fallacies_or_tricks:
        a.required_response_type = "restore_ground"
    elif "proof_by_assertion" in a.fallacies_or_tricks:
        a.required_response_type = "stop"
    else:
        a.required_response_type = "any"

    # Continue/stop
    high_severity = {"straw_man", "proof_by_assertion", "motte_and_bailey"}
    if any(h in high_severity for h in a.fallacies_or_tricks):
        a.continue_or_stop = "stop"

    a.confidence = 0.6 if a.fallacies_or_tricks else 0.8
    a.notes = reason
    return a


# ------------------ Anti-slop gate ------------------
@dataclass
class AntiSlopVerdict:
    passes_anti_slop: bool
    detected_slop_signals: list[str] = field(default_factory=list)
    suggested_alternative_form: str | None = None


def check_anti_slop(
    candidate_form: str,
    turns: list[TurnRecord],
    argument_map: ArgumentMap,
) -> AntiSlopVerdict:
    """Blocks synthesis when the council did not do the actual work.

    Rule: synthesis requires at least one attack_presupposition AND at least
    one defend on the trace. Otherwise proposes polyphony or
    decision_with_dissent (whichever fits).
    """
    if candidate_form != "synthesis":
        return AntiSlopVerdict(passes_anti_slop=True)
    ops = {t.operation for t in turns}
    signals: list[str] = []
    if "attack_presupposition" not in ops and "attack" not in ops:
        signals.append("no_presupposition_attack")
    if "defend" not in ops:
        signals.append("no_defence")
    if len({t.persona_id for t in turns}) < 3:
        signals.append("fewer_than_three_distinct_voices")
    if signals:
        alt = "decision_with_dissent" if "defend" in ops else "polyphony"
        return AntiSlopVerdict(
            passes_anti_slop=False,
            detected_slop_signals=signals,
            suggested_alternative_form=alt,
        )
    return AntiSlopVerdict(passes_anti_slop=True)

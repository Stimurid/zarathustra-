"""B2Q — proportional Socratic question topology.

**Not a persona.** **Not a second Socrates identity.** **Not a
question ontology.**

`QuestionSetPlan` is a narrow typed post-terminal object that
governs the shape of a returned question set when the caller
explicitly opts in via a `question_set_request` control field on
the API. The plan reads Scene/Telos/Operation/Ownership from
state, honours a caller-supplied topology hint (list of material
forks/unknowns + optional typed subordinates), applies the level-
coherence + explicit-count rules from §3, and produces a
deterministic list of `QuestionCandidate` records that becomes
the returned response text via :func:`render_plan_as_text`.

Central rule:

    QUESTION SET SHAPE = f(Scene, Telos, Operation, material fork
                           topology, level coherence, coverage)
    Count is DERIVED when no explicit N;
    Explicit N is form authority but NEVER content authority.

Hard invariants (public + test-enforced):

    * ``AUTHORITY = "NO_TRUTH_STATUS_AUTHORITY"``
    * Explicit activation only: only the typed request field
      activates the plan; lexical mentions in user text CANNOT.
    * Never fabricates peer forks to reach N; only real
      topology-derived peers plus explicitly typed subordinates
      count.
    * Meta escalation legitimate only when
      ``request.intent == "meta"`` OR the S4 operation.kind
      itself is unambiguously META*. Lexical bait (Socrates,
      Alcibiades, mimesis in text) does NOT escalate.
    * Ownership is sovereign: the plan reads
      ``state.ownership`` and records the ownership state in
      ``stop_reason_grounds`` but cannot bind a HUMAN-owned
      choice — plans produce question TEXT only, not decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


AUTHORITY: str = "NO_TRUTH_STATUS_AUTHORITY"
_DEFAULT_BUDGET_CEILING: int = 12


# =========================================================== enums


class QuestionRegime(str, Enum):
    DECISION_SEPARATING = "DECISION_SEPARATING"
    DIAGNOSTIC = "DIAGNOSTIC"
    FALSIFICATION_OR_COUNTEREXAMPLE = "FALSIFICATION_OR_COUNTEREXAMPLE"
    SOURCE_OR_ATTRIBUTION = "SOURCE_OR_ATTRIBUTION"
    GENERATIVE = "GENERATIVE"
    REFLECTIVE_OR_META = "REFLECTIVE_OR_META"


class HierarchyPolicy(str, Enum):
    PRIMARY_ONLY = "PRIMARY_ONLY"
    PRIMARY_PLUS_TYPED_SUBORDINATE = "PRIMARY_PLUS_TYPED_SUBORDINATE"


class StopReason(str, Enum):
    COVERAGE_SATURATED = "COVERAGE_SATURATED"
    EXPLICIT_COUNT_MET = "EXPLICIT_COUNT_MET"
    EXPLICIT_COUNT_UNDER_PEERS = "EXPLICIT_COUNT_UNDER_PEERS"
    EXPLICIT_COUNT_EXCEEDS_PEERS = "EXPLICIT_COUNT_EXCEEDS_PEERS"
    NO_TOPOLOGY = "NO_TOPOLOGY"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"


class MetaEscalation(str, Enum):
    NONE = "NONE"
    LEGITIMATE = "LEGITIMATE"
    DECLINED_LEXICAL = "DECLINED_LEXICAL"


# =========================================================== dataclasses


@dataclass(frozen=True)
class QuestionCandidate:
    text: str
    regime: str
    fork_ref: str = ""
    parent_fork_ref: str = ""
    is_subordinate: bool = False
    #: "MODEL_MATERIAL" — text came from the model's candidate_question
    #: for a validated proposal (B2Q-R). "TEMPLATE_FALLBACK" — the
    #: deterministic template phrasing was used because no material
    #: was available. Public so a trace reader can verify closure of
    #: D-S26-QSEL-002 case-by-case.
    text_source: str = "TEMPLATE_FALLBACK"
    material_refs: tuple[str, ...] = ()

    def to_public(self) -> dict[str, Any]:
        return {
            "text": self.text, "regime": self.regime,
            "fork_ref": self.fork_ref,
            "parent_fork_ref": self.parent_fork_ref,
            "is_subordinate": self.is_subordinate,
            "text_source": self.text_source,
            "material_refs": list(self.material_refs),
        }


@dataclass(frozen=True)
class QuestionSetPlan:
    """Narrow typed record. Fields only if a real consumer or
    acceptance test reads them.
    """
    purpose: str
    question_regime: str
    selected_level: str
    hierarchy_policy: str
    target_forks_or_unknowns: tuple[str, ...]
    explicit_count_constraint: int | None
    question_budget_ceiling: int
    selected_questions: tuple[QuestionCandidate, ...]
    primary_count: int
    subordinate_count: int
    total_count: int
    stop_reason: str
    stop_reason_grounds: str
    clarification_required: bool
    clarification_grounds: str
    meta_escalation: str
    ownership_owner: str
    ownership_resolved: bool
    #: B2Q-R plan origin — either the deterministic caller override
    #: path or the LIVE-inferred natural-language path. Public so a
    #: trace reader can distinguish CONTROL_OVERRIDE (test/admin) from
    #: MODEL_PRODUCED_VALIDATED (product path).
    origin: str = "CONTROL_OVERRIDE"
    authority: str = AUTHORITY

    def to_public(self) -> dict[str, Any]:
        return {
            "purpose": self.purpose,
            "question_regime": self.question_regime,
            "selected_level": self.selected_level,
            "hierarchy_policy": self.hierarchy_policy,
            "target_forks_or_unknowns": list(self.target_forks_or_unknowns),
            "explicit_count_constraint": self.explicit_count_constraint,
            "question_budget_ceiling": self.question_budget_ceiling,
            "selected_questions": [q.to_public()
                                    for q in self.selected_questions],
            "primary_count": self.primary_count,
            "subordinate_count": self.subordinate_count,
            "total_count": self.total_count,
            "stop_reason": self.stop_reason,
            "stop_reason_grounds": self.stop_reason_grounds,
            "clarification_required": self.clarification_required,
            "clarification_grounds": self.clarification_grounds,
            "meta_escalation": self.meta_escalation,
            "ownership_owner": self.ownership_owner,
            "ownership_resolved": self.ownership_resolved,
            "origin": self.origin,
            "authority": self.authority,
        }


# =========================================================== regime selection


def _select_regime(operation: Any, scene: Any,
                    request_regime_hint: str | None,
                    intent_hint: str | None) -> tuple[str, str]:
    """Return `(regime, meta_escalation)`.

    Uses `operation.kind` as the primary signal (S4 output); falls
    back to a deterministic mapping. Lexical content of user text
    is NEVER inspected here.
    """
    if intent_hint == "meta":
        return (QuestionRegime.REFLECTIVE_OR_META.value,
                MetaEscalation.LEGITIMATE.value)

    if request_regime_hint:
        # Explicit control-field regime hint wins. Meta escalation
        # not granted implicitly.
        if request_regime_hint == QuestionRegime.REFLECTIVE_OR_META.value:
            return (request_regime_hint, MetaEscalation.LEGITIMATE.value)
        return (request_regime_hint, MetaEscalation.NONE.value)

    kind = (getattr(operation, "kind", "") or "").upper()
    if kind.startswith("META_") or "REFLECT_ON_QUESTION" in kind:
        return (QuestionRegime.REFLECTIVE_OR_META.value,
                MetaEscalation.LEGITIMATE.value)

    if any(k in kind for k in ("REFUTE", "FALSIFY",
                                 "COUNTEREXAMPLE",
                                 "TEST_ROBUSTNESS")):
        return (QuestionRegime.FALSIFICATION_OR_COUNTEREXAMPLE.value,
                MetaEscalation.NONE.value)
    if any(k in kind for k in ("ATTRIBUTE", "VERIFY_SOURCE",
                                 "PROVENANCE", "SOURCE_CHECK")):
        return (QuestionRegime.SOURCE_OR_ATTRIBUTION.value,
                MetaEscalation.NONE.value)
    if any(k in kind for k in ("DIAGNOSE", "EXPLAIN_CAUSE",
                                 "STRUCTURE", "ROOT_CAUSE")):
        return (QuestionRegime.DIAGNOSTIC.value,
                MetaEscalation.NONE.value)
    if any(k in kind for k in ("GENERATE_ALTERNATIVES",
                                 "OPEN_FRAMING")):
        return (QuestionRegime.GENERATIVE.value,
                MetaEscalation.NONE.value)

    # Default: decision-separating — the safe regime for most fork
    # sets (planning, comparison, selection).
    return (QuestionRegime.DECISION_SEPARATING.value,
            MetaEscalation.NONE.value)


# =========================================================== derivation


def derive_question_set_plan(
        *, scene: Any, operation: Any, ownership: Any,
        request: dict[str, Any] | None,
        origin: str = "CONTROL_OVERRIDE",
        ) -> QuestionSetPlan | None:
    """Materialise a plan from state + the typed `question_set_request`.

    ``request=None`` returns None — no plan derived, and the runtime
    keeps its existing rendering path. This is the explicit-activation
    contract: only a typed control field can turn the plan on.

    `request` schema (opt-in from the caller):

        {
            "count":         int | null,        # explicit N, form authority only
            "regime":        str | null,        # QuestionRegime value; hint
            "intent":        "meta" | "ordinary" | null,
            "topology": {
                "forks":       [{"id": "F1", "label": "..."}],
                "subordinates":[{"parent": "F1", "id": "F1.a", "label": "..."}]
            } | null,
            "ambiguity":     null | {
                "kind":    "REPRESENTABLE" | "OPERATION_CHANGING",
                "grounds": "..."
            }
        }
    """
    if request is None:
        return None

    request = dict(request)                       # defensive shallow copy
    explicit_count = request.get("count")
    if explicit_count is not None:
        try:
            explicit_count = int(explicit_count)
        except (TypeError, ValueError):
            explicit_count = None

    regime_hint = request.get("regime")
    intent_hint = request.get("intent")

    regime, meta = _select_regime(operation, scene, regime_hint, intent_hint)

    ambiguity = request.get("ambiguity") or {}
    clarification_required = False
    clarification_grounds = ""
    if ambiguity.get("kind") == "OPERATION_CHANGING":
        clarification_required = True
        clarification_grounds = str(ambiguity.get("grounds") or
                                      "operation-changing ambiguity")

    topology = request.get("topology") or {}
    forks = list(topology.get("forks") or [])
    subordinates = list(topology.get("subordinates") or [])

    owner_raw = getattr(ownership, "owner", None)
    if hasattr(owner_raw, "value"):                      # enum-like (Authority)
        owner_str = str(owner_raw.value)
    elif owner_raw is None:
        owner_str = "UNSET"
    else:
        owner_str = str(owner_raw)
    # Authority enum values are lowercase ("human"); tests may pass
    # uppercase strings ("HUMAN"). Normalise to upper for comparison
    # and public projection.
    owner_str = owner_str.upper()
    human_resolved = bool(getattr(ownership, "human_resolved", False))

    ownership_note = ""
    if owner_str in ("HUMAN", "JOINT") and not human_resolved:
        ownership_note = (
            "human-owned operation; questions may clarify but cannot "
            "bind the decision")

    if clarification_required:
        return QuestionSetPlan(
            purpose="clarification",
            question_regime=regime,
            selected_level="PEER",
            hierarchy_policy=HierarchyPolicy.PRIMARY_ONLY.value,
            target_forks_or_unknowns=tuple(f["id"] for f in forks),
            explicit_count_constraint=explicit_count,
            question_budget_ceiling=_DEFAULT_BUDGET_CEILING,
            selected_questions=(),
            primary_count=0, subordinate_count=0, total_count=0,
            stop_reason=StopReason.CLARIFICATION_REQUIRED.value,
            stop_reason_grounds=clarification_grounds,
            clarification_required=True,
            clarification_grounds=clarification_grounds,
            meta_escalation=meta,
            ownership_owner=owner_str,
            ownership_resolved=human_resolved,
            origin=origin)

    if not forks:
        return QuestionSetPlan(
            purpose="no_topology",
            question_regime=regime,
            selected_level="PEER",
            hierarchy_policy=HierarchyPolicy.PRIMARY_ONLY.value,
            target_forks_or_unknowns=(),
            explicit_count_constraint=explicit_count,
            question_budget_ceiling=_DEFAULT_BUDGET_CEILING,
            selected_questions=(),
            primary_count=0, subordinate_count=0, total_count=0,
            stop_reason=StopReason.NO_TOPOLOGY.value,
            stop_reason_grounds=(
                "no topology supplied; caller has not surfaced material "
                "forks/unknowns"),
            clarification_required=False,
            clarification_grounds="",
            meta_escalation=meta,
            ownership_owner=owner_str,
            ownership_resolved=human_resolved,
            origin=origin)

    primary_peers_deduped = _dedupe_forks_by_label(forks)
    primary_target = len(primary_peers_deduped)

    if explicit_count is None:
        primary_selected = list(primary_peers_deduped)
        subs_selected: list[dict[str, Any]] = []
        stop = StopReason.COVERAGE_SATURATED.value
        stop_grounds = (
            "no explicit count; selected one question per material peer "
            f"fork ({primary_target}) — adding more would either "
            "paraphrase or drop below peer level")
        hierarchy = HierarchyPolicy.PRIMARY_ONLY.value
    elif explicit_count < primary_target:
        primary_selected = list(primary_peers_deduped[:explicit_count])
        subs_selected = []
        stop = StopReason.EXPLICIT_COUNT_UNDER_PEERS.value
        stop_grounds = (
            f"explicit count {explicit_count} < material peer count "
            f"{primary_target}; returning the first {explicit_count} "
            "peer forks without inventing sub-questions")
        hierarchy = HierarchyPolicy.PRIMARY_ONLY.value
    elif explicit_count == primary_target:
        primary_selected = list(primary_peers_deduped)
        subs_selected = []
        stop = StopReason.EXPLICIT_COUNT_MET.value
        stop_grounds = (
            f"explicit count {explicit_count} matches material peer count "
            "exactly")
        hierarchy = HierarchyPolicy.PRIMARY_ONLY.value
    else:                                                # N > peers
        primary_selected = list(primary_peers_deduped)
        peer_ids = {f["id"] for f in primary_selected}
        real_subs = [s for s in subordinates
                     if s.get("parent") in peer_ids]
        need = explicit_count - primary_target
        subs_selected = list(real_subs[:need])
        stop = StopReason.EXPLICIT_COUNT_EXCEEDS_PEERS.value
        stop_grounds = (
            f"explicit count {explicit_count} > material peer count "
            f"{primary_target}; returning {primary_target} peers plus "
            f"{len(subs_selected)} explicitly typed subordinate items "
            "(fake peer forks NOT fabricated to reach N)")
        hierarchy = HierarchyPolicy.PRIMARY_PLUS_TYPED_SUBORDINATE.value

    peer_qs = tuple(_peer_question(f, regime) for f in primary_selected)
    sub_qs = tuple(_sub_question(s, regime) for s in subs_selected)
    selected = _dedupe_by_text(peer_qs + sub_qs)

    primary_count = sum(1 for q in selected if not q.is_subordinate)
    subordinate_count = sum(1 for q in selected if q.is_subordinate)
    total_count = len(selected)

    return QuestionSetPlan(
        purpose="fork_discrimination",
        question_regime=regime,
        selected_level=("PEER" if hierarchy == HierarchyPolicy.PRIMARY_ONLY.value
                         else "PEER_PLUS_SUBORDINATE"),
        hierarchy_policy=hierarchy,
        target_forks_or_unknowns=tuple(f["id"] for f in primary_peers_deduped),
        explicit_count_constraint=explicit_count,
        question_budget_ceiling=max(_DEFAULT_BUDGET_CEILING, total_count),
        selected_questions=selected,
        primary_count=primary_count,
        subordinate_count=subordinate_count,
        total_count=total_count,
        stop_reason=stop,
        stop_reason_grounds=(
            stop_grounds + (" | " + ownership_note if ownership_note else "")),
        clarification_required=False,
        clarification_grounds="",
        meta_escalation=meta,
        ownership_owner=owner_str,
        ownership_resolved=human_resolved,
        origin=origin,
    )


# =========================================================== helpers


def _dedupe_forks_by_label(forks: list[dict[str, Any]]
                            ) -> list[dict[str, Any]]:
    """Preserve first occurrence of each unique label."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for f in forks:
        label = str(f.get("label") or f.get("id") or "").strip().lower()
        if not label or label in seen:
            continue
        seen.add(label)
        out.append(f)
    return out


def _dedupe_by_text(cands: tuple[QuestionCandidate, ...]
                     ) -> tuple[QuestionCandidate, ...]:
    seen: set[str] = set()
    out: list[QuestionCandidate] = []
    for c in cands:
        key = c.text.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return tuple(out)


def _peer_question(fork: dict[str, Any], regime: str) -> QuestionCandidate:
    """Build a peer question. When the model surfaced a
    material-specific `candidate_question` (B2Q-R), use it verbatim
    and mark ``text_source="MODEL_MATERIAL"``; otherwise fall back
    to the deterministic template phrasing (D-S26-QSEL-002 fallback).
    """
    label = str(fork.get("label") or fork.get("id"))
    fid = str(fork.get("id"))
    candidate = str(fork.get("candidate_question") or "").strip()
    material_refs = tuple(str(m) for m in (fork.get("material_refs") or ()))
    if candidate:
        return QuestionCandidate(
            text=candidate, regime=regime, fork_ref=fid,
            parent_fork_ref="", is_subordinate=False,
            text_source="MODEL_MATERIAL", material_refs=material_refs)
    return QuestionCandidate(
        text=_phrase(label, regime),
        regime=regime, fork_ref=fid,
        parent_fork_ref="", is_subordinate=False,
        text_source="TEMPLATE_FALLBACK", material_refs=material_refs)


def _sub_question(sub: dict[str, Any], regime: str) -> QuestionCandidate:
    label = str(sub.get("label") or sub.get("id"))
    parent = str(sub.get("parent") or "")
    sid = str(sub.get("id"))
    candidate = str(sub.get("candidate_question") or "").strip()
    if candidate:
        return QuestionCandidate(
            text=candidate, regime=regime, fork_ref=sid,
            parent_fork_ref=parent, is_subordinate=True,
            text_source="MODEL_MATERIAL")
    return QuestionCandidate(
        text=_phrase(label, regime, subordinate=True),
        regime=regime, fork_ref=sid,
        parent_fork_ref=parent, is_subordinate=True,
        text_source="TEMPLATE_FALLBACK")


def _phrase(label: str, regime: str, *, subordinate: bool = False) -> str:
    prefix = "Подвопрос: " if subordinate else ""
    if regime == QuestionRegime.DECISION_SEPARATING.value:
        return f"{prefix}Что различает «{label}» от смежных вариантов?"
    if regime == QuestionRegime.DIAGNOSTIC.value:
        return f"{prefix}Что вызывает «{label}»?"
    if regime == QuestionRegime.FALSIFICATION_OR_COUNTEREXAMPLE.value:
        return f"{prefix}Какой контрпример опровергнет «{label}»?"
    if regime == QuestionRegime.SOURCE_OR_ATTRIBUTION.value:
        return f"{prefix}На каком источнике держится «{label}»?"
    if regime == QuestionRegime.GENERATIVE.value:
        return f"{prefix}Какие альтернативные формулировки «{label}»?"
    if regime == QuestionRegime.REFLECTIVE_OR_META.value:
        return f"{prefix}Какой вопрос стоит задать относительно «{label}»?"
    return f"{prefix}Вопрос по «{label}»?"


# =========================================================== render helper


def render_plan_as_text(plan: QuestionSetPlan) -> str:
    """Deterministic text rendering of the plan's selected questions.

    Returned INSTEAD OF the stochastic renderer when the plan is
    present with a non-empty topology. This is the causal proof
    that the plan governs the final output: the LLM does not get
    to invent a different question count.
    """
    if plan.clarification_required:
        return (
            "Уточнение обязательно перед составлением списка вопросов: "
            f"{plan.clarification_grounds or 'операционно-значимая двусмысленность'}.")

    if plan.total_count == 0:
        return (
            "Список вопросов не составлен: топология материальных развилок "
            "не предоставлена (stop_reason=NO_TOPOLOGY). Уточните состав "
            "развилок/неизвестных для последующего разбора.")

    lines: list[str] = []
    header = (f"Режим вопросов: {plan.question_regime}. "
              f"Уровень: {plan.selected_level}. "
              f"Всего: {plan.total_count} "
              f"(основных: {plan.primary_count}"
              + (f", подчинённых: {plan.subordinate_count}"
                 if plan.subordinate_count else "")
              + ").")
    lines.append(header)
    primary_idx = 0
    subord_idx = 0
    printed_sub_header = False
    for q in plan.selected_questions:
        if not q.is_subordinate:
            primary_idx += 1
            lines.append(f"{primary_idx}. {q.text}")
        else:
            if not printed_sub_header:
                lines.append("Подвопросы:")
                printed_sub_header = True
            subord_idx += 1
            parent = q.parent_fork_ref or "?"
            lines.append(f"  {primary_idx}.{subord_idx} {q.text} "
                          f"[родитель: {parent}]")
    if plan.meta_escalation == MetaEscalation.LEGITIMATE.value:
        lines.append(
            "(Метарежим активирован явно: постановка задачи касается "
            "самой формы вопрошания.)")
    if plan.ownership_owner in ("HUMAN", "JOINT") and not plan.ownership_resolved:
        lines.append(
            "(Замечание: операция принадлежит человеку и не разрешена; "
            "вопросы выше уточняют развилки, но не связывают решение.)")
    return "\n".join(lines)


__all__ = [
    "AUTHORITY",
    "QuestionRegime", "HierarchyPolicy", "StopReason", "MetaEscalation",
    "QuestionCandidate", "QuestionSetPlan",
    "derive_question_set_plan",
    "render_plan_as_text",
]

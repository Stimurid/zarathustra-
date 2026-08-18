"""3D hybrid dyad / co-individuation — typed projection, not a new store.

Reuses Scene / Space / Branch, UserEpistemicView, SurpriseAssessment,
ConflictRegistry, context snapshots, and B05 write denial.

create_new_store = false.

This module never:
- writes identity/persona truth
- treats inference as user fact
- authorises durable/global memory
- rewrites constitution or prompts
- bounces 3C ↔ 3D without a stop
"""
from __future__ import annotations

import hashlib
import re
import secrets
import time
from dataclasses import asdict, dataclass, field, replace
from enum import Enum
from typing import Any

from .context_governance import (
    UserEpistemicView,
    UserHypothesis,
    new_view,
)
from .epistemic_model import (
    ConflictFamily,
    ConflictHandlingMode,
    ConflictHoldingState,
)
from .state import PipelineState, Terminal, TerminalOutcome


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class DyadCategory(str, Enum):
    USER_OBSERVED = "USER_OBSERVED"
    USER_POSITION_CANDIDATE = "USER_POSITION_CANDIDATE"
    USER_EPISTEMIC_HYPOTHESIS = "USER_EPISTEMIC_HYPOTHESIS"
    USER_PREFERENCE_HYPOTHESIS = "USER_PREFERENCE_HYPOTHESIS"
    SOCRATES_POSITION = "SOCRATES_POSITION"
    DYADIC_PATTERN_HYPOTHESIS = "DYADIC_PATTERN_HYPOTHESIS"
    SHARED_OBJECT_STATE = "SHARED_OBJECT_STATE"
    SCENE_STATE = "SCENE_STATE"
    COMMITMENT = "COMMITMENT"
    SURPRISE = "SURPRISE"
    MODEL_REVISION = "MODEL_REVISION"


class HypothesisStatus(str, Enum):
    ACTIVE = "ACTIVE"
    WEAKENED = "WEAKENED"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"
    SCENE_LOCAL = "SCENE_LOCAL"


class SurpriseClass(str, Enum):
    EXPECTED = "EXPECTED"
    INFORMATIVE_SURPRISE = "INFORMATIVE_SURPRISE"
    AMBIGUOUS = "AMBIGUOUS"
    NOVEL_BRANCH = "NOVEL_BRANCH"
    SCENE_SHIFT = "SCENE_SHIFT"
    MODEL_FAILURE_CANDIDATE = "MODEL_FAILURE_CANDIDATE"


class PredictionClass(str, Enum):
    REUSE_DISTINCTION = "REUSE_DISTINCTION"
    USER_ACCEPTS_CLAIM = "USER_ACCEPTS_CLAIM"
    USER_NEED = "USER_NEED"
    NONE = "NONE"


class NeedKind(str, Enum):
    EXPLANATION = "EXPLANATION"
    CHALLENGE = "CHALLENGE"
    RECONSTRUCTION = "RECONSTRUCTION"
    EVIDENCE = "EVIDENCE"
    SYNTHESIS = "SYNTHESIS"
    DECISION = "DECISION"
    ACTION = "ACTION"
    UNKNOWN = "UNKNOWN"


class AuthorityRank(str, Enum):
    USER_EXPLICIT_STATEMENT = "USER_EXPLICIT_STATEMENT"
    REPEATED_OBSERVED_EVIDENCE = "REPEATED_OBSERVED_EVIDENCE"
    SINGLE_OBSERVED_BEHAVIOUR = "SINGLE_OBSERVED_BEHAVIOUR"
    SOCRATES_INFERENCE = "SOCRATES_INFERENCE"
    RETRIEVED_EXTERNAL = "RETRIEVED_EXTERNAL"


class AssertedBy(str, Enum):
    USER = "USER"
    SOCRATES = "SOCRATES"
    JOINT = "JOINT"
    RETRIEVED = "RETRIEVED"


class ScopeKind(str, Enum):
    SCENE = "SCENE"
    SPACE = "SPACE"
    BRANCH = "BRANCH"
    CONTEXT = "CONTEXT"


class WriteDecision(str, Enum):
    EPHEMERAL_SESSION = "EPHEMERAL_SESSION"
    SCENE_LOCAL_PROJECTION = "SCENE_LOCAL_PROJECTION"
    BRANCH_LOCAL_PROJECTION = "BRANCH_LOCAL_PROJECTION"
    NO_DURABLE_WRITE = "NO_DURABLE_WRITE"
    BLOCKED_RETRIEVED_INJECTION = "BLOCKED_RETRIEVED_INJECTION"


class FailureSource(str, Enum):
    NONE = "NONE"
    USER_MODEL_MISMATCH = "USER_MODEL_MISMATCH"
    SCENE_MISMATCH = "SCENE_MISMATCH"
    APPARATUS_MISMATCH = "APPARATUS_MISMATCH"
    GENUINE_DISAGREEMENT = "GENUINE_DISAGREEMENT"


class CommitmentKind(str, Enum):
    PROPOSITION = "PROPOSITION"
    METHOD = "METHOD"
    NEXT_ACTION = "NEXT_ACTION"
    WORKING_ASSUMPTION = "WORKING_ASSUMPTION"


@dataclass(frozen=True)
class DyadRecord:
    record_id: str
    category: DyadCategory
    claim: str
    asserted_by: AssertedBy
    inferred_by: AssertedBy | None
    jointly_established: bool
    confirmed_by_user: bool
    scope_kind: ScopeKind
    scope_id: str
    status: HypothesisStatus
    confidence: float
    authority_rank: AuthorityRank
    evidence_refs: tuple[str, ...]
    counterevidence_refs: tuple[str, ...]
    predecessor_id: str = ""
    revision_reason: str = ""
    sequence: int = 0
    timestamp: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        d["asserted_by"] = self.asserted_by.value
        d["inferred_by"] = self.inferred_by.value if self.inferred_by else None
        d["scope_kind"] = self.scope_kind.value
        d["status"] = self.status.value
        d["authority_rank"] = self.authority_rank.value
        d["evidence_refs"] = list(self.evidence_refs)
        d["counterevidence_refs"] = list(self.counterevidence_refs)
        return d


@dataclass(frozen=True)
class SharedObjectDelta:
    delta_id: str
    object_ref: str
    added: tuple[str, ...]
    changed: tuple[str, ...]
    contributor: AssertedBy
    not_user_model: bool = True
    predecessor_object_ref: str = ""

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["contributor"] = self.contributor.value
        d["added"] = list(self.added)
        d["changed"] = list(self.changed)
        return d


@dataclass
class DyadicSession:
    """Ephemeral typed projection over one context. Not a memory DB."""

    session_key: str
    records: list[DyadRecord] = field(default_factory=list)
    sequence: int = 0
    user_view: UserEpistemicView = field(default_factory=new_view)
    last_prediction_class: str = PredictionClass.NONE.value
    last_predicted_need: str = NeedKind.UNKNOWN.value
    last_predicted_claim: str = ""
    consecutive_failures: int = 0
    shared_object_ids: list[str] = field(default_factory=list)

    def to_public(self) -> dict[str, Any]:
        return {
            "session_key": self.session_key,
            "sequence": self.sequence,
            "records": [r.to_public() for r in self.records],
            "user_view": self.user_view.to_public(),
            "last_prediction_class": self.last_prediction_class,
            "last_predicted_need": self.last_predicted_need,
            "last_predicted_claim": self.last_predicted_claim,
            "consecutive_failures": self.consecutive_failures,
            "shared_object_ids": list(self.shared_object_ids),
        }

    @classmethod
    def from_public(cls, data: dict[str, Any] | None) -> DyadicSession:
        if not data:
            return cls(session_key="")
        recs = []
        for raw in data.get("records") or []:
            recs.append(DyadRecord(
                record_id=raw["record_id"],
                category=DyadCategory(raw["category"]),
                claim=raw.get("claim", ""),
                asserted_by=AssertedBy(raw["asserted_by"]),
                inferred_by=(AssertedBy(raw["inferred_by"])
                             if raw.get("inferred_by") else None),
                jointly_established=bool(raw.get("jointly_established")),
                confirmed_by_user=bool(raw.get("confirmed_by_user")),
                scope_kind=ScopeKind(raw["scope_kind"]),
                scope_id=raw.get("scope_id", ""),
                status=HypothesisStatus(raw["status"]),
                confidence=float(raw.get("confidence") or 0),
                authority_rank=AuthorityRank(raw["authority_rank"]),
                evidence_refs=tuple(raw.get("evidence_refs") or ()),
                counterevidence_refs=tuple(raw.get("counterevidence_refs") or ()),
                predecessor_id=raw.get("predecessor_id", ""),
                revision_reason=raw.get("revision_reason", ""),
                sequence=int(raw.get("sequence") or 0),
                timestamp=raw.get("timestamp", ""),
                extra=dict(raw.get("extra") or {}),
            ))
        view = new_view()
        uv = data.get("user_view") or {}
        view.view_id = uv.get("view_id") or view.view_id
        for h in uv.get("hypotheses") or []:
            view.hypotheses.append(UserHypothesis(
                hypothesis_id=h.get("hypothesis_id") or _new_id("uh"),
                scope=h.get("scope", ""),
                claim=h.get("claim", ""),
                falsifier=h.get("falsifier", ""),
                confidence=float(h.get("confidence") or 0),
                superseded_by=h.get("superseded_by", ""),
                withdrawn_at=h.get("withdrawn_at", ""),
            ))
        return cls(
            session_key=data.get("session_key", ""),
            records=recs,
            sequence=int(data.get("sequence") or 0),
            user_view=view,
            last_prediction_class=data.get("last_prediction_class")
            or PredictionClass.NONE.value,
            last_predicted_need=data.get("last_predicted_need")
            or NeedKind.UNKNOWN.value,
            last_predicted_claim=data.get("last_predicted_claim", ""),
            consecutive_failures=int(data.get("consecutive_failures") or 0),
            shared_object_ids=list(data.get("shared_object_ids") or []),
        )


@dataclass
class DyadicPassResult:
    dyadic_state_ref: str
    prediction_class: PredictionClass
    predicted_need: NeedKind
    predicted_claim: str
    surprise_class: SurpriseClass
    revision_proposed: bool
    shared_object_delta: SharedObjectDelta | None
    scene_scope: str
    space_scope: str
    evidence_refs: tuple[str, ...]
    write_decision: WriteDecision
    authority: str
    used_prior_record_ids: tuple[str, ...]
    public_excerpt: str
    causal_effect: str
    likely_failure_source: FailureSource
    extra_inference_pass: bool
    stop_reason: str
    disagreement_held: bool
    socrates_position_revised: bool
    user_hypothesis_revised: bool
    session_projection: dict[str, Any] = field(default_factory=dict)

    def to_public(self) -> dict[str, Any]:
        return {
            "dyadic_state_ref": self.dyadic_state_ref,
            "prediction_class": self.prediction_class.value,
            "predicted_need": self.predicted_need.value,
            "predicted_claim": self.predicted_claim,
            "surprise_class": self.surprise_class.value,
            "revision_proposed": self.revision_proposed,
            "shared_object_delta": (
                self.shared_object_delta.to_public()
                if self.shared_object_delta else None),
            "scene_scope": self.scene_scope,
            "space_scope": self.space_scope,
            "evidence_refs": list(self.evidence_refs),
            "write_decision": self.write_decision.value,
            "authority": self.authority,
            "used_prior_record_ids": list(self.used_prior_record_ids),
            "public_excerpt": self.public_excerpt,
            "causal_effect": self.causal_effect,
            "likely_failure_source": self.likely_failure_source.value,
            "extra_inference_pass": self.extra_inference_pass,
            "stop_reason": self.stop_reason,
            "disagreement_held": self.disagreement_held,
            "socrates_position_revised": self.socrates_position_revised,
            "user_hypothesis_revised": self.user_hypothesis_revised,
        }


class DyadicSessionRegistry:
    """In-process working projection. Persistence rides existing context
    snapshots (recognition_state.dyad), not a second database.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, DyadicSession] = {}

    def get(self, key: str) -> DyadicSession:
        if key not in self._sessions:
            self._sessions[key] = DyadicSession(session_key=key)
        return self._sessions[key]

    def put(self, session: DyadicSession) -> None:
        self._sessions[session.session_key] = session


def scene_scope_key(state: PipelineState) -> str:
    """Dyad scene isolation follows current telos.

    ``scene_id`` is assigned in 3A+ recognition *after* the 3D pass on
    a first turn, so keying the dyad on ``scene_id`` would split the
    same telos across turns. Telos is the discriminator available at
    the 3D seam.
    """
    telos = (state.scene.telos or "").strip().lower()
    return f"telos:{telos}" if telos else "scene:default"


def space_scope_key(state: PipelineState) -> str:
    return getattr(state, "space_id", "") or "space_default_workspace"


def session_key_for(context_id: str | None) -> str:
    cid = (context_id or "").strip()
    return cid or "_process_local"


_DISTINCTION_RE = re.compile(
    r"(?:distinguish|отличи(?:ть|м))\s+(.+?)\s+from\s+(.+?)(?:[.!?]|$)",
    re.I,
)
_DISTINCTION_MARK = re.compile(
    r"new distinction:\s*(.+?)(?:[.!?]|$)", re.I)
_REJECT_RE = re.compile(
    r"(?:i (?:do not accept|reject)|that's (?:false|wrong)|это неверно|"
    r"i explicitly reject)\s*:?\s*(.+?)(?:[.!?]|$)",
    re.I,
)
_COMMIT_METHOD_RE = re.compile(
    r"(?:for this project use|use method|we will use method|"
    r"для этого проекта использу(?:й|ем))\s+(.+?)(?:[.!?]|$)",
    re.I,
)
_POSITION_USER_RE = re.compile(
    r"(?:my position is|моя позиция[: ]+)\s*(.+?)(?:[.!?]|$)", re.I)
_RETRIEVED_INJECT_RE = re.compile(
    r"(the user believes|store this permanently|запиши это как факт о пользователе)",
    re.I,
)
_DISAGREE_RE = re.compile(
    r"(we (?:still )?disagree|incompatible positions|сохраняем разногласие)",
    re.I,
)
_SOC_WRONG_RE = re.compile(
    r"(?:your working position (?:is|that).{0,80}(?:false|wrong)|"
    r"evidence shows (?:that )?.{0,80}(?:false|wrong)|"
    r"that working position is (?:false|wrong))",
    re.I,
)


def classify_need(text: str) -> NeedKind:
    t = (text or "").lower()
    if re.search(r"\bwithout reconstruct", t) and re.search(
            r"\b(apply that|next step)\b", t):
        return NeedKind.ACTION
    if re.search(r"\b(why|explain|объясн)", t):
        return NeedKind.EXPLANATION
    if re.search(r"\b(challenge|оспор)\b|\bi reject\b|\bi explicitly reject\b", t):
        return NeedKind.CHALLENGE
    if re.search(r"\b(reconstruct|пересобери|rebuild)\b", t):
        return NeedKind.RECONSTRUCTION
    if re.search(r"\b(evidence|source|доказат|цитир)", t):
        return NeedKind.EVIDENCE
    if re.search(r"\b(synthe|свед|combine)\b", t):
        return NeedKind.SYNTHESIS
    if re.search(r"\b(decide|выбор|commit to)\b", t):
        return NeedKind.DECISION
    if re.search(r"\b(do it|implement|apply that|next step|действуй|реализуй)\b", t):
        return NeedKind.ACTION
    if t.strip().endswith("?"):
        return NeedKind.EXPLANATION
    return NeedKind.UNKNOWN


def is_easy_direct(text: str, session: DyadicSession) -> bool:
    t = (text or "").strip()
    if _DISTINCTION_RE.search(t) or _DISTINCTION_MARK.search(t):
        return False
    if _REJECT_RE.search(t) or _COMMIT_METHOD_RE.search(t):
        return False
    if _DISAGREE_RE.search(t) or _SOC_WRONG_RE.search(t):
        return False
    active = [r for r in session.records
              if r.status in {HypothesisStatus.ACTIVE, HypothesisStatus.SCENE_LOCAL,
                              HypothesisStatus.WEAKENED}]
    if active:
        return False
    if len(t) <= 180 and t.endswith("?"):
        return True
    return False


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().strip("\"'")).strip()


def _visible_records(session: DyadicSession, scene_key: str,
                     space_key: str) -> list[DyadRecord]:
    out = []
    for r in session.records:
        if r.status in {HypothesisStatus.SUPERSEDED, HypothesisStatus.REJECTED}:
            continue
        if r.scope_kind == ScopeKind.SCENE and r.scope_id != scene_key:
            continue
        if r.scope_kind == ScopeKind.SPACE and r.scope_id != space_key:
            continue
        out.append(r)
    return out


def _append(session: DyadicSession, rec: DyadRecord) -> DyadRecord:
    session.sequence += 1
    rec = replace(rec, sequence=session.sequence, timestamp=_now_iso())
    session.records.append(rec)
    return rec


def _revise(session: DyadicSession, old: DyadRecord, *,
            status: HypothesisStatus, reason: str,
            confidence: float, counter: tuple[str, ...],
            new_claim: str | None = None,
            category: DyadCategory | None = None) -> DyadRecord:
    parked = replace(
        old, status=status, revision_reason=reason,
        counterevidence_refs=old.counterevidence_refs + counter)
    for i, r in enumerate(session.records):
        if r.record_id == old.record_id:
            session.records[i] = parked
            break
    successor_status = (HypothesisStatus.REJECTED
                        if status == HypothesisStatus.REJECTED
                        else HypothesisStatus.ACTIVE)
    successor = _append(session, DyadRecord(
        record_id=_new_id("drec"),
        category=category or old.category,
        claim=new_claim if new_claim is not None else old.claim,
        asserted_by=old.asserted_by,
        inferred_by=old.inferred_by,
        jointly_established=old.jointly_established,
        confirmed_by_user=old.confirmed_by_user,
        scope_kind=old.scope_kind,
        scope_id=old.scope_id,
        status=successor_status,
        confidence=confidence,
        authority_rank=old.authority_rank,
        evidence_refs=old.evidence_refs + counter,
        counterevidence_refs=counter,
        predecessor_id=old.record_id,
        revision_reason=reason,
    ))
    return successor


def run_dyadic_pass(
    state: PipelineState,
    outcome: TerminalOutcome,
    *,
    input_text: str,
    session: DyadicSession,
    apparatus_diag: dict[str, Any] | None = None,
    private_work: dict[str, Any] | None = None,
    prior_scene_key: str = "",
) -> DyadicPassResult:
    """Deterministic dyadic loop. No extra LLM pass. No durable write."""
    scene_key = scene_scope_key(state)
    space_key = space_scope_key(state)
    apparatus_diag = apparatus_diag or {}
    private_work = private_work or {}
    text = input_text or ""
    material_ref = f"obs_{hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]}"

    extra_pass = (private_work.get("additional_private_pass_count") or 0) > 0
    easy = is_easy_direct(text, session)
    if not prior_scene_key:
        prior_scopes = {
            r.scope_id for r in session.records
            if r.scope_kind == ScopeKind.SCENE and r.scope_id
        }
        if scene_key in prior_scopes:
            prior_scene_key = scene_key
        elif len(prior_scopes) == 1:
            prior_scene_key = next(iter(prior_scopes))
        elif prior_scopes:
            prior_scene_key = sorted(prior_scopes)[-1]
    scene_shift = bool(prior_scene_key and prior_scene_key != scene_key)
    visible = _visible_records(session, scene_key, space_key)

    retrieved_injection = bool(_RETRIEVED_INJECT_RE.search(text))
    write = WriteDecision.NO_DURABLE_WRITE
    authority = "NO_DURABLE_WRITE"
    if retrieved_injection:
        write = WriteDecision.BLOCKED_RETRIEVED_INJECTION

    pred_class = PredictionClass.NONE
    pred_claim = session.last_predicted_claim
    pred_need = NeedKind.UNKNOWN
    if session.last_predicted_need in NeedKind._value2member_map_:
        pred_need = NeedKind(session.last_predicted_need)
    used_prior: list[str] = []
    dist_recs = [r for r in visible if r.category == DyadCategory.SHARED_OBJECT_STATE
                 and r.status in {HypothesisStatus.ACTIVE, HypothesisStatus.SCENE_LOCAL}]
    accept_hyps = [r for r in visible
                   if r.category == DyadCategory.USER_EPISTEMIC_HYPOTHESIS
                   and r.status == HypothesisStatus.ACTIVE]
    if dist_recs:
        pred_class = PredictionClass.REUSE_DISTINCTION
        pred_claim = dist_recs[-1].claim
        used_prior.append(dist_recs[-1].record_id)
        pred_need = NeedKind.ACTION
    elif accept_hyps:
        pred_class = PredictionClass.USER_ACCEPTS_CLAIM
        pred_claim = accept_hyps[-1].claim
        used_prior.append(accept_hyps[-1].record_id)
    elif (not scene_shift
            and session.last_predicted_need
            and session.last_predicted_need != NeedKind.UNKNOWN.value):
        pred_class = PredictionClass.USER_NEED
        pred_need = NeedKind(session.last_predicted_need)

    observed_need = classify_need(text)

    excerpt_bits: list[str] = []
    causal = "none"
    revision = False
    user_rev = False
    soc_rev = False
    disagreement = False
    delta: SharedObjectDelta | None = None
    evidence = [material_ref]
    surprise = SurpriseClass.AMBIGUOUS

    if easy and not visible:
        session.last_prediction_class = pred_class.value
        session.last_predicted_need = observed_need.value
        return DyadicPassResult(
            dyadic_state_ref=session.session_key or "_process_local",
            prediction_class=pred_class,
            predicted_need=pred_need,
            predicted_claim=pred_claim,
            surprise_class=SurpriseClass.EXPECTED,
            revision_proposed=False,
            shared_object_delta=None,
            scene_scope=scene_key,
            space_scope=space_key,
            evidence_refs=tuple(evidence),
            write_decision=WriteDecision.NO_DURABLE_WRITE,
            authority=authority,
            used_prior_record_ids=(),
            public_excerpt="",
            causal_effect="skipped_easy_direct",
            likely_failure_source=FailureSource.NONE,
            extra_inference_pass=False,
            stop_reason="easy_direct_no_extra_dyad_inference",
            disagreement_held=False,
            socrates_position_revised=False,
            user_hypothesis_revised=False,
            session_projection=session.to_public(),
        )

    if scene_shift:
        surprise = SurpriseClass.SCENE_SHIFT
        used_prior = []
        pred_class = PredictionClass.NONE
        pred_need = NeedKind.UNKNOWN

    m_dist = _DISTINCTION_RE.search(text) or _DISTINCTION_MARK.search(text)
    if m_dist and not retrieved_injection:
        if m_dist.lastindex and m_dist.lastindex >= 2:
            left = _norm(m_dist.group(1))
            right = _norm(m_dist.group(2))
            claim = f"{left} ≠ {right}" if right else left
        else:
            claim = _norm(m_dist.group(1))
        rec = _append(session, DyadRecord(
            record_id=_new_id("drec"),
            category=DyadCategory.SHARED_OBJECT_STATE,
            claim=claim,
            asserted_by=AssertedBy.USER,
            inferred_by=None,
            jointly_established=True,
            confirmed_by_user=True,
            scope_kind=ScopeKind.SCENE,
            scope_id=scene_key,
            status=HypothesisStatus.SCENE_LOCAL,
            confidence=0.9,
            authority_rank=AuthorityRank.USER_EXPLICIT_STATEMENT,
            evidence_refs=(material_ref,),
            counterevidence_refs=(),
            extra={"kind": "distinction"},
        ))
        obs = _append(session, DyadRecord(
            record_id=_new_id("drec"),
            category=DyadCategory.USER_OBSERVED,
            claim=f"asserted distinction {claim}",
            asserted_by=AssertedBy.USER,
            inferred_by=None,
            jointly_established=False,
            confirmed_by_user=True,
            scope_kind=ScopeKind.SCENE,
            scope_id=scene_key,
            status=HypothesisStatus.ACTIVE,
            confidence=1.0,
            authority_rank=AuthorityRank.USER_EXPLICIT_STATEMENT,
            evidence_refs=(material_ref,),
            counterevidence_refs=(),
        ))
        session.shared_object_ids.append(rec.record_id)
        delta = SharedObjectDelta(
            delta_id=_new_id("sobj"),
            object_ref=rec.record_id,
            added=(claim,),
            changed=(),
            contributor=AssertedBy.USER,
            predecessor_object_ref=(dist_recs[-1].record_id if dist_recs else ""),
        )
        surprise = SurpriseClass.EXPECTED if pred_class == PredictionClass.REUSE_DISTINCTION else SurpriseClass.NOVEL_BRANCH
        excerpt_bits.append(f"[dyad shared-object {rec.record_id}: {claim}]")
        causal = "shared_object_delta"
        evidence.extend([rec.record_id, obs.record_id])
        write = WriteDecision.SCENE_LOCAL_PROJECTION

    m_rej = _REJECT_RE.search(text)
    if m_rej and not retrieved_injection:
        rejected = _norm(m_rej.group(1))
        _append(session, DyadRecord(
            record_id=_new_id("drec"),
            category=DyadCategory.USER_OBSERVED,
            claim=f"rejected {rejected}",
            asserted_by=AssertedBy.USER,
            inferred_by=None,
            jointly_established=False,
            confirmed_by_user=True,
            scope_kind=ScopeKind.SCENE,
            scope_id=scene_key,
            status=HypothesisStatus.ACTIVE,
            confidence=1.0,
            authority_rank=AuthorityRank.USER_EXPLICIT_STATEMENT,
            evidence_refs=(material_ref,),
            counterevidence_refs=(),
        ))
        matched = None
        for h in list(accept_hyps):
            if h.claim.lower() in rejected.lower() or rejected.lower() in h.claim.lower():
                matched = h
                break
        if matched is None and accept_hyps and pred_class == PredictionClass.USER_ACCEPTS_CLAIM:
            matched = accept_hyps[-1]
        if matched:
            weak = matched.confidence < 0.55
            if weak:
                parked = replace(
                    matched, status=HypothesisStatus.WEAKENED,
                    revision_reason="single_unusual_turn_no_overupdate",
                    counterevidence_refs=matched.counterevidence_refs + (material_ref,),
                    confidence=max(0.1, matched.confidence * 0.5))
                for i, r in enumerate(session.records):
                    if r.record_id == matched.record_id:
                        session.records[i] = parked
                        break
                surprise = SurpriseClass.AMBIGUOUS
                causal = "no_overupdate_weak_hypothesis"
                revision = True
                user_rev = True
            else:
                _revise(session, matched, status=HypothesisStatus.REJECTED,
                        reason="user_explicit_rejection",
                        confidence=0.15, counter=(material_ref,))
                surprise = SurpriseClass.INFORMATIVE_SURPRISE
                causal = "user_hypothesis_rejected"
                revision = True
                user_rev = True
                excerpt_bits.append(
                    f"[dyad revision: hypothesis {matched.record_id} rejected]")
                session.consecutive_failures += 1
        elif pred_class != PredictionClass.NONE:
            surprise = SurpriseClass.INFORMATIVE_SURPRISE

    m_commit = _COMMIT_METHOD_RE.search(text)
    if m_commit and not retrieved_injection:
        method = _norm(m_commit.group(1))
        rec = _append(session, DyadRecord(
            record_id=_new_id("drec"),
            category=DyadCategory.COMMITMENT,
            claim=method,
            asserted_by=AssertedBy.USER,
            inferred_by=None,
            jointly_established=False,
            confirmed_by_user=True,
            scope_kind=ScopeKind.SCENE,
            scope_id=scene_key,
            status=HypothesisStatus.ACTIVE,
            confidence=1.0,
            authority_rank=AuthorityRank.USER_EXPLICIT_STATEMENT,
            evidence_refs=(material_ref,),
            counterevidence_refs=(),
            extra={"commitment_kind": CommitmentKind.METHOD.value},
        ))
        excerpt_bits.append(f"[dyad explicit commitment/method: {method}]")
        causal = "explicit_commitment"
        write = WriteDecision.SCENE_LOCAL_PROJECTION
        if pred_class == PredictionClass.NONE and surprise == SurpriseClass.AMBIGUOUS:
            surprise = SurpriseClass.EXPECTED
        del rec

    m_upos = _POSITION_USER_RE.search(text)
    if m_upos and not retrieved_injection:
        claim = _norm(m_upos.group(1))
        _append(session, DyadRecord(
            record_id=_new_id("drec"),
            category=DyadCategory.USER_POSITION_CANDIDATE,
            claim=claim,
            asserted_by=AssertedBy.USER,
            inferred_by=None,
            jointly_established=False,
            confirmed_by_user=True,
            scope_kind=ScopeKind.SCENE,
            scope_id=scene_key,
            status=HypothesisStatus.ACTIVE,
            confidence=0.85,
            authority_rank=AuthorityRank.USER_EXPLICIT_STATEMENT,
            evidence_refs=(material_ref,),
            counterevidence_refs=(),
        ))

    soc_existing = [r for r in visible if r.category == DyadCategory.SOCRATES_POSITION
                    and r.status == HypothesisStatus.ACTIVE]
    telos = (state.scene.telos or "").strip()
    if telos and not soc_existing:
        _append(session, DyadRecord(
            record_id=_new_id("drec"),
            category=DyadCategory.SOCRATES_POSITION,
            claim=telos,
            asserted_by=AssertedBy.SOCRATES,
            inferred_by=AssertedBy.SOCRATES,
            jointly_established=False,
            confirmed_by_user=False,
            scope_kind=ScopeKind.SCENE,
            scope_id=scene_key,
            status=HypothesisStatus.ACTIVE,
            confidence=0.4,
            authority_rank=AuthorityRank.SOCRATES_INFERENCE,
            evidence_refs=(f"scene.telos:{telos}",),
            counterevidence_refs=(),
        ))
        soc_existing = [r for r in session.records
                        if r.category == DyadCategory.SOCRATES_POSITION
                        and r.status == HypothesisStatus.ACTIVE
                        and r.scope_id == scene_key]

    if _SOC_WRONG_RE.search(text) and soc_existing and not retrieved_injection:
        old = soc_existing[-1]
        _revise(session, old, status=HypothesisStatus.SUPERSEDED,
                reason="interaction_evidence_invalidated_socrates_position",
                confidence=0.2, counter=(material_ref,),
                new_claim=f"revised: not {old.claim}")
        soc_rev = True
        revision = True
        surprise = SurpriseClass.INFORMATIVE_SURPRISE
        causal = "socrates_position_revised"
        excerpt_bits.append(f"[dyad socrates-position revised from {old.record_id}]")

    if _DISAGREE_RE.search(text) and not retrieved_injection:
        disagreement = True
        sclaim = soc_existing[-1].claim if soc_existing else telos
        up = [r for r in session.records
              if r.category == DyadCategory.USER_POSITION_CANDIDATE
              and r.status == HypothesisStatus.ACTIVE]
        uclaim = up[-1].claim if up else ""
        state.conflict_registry.add(ConflictHoldingState(
            conflict_id=_new_id("conf"),
            family=ConflictFamily.VALUE,
            handling_mode=ConflictHandlingMode.HOLD,
            parties=("USER", "SOCRATES"),
            subject_refs=(uclaim, sclaim),
            space_ids=(space_key,),
            scene_ids=(scene_key,),
            description="productive disagreement held; no forced convergence",
            status="held",
        ))
        excerpt_bits.append("[dyad disagreement held]")
        causal = "disagreement_held"
        if surprise == SurpriseClass.AMBIGUOUS:
            surprise = SurpriseClass.EXPECTED

    infer_accept = re.search(
        r"you (?:will |likely )?accept\s+(.+?)(?:[.!?]|$)", text, re.I)
    if infer_accept and not retrieved_injection:
        claim = _norm(infer_accept.group(1))
        weak = "likely" in text.lower() or "might" in text.lower()
        _append(session, DyadRecord(
            record_id=_new_id("drec"),
            category=DyadCategory.USER_EPISTEMIC_HYPOTHESIS,
            claim=claim,
            asserted_by=AssertedBy.SOCRATES,
            inferred_by=AssertedBy.SOCRATES,
            jointly_established=False,
            confirmed_by_user=False,
            scope_kind=ScopeKind.SCENE,
            scope_id=scene_key,
            status=HypothesisStatus.ACTIVE,
            confidence=0.45 if weak else 0.7,
            authority_rank=AuthorityRank.SOCRATES_INFERENCE,
            evidence_refs=(material_ref,),
            counterevidence_refs=(),
        ))
        session.user_view.add_hypothesis(UserHypothesis(
            hypothesis_id=_new_id("uh"),
            scope=scene_key,
            claim=claim,
            falsifier="explicit user rejection",
            confidence=0.45 if weak else 0.7,
        ))

    if retrieved_injection:
        _append(session, DyadRecord(
            record_id=_new_id("drec"),
            category=DyadCategory.USER_EPISTEMIC_HYPOTHESIS,
            claim="retrieved_injection_blocked",
            asserted_by=AssertedBy.RETRIEVED,
            inferred_by=AssertedBy.SOCRATES,
            jointly_established=False,
            confirmed_by_user=False,
            scope_kind=ScopeKind.SCENE,
            scope_id=scene_key,
            status=HypothesisStatus.REJECTED,
            confidence=0.0,
            authority_rank=AuthorityRank.RETRIEVED_EXTERNAL,
            evidence_refs=(material_ref,),
            counterevidence_refs=(material_ref,),
            revision_reason="retrieved_text_has_no_user_fact_authority",
        ))
        causal = "retrieved_injection_blocked"
        excerpt_bits.append("[dyad retrieved injection has no user-fact authority]")

    if pred_class == PredictionClass.REUSE_DISTINCTION and dist_recs and not m_dist:
        if observed_need in {NeedKind.ACTION, NeedKind.SYNTHESIS, NeedKind.DECISION} or \
           re.search(r"apply that|use (?:the )?distinction|without reconstructing", text, re.I):
            surprise = SurpriseClass.EXPECTED
            causal = "reuse_prior_distinction"
            used_prior = [dist_recs[-1].record_id]
            excerpt_bits.insert(
                0, f"[dyad reuse distinction {dist_recs[-1].record_id}: {dist_recs[-1].claim}]")
            session.consecutive_failures = 0
        elif observed_need == NeedKind.EXPLANATION and pred_need == NeedKind.ACTION:
            surprise = SurpriseClass.INFORMATIVE_SURPRISE
            causal = "prediction_failure_need"
            revision = True
            session.consecutive_failures += 1
            excerpt_bits.append(
                "[dyad prediction failure: need mismatch, no retrospective fit]")

    if pred_class == PredictionClass.USER_NEED and pred_need != NeedKind.UNKNOWN:
        if observed_need == pred_need:
            surprise = SurpriseClass.EXPECTED
            if causal == "none":
                causal = "prediction_success_need"
            session.consecutive_failures = 0
        elif observed_need != NeedKind.UNKNOWN:
            surprise = SurpriseClass.INFORMATIVE_SURPRISE
            causal = "prediction_failure_need"
            session.consecutive_failures += 1

    if session.consecutive_failures >= 2 and surprise == SurpriseClass.INFORMATIVE_SURPRISE:
        surprise = SurpriseClass.MODEL_FAILURE_CANDIDATE

    aclass = str(apparatus_diag.get("classification") or "")
    likely = FailureSource.NONE
    if surprise == SurpriseClass.SCENE_SHIFT or scene_shift:
        likely = FailureSource.SCENE_MISMATCH
    elif user_rev and surprise in {SurpriseClass.INFORMATIVE_SURPRISE,
                                   SurpriseClass.MODEL_FAILURE_CANDIDATE}:
        likely = FailureSource.USER_MODEL_MISMATCH
    elif aclass == "GENUINE_APORIA" or disagreement:
        likely = FailureSource.GENUINE_DISAGREEMENT
    elif aclass in {"APPARATUS_MISMATCH_CANDIDATE", "PROJECTION_GAP", "ONTOLOGY_GAP"}:
        likely = FailureSource.APPARATUS_MISMATCH

    session.last_prediction_class = pred_class.value
    session.last_predicted_need = observed_need.value
    session.last_predicted_claim = pred_claim

    return DyadicPassResult(
        dyadic_state_ref=session.session_key or "_process_local",
        prediction_class=pred_class,
        predicted_need=pred_need,
        predicted_claim=pred_claim,
        surprise_class=surprise,
        revision_proposed=revision,
        shared_object_delta=delta,
        scene_scope=scene_key,
        space_scope=space_key,
        evidence_refs=tuple(evidence),
        write_decision=write,
        authority=authority,
        used_prior_record_ids=tuple(used_prior),
        public_excerpt=" ".join(excerpt_bits).strip(),
        causal_effect=causal,
        likely_failure_source=likely,
        extra_inference_pass=extra_pass,
        stop_reason="no_3c_reentry",
        disagreement_held=disagreement,
        socrates_position_revised=soc_rev,
        user_hypothesis_revised=user_rev,
        session_projection=session.to_public(),
    )


def apply_dyad_to_outcome(
    outcome: TerminalOutcome,
    dyad: DyadicPassResult,
) -> TerminalOutcome:
    """Bounded public effect. Never masks PRESERVE_APORIA. No consensus max."""
    if outcome.terminal in {
        Terminal.FAILED_EXPLICIT,
        Terminal.SEMANTIC_MOUNT_MISSING,
        Terminal.SEMANTIC_CONTEXT_BUDGET_EXCEEDED,
        Terminal.PRESERVE_APORIA,
        Terminal.RETURN_OPERATION,
    }:
        return outcome
    excerpt = (dyad.public_excerpt or "").strip()
    text = outcome.response_text or ""
    if excerpt and excerpt not in text:
        text = (excerpt + "\n" + text).strip()
    new_terminal = outcome.terminal
    if (dyad.causal_effect == "user_hypothesis_rejected"
            and outcome.terminal == Terminal.ANSWER):
        new_terminal = Terminal.CHALLENGE
    if (dyad.causal_effect == "reuse_prior_distinction"
            and outcome.terminal == Terminal.ANSWER):
        new_terminal = Terminal.DISTINGUISH
    if (dyad.causal_effect == "socrates_position_revised"
            and outcome.terminal == Terminal.ANSWER):
        new_terminal = Terminal.REFRAME
    return TerminalOutcome(
        terminal=new_terminal,
        response_text=text,
        rationale=(outcome.rationale or "") + f" dyad:{dyad.causal_effect}",
        memory_proposal=outcome.memory_proposal,
    )


__all__ = [
    "AssertedBy",
    "AuthorityRank",
    "DyadCategory",
    "DyadRecord",
    "DyadicPassResult",
    "DyadicSession",
    "DyadicSessionRegistry",
    "FailureSource",
    "HypothesisStatus",
    "NeedKind",
    "PredictionClass",
    "ScopeKind",
    "SharedObjectDelta",
    "SurpriseClass",
    "WriteDecision",
    "apply_dyad_to_outcome",
    "run_dyadic_pass",
    "scene_scope_key",
    "session_key_for",
    "space_scope_key",
]

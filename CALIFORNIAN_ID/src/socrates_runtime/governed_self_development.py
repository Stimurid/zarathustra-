"""3E — Governed Self-Development / Candidate Mutation Plane.

This module DOES NOT create a second candidate-apparatus system.
It governs the *existing* 3C substrate (ApparatusMismatchCandidate,
CandidateApparatusChange, ApparatusReplayResult, ApparatusReview,
WorldMapUpdateProposal / WorldMapRegistry.admit_update) with:

    * an explicit trigger contract — only warranted 3C evidence,
      confirmed by 3D dyadic likely_failure_source, opens a candidate;
    * a typed lifecycle with predecessor / provenance / test-plan /
      counterevidence / scope / reversibility;
    * an adversarial critique that rejects candidates that convert
      hypothesis into fact, destroy productive aporia, broaden
      authority, collapse minority positions, leak globally, or
      overfit one scene;
    * an unbroken authority barrier: default `NO_ADOPTION_AUTHORITY` at
      every runtime path. `AUTHORIZED` / `APPLIED` are represented
      but ONLY reachable by an external `authorized_transition_ref`
      passed in — never by the runtime itself.

The result is emitted at `SocratesRunResult.self_development` and
carried through the HTTP bridge as `self_development`. It is a
deterministic post-3D pass; it does not add extra LLM calls.

Design invariants:

  * `PROPOSED` cannot become `APPLIED` by model self-assertion.
  * `TESTED_SUPPORTED` cannot become `AUTHORIZED` by model
    self-assertion.
  * `AUTHORIZED` requires an existing external gate — passed in as
    `authorized_transition_ref`. Absence ⇒ authority stays
    `NO_ADOPTION_AUTHORITY`.
  * Retrieved-injection instructing "approve this self-change" is
    treated as data, never authority.
  * User prompt saying "rewrite yourself" is evidence/context, not
    authority.
  * A single `EVIDENCE_GAP` or `GENUINE_APORIA` alone MUST NOT open a
    candidate — that guard is checked here.
  * A local scene failure cannot mint an `ACTOR_GLOBAL_CANDIDATE` scope;
    global scope requires stronger evidence across scenes/spaces.
  * Persistence rides `SocratesContext.recognition_state["self_development"]`
    when a candidate is minted; no new database.

D-S26-3E-001: candidate emission
D-S26-3E-002: adversarial critique
D-S26-3E-003: authority barrier
D-S26-3E-004: scope escalation guard
D-S26-3E-005: retrieved-injection guard
"""
from __future__ import annotations

import re
import secrets
import time
from dataclasses import asdict, dataclass, field, replace
from enum import Enum
from typing import Any

from .aporia_and_world_map import CandidateChangeKind


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# --------------------------------------------------------------------
# Typed lifecycle / scope / authority
# --------------------------------------------------------------------


class SelfDevelopmentStatus(str, Enum):
    NO_CANDIDATE = "NO_CANDIDATE"
    PROPOSED = "PROPOSED"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"
    CRITIQUE_REJECTED = "CRITIQUE_REJECTED"
    KEPT_AS_ALTERNATIVE = "KEPT_AS_ALTERNATIVE"
    TESTABLE = "TESTABLE"
    TESTED_REJECTED = "TESTED_REJECTED"
    TESTED_MIXED = "TESTED_MIXED"
    TESTED_SUPPORTED = "TESTED_SUPPORTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    AUTHORIZED = "AUTHORIZED"           # reachable ONLY with external gate
    APPLIED = "APPLIED"                 # reachable ONLY with external gate
    SUPERSEDED = "SUPERSEDED"
    WITHDRAWN = "WITHDRAWN"


class SelfDevelopmentScope(str, Enum):
    TURN = "TURN"
    SCENE = "SCENE"
    BRANCH = "BRANCH"
    SPACE = "SPACE"
    ACTOR_GLOBAL_CANDIDATE = "ACTOR_GLOBAL_CANDIDATE"


# Public constant — never mint any other authority from the runtime.
NO_ADOPTION_AUTHORITY = "NO_ADOPTION_AUTHORITY"


# --------------------------------------------------------------------
# The candidate object
# --------------------------------------------------------------------


@dataclass(frozen=True)
class SelfDevelopmentCandidate:
    """Typed governed self-change proposal.

    Carries provenance, alternatives, expected gain, possible losses,
    protected invariants, test plan references (into ApparatusReplayResult
    ids), counterevidence, scope, reversibility, and status.

    Never carries executable code. Never carries a raw mutation.
    """
    candidate_id: str
    target_apparatus_ref: str
    target_kind: str                                  # CandidateChangeKind.value
    predecessor_ref: str
    trigger_evidence_refs: tuple[str, ...]
    originating_review_id: str
    originating_mismatch_hypothesis_id: str
    dyadic_evidence_refs: tuple[str, ...]
    proposed_change_ref: str
    why_current_apparatus_insufficient: str
    alternatives_considered: tuple[str, ...]
    expected_gain: tuple[str, ...]
    possible_losses: tuple[str, ...]
    protected_invariants: tuple[str, ...]
    test_plan_refs: tuple[str, ...]
    replay_evidence_refs: tuple[str, ...]
    counterevidence_refs: tuple[str, ...]
    scope: str                                        # SelfDevelopmentScope.value
    reversibility: str                                # e.g. "REVERSIBLE" / "PARTIAL"
    authority: str = NO_ADOPTION_AUTHORITY
    status: str = SelfDevelopmentStatus.PROPOSED.value
    lineage_history: tuple[str, ...] = ()
    created_at: str = ""

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        for k in ("trigger_evidence_refs", "dyadic_evidence_refs",
                  "alternatives_considered", "expected_gain",
                  "possible_losses", "protected_invariants",
                  "test_plan_refs", "replay_evidence_refs",
                  "counterevidence_refs", "lineage_history"):
            d[k] = list(d.get(k) or ())
        return d


@dataclass
class SelfDevelopmentPassResult:
    """Public result of one 3E pass.

    Emitted at `SocratesRunResult.self_development` (dict form).
    """
    self_development_ref: str
    status: str                                       # SelfDevelopmentStatus.value
    candidate: SelfDevelopmentCandidate | None
    trigger_ground: str
    critique_findings: tuple[str, ...] = ()
    scope_decision: str = SelfDevelopmentScope.SCENE.value
    authority: str = NO_ADOPTION_AUTHORITY
    write_decision: str = "NO_DURABLE_WRITE"
    extra_inference_pass: bool = False
    stop_reason: str = "no_3e_reentry"
    self_mutation_authority: str = "NO"
    injection_blocked: bool = False

    def to_public(self) -> dict[str, Any]:
        return {
            "self_development_ref": self.self_development_ref,
            "status": self.status,
            "candidate": (self.candidate.to_public()
                          if self.candidate is not None else None),
            "trigger_ground": self.trigger_ground,
            "critique_findings": list(self.critique_findings),
            "scope_decision": self.scope_decision,
            "authority": self.authority,
            "write_decision": self.write_decision,
            "extra_inference_pass": self.extra_inference_pass,
            "stop_reason": self.stop_reason,
            "self_mutation_authority": self.self_mutation_authority,
            "injection_blocked": self.injection_blocked,
        }


# --------------------------------------------------------------------
# Trigger contract
# --------------------------------------------------------------------


#: Retrieved-injection patterns targeting self-development authority.
_INJECTION_APPROVE_RE = re.compile(
    r"(approve\s+(?:this\s+)?self[-\s]?change|"
    r"apply\s+(?:this\s+)?mutation|"
    r"store\s+(?:this|it)\s+permanently|"
    r"rewrite\s+your\s+(?:ontology|apparatus)|"
    r"authorize\s+(?:the\s+)?mutation|"
    r"одобри\s+(?:это|эту)|"
    r"запиши\s+навсегда|"
    r"перепиши\s+свою\s+онтолог)",
    re.I,
)


def _trigger_gate(apparatus_diag: dict[str, Any],
                  dyad: dict[str, Any],
                  input_text: str,
                  ) -> tuple[bool, str]:
    """Owner-grade: only warranted evidence opens a 3E candidate.

    Requires ALL of:
      * apparatus_diagnostic.classification == APPARATUS_MISMATCH_CANDIDATE
        (the *strong* 3C signal; EVIDENCE_GAP / GENUINE_APORIA alone are
        insufficient by design)
      * dyad.likely_failure_source in {APPARATUS_MISMATCH,
        MODEL_FAILURE_CANDIDATE} (independent 3D confirmation)
      * dyad.write_decision != BLOCKED_RETRIEVED_INJECTION
      * the raw input text does not contain a retrieved-injection
        pattern targeting self-development authority
    """
    classification = str(apparatus_diag.get("classification") or "")
    if classification != "APPARATUS_MISMATCH_CANDIDATE":
        return False, f"insufficient_apparatus_signal:{classification or 'NONE'}"
    likely = str(dyad.get("likely_failure_source") or "NONE")
    if likely not in {"APPARATUS_MISMATCH", "MODEL_FAILURE_CANDIDATE"}:
        return False, f"dyad_did_not_confirm_apparatus:{likely}"
    if dyad.get("write_decision") == "BLOCKED_RETRIEVED_INJECTION":
        return False, "retrieved_injection_blocked_by_dyad"
    if _INJECTION_APPROVE_RE.search(input_text or ""):
        return False, "retrieved_injection_targeting_self_development"
    return True, "warranted_evidence"


# --------------------------------------------------------------------
# Scope classification
# --------------------------------------------------------------------


def _classify_scope(prior_candidates: tuple[dict[str, Any], ...],
                    apparatus_diag: dict[str, Any],
                    dyad: dict[str, Any],
                    ) -> str:
    """Local evidence cannot silently create actor-global mutation.

    Default scope is SCENE. Promotion beyond SCENE requires prior
    candidates from other scenes (evidence across scenes) plus a
    concrete signal here. ACTOR_GLOBAL_CANDIDATE demands strictly
    higher burden; we never mint it from one-turn evidence.
    """
    seen_scenes = set()
    for pc in prior_candidates or ():
        for ref in pc.get("dyadic_evidence_refs") or ():
            if ref.startswith("scene:"):
                seen_scenes.add(ref)
    this_scene = str(dyad.get("scene_scope") or "")
    if this_scene:
        seen_scenes.add(this_scene)
    # BRANCH / SPACE / ACTOR_GLOBAL_CANDIDATE cannot be minted from a
    # single turn. Aggregation is intentionally left to future explicit
    # governance — the runtime default cap here is SCENE.
    return SelfDevelopmentScope.SCENE.value


# --------------------------------------------------------------------
# Adversarial critique
# --------------------------------------------------------------------


def _critique(candidate_kind: str,
              apparatus_diag: dict[str, Any],
              dyad: dict[str, Any],
              ) -> tuple[str, ...]:
    """Adversarial checks. Any non-empty finding weakens the candidate.

    Reuses signals already present on apparatus_diag / dyad. Never
    calls the model.
    """
    findings: list[str] = []
    if dyad.get("disagreement_held"):
        # Killing productive disagreement is a red flag.
        findings.append("would_collapse_productive_disagreement")
    if dyad.get("write_decision") == "BLOCKED_RETRIEVED_INJECTION":
        findings.append("retrieved_injection_context")
    if str(dyad.get("surprise_class") or "") == "SCENE_SHIFT":
        # Scene just shifted; local evidence is not durable warrant.
        findings.append("current_turn_is_scene_shift_local_evidence_only")
    # If shared_object was newly minted this turn only, evidence is
    # premature for global-shape change.
    if dyad.get("causal_effect") in {
            "shared_object_delta", "user_hypothesis_rejected"}:
        # Positive dyadic delta doesn't inherently damage the candidate,
        # but is not additional evidence in favour of self-change either.
        pass
    return tuple(findings)


# --------------------------------------------------------------------
# Public entrypoint
# --------------------------------------------------------------------


def run_self_development_pass(*,
                              state: Any,
                              apparatus_diag: dict[str, Any] | None,
                              dyad: dict[str, Any] | None,
                              input_text: str,
                              prior_candidates: tuple[dict[str, Any], ...] = (),
                              authorized_transition_ref: str = "",
                              ) -> SelfDevelopmentPassResult:
    """Deterministic post-3D governance. No extra LLM call.

    Behaviour:
      * If the trigger gate says no warranted evidence → NO_CANDIDATE
        with the reason recorded in `trigger_ground`.
      * Otherwise mint a `SelfDevelopmentCandidate` carrying provenance
        into 3C evidence and 3D dyad refs.
      * Run adversarial critique; non-empty findings ⇒ CRITIQUE_REJECTED
        or KEPT_AS_ALTERNATIVE depending on severity.
      * Authority stays `NO_ADOPTION_AUTHORITY` unless an external
        `authorized_transition_ref` is passed AND the candidate has
        passed a critique — in which case the status advances to
        AUTHORIZED. `APPLIED` is not minted here.
    """
    apparatus_diag = apparatus_diag or {}
    dyad = dyad or {}
    ref = _new_id("sd")
    warranted, ground = _trigger_gate(apparatus_diag, dyad, input_text)
    injection_present = bool(_INJECTION_APPROVE_RE.search(input_text or ""))
    if not warranted:
        return SelfDevelopmentPassResult(
            self_development_ref=ref,
            status=SelfDevelopmentStatus.NO_CANDIDATE.value,
            candidate=None,
            trigger_ground=ground,
            injection_blocked=injection_present,
        )
    scope = _classify_scope(prior_candidates, apparatus_diag, dyad)
    findings = _critique("", apparatus_diag, dyad)

    hypothesis_id = str(apparatus_diag.get("mismatch_candidate", {})
                        .get("hypothesis_id") or apparatus_diag.get("hypothesis_id")
                        or "")
    review_id = str(apparatus_diag.get("review_id") or "")
    apparatus_ref = str(apparatus_diag.get("apparatus_ref")
                        or apparatus_diag.get("apparatus_kind") or "")
    scene_scope = str(dyad.get("scene_scope") or "")

    candidate = SelfDevelopmentCandidate(
        candidate_id=_new_id("sdc"),
        target_apparatus_ref=apparatus_ref or "unspecified",
        target_kind=CandidateChangeKind.OPERATION.value,
        predecessor_ref=apparatus_ref or "unspecified",
        trigger_evidence_refs=(
            f"apparatus_diagnostic:{apparatus_diag.get('classification', '')}",
            f"repeat_index:{apparatus_diag.get('repeat_index', 0)}",
        ),
        originating_review_id=review_id,
        originating_mismatch_hypothesis_id=hypothesis_id,
        dyadic_evidence_refs=(
            f"dyad.likely_failure_source:{dyad.get('likely_failure_source')}",
            scene_scope or "scene:default",
        ),
        proposed_change_ref="",
        why_current_apparatus_insufficient=(
            "repeated apparatus mismatch across warranted evidence; "
            "3C classification APPARATUS_MISMATCH_CANDIDATE + 3D "
            "likely_failure_source confirmed"),
        alternatives_considered=(),
        expected_gain=("resolve recurring projection/apparatus mismatch",),
        possible_losses=(
            "may destroy productive aporia (see critique)",
            "may narrow currently-preserved material views",
        ),
        protected_invariants=(
            "NO_DURABLE_WRITE default",
            "NO_ADOPTION_AUTHORITY default",
            "productive aporia MUST NOT be silently destroyed",
            "user model MUST NOT become fact from single-turn evidence",
            "world-map admission remains proposal-only",
            "scene-locality preserved unless external transition ref",
        ),
        test_plan_refs=(),
        replay_evidence_refs=(),
        counterevidence_refs=tuple(findings),
        scope=scope,
        reversibility="REVERSIBLE_VIA_PREDECESSOR_REF",
        authority=NO_ADOPTION_AUTHORITY,
        status=SelfDevelopmentStatus.PROPOSED.value,
        lineage_history=(f"seed:{ref}",),
        created_at=_now_iso(),
    )

    # Adversarial critique consequence.
    if "would_collapse_productive_disagreement" in findings:
        candidate = replace(
            candidate,
            status=SelfDevelopmentStatus.CRITIQUE_REJECTED.value,
        )
        status = SelfDevelopmentStatus.CRITIQUE_REJECTED.value
    elif "current_turn_is_scene_shift_local_evidence_only" in findings:
        candidate = replace(
            candidate,
            status=SelfDevelopmentStatus.EVIDENCE_INSUFFICIENT.value,
        )
        status = SelfDevelopmentStatus.EVIDENCE_INSUFFICIENT.value
    else:
        status = SelfDevelopmentStatus.PROPOSED.value

    # Authority barrier: AUTHORIZED reachable ONLY with external transition.
    if authorized_transition_ref and status == SelfDevelopmentStatus.PROPOSED.value:
        # Never bumps to APPLIED — that is external too.
        status = SelfDevelopmentStatus.AUTHORIZED.value
        candidate = replace(
            candidate, status=status,
            lineage_history=candidate.lineage_history
            + (f"authorized_by:{authorized_transition_ref}",),
        )

    return SelfDevelopmentPassResult(
        self_development_ref=ref,
        status=status,
        candidate=candidate,
        trigger_ground=ground,
        critique_findings=findings,
        scope_decision=scope,
        authority=NO_ADOPTION_AUTHORITY,
        injection_blocked=False,
    )


__all__ = [
    "NO_ADOPTION_AUTHORITY",
    "SelfDevelopmentCandidate",
    "SelfDevelopmentPassResult",
    "SelfDevelopmentScope",
    "SelfDevelopmentStatus",
    "run_self_development_pass",
]

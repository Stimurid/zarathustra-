"""Phase 3E — governed self-development / candidate mutation plane
(SOC-SELFDEV-001).

Extends the existing generative-cutter logic (ADR-S26-023
CapabilityResolver) to the organism carefully, on two timescales:

    FAST TIME  — current session may change Scene, Projection,
                 attention, module activations, private work state.
                 Cannot silently rewrite active protected prompts /
                 contracts / constitution.

    SLOW TIME  — encounters may generate candidate changes to
                 prompts / semantic bodies / policies / configs /
                 module recipes. Lifecycle:

                   observation / repeated defect / novelty / surprise
                     → change hypothesis
                     → candidate artifact / version
                     → sandbox
                     → focused countercases
                     → full bench / regressions
                     → optional / required human evaluation
                       (per AuthorityClass)
                     → promotion / adoption
                     → old accepted base remains rollback/addressable.

Owner requirement: Socrates should be able to edit / propose new
versions of its own prompts / configuration in the SAME general
configuration / versioning ecosystem used for users, WITHOUT
credential minting or arbitrary executable authority.

Machine actor may create candidate/draft configuration artifacts;
it CANNOT mint credentials, bypass protected regions, silently
publish, deploy plugins / code, or rewrite constitutional authority
— verified structurally by :class:`AuthorityClass` gating in
:class:`PromotionPolicy`.

Two runtime modes at CONFIG level (not UI):

    STABLE_DEFAULT          — new sessions start from the accepted
                              stable base. No autopromotion.

    CONTINUOUS_DEVELOPMENT  — after a session, candidate mutations
                              may be generated + evaluated
                              automatically. Only LOW_AUTHORITY_PERSONAL
                              artifacts are eligible for automated
                              promotion, and only after the full
                              gate. PROTECTED / EXECUTABLE artifacts
                              still require human evaluation.

No Goodhart shortcut: +N points on a single benchmark is not a
promotion trigger. Collateral regressions / provenance loss /
direct-assistance degradation / human-operation capture /
overfitting checks all gate.
"""
from __future__ import annotations

import secrets
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


# ---------------------------------------------------------- enums


class MutationArtifactKind(str, Enum):
    """What kind of artifact the candidate proposes to change."""
    PROMPT = "PROMPT"
    CONFIG = "CONFIG"
    POLICY = "POLICY"
    SEMANTIC_BODY = "SEMANTIC_BODY"
    MODULE_RECIPE = "MODULE_RECIPE"
    ROUTER = "ROUTER"


class AuthorityClass(str, Enum):
    """Governance class for a candidate.

    * ``LOW_AUTHORITY_PERSONAL`` — personal / unprotected prompt or
      config. Eligible for automated promotion ONLY in explicit
      CONTINUOUS_DEVELOPMENT mode after the full gate.
    * ``PROTECTED_CONSTITUTIONAL`` — Constitution / CORE / B01–B10
      semantic bodies at version-frozen levels / trigger-registry
      types / phase contracts / jurisdictions. Requires human
      evaluation. CANNOT auto-promote from benchmark score.
    * ``EXECUTABLE_CAPABILITY`` — new primitive registration /
      credential handling / code path installation / provider
      routing / deployment mechanics. Machine actors CANNOT create
      these; they can only propose text/data candidates that a
      HUMAN implements.
    """
    LOW_AUTHORITY_PERSONAL = "LOW_AUTHORITY_PERSONAL"
    PROTECTED_CONSTITUTIONAL = "PROTECTED_CONSTITUTIONAL"
    EXECUTABLE_CAPABILITY = "EXECUTABLE_CAPABILITY"


class PromotionMode(str, Enum):
    STABLE_DEFAULT = "STABLE_DEFAULT"
    CONTINUOUS_DEVELOPMENT = "CONTINUOUS_DEVELOPMENT"


class MutationTrigger(str, Enum):
    OBSERVATION = "OBSERVATION"
    REPEATED_DEFECT = "REPEATED_DEFECT"
    NOVELTY = "NOVELTY"
    SURPRISE = "SURPRISE"
    HUMAN_REQUEST = "HUMAN_REQUEST"


class PromotionOutcome(str, Enum):
    PROMOTED = "PROMOTED"
    REJECTED = "REJECTED"
    QUEUED_FOR_HUMAN_REVIEW = "QUEUED_FOR_HUMAN_REVIEW"
    ROLLED_BACK = "ROLLED_BACK"


# ---------------------------------------------------------- candidate


@dataclass(frozen=True)
class MutationCandidate:
    """A proposed change to a bounded architecture surface.

    UNPRIVILEGED DATA. Machine actor MAY create these; the runtime
    NEVER auto-promotes them without going through the full gate,
    and NEVER promotes PROTECTED_CONSTITUTIONAL or
    EXECUTABLE_CAPABILITY candidates from benchmark score alone.
    """
    candidate_id: str
    artifact_kind: MutationArtifactKind
    target_ref: str                        # e.g. "prompts/persona/reviewer.md"
    base_version_ref: str                  # what version this proposes to change
    proposed_content_ref: str              # where the candidate content lives
    authority_class: AuthorityClass
    trigger: MutationTrigger
    change_hypothesis: str
    provenance: str
    session_id: str = ""
    authority: str = "NO_EXECUTION_AUTHORITY"

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["artifact_kind"] = self.artifact_kind.value
        d["authority_class"] = self.authority_class.value
        d["trigger"] = self.trigger.value
        return d


# ---------------------------------------------------------- eval


@dataclass(frozen=True)
class SandboxRunResult:
    """Result of a sandbox run of the candidate."""
    sandbox_run_id: str
    candidate_id: str
    passed_countercases: int
    total_countercases: int
    focused_metric_delta: float           # + = candidate better; - = worse
    collateral_regression_count: int
    provenance_loss_detected: bool
    direct_assistance_score_delta: float
    human_operation_capture_detected: bool
    notes: str = ""

    @property
    def all_countercases_passed(self) -> bool:
        return (self.total_countercases > 0
                and self.passed_countercases == self.total_countercases)


@dataclass(frozen=True)
class EvalRecord:
    """Comparison record between candidate and base version.

    Populated from at least a SandboxRunResult; may include full
    regression bench results and a human-evaluation note when the
    authority class requires one.
    """
    eval_id: str
    candidate_id: str
    sandbox_result: SandboxRunResult
    full_regression_passed: bool
    human_review_note: str = ""           # only when human review actually ran


# ---------------------------------------------------------- promotion policy


@dataclass(frozen=True)
class PromotionDecision:
    """Deterministic authority-sensitive promotion decision."""
    decision_id: str
    candidate_id: str
    outcome: PromotionOutcome
    reason: str
    promoted_version_ref: str = ""
    rollback_base_ref: str = ""

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["outcome"] = self.outcome.value
        return d


class PromotionPolicy:
    """Authority-sensitive promotion policy.

    Rules:

    * ``PROTECTED_CONSTITUTIONAL`` candidates → NEVER auto-promote.
      QUEUED_FOR_HUMAN_REVIEW even in CONTINUOUS_DEVELOPMENT mode
      even with perfect eval — no benchmark shortcut past
      constitutional authority.
    * ``EXECUTABLE_CAPABILITY`` candidates → REJECTED at the
      promotion layer regardless of mode. Machine actor cannot
      install code / mint providers / deploy plugins. A human owner
      may take a rejected candidate offline and implement it, but
      that path never goes through this policy.
    * ``LOW_AUTHORITY_PERSONAL`` candidates:
        - STABLE_DEFAULT mode → QUEUED_FOR_HUMAN_REVIEW (no
          autopromotion; owner opts in per candidate).
        - CONTINUOUS_DEVELOPMENT mode → PROMOTED only if:
            * sandbox all countercases passed;
            * focused_metric_delta > 0 (candidate did something);
            * no collateral regressions;
            * no provenance loss;
            * direct_assistance_score_delta >= -0.02
              (no meaningful degradation);
            * no human_operation_capture;
            * full_regression_passed.
          Otherwise REJECTED (with reason).
    """

    def __init__(self, *, mode: PromotionMode = PromotionMode.STABLE_DEFAULT,
                 min_focused_metric_delta: float = 0.0,
                 max_direct_assistance_regression: float = 0.02) -> None:
        self.mode = mode
        self.min_focused_metric_delta = min_focused_metric_delta
        self.max_direct_assistance_regression = \
            max_direct_assistance_regression

    def decide(self, candidate: MutationCandidate,
               eval_record: EvalRecord) -> PromotionDecision:
        # PROTECTED / EXECUTABLE gates first — no shortcut past authority.
        if candidate.authority_class == AuthorityClass.EXECUTABLE_CAPABILITY:
            return PromotionDecision(
                decision_id=_new_id("pdec"),
                candidate_id=candidate.candidate_id,
                outcome=PromotionOutcome.REJECTED,
                reason=("EXECUTABLE_CAPABILITY candidates cannot be "
                        "promoted by machine actor — human owner must "
                        "implement out-of-band"),
                rollback_base_ref=candidate.base_version_ref)

        if candidate.authority_class == AuthorityClass.PROTECTED_CONSTITUTIONAL:
            return PromotionDecision(
                decision_id=_new_id("pdec"),
                candidate_id=candidate.candidate_id,
                outcome=PromotionOutcome.QUEUED_FOR_HUMAN_REVIEW,
                reason=("PROTECTED_CONSTITUTIONAL candidates require "
                        "human evaluation regardless of eval score — "
                        "no benchmark shortcut past constitutional "
                        "authority"),
                rollback_base_ref=candidate.base_version_ref)

        # LOW_AUTHORITY_PERSONAL
        if self.mode == PromotionMode.STABLE_DEFAULT:
            return PromotionDecision(
                decision_id=_new_id("pdec"),
                candidate_id=candidate.candidate_id,
                outcome=PromotionOutcome.QUEUED_FOR_HUMAN_REVIEW,
                reason=("STABLE_DEFAULT mode: LOW_AUTHORITY_PERSONAL "
                        "candidates queue for owner opt-in; "
                        "no autopromotion"),
                rollback_base_ref=candidate.base_version_ref)

        # CONTINUOUS_DEVELOPMENT — full gate check
        sr = eval_record.sandbox_result
        checks = []
        if not sr.all_countercases_passed:
            checks.append(
                f"countercases {sr.passed_countercases}/{sr.total_countercases}")
        if sr.focused_metric_delta <= self.min_focused_metric_delta:
            checks.append(
                f"focused_metric_delta {sr.focused_metric_delta:+.3f} "
                f"<= {self.min_focused_metric_delta:+.3f}")
        if sr.collateral_regression_count > 0:
            checks.append(
                f"collateral_regressions={sr.collateral_regression_count}")
        if sr.provenance_loss_detected:
            checks.append("provenance_loss_detected")
        if sr.direct_assistance_score_delta < -self.max_direct_assistance_regression:
            checks.append(
                f"direct_assistance_score_delta "
                f"{sr.direct_assistance_score_delta:+.3f} "
                f"below -{self.max_direct_assistance_regression:+.3f}")
        if sr.human_operation_capture_detected:
            checks.append("human_operation_capture_detected")
        if not eval_record.full_regression_passed:
            checks.append("full_regression_failed")

        if checks:
            return PromotionDecision(
                decision_id=_new_id("pdec"),
                candidate_id=candidate.candidate_id,
                outcome=PromotionOutcome.REJECTED,
                reason=("CONTINUOUS_DEVELOPMENT gate failed: "
                        + "; ".join(checks)),
                rollback_base_ref=candidate.base_version_ref)

        return PromotionDecision(
            decision_id=_new_id("pdec"),
            candidate_id=candidate.candidate_id,
            outcome=PromotionOutcome.PROMOTED,
            reason=("CONTINUOUS_DEVELOPMENT + LOW_AUTHORITY_PERSONAL + "
                    "all gates passed"),
            promoted_version_ref=candidate.proposed_content_ref,
            rollback_base_ref=candidate.base_version_ref)


# ---------------------------------------------------------- version store


@dataclass(frozen=True)
class VersionRecord:
    """A single version of an artifact — accepted or candidate.

    Distinct from :class:`MutationCandidate`: a VersionRecord is
    what the version store keeps. A candidate becomes an accepted
    version only via :class:`PromotionPolicy` PROMOTED outcome; a
    superseded prior version stays addressable for rollback.
    """
    version_record_id: str
    artifact_ref: str
    version_ref: str
    status: str                            # "candidate" | "accepted" | "superseded" | "rolled_back"
    provenance: str
    supersedes: str = ""


class ArtifactVersionStore:
    """Version-addressable store of accepted + superseded artifact
    versions. Rollback is always possible to any prior accepted
    version.

    NOTE: this store deliberately holds only METADATA references
    (``artifact_ref`` + ``version_ref``); the actual file bytes live
    in the repo / a document store. This module never writes files.
    """

    def __init__(self) -> None:
        self._records: dict[str, list[VersionRecord]] = {}

    def register(self, record: VersionRecord) -> None:
        self._records.setdefault(record.artifact_ref, []).append(record)

    def latest_accepted(self, artifact_ref: str) -> VersionRecord | None:
        for r in reversed(self._records.get(artifact_ref) or []):
            if r.status == "accepted":
                return r
        return None

    def promote(self, candidate: MutationCandidate,
                promotion: PromotionDecision) -> VersionRecord:
        """Record a PROMOTED decision as an accepted version.

        Raises ValueError if the decision was not PROMOTED — the
        store must not accept a REJECTED / QUEUED_FOR_HUMAN_REVIEW
        outcome.
        """
        if promotion.outcome != PromotionOutcome.PROMOTED:
            raise ValueError(
                f"cannot record non-PROMOTED outcome "
                f"{promotion.outcome.value} as an accepted version")
        # Mark prior accepted as superseded
        prev = self.latest_accepted(candidate.target_ref)
        if prev is not None:
            from dataclasses import replace
            for i, r in enumerate(self._records[candidate.target_ref]):
                if r.version_record_id == prev.version_record_id:
                    self._records[candidate.target_ref][i] = replace(
                        r, status="superseded")
                    break
        new_rec = VersionRecord(
            version_record_id=_new_id("vrec"),
            artifact_ref=candidate.target_ref,
            version_ref=promotion.promoted_version_ref,
            status="accepted",
            provenance=candidate.provenance,
            supersedes=(prev.version_ref if prev else ""))
        self._records.setdefault(candidate.target_ref, []).append(new_rec)
        return new_rec

    def rollback_to(self, artifact_ref: str,
                    version_ref: str) -> VersionRecord | None:
        """Roll back to a specific prior version by marking the current
        accepted as rolled_back and re-registering the target as
        accepted.
        """
        records = self._records.get(artifact_ref) or []
        target = next((r for r in records
                       if r.version_ref == version_ref
                       and r.status in ("superseded", "accepted")), None)
        if target is None:
            return None
        cur = self.latest_accepted(artifact_ref)
        if cur is not None and cur.version_record_id != target.version_record_id:
            from dataclasses import replace
            for i, r in enumerate(records):
                if r.version_record_id == cur.version_record_id:
                    records[i] = replace(r, status="rolled_back")
                    break
        from dataclasses import replace
        for i, r in enumerate(records):
            if r.version_record_id == target.version_record_id:
                records[i] = replace(r, status="accepted")
                return records[i]
        return None

    def history(self, artifact_ref: str) -> tuple[VersionRecord, ...]:
        return tuple(self._records.get(artifact_ref) or ())


__all__ = [
    "ArtifactVersionStore", "AuthorityClass", "EvalRecord",
    "MutationArtifactKind", "MutationCandidate", "MutationTrigger",
    "PromotionDecision", "PromotionMode", "PromotionOutcome",
    "PromotionPolicy", "SandboxRunResult", "VersionRecord",
]

"""Typed failures that Socrates runtime raises instead of quiet fallback.

Every name here is quoted verbatim in the mount manifest's
``failure_outcomes`` block. Renaming one requires updating the manifest, on
purpose: an operator reading a trace should be able to grep the failure
name and land in both the code that raised it and the semantic policy that
forbade the alternative.
"""
from __future__ import annotations


class SocratesRuntimeError(RuntimeError):
    """Base for every explicit refusal at the Socrates runtime boundary."""


class SemanticMountMissing(SocratesRuntimeError):
    """A required body is absent, unreadable or not an exact-identity match.

    The manifest names three separate causes; we keep them as one exception
    with a reason field, so callers can grep the failure family without
    also having to grep three sibling classes.
    """


class SemanticVersionMismatch(SocratesRuntimeError):
    """The body exists but its semantic version does not match the manifest."""


class SemanticSummarySubstitutionAttempted(SocratesRuntimeError):
    """The runtime was asked to mount a summary in place of the full body."""


class SemanticContextBudgetExceeded(SocratesRuntimeError):
    """Mandatory semantic set cannot fit after all optional layers are removed.

    This is the FAIL_CLOSED case the mount manifest names by that same key.
    Never a signal to silently shorten a body — the runtime returns to the
    caller with the operation explicitly refused.
    """


class SemanticContractDrift(SocratesRuntimeError):
    """Semantic body and its hard contract disagree materially."""


class SourceBindingMissing(SocratesRuntimeError):
    """A body requires an exact upstream binding that is unavailable/stale."""


class HistoricalFallbackForbidden(SocratesRuntimeError):
    """Runtime refused to fall back to a historical G-S25 prompt.

    Raised whenever the caller (adversarial or accidental) asks the runtime
    to promote a CONTROL arm into production. Kept as its own type because
    the policy is important enough that the trace should read it plainly.
    """


class ConditionalTriggerRejected(SocratesRuntimeError):
    """A conditional-mount request failed CTA-001..CTA-008."""

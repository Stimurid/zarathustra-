"""Workbench identity — users, sessions and personal ownership.

Separate from ``californian_id.users``: that package authenticates callers of
the Tinkuy runtime API. This one is about *who owns a PipelineConfig*, and
answers a narrower question — which UserStore signs the assertion "this is my
active build". Same repository, same hash primitives; different concern.

Onboarding follows the Paideia pattern: a curator mints a code, the operator
redeems it and picks a display name — no self-registration form.

Roles:
    user     — may author personal builds (:mod:`workbench_configs`).
    curator  — may additionally publish a build as the line default.
    admin    — may mint auth codes and manage users.

Nothing here decides authorization for individual actions; that belongs to
``workbench_configs`` and to the HTTP layer. This package only issues honest
identities and verifies them.
"""
from __future__ import annotations

from .models import AuthCode, Role, Session, User
from .service import (
    AuthError,
    InvalidCode,
    RedemptionResult,
    UnknownUser,
    WorkbenchAuth,
)
from .store import WorkbenchAuthStore
from .tokens import TokenError, issue_token, verify_token

__all__ = [
    "AuthCode",
    "AuthError",
    "InvalidCode",
    "RedemptionResult",
    "Role",
    "Session",
    "TokenError",
    "UnknownUser",
    "User",
    "WorkbenchAuth",
    "WorkbenchAuthStore",
    "issue_token",
    "verify_token",
]

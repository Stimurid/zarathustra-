"""Domain types for Workbench identity — no persistence here, no HTTP here.

Kept as plain dataclasses so a caller can produce and inspect a User without
touching a database. The store owns durability; these types own shape.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


class Role:
    """The three roles the Workbench distinguishes.

    Not an ``enum.Enum`` on purpose: role strings cross the JWT boundary and
    are stored in JSON columns. A bare string keeps the JWT payload readable
    and avoids two shapes for one concept.
    """

    USER = "user"
    CURATOR = "curator"
    ADMIN = "admin"

    ALL: frozenset[str] = frozenset({"user", "curator", "admin"})

    @staticmethod
    def normalise(role: str) -> str:
        """Reject unknown role strings loudly at the boundary."""
        r = (role or "").strip().lower()
        if r not in Role.ALL:
            raise ValueError(f"unknown role {role!r}; expected one of {sorted(Role.ALL)}")
        return r


@dataclass(frozen=True)
class User:
    user_id: str
    display_name: str
    roles: tuple[str, ...]
    created_at: str
    disabled: bool = False

    def has_role(self, role: str) -> bool:
        return Role.normalise(role) in self.roles

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["roles"] = list(self.roles)
        return d


@dataclass(frozen=True)
class AuthCode:
    """One-shot redemption code minted by a curator.

    ``roles`` is the set of roles the redeemer will get. That reflects a
    real practice: a curator hands out ``curator`` codes only when the
    receiver is meant to publish line defaults; the default is ``user``.
    """
    code: str
    roles: tuple[str, ...]
    minted_by: str
    minted_at: str
    expires_at: str = ""
    redeemed_by: str = ""
    redeemed_at: str = ""
    note: str = ""

    @property
    def redeemed(self) -> bool:
        return bool(self.redeemed_by)

    def to_public(self, *, reveal_code: bool = False) -> dict[str, Any]:
        d = asdict(self)
        d["roles"] = list(self.roles)
        if not reveal_code:
            # A minted code is a secret until it reaches the intended human;
            # listings show only the tail, so an operator can identify their
            # code without leaking the whole batch.
            d["code"] = f"…{self.code[-4:]}"
        return d


@dataclass(frozen=True)
class Session:
    """A minted JWT and the identity behind it."""
    token: str
    user: User
    expires_at: int
    issued_at: int

    def to_public(self) -> dict[str, Any]:
        return {
            "token": self.token,
            "expires_at": self.expires_at,
            "issued_at": self.issued_at,
            "user": self.user.to_public(),
        }

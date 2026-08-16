"""Public facade — all callers go through here, no one imports the store.

Enforces the small handful of invariants that must not be scattered across
callers:

    * a code can be redeemed exactly once;
    * an expired code cannot be redeemed;
    * a display name is picked at redemption time and belongs to the user;
    * password login is available when a password was set, and never
      substitutes an empty hash for a match;
    * roles named at redemption come from the code, not from the request.

Nothing about *authorization* lives here — that is per-action policy owned by
whoever owns the action.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .models import AuthCode, Role, Session, User
from .passwords import hash_password, verify_password
from .store import WorkbenchAuthStore
from .tokens import DEFAULT_TTL_SEC, issue_token, verify_token


class AuthError(Exception):
    """Anything the caller passed that we refuse to accept."""


class InvalidCode(AuthError):
    """Redemption failed for a reason the user should hear plainly."""


class UnknownUser(AuthError):
    """Token verified, but the subject no longer exists or is disabled."""


@dataclass(frozen=True)
class RedemptionResult:
    user: User
    session: Session
    code: AuthCode


class WorkbenchAuth:
    def __init__(self, store: WorkbenchAuthStore,
                 state_dir: Path | None = None,
                 token_ttl_sec: int = DEFAULT_TTL_SEC) -> None:
        self.store = store
        self.state_dir = Path(state_dir) if state_dir else store.db_path.parent
        self.token_ttl_sec = int(token_ttl_sec)

    # ---------- bootstrap ----------

    def ensure_seed_admin(self, display_name: str = "operator",
                          note: str = "seed") -> AuthCode | None:
        """First run only: mint one admin code if the user table is empty.

        Returns the minted code, or ``None`` if the system already has users.
        The code is minted by the string ``"system"`` so it is visible in
        listings as bootstrap, not attributed to a real operator.
        """
        if self.store.list_users(limit=1):
            return None
        return self.store.mint_code([Role.ADMIN], minted_by="system", note=note)

    # ---------- codes ----------

    def mint_code(self, roles: list[str], minted_by_user: User,
                  expires_in_hours: int = 168, note: str = "") -> AuthCode:
        """Mint a code. Only admins may hand out admin/curator roles.

        A curator may mint ``user`` codes for their own workspace but may not
        mint ``curator`` or ``admin`` codes — that would let curator authority
        propagate horizontally without an admin having authorised it.
        """
        wanted = {Role.normalise(r) for r in roles} or {Role.USER}
        if not minted_by_user.has_role(Role.ADMIN):
            if not minted_by_user.has_role(Role.CURATOR):
                raise AuthError("only curators or admins may mint auth codes")
            if wanted - {Role.USER}:
                raise AuthError(
                    "curator may mint only 'user' codes; admin required for "
                    "'curator' or 'admin' codes")
        expires_at = ""
        if expires_in_hours > 0:
            expires_ts = time.time() + expires_in_hours * 3600
            expires_at = datetime.fromtimestamp(
                expires_ts, tz=timezone.utc).isoformat()
        return self.store.mint_code(sorted(wanted), minted_by_user.user_id,
                                    expires_at=expires_at, note=note)

    # ---------- redemption ----------

    def redeem(self, code: str, display_name: str,
               password: str = "") -> RedemptionResult:
        c = self.store.get_code(code)
        if c is None:
            raise InvalidCode("код не найден")
        if c.redeemed:
            raise InvalidCode("код уже использован")
        if c.expires_at:
            # Compare as isoformat strings — timezone is baked in on write.
            if datetime.fromisoformat(c.expires_at) < datetime.now(timezone.utc):
                raise InvalidCode("код истёк")
        pw_hash, pw_salt, pw_iters = hash_password(password) if password else (
            b"", b"", 0)
        try:
            user = self.store.add_user(
                display_name, c.roles, pw_hash=pw_hash, pw_salt=pw_salt,
                pw_iters=pw_iters)
        except ValueError as exc:
            raise InvalidCode(str(exc)) from None
        self.store.mark_redeemed(c.code, user.user_id)
        session = self._issue_session(user)
        redeemed = self.store.get_code(c.code)          # type: ignore[assignment]
        return RedemptionResult(user=user, session=session, code=redeemed)

    # ---------- login by password ----------

    def login(self, display_name: str, password: str) -> Session:
        user = self.store.get_user_by_name(display_name)
        if user is None or user.disabled:
            raise AuthError("неверное имя или пароль")
        mat = self.store.get_password_material(user.user_id)
        if mat is None or not any((mat[0], mat[1], mat[2])):
            raise AuthError("для этого аккаунта пароль не установлен")
        if not verify_password(password, *mat):
            raise AuthError("неверное имя или пароль")
        return self._issue_session(user)

    def set_password(self, user: User, new_password: str) -> None:
        if not new_password or len(new_password) < 8:
            raise AuthError("пароль слишком короткий (минимум 8 символов)")
        pw_hash, pw_salt, pw_iters = hash_password(new_password)
        self.store.set_password(user.user_id, pw_hash, pw_salt, pw_iters)

    # ---------- verification ----------

    def verify(self, token: str) -> User:
        """Return the current user for a signed token.

        The token proves *identity*. Roles come from the store — always.
        A stale token whose ``roles`` claim disagrees with the store cannot
        expand authority (the store had to grant it) and cannot preserve
        revoked authority (the store had to still have it). Every action
        that cares about a role reads it from :class:`User`, not from the
        claim.
        """
        claims = verify_token(token, state_dir=self.state_dir)
        sub = claims.get("sub")
        user = self.store.get_user(sub) if sub else None
        if user is None or user.disabled:
            raise UnknownUser(f"пользователь не найден или отключён: {sub!r}")
        return user

    def _issue_session(self, user: User) -> Session:
        token, iat, exp = issue_token(
            user.user_id, list(user.roles),
            ttl_sec=self.token_ttl_sec,
            extra_claims={"name": user.display_name},
            state_dir=self.state_dir,
        )
        return Session(token=token, user=user, expires_at=exp, issued_at=iat)

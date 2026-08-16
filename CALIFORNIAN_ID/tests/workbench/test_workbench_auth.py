"""Workbench identity — code-redemption onboarding + JWT + role invariants."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from workbench_auth import (
    AuthError,
    InvalidCode,
    Role,
    TokenError,
    UnknownUser,
    WorkbenchAuth,
    WorkbenchAuthStore,
    verify_token,
)
from workbench_auth.tokens import issue_token


@pytest.fixture()
def auth(tmp_path):
    store = WorkbenchAuthStore(tmp_path / "auth.sqlite3")
    return WorkbenchAuth(store, state_dir=tmp_path, token_ttl_sec=3600)


# ---------------- bootstrap + redemption ----------------

def test_seed_admin_created_only_when_no_users(auth):
    code = auth.ensure_seed_admin()
    assert code is not None
    assert Role.ADMIN in code.roles
    assert code.minted_by == "system"

    # After redeeming, seeding is a no-op
    auth.redeem(code.code, "operator")
    assert auth.ensure_seed_admin() is None


def test_redemption_binds_display_name_and_roles_from_code(auth):
    code = auth.ensure_seed_admin()
    result = auth.redeem(code.code, "operator")
    assert result.user.display_name == "operator"
    assert set(result.user.roles) == {Role.ADMIN}
    assert result.code.redeemed is True
    assert result.code.redeemed_by == result.user.user_id


def test_code_cannot_be_redeemed_twice(auth):
    code = auth.ensure_seed_admin()
    auth.redeem(code.code, "first")
    with pytest.raises(InvalidCode, match="уже"):
        auth.redeem(code.code, "second")


def test_expired_code_is_refused(tmp_path):
    store = WorkbenchAuthStore(tmp_path / "auth.sqlite3")
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    store._conn.execute(
        "INSERT INTO workbench_auth_code (code, roles_json, minted_by, minted_at, "
        "expires_at) VALUES ('EXPIRED-CODE', '[\"user\"]', 'system', ?, ?)",
        (datetime.now(timezone.utc).isoformat(), past),
    )
    auth = WorkbenchAuth(store, state_dir=tmp_path)
    with pytest.raises(InvalidCode, match="истёк"):
        auth.redeem("EXPIRED-CODE", "victim")


def test_unknown_code_is_refused_cleanly(auth):
    with pytest.raises(InvalidCode, match="не найден"):
        auth.redeem("NOPE-NOPE-NOPE", "victim")


def test_display_name_uniqueness_is_enforced(auth):
    c1 = auth.ensure_seed_admin()
    auth.redeem(c1.code, "operator")
    c2 = auth.store.mint_code([Role.USER], minted_by="system")
    with pytest.raises(InvalidCode, match="already taken"):
        auth.redeem(c2.code, "operator")


# ---------------- role authority invariants ----------------

def test_only_admin_may_mint_privileged_codes(auth):
    admin_code = auth.ensure_seed_admin()
    admin = auth.redeem(admin_code.code, "admin").user

    curator_code = auth.mint_code([Role.CURATOR], minted_by_user=admin)
    curator = auth.redeem(curator_code.code, "curator").user
    assert Role.CURATOR in curator.roles

    # A curator may mint 'user' codes for themselves
    user_code = auth.mint_code([Role.USER], minted_by_user=curator)
    assert Role.USER in user_code.roles

    # …but never 'curator' or 'admin' codes
    with pytest.raises(AuthError, match="admin required"):
        auth.mint_code([Role.CURATOR], minted_by_user=curator)
    with pytest.raises(AuthError, match="admin required"):
        auth.mint_code([Role.ADMIN], minted_by_user=curator)


def test_plain_user_cannot_mint_at_all(auth):
    admin_code = auth.ensure_seed_admin()
    admin = auth.redeem(admin_code.code, "admin").user
    user_code = auth.mint_code([Role.USER], minted_by_user=admin)
    user = auth.redeem(user_code.code, "user").user

    with pytest.raises(AuthError, match="curators or admins"):
        auth.mint_code([Role.USER], minted_by_user=user)


# ---------------- password flow ----------------

def test_password_login_when_set(auth):
    code = auth.ensure_seed_admin()
    result = auth.redeem(code.code, "operator", password="correct-horse-battery")
    session = auth.login("operator", "correct-horse-battery")
    assert session.user.user_id == result.user.user_id

    with pytest.raises(AuthError, match="неверное"):
        auth.login("operator", "wrong")


def test_empty_password_account_refuses_login(auth):
    code = auth.ensure_seed_admin()
    result = auth.redeem(code.code, "operator")  # no password
    with pytest.raises(AuthError, match="не установлен"):
        auth.login("operator", "")
    with pytest.raises(AuthError, match="не установлен"):
        auth.login("operator", "anything")


def test_set_password_rejects_short(auth):
    code = auth.ensure_seed_admin()
    result = auth.redeem(code.code, "operator")
    with pytest.raises(AuthError, match="слишком короткий"):
        auth.set_password(result.user, "short")
    auth.set_password(result.user, "long-enough-password")
    auth.login("operator", "long-enough-password")


# ---------------- JWT ----------------

def test_verify_returns_the_user(auth):
    code = auth.ensure_seed_admin()
    result = auth.redeem(code.code, "operator")
    checked = auth.verify(result.session.token)
    assert checked.user_id == result.user.user_id
    assert Role.ADMIN in checked.roles


def test_verify_rejects_malformed_and_unsigned(auth, tmp_path):
    with pytest.raises(TokenError):
        verify_token("not-a-token", state_dir=tmp_path)
    with pytest.raises(TokenError):
        verify_token("aaa.bbb.ccc", state_dir=tmp_path)


def test_verify_rejects_expired_token(auth):
    code = auth.ensure_seed_admin()
    result = auth.redeem(code.code, "operator")
    # Mint a stale token in-place with ttl 0 so it is already expired.
    stale, _iat, _exp = issue_token(result.user.user_id, list(result.user.roles),
                                    ttl_sec=-10, state_dir=auth.state_dir)
    time.sleep(0.01)
    with pytest.raises(TokenError, match="expired"):
        verify_token(stale, state_dir=auth.state_dir)


def test_verify_rejects_unknown_subject(auth):
    code = auth.ensure_seed_admin()
    result = auth.redeem(code.code, "operator")
    # Remove the user; the token remains cryptographically valid
    auth.store._conn.execute(
        "DELETE FROM workbench_user WHERE user_id=?", (result.user.user_id,))
    with pytest.raises(UnknownUser):
        auth.verify(result.session.token)


def test_role_narrowing_on_verify(auth):
    """A token role claim cannot exceed the user's current roles."""
    admin_code = auth.ensure_seed_admin()
    admin = auth.redeem(admin_code.code, "admin")
    # Narrow the user's roles after the token was issued
    auth.store.set_roles(admin.user.user_id, [Role.USER])
    checked = auth.verify(admin.session.token)
    assert Role.ADMIN not in checked.roles
    assert Role.USER in checked.roles


def test_workbench_jwt_secret_is_separate_from_runtime(auth, monkeypatch, tmp_path):
    """Runtime and Workbench must not be confusable by token exchange.

    A token minted with the runtime's ``CALIFORNIAN_ID_JWT_SECRET`` must not
    verify against a Workbench that has ``WORKBENCH_JWT_SECRET`` set.
    """
    monkeypatch.setenv("WORKBENCH_JWT_SECRET", "workbench-only")
    monkeypatch.setenv("CALIFORNIAN_ID_JWT_SECRET", "runtime-only")

    from californian_id.jwt_auth import issue_token as runtime_issue

    runtime_token = runtime_issue(sub="anyone", roles=["admin"])
    with pytest.raises(TokenError):
        verify_token(runtime_token, state_dir=tmp_path)


# ---------------- listings ----------------

def test_codes_are_masked_in_listings(auth):
    code = auth.ensure_seed_admin()
    admin = auth.redeem(code.code, "admin").user
    minted = auth.mint_code([Role.USER], minted_by_user=admin, note="for Kate")
    listed = auth.store.list_codes()
    public = [c.to_public() for c in listed]
    assert any(p["code"].startswith("…") for p in public)
    # But the raw store still holds the full code for the operator to reveal
    reveal = [c.to_public(reveal_code=True) for c in listed]
    assert any("-" in r["code"] for r in reveal)

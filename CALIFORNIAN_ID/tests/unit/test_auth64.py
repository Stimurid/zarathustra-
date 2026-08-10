"""Пик 6.4 — users store + JWT auth."""
from __future__ import annotations

import time

import pytest

from californian_id import auth, jwt_auth


# ---------- 6.4.1 users ----------
def test_users_add_and_verify(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.users.RUNS_DIR", tmp_path)
    from californian_id.users import UserStore
    store = UserStore(db_path=tmp_path / "users.sqlite3")
    try:
        u = store.add("alice", "s3cret-p@ss", roles=["user", "editor"])
        assert u.username == "alice"
        assert u.roles == ["user", "editor"]
        verified = store.verify("alice", "s3cret-p@ss")
        assert verified is not None
        assert verified.username == "alice"
        assert store.verify("alice", "wrong") is None
        assert store.verify("nobody", "any") is None
    finally:
        store.close()


def test_users_add_rejects_short_password(tmp_path):
    from californian_id.users import UserStore
    store = UserStore(db_path=tmp_path / "u.db")
    try:
        with pytest.raises(ValueError, match="password too short"):
            store.add("alice", "short")
    finally:
        store.close()


def test_users_add_rejects_bad_username(tmp_path):
    from californian_id.users import UserStore
    store = UserStore(db_path=tmp_path / "u.db")
    try:
        for bad in ["../etc", "with space", "user/x", ""]:
            with pytest.raises(ValueError):
                store.add(bad, "goodpass12")
    finally:
        store.close()


def test_users_delete_and_disable(tmp_path):
    from californian_id.users import UserStore
    store = UserStore(db_path=tmp_path / "u.db")
    try:
        store.add("bob", "goodpass12")
        assert store.set_disabled("bob", True)
        assert store.verify("bob", "goodpass12") is None
        assert store.set_disabled("bob", False)
        assert store.verify("bob", "goodpass12") is not None
        assert store.delete("bob")
        assert not store.delete("bob")
    finally:
        store.close()


def test_users_list(tmp_path):
    from californian_id.users import UserStore
    store = UserStore(db_path=tmp_path / "u.db")
    try:
        store.add("alice", "pass1234")
        store.add("bob", "pass1234")
        names = {u.username for u in store.list()}
        assert names == {"alice", "bob"}
    finally:
        store.close()


# ---------- 6.4.2 JWT ----------
def test_jwt_round_trip(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.jwt_auth.RUNS_DIR", tmp_path)
    tok = jwt_auth.issue_token(sub="alice", roles=["user"])
    payload = jwt_auth.verify_token(tok)
    assert payload["sub"] == "alice"
    assert payload["roles"] == ["user"]
    assert payload["iss"] == "tinkuy"
    assert isinstance(payload["exp"], int)


def test_jwt_looks_like_jwt(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.jwt_auth.RUNS_DIR", tmp_path)
    tok = jwt_auth.issue_token(sub="x")
    assert jwt_auth.looks_like_jwt(tok)
    assert not jwt_auth.looks_like_jwt("not-a-jwt")
    assert not jwt_auth.looks_like_jwt("")
    assert not jwt_auth.looks_like_jwt("a.b")


def test_jwt_rejects_bad_signature(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.jwt_auth.RUNS_DIR", tmp_path)
    tok = jwt_auth.issue_token(sub="x")
    parts = tok.split(".")
    tampered = ".".join(parts[:2] + ["AAAAAA"])
    with pytest.raises(jwt_auth.JWTError):
        jwt_auth.verify_token(tampered)


def test_jwt_rejects_expired(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.jwt_auth.RUNS_DIR", tmp_path)
    tok = jwt_auth.issue_token(sub="x", ttl_sec=1)
    time.sleep(1.5)
    with pytest.raises(jwt_auth.JWTError, match="expired"):
        jwt_auth.verify_token(tok)


def test_jwt_secret_persisted(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.jwt_auth.RUNS_DIR", tmp_path)
    monkeypatch.delenv(jwt_auth.JWT_ENV, raising=False)
    tok1 = jwt_auth.issue_token(sub="x")
    # secret file must have been created
    secret_path = tmp_path / "jwt.secret"
    assert secret_path.exists()
    # verify still works after "restart" (same file)
    payload = jwt_auth.verify_token(tok1)
    assert payload["sub"] == "x"


# ---------- 6.4.3 label_for_bearer via JWT ----------
def test_label_for_bearer_recognizes_jwt(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.jwt_auth.RUNS_DIR", tmp_path)
    tok = jwt_auth.issue_token(sub="alice", roles=["user"])
    label = auth.label_for_bearer(tok)
    assert label == "jwt:alice"


def test_label_for_bearer_rejects_bad_jwt(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.jwt_auth.RUNS_DIR", tmp_path)
    parts = jwt_auth.issue_token(sub="x").split(".")
    tampered = ".".join(parts[:2] + ["AAAAAA"])
    assert auth.label_for_bearer(tampered) is None

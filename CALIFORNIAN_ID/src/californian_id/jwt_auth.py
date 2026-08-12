"""Пик 6.4.2 — JWT issue/verify (HS256, только stdlib).

RFC 7519 совместимый JWT минимальной реализации. HS256 через hmac-sha256.

Secret:
  1. env CALIFORNIAN_ID_JWT_SECRET (base64url или сырой)
  2. persisted в RUNS_DIR/jwt.secret (auto-generated при первом запуске)

Не PoC-crypto: base64url без padding, constant-time compare, standard claims
(iss, iat, exp, sub, roles).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

from .config import RUNS_DIR


JWT_ENV = "CALIFORNIAN_ID_JWT_SECRET"
ALG = "HS256"
ISS = "tinkuy"
DEFAULT_TTL_SEC = 24 * 3600  # 24h


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _secret_bytes() -> bytes:
    """Load secret from env or from persisted file. Persist auto-generated."""
    env = os.environ.get(JWT_ENV, "").strip()
    if env:
        # If looks base64url — decode; иначе raw
        try:
            raw = _b64url_decode(env)
            if len(raw) >= 32:
                return raw
        except Exception:
            pass
        # Треhем raw bytes длиной ≥32
        raw = env.encode("utf-8")
        if len(raw) < 32:
            # растянуть через sha256
            raw = hashlib.sha256(raw).digest()
        return raw
    path = RUNS_DIR / "jwt.secret"
    if path.exists():
        return path.read_bytes()
    # generate
    secret = secrets.token_bytes(48)
    try:
        path.write_bytes(secret)
        try:
            os.chmod(path, 0o600)
        except Exception:
            pass
    except Exception:
        pass
    return secret


def issue_token(
    sub: str,
    roles: list[str] | None = None,
    ttl_sec: int = DEFAULT_TTL_SEC,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = int(time.time())
    header = {"alg": ALG, "typ": "JWT"}
    payload: dict[str, Any] = {
        "iss": ISS,
        "sub": sub,
        "iat": now,
        "exp": now + int(ttl_sec),
        "roles": list(roles or []),
    }
    if extra_claims:
        payload.update(extra_claims)
    h = _b64url_encode(json.dumps(header, separators=(",", ":"),
                                  ensure_ascii=False).encode("utf-8"))
    p = _b64url_encode(json.dumps(payload, separators=(",", ":"),
                                  ensure_ascii=False).encode("utf-8"))
    signing_input = f"{h}.{p}".encode("ascii")
    sig = hmac.new(_secret_bytes(), signing_input, hashlib.sha256).digest()
    s = _b64url_encode(sig)
    return f"{h}.{p}.{s}"


class JWTError(Exception):
    pass


def verify_token(token: str) -> dict[str, Any]:
    if not token or token.count(".") != 2:
        raise JWTError("malformed token")
    h_b64, p_b64, s_b64 = token.split(".")
    try:
        header = json.loads(_b64url_decode(h_b64))
    except Exception as exc:
        raise JWTError(f"header parse: {exc}")
    if header.get("alg") != ALG or header.get("typ") not in {"JWT", None}:
        raise JWTError(f"unsupported alg/typ")
    signing_input = f"{h_b64}.{p_b64}".encode("ascii")
    expected = hmac.new(_secret_bytes(), signing_input, hashlib.sha256).digest()
    try:
        got = _b64url_decode(s_b64)
    except Exception:
        raise JWTError("signature b64 decode")
    if not hmac.compare_digest(expected, got):
        raise JWTError("bad signature")
    try:
        payload = json.loads(_b64url_decode(p_b64))
    except Exception as exc:
        raise JWTError(f"payload parse: {exc}")
    now = int(time.time())
    exp = payload.get("exp")
    if exp is not None and now >= int(exp):
        raise JWTError("expired")
    iat = payload.get("iat")
    if iat is not None and int(iat) > now + 60:
        raise JWTError("iat in future")
    if payload.get("iss") not in {ISS, None}:
        raise JWTError("bad issuer")
    return payload


def looks_like_jwt(token: str) -> bool:
    """Быстрая эвристика: три сегмента base64url + первый декодируется как
    JSON с полем 'alg'."""
    if not token or token.count(".") != 2:
        return False
    try:
        h = json.loads(_b64url_decode(token.split(".", 1)[0]))
        return "alg" in h
    except Exception:
        return False

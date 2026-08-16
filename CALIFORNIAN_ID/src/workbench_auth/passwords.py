"""Password hashing — PBKDF2-SHA256 with the same cost as ``californian_id.users``.

Constant chosen once (200_000 iterations) to match the rest of this
repository. If bcrypt is preferred later, this file is the single place to
change: every caller goes through ``hash_password`` / ``verify_password``.

Empty passwords are legal because Workbench also supports code-redemption
onboarding, where a user has no password at all. An empty stored hash accepts
only an empty input — never a wildcard.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

ITERATIONS = 200_000
SALT_BYTES = 16
DK_LEN = 32


def hash_password(plain: str, salt: bytes | None = None,
                  iters: int = ITERATIONS) -> tuple[bytes, bytes, int]:
    """Return (hash, salt, iters) so callers can persist all three."""
    if plain == "":
        return b"", b"", 0
    salt = salt or secrets.token_bytes(SALT_BYTES)
    dk = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, iters, DK_LEN)
    return dk, salt, iters


def verify_password(plain: str, pw_hash: bytes, salt: bytes, iters: int) -> bool:
    """Timing-safe. Empty stored hash matches only an empty attempt."""
    if not pw_hash and not salt and iters == 0:
        return plain == ""
    if plain == "":
        return False
    dk = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, iters, DK_LEN)
    return hmac.compare_digest(dk, pw_hash)

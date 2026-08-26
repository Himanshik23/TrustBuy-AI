"""Argon2id password hashing (docs/SECURITY.md §1).

`argon2.PasswordHasher` defaults to the Argon2id variant with sane
time/memory cost parameters - no bcrypt fallback, per DECISIONS.md.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        # Malformed/legacy hash, or any other unexpected argon2 error - treat as
        # a failed verification rather than raising through to a 500.
        return False


def needs_rehash(password_hash: str) -> bool:
    """True if the hash was created with weaker-than-current parameters -
    callers should re-hash and persist on the next successful login."""
    try:
        return _hasher.check_needs_rehash(password_hash)
    except Exception:
        return False

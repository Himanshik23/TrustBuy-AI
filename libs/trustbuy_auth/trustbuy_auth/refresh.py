"""Opaque refresh-token generation/hashing.

The raw token is returned to the client exactly once (set as an httpOnly
cookie by the Authentication Service) and never stored; only its SHA-256
hash lives in `refresh_tokens.token_hash`, so a leaked database can't be
used to forge sessions.
"""

from __future__ import annotations

import hashlib
import os
import secrets

REFRESH_TOKEN_TTL_DAYS = int(os.environ.get("REFRESH_TOKEN_TTL_DAYS", 30))


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

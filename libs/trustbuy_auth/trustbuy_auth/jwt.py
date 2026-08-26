"""RS256 access-token issuance/verification (docs/SECURITY.md §1-2,
DECISIONS.md ADR-006).

Access tokens are short-lived stateless JWTs. Refresh tokens are opaque
random strings (not JWTs) whose *hash* is stored in the `refresh_tokens`
table so they can be individually revoked - see `refresh.py`.
"""

from __future__ import annotations

import os
import time
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import jwt as pyjwt

Role = Literal["user", "moderator", "admin"]

ACCESS_TOKEN_TTL_SECONDS = int(os.environ.get("ACCESS_TOKEN_TTL_SECONDS", 15 * 60))


class TokenError(Exception):
    """Raised for any invalid, expired, or malformed access token."""


@lru_cache
def _private_key() -> str:
    path = Path(os.environ.get("JWT_PRIVATE_KEY_PATH", "/keys/private.pem"))
    return path.read_text()


@lru_cache
def _public_key() -> str:
    path = Path(os.environ.get("JWT_PUBLIC_KEY_PATH", "/keys/public.pem"))
    return path.read_text()


def create_access_token(
    *, subject: str, role: Role, extra: dict[str, Any] | None = None, expires_in: int = ACCESS_TOKEN_TTL_SECONDS
) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + expires_in,
        "jti": str(uuid.uuid4()),
    }
    if extra:
        payload.update(extra)
    return pyjwt.encode(payload, _private_key(), algorithm="RS256")


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        claims = pyjwt.decode(token, _public_key(), algorithms=["RS256"])
    except pyjwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc
    if claims.get("type") != "access":
        raise TokenError("Not an access token.")
    return claims

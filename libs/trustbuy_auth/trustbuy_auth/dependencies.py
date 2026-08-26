"""FastAPI dependencies for authentication/RBAC, shared by the Gateway and
every downstream service (docs/SECURITY.md §1).
"""

from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from trustbuy_auth.jwt import TokenError, decode_access_token
from trustbuy_common.errors import ForbiddenError, UnauthorizedError

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict:
    """Require a valid access token; raises 401 otherwise."""
    if credentials is None:
        raise UnauthorizedError("Missing bearer token.")
    try:
        return decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise UnauthorizedError("Invalid or expired token.") from exc


async def get_optional_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict | None:
    """Same as get_current_claims but returns None instead of raising -
    for routes that allow anonymous access with elevated behavior when
    authenticated (e.g. `POST /investigations`)."""
    if credentials is None:
        return None
    try:
        return decode_access_token(credentials.credentials)
    except TokenError:
        return None


def require_role(*roles: str):
    """Dependency factory for RBAC: `Depends(require_role("admin", "moderator"))`."""

    async def _dependency(claims: dict = Depends(get_current_claims)) -> dict:
        if roles and claims.get("role") not in roles:
            raise ForbiddenError("You do not have permission to perform this action.")
        return claims

    return _dependency

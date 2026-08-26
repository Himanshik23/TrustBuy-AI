"""Authentication Service HTTP routes. Matches API_DOCUMENTATION.md §1.

`verify-email` and `password/forgot`+`password/reset` are intentionally
NOT implemented in Phase 1 - they require the Notification Service (SES)
which lands later in ROADMAP.md. Signup succeeds without email
verification for now; `email_verified_at` stays null and is reserved for
that later phase, not silently dropped from the schema.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app import service
from app.config import get_settings
from app.schemas import LoginRequest, LoginResponse, SessionInfo, SignupRequest, UserPublic
from trustbuy_auth.dependencies import get_current_claims
from trustbuy_common.errors import UnauthorizedError
from trustbuy_db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "trustbuy_refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=get_settings().is_production,
        samesite="strict",
        max_age=60 * 60 * 24 * 30,
        path=REFRESH_COOKIE_PATH,
    )


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _device_label(request: Request) -> str | None:
    """Real browser User-Agent strings routinely exceed 120 chars (extension
    identifiers, engine tokens, ...) - truncate to fit `device_label
    VARCHAR(120)` (DATABASE_SCHEMA.md §2.1) rather than reject the request."""
    user_agent = request.headers.get("user-agent")
    return user_agent[:120] if user_agent else None


@router.post("/signup", response_model=LoginResponse, status_code=201)
async def signup_route(
    payload: SignupRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    user = await service.signup(
        db, email=payload.email, password=payload.password, display_name=payload.display_name
    )
    access_token, raw_refresh, expires_in = await service.issue_session(
        db, user=user, device_label=_device_label(request), ip_address=_client_ip(request)
    )
    _set_refresh_cookie(response, raw_refresh)
    return LoginResponse(access_token=access_token, expires_in=expires_in, user=UserPublic.model_validate(user))


@router.post("/login", response_model=LoginResponse)
async def login_route(
    payload: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    user = await service.authenticate(db, email=payload.email, password=payload.password)
    access_token, raw_refresh, expires_in = await service.issue_session(
        db, user=user, device_label=_device_label(request), ip_address=_client_ip(request)
    )
    _set_refresh_cookie(response, raw_refresh)
    return LoginResponse(access_token=access_token, expires_in=expires_in, user=UserPublic.model_validate(user))


@router.post("/refresh", response_model=LoginResponse)
async def refresh_route(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    trustbuy_refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> LoginResponse:
    if not trustbuy_refresh_token:
        raise UnauthorizedError("Missing refresh token.", code="MISSING_REFRESH_TOKEN")

    access_token, new_raw_refresh, expires_in, user = await service.rotate_refresh_token(
        db, raw_refresh_token=trustbuy_refresh_token, ip_address=_client_ip(request)
    )
    _set_refresh_cookie(response, new_raw_refresh)
    return LoginResponse(access_token=access_token, expires_in=expires_in, user=UserPublic.model_validate(user))


@router.post("/logout", status_code=204)
async def logout_route(
    response: Response,
    db: AsyncSession = Depends(get_db),
    trustbuy_refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> None:
    if trustbuy_refresh_token:
        await service.revoke_refresh_token(db, raw_refresh_token=trustbuy_refresh_token)
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


@router.get("/me", response_model=UserPublic)
async def me_route(
    claims: dict = Depends(get_current_claims), db: AsyncSession = Depends(get_db)
) -> UserPublic:
    user = await service.get_user(db, user_id=uuid.UUID(claims["sub"]))
    return UserPublic.model_validate(user)


@router.get("/sessions", response_model=list[SessionInfo])
async def sessions_route(
    claims: dict = Depends(get_current_claims), db: AsyncSession = Depends(get_db)
) -> list[SessionInfo]:
    rows = await service.list_sessions(db, user_id=uuid.UUID(claims["sub"]))
    return [
        SessionInfo(
            id=row.id,
            device_label=row.device_label,
            ip_address=str(row.ip_address) if row.ip_address else None,
            issued_at=row.issued_at,
            expires_at=row.expires_at,
        )
        for row in rows
    ]


@router.delete("/sessions/{session_id}", status_code=204)
async def revoke_session_route(
    session_id: uuid.UUID, claims: dict = Depends(get_current_claims), db: AsyncSession = Depends(get_db)
) -> None:
    await service.revoke_session(db, user_id=uuid.UUID(claims["sub"]), session_id=session_id)

"""Request/response models for the Authentication Service. Mirrors
API_DOCUMENTATION.md §1.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    display_name: str
    avatar_url: str | None = None
    trust_points: int
    reputation_level: str
    is_admin: bool
    is_moderator: bool
    created_at: datetime


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic


class SessionInfo(BaseModel):
    id: uuid.UUID
    device_label: str | None
    ip_address: str | None
    issued_at: datetime
    expires_at: datetime

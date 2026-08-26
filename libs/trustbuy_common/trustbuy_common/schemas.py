"""Common response shapes shared across every TrustBuy AI service.

Mirrors the conventions documented in API_DOCUMENTATION.md "Conventions".
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str
    environment: str
    version: str = Field(default="0.1.0")

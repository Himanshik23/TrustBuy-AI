"""TrustBuy AI shared common library.

Provides base configuration, structured logging, and a uniform error
envelope shared by every FastAPI service in the platform. See
ARCHITECTURE.md and docs/SECURITY.md in the repo root for the contracts
this package implements.
"""

from trustbuy_common.errors import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationAppError,
    register_exception_handlers,
)
from trustbuy_common.logging import configure_logging, get_logger
from trustbuy_common.middleware import RequestIdMiddleware
from trustbuy_common.schemas import ErrorDetail, ErrorResponse, HealthResponse
from trustbuy_common.storage import StorageProvider, UploadRejectedError, get_storage_provider

__all__ = [
    "AppError",
    "ConflictError",
    "ForbiddenError",
    "NotFoundError",
    "UnauthorizedError",
    "ValidationAppError",
    "register_exception_handlers",
    "configure_logging",
    "get_logger",
    "RequestIdMiddleware",
    "ErrorDetail",
    "ErrorResponse",
    "HealthResponse",
    "StorageProvider",
    "UploadRejectedError",
    "get_storage_provider",
]

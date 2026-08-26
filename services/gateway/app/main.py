from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.proxy import router as proxy_router
from app.rate_limit import RateLimitMiddleware
from trustbuy_common.errors import register_exception_handlers
from trustbuy_common.logging import configure_logging
from trustbuy_common.middleware import RequestIdMiddleware
from trustbuy_common.schemas import HealthResponse

settings = get_settings()
configure_logging(settings.service_name, settings.log_level)

app = FastAPI(title="TrustBuy AI - API Gateway", version="0.1.0")

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    redis_url=settings.redis_url,
    limit=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(proxy_router)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(service=settings.service_name, environment=settings.environment)

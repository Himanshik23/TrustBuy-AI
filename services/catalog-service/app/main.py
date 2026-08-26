from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.admin_routes import router as admin_router
from app.config import get_settings
from app.routes import me_router
from app.routes import router as investigations_router
from app.routes_advisor import router as advisor_router
from app.routes_copilot import router as copilot_router
from trustbuy_common.errors import register_exception_handlers
from trustbuy_common.logging import configure_logging
from trustbuy_common.middleware import RequestIdMiddleware
from trustbuy_common.schemas import HealthResponse

settings = get_settings()
configure_logging(settings.service_name, settings.log_level)

app = FastAPI(title="TrustBuy AI - Catalog Service (Product Extraction + Investigations)", version="0.1.0")

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(investigations_router, prefix="/api/v1")
app.include_router(me_router, prefix="/api/v1")
app.include_router(copilot_router, prefix="/api/v1")
app.include_router(advisor_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(service=settings.service_name, environment=settings.environment)

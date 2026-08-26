from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.admin_routes import router as admin_router
from app.badges import seed_badges
from app.config import get_settings
from app.routes import router
from trustbuy_common.errors import register_exception_handlers
from trustbuy_common.logging import configure_logging
from trustbuy_common.middleware import RequestIdMiddleware
from trustbuy_common.schemas import HealthResponse
from trustbuy_db.base import get_session_factory

settings = get_settings()
configure_logging(settings.service_name, settings.log_level)

# Ensure the local upload directory exists before StaticFiles mounts it -
# only relevant when running on LocalDiskStorageProvider (no
# TRUSTBUY_S3_BUCKET set); harmless no-op otherwise.
_local_storage_dir = os.environ.get("TRUSTBUY_LOCAL_STORAGE_DIR", "/data/uploads")
Path(_local_storage_dir).mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    session_factory = get_session_factory()
    async with session_factory() as db:
        await seed_badges(db)
    yield


app = FastAPI(title="TrustBuy AI - Community Intelligence Service", version="0.1.0", lifespan=lifespan)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")

if not os.environ.get("TRUSTBUY_S3_BUCKET"):
    app.mount("/uploads", StaticFiles(directory=_local_storage_dir), name="uploads")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(service=settings.service_name, environment=settings.environment)

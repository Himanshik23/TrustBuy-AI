from __future__ import annotations

from functools import lru_cache

from trustbuy_common.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "catalog-service"
    agent_weight_version: str = "v1"
    fusion_model_version: str = "fusion-2026.1"
    investigation_cache_ttl_seconds: int = 3600


@lru_cache
def get_settings() -> Settings:
    return Settings()

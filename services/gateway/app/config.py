from __future__ import annotations

from functools import lru_cache

from trustbuy_common.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "gateway"

    # Downstream service base URLs. More entries land here as services/*/
    # come online (ARCHITECTURE.md §4).
    auth_service_url: str = "http://auth-service:8000"
    catalog_service_url: str = "http://catalog-service:8000"
    community_service_url: str = "http://community-service:8000"

    redis_url: str = "redis://redis:6379/0"
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()

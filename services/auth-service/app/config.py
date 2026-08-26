from __future__ import annotations

from functools import lru_cache

from trustbuy_common.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "auth-service"


@lru_cache
def get_settings() -> Settings:
    return Settings()

"""Base settings every service extends.

Each service defines its own `Settings(BaseServiceSettings)` subclass with
service-specific fields, but inherits the environment/logging/CORS
conventions defined here so every service in the monorepo reads its
configuration the same way. See DECISIONS.md ADR-006 (auth) and
docs/SECURITY.md for the conventions this backs.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    service_name: str = "trustbuy-service"
    environment: str = "local"  # local | dev | staging | production
    log_level: str = "INFO"

    # Comma-separated in the environment, parsed to a list for CORS middleware.
    cors_allow_origins: str = "http://localhost:3010"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_base_settings() -> BaseServiceSettings:
    """Cached accessor for callers that only need the shared base fields."""
    return BaseServiceSettings()

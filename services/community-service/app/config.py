from __future__ import annotations

from functools import lru_cache

from trustbuy_common.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    service_name: str = "community-service"
    # Minimum reputation level (by threshold) required to verify others'
    # reports - docs/USER_FLOWS.md §5.1 ("Investigator" tier and above).
    min_points_to_verify: int = 100
    # Rate limits (docs/SECURITY.md §5) - simple per-user counters, no Redis
    # dependency needed at this volume; revisit if abused.
    max_reports_per_day: int = 20
    max_votes_per_day: int = 200


@lru_cache
def get_settings() -> Settings:
    return Settings()

"""Smoke test only - the gateway's real job (proxying + rate limiting) needs
a running auth-service + Redis and is covered by the manual/CI integration
smoke test against docker compose, not a unit test. `/health` is exempt
from the rate limiter (app/rate_limit.py), so this never touches Redis.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health_ok():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok", "service": "gateway", "environment": "local", "version": "0.1.0"}

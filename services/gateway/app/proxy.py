"""Reverse-proxy routing to downstream services (ARCHITECTURE.md §4).

Routes are matched by longest-prefix-wins, not just the first path
segment - required now that both catalog-service (`/users/me/investigations`)
and community-service (`/users/me/badges`, `/users/{id}/reputation`) own
routes under `/users/*`. Adding a new source is: add a `(prefix, url)`
entry to `_SERVICE_ROUTES` - nothing else in the codebase branches on it.

Note on AuthN/Z: every route proxied here already enforces its own JWT
check at the receiving service (`Depends(get_current_claims)`), per
docs/SECURITY.md's defense-in-depth principle - the raw `Authorization`
header is forwarded through untouched.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Request, Response

from app.config import get_settings
from trustbuy_common.errors import NotFoundError

router = APIRouter()

_HOP_BY_HOP_HEADERS = {"content-length", "transfer-encoding", "connection", "keep-alive", "content-encoding"}


def _service_routes() -> list[tuple[str, str]]:
    settings = get_settings()
    return [
        ("auth", settings.auth_service_url),
        ("investigations", settings.catalog_service_url),
        ("copilot", settings.catalog_service_url),
        ("users/me/investigations", settings.catalog_service_url),
        ("users", settings.community_service_url),
        ("reports", settings.community_service_url),
        ("leaderboard", settings.community_service_url),
        # Admin routes are split by resource across the services that own
        # the underlying data - longest-prefix-wins picks the right one.
        ("admin/users", settings.auth_service_url),
        ("admin/investigations", settings.catalog_service_url),
        ("admin/metrics", settings.catalog_service_url),
        ("admin/reports", settings.community_service_url),
    ]


def _resolve_target(full_path: str) -> str | None:
    best_match: tuple[int, str] | None = None
    for prefix, base_url in _service_routes():
        if full_path == prefix or full_path.startswith(prefix + "/"):
            if best_match is None or len(prefix) > best_match[0]:
                best_match = (len(prefix), base_url)
    return best_match[1] if best_match else None


@router.api_route(
    "/api/v1/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy(full_path: str, request: Request) -> Response:
    target_base = _resolve_target(full_path)
    if target_base is None:
        raise NotFoundError(f"No route registered for /api/v1/{full_path}.")

    upstream_url = f"{target_base}/api/v1/{full_path}"
    body = await request.body()

    forward_headers = {k: v for k, v in request.headers.items() if k.lower() not in {"host", "content-length"}}

    async with httpx.AsyncClient(timeout=30.0) as client:
        upstream = await client.request(
            request.method,
            upstream_url,
            content=body,
            headers=forward_headers,
            params=request.query_params,
        )

    response = Response(content=upstream.content, status_code=upstream.status_code)
    for key, value in upstream.headers.items():
        if key.lower() in _HOP_BY_HOP_HEADERS or key.lower() == "set-cookie":
            continue
        response.headers[key] = value

    for cookie_value in upstream.headers.get_list("set-cookie"):
        response.headers.append("set-cookie", cookie_value)

    return response

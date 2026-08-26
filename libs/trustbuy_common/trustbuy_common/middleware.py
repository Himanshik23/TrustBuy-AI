"""Request-ID middleware shared by every service.

Stamps every request with a UUID (reused from the incoming `X-Request-ID`
header when the gateway already set one), attaches it to `request.state`
for the error handlers in `errors.py`, and echoes it back on the response
so a single investigation/request can be traced across services per
ARCHITECTURE.md §10.
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

"""Redis-backed token-bucket rate limiter (docs/SECURITY.md §5).

Replaces the earlier fixed-window limiter (DECISIONS.md ADR-009, Phase 1
implementation-scope note) with the token-bucket design that doc actually
specifies. Each client (by IP) gets a bucket that holds up to `limit`
tokens, refills continuously at `limit / window_seconds` tokens/sec, and
spends one token per request. State lives in Redis and every read-modify-
write happens inside one atomic Lua script (`EVAL`), so concurrent
requests from the same client can never race each other into spending
more tokens than were actually available - a real correctness gap a
naive GET-then-SET implementation would have under load.

Fixed-window's edge-of-window burst (a client can send `limit` requests
in the last second of one window and another `limit` in the first second
of the next - 2x the intended rate for a moment) is gone as a side effect
of switching algorithms, not a separate feature bolted on top.
"""

from __future__ import annotations

import time

import redis.asyncio as redis
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

EXEMPT_PATHS = {"/health"}

# KEYS[1] = bucket key
# ARGV[1] = capacity (max tokens a bucket can hold)
# ARGV[2] = refill_rate (tokens added per second)
# ARGV[3] = now (unix seconds, float - passed in rather than read server-side
#           so this stays testable/deterministic against a fake clock)
# ARGV[4] = idle TTL in seconds for the bucket key
# Returns {allowed (0/1), tokens_remaining (string float), retry_after_seconds (string float)}
_TOKEN_BUCKET_LUA = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local ttl = tonumber(ARGV[4])

local bucket = redis.call("HMGET", key, "tokens", "ts")
local tokens = tonumber(bucket[1])
local last_ts = tonumber(bucket[2])

if tokens == nil then
    tokens = capacity
    last_ts = now
end

local elapsed = now - last_ts
if elapsed < 0 then
    elapsed = 0
end
tokens = math.min(capacity, tokens + elapsed * refill_rate)

local allowed = 0
local retry_after = 0
if tokens >= 1 then
    allowed = 1
    tokens = tokens - 1
else
    retry_after = (1 - tokens) / refill_rate
end

redis.call("HMSET", key, "tokens", tostring(tokens), "ts", tostring(now))
redis.call("EXPIRE", key, ttl)

return {allowed, tostring(tokens), tostring(retry_after)}
"""


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, redis_url: str, limit: int, window_seconds: int) -> None:
        super().__init__(app)
        self._redis = redis.from_url(redis_url, decode_responses=True)
        self._capacity = limit
        self._refill_rate = limit / window_seconds
        # A bucket idle for 2 full windows is safe to drop - a client that
        # returns later just starts back at a full bucket, which is exactly
        # correct (they weren't being limited when they left).
        self._ttl_seconds = max(60, window_seconds * 2)
        self._script = self._redis.register_script(_TOKEN_BUCKET_LUA)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        client_id = request.client.host if request.client else "unknown"
        bucket_key = f"ratelimit:tb:{client_id}"

        allowed, _tokens, retry_after = await self._script(
            keys=[bucket_key],
            args=[self._capacity, self._refill_rate, time.time(), self._ttl_seconds],
        )

        if not int(allowed):
            request_id = request.headers.get("x-request-id", "")
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "Too many requests. Please slow down.",
                        "request_id": request_id,
                    }
                },
                headers={"Retry-After": str(max(1, int(float(retry_after)) + 1))},
            )

        return await call_next(request)

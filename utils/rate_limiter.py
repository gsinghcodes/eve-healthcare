import hashlib
import logging
import math
from dataclasses import dataclass

from fastapi import HTTPException, Request
from redis.exceptions import RedisError


logger = logging.getLogger(__name__)
RATE_LIMIT_MESSAGE = "Too many requests. Please try again later."
RATE_LIMIT_UNAVAILABLE_MESSAGE = "Rate limiting temporarily unavailable."

_RATE_LIMIT_SCRIPT = """
local blocked = 0
local retry_after_ms = 0
for i, key in ipairs(KEYS) do
    local count = redis.call('INCR', key)
    local ttl = redis.call('PTTL', key)
    local window_ms = tonumber(ARGV[(i - 1) * 2 + 2])
    if ttl < 0 then
        redis.call('PEXPIRE', key, window_ms)
        ttl = window_ms
    end
    if count > tonumber(ARGV[(i - 1) * 2 + 1]) then
        blocked = 1
        if ttl > retry_after_ms then
            retry_after_ms = ttl
        end
    end
end
return {blocked, retry_after_ms}
"""


@dataclass(frozen=True)
class RateLimit:
    key: str
    limit: int
    window_seconds: int


def hashed_identifier(identifier: str) -> str:
    return hashlib.sha256(identifier.encode("utf-8")).hexdigest()


def request_client_ip(request: Request) -> str:
    if request.client is None or not request.client.host:
        logger.error("Rate-limit check failed because request client IP is unavailable")
        raise HTTPException(
            status_code=503,
            detail=RATE_LIMIT_UNAVAILABLE_MESSAGE,
        )
    return request.client.host


def check_rate_limits(redis_client, limits: list[RateLimit]) -> None:
    if not limits:
        return

    keys = [limit.key for limit in limits]
    arguments = [
        value
        for limit in limits
        for value in (limit.limit, limit.window_seconds * 1000)
    ]

    try:
        blocked, retry_after_ms = redis_client.eval(
            _RATE_LIMIT_SCRIPT,
            len(keys),
            *keys,
            *arguments,
        )
    except RedisError:
        logger.exception("Redis rate-limit check failed")
        raise HTTPException(
            status_code=503,
            detail=RATE_LIMIT_UNAVAILABLE_MESSAGE,
        ) from None

    if blocked:
        raise HTTPException(
            status_code=429,
            detail=RATE_LIMIT_MESSAGE,
            headers={"Retry-After": str(max(1, math.ceil(retry_after_ms / 1000)))},
        )
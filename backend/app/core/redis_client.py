"""Redis connection helper.

The client is created lazily and never raises at import time, so the API can
boot (and report degraded caching) when Redis is unavailable.
"""

import logging

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _redis_client


def redis_available() -> bool:
    try:
        return bool(get_redis().ping())
    except Exception:  # pragma: no cover - depends on external service
        logger.warning("Redis unavailable; continuing without cache")
        return False

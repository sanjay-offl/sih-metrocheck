"""Redis cache for vision extractions.

Extraction is the slow, paid step, so identical images (the same label scanned
twice in a store, or a demo re-run) are served from cache. Every operation is
best-effort: a Redis outage must never break a scan.
"""

import json
import logging
from typing import Any, Optional

from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)

EXTRACTION_TTL_SECONDS = 60 * 60 * 24  # 24 hours
_KEY_PREFIX = "metrocheck:extract:"


def _key(image_sha256: str, model: str) -> str:
    return f"{_KEY_PREFIX}{model}:{image_sha256}"


def get_cached_extraction(image_sha256: str, model: str) -> Optional[dict[str, Any]]:
    if not image_sha256:
        return None
    try:
        raw = get_redis().get(_key(image_sha256, model))
        if not raw:
            return None
        payload = json.loads(raw)
        payload["cache_hit"] = True
        return payload
    except Exception as exc:  # noqa: BLE001 - cache must never be fatal
        logger.warning("Cache read failed: %s", exc)
        return None


def set_cached_extraction(
    image_sha256: str, model: str, payload: dict[str, Any]
) -> None:
    if not image_sha256:
        return
    try:
        stored = {k: v for k, v in payload.items() if k != "cache_hit"}
        get_redis().setex(
            _key(image_sha256, model),
            EXTRACTION_TTL_SECONDS,
            json.dumps(stored, default=str),
        )
    except Exception as exc:  # noqa: BLE001 - cache must never be fatal
        logger.warning("Cache write failed: %s", exc)


def invalidate_extraction(image_sha256: str, model: str) -> None:
    try:
        get_redis().delete(_key(image_sha256, model))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cache delete failed: %s", exc)


def cache_health() -> dict[str, Any]:
    """Small diagnostics payload exposed on /health."""
    try:
        client = get_redis()
        client.ping()
        return {
            "redis": "ok",
            "extraction_keys": client.dbsize(),
        }
    except Exception as exc:  # noqa: BLE001
        return {"redis": "unavailable", "error": str(exc)}

import logging
from datetime import datetime, timedelta

from config import CACHE_TTL_MINUTES

logger = logging.getLogger(__name__)

_store: dict[str, object] = {}
_timestamps: dict[str, datetime] = {}


def cache_get(key: str) -> object | None:
    """Return the cached value for *key*, or ``None`` if missing or expired."""
    _evict_expired()
    value = _store.get(key)
    if value is not None:
        logger.debug("Cache hit: %s", key)
    return value


def cache_put(key: str, value: object) -> None:
    """Store *value* under *key* with a fresh TTL."""
    _store[key] = value
    _timestamps[key] = datetime.now()
    logger.debug("Cache set: %s", key)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _is_expired(timestamp: datetime) -> bool:
    return datetime.now() - timestamp > timedelta(minutes=CACHE_TTL_MINUTES)


def _evict_expired() -> None:
    expired = [k for k, ts in _timestamps.items() if _is_expired(ts)]
    for key in expired:
        logger.debug("Cache evict: %s", key)
        _store.pop(key, None)
        _timestamps.pop(key, None)

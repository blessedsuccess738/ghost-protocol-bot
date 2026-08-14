"""middleware/error.py — centralized error logging middleware."""
import logging
from functools import wraps

logger = logging.getLogger(__name__)


def error_middleware(fn):
    """Wrap a handler so unexpected exceptions are logged and not raised."""

    @wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except Exception as exc:  # pragma: no cover
            logger.error("Handler error in %s: %s", getattr(fn, "__name__", fn), exc, exc_info=True)
            return None

    return wrapper

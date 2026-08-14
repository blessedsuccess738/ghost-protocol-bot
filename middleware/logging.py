"""middleware/logging.py — per-update request logging middleware."""
import logging
import time

logger = logging.getLogger(__name__)


def log_update(fn):
    """Wrap a handler with update timing logs."""

    async def wrapper(update, context):
        start = time.perf_counter()
        try:
            return await fn(update, context)
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            uid = getattr(update.effective_user, "id", None)
            text = getattr(update.effective_message, "text", None)
            logger.info("update user=%s text=%r took=%.1fms", uid, (text or "")[:60], elapsed)

    return wrapper

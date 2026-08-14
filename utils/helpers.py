"""utils/helpers.py — misc helpers."""
import hashlib
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def ensure_dir(path: str) -> None:
    if path:
        os.makedirs(path, exist_ok=True)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError as exc:
        logger.error("sha256 failed for %s: %s", path, exc)
        return ""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_aware(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def truncate(text: str, limit: int = 100) -> str:
    text = text or ""
    return text if len(text) <= limit else text[:limit - 3] + "..."

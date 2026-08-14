"""services/cache_service.py — in-memory TTL cache."""
import logging
import threading
import time

import config

logger = logging.getLogger(__name__)


class TTLCache:
    def __init__(self, default_ttl: int | None = None):
        self._store = {}
        self._lock = threading.Lock()
        self.default_ttl = default_ttl or config.CACHE_TTL

    def get(self, key: str):
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            expires, value = item
            if expires < time.monotonic():
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value, ttl: int | None = None) -> None:
        ttl = ttl or self.default_ttl
        with self._lock:
            self._store[key] = (time.monotonic() + ttl, value)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._store)


cache_service = TTLCache()

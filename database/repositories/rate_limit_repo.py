"""database/repositories/rate_limit_repo.py — Rate-limit persistence (sliding window)."""
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from models import RateLimit

logger = logging.getLogger(__name__)


class RateLimitRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _session(self) -> Session:
        from database.connection import get_session
        return get_session()

    def record(self, user_id: int | None, action: str) -> RateLimit:
        with self._session() as s:
            entry = RateLimit(user_id=user_id, action=action)
            s.add(entry)
            s.commit()
            s.refresh(entry)
            return entry

    def count_in_window(self, user_id: int | None, action: str, window_seconds: int) -> int:
        cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
        with self._session() as s:
            q = select(func.count()).select_from(RateLimit).where(
                RateLimit.action == action, RateLimit.timestamp >= cutoff)
            if user_id is not None:
                q = q.where(RateLimit.user_id == user_id)
            return int(s.scalar(q) or 0)

    def cleanup_older_than(self, days: int = 1) -> int:
        cutoff = datetime.utcnow() - timedelta(days=days)
        with self._session() as s:
            result = s.query(RateLimit).filter(RateLimit.timestamp < cutoff).delete()
            s.commit()
            return int(result or 0)

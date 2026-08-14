"""database/repositories/analytics_repo.py — Analytics persistence (Repository pattern)."""
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from models import Analytics

logger = logging.getLogger(__name__)


class AnalyticsRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _session(self) -> Session:
        from database.connection import get_session
        return get_session()

    def record(self, metric: str, value: float = 1, category: str | None = None,
               admin_id: int | None = None) -> Analytics:
        with self._session() as s:
            a = Analytics(metric=metric, value=value, category=category, admin_id=admin_id)
            s.add(a)
            s.commit()
            s.refresh(a)
            return a

    def count_metric(self, metric: str, since: datetime | None = None) -> int:
        with self._session() as s:
            q = select(func.count()).select_from(Analytics).where(Analytics.metric == metric)
            if since:
                q = q.where(Analytics.timestamp >= since)
            return int(s.scalar(q) or 0)

    def trend(self, metric: str, days: int = 7):
        from datetime import date, datetime, time
        today = date.today()
        result = []
        with self._session() as s:
            for offset in range(days - 1, -1, -1):
                day = today - timedelta(days=offset)
                start = datetime.combine(day, time.min)
                end = start + timedelta(days=1)
                count = int(s.scalar(select(func.count()).select_from(Analytics).where(
                    Analytics.metric == metric, Analytics.timestamp >= start, Analytics.timestamp < end)) or 0)
                result.append({"date": day.isoformat(), "count": count})
        return result

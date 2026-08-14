"""database/repositories/notification_repo.py — Notification persistence (Repository pattern)."""
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import func, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from models import Notification

logger = logging.getLogger(__name__)


class NotificationRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _session(self) -> Session:
        from database.connection import get_session
        return get_session()

    def create(self, admin_id: int | None, type_: str, title: str, message: str) -> Notification:
        with self._session() as s:
            n = Notification(admin_id=admin_id, type=type_, title=title, message=message)
            s.add(n)
            s.commit()
            s.refresh(n)
            return n

    def list_for_admin(self, admin_id: int, page: int = 1, per_page: int = 10, unread_only: bool = False):
        with self._session() as s:
            q = select(Notification).where(Notification.admin_id == admin_id)
            if unread_only:
                q = q.where(Notification.is_read == 0)
            q = q.order_by(Notification.created_at.desc())
            total = s.scalar(select(func.count()).select_from(q.subquery()))
            rows = s.scalars(q.offset((page - 1) * per_page).limit(per_page)).all()
            return list(rows), int(total or 0)

    def count_unread(self, admin_id: int) -> int:
        with self._session() as s:
            return int(s.scalar(select(func.count()).select_from(Notification).where(
                Notification.admin_id == admin_id, Notification.is_read == 0)) or 0)

    def mark_read(self, notification_id: int) -> None:
        with self._session() as s:
            s.execute(update(Notification).where(Notification.id == notification_id)
                      .values(is_read=1, read_at=datetime.now(timezone.utc)))
            s.commit()

    def mark_all_read(self, admin_id: int) -> None:
        with self._session() as s:
            s.execute(update(Notification).where(Notification.admin_id == admin_id, Notification.is_read == 0)
                      .values(is_read=1, read_at=datetime.now(timezone.utc)))
            s.commit()

    def count_all(self) -> int:
        with self._session() as s:
            return int(s.scalar(select(func.count()).select_from(Notification)) or 0)

    def list_broadcasts(self, page: int = 1, per_page: int = 10):
        with self._session() as s:
            q = select(Notification).where(Notification.type == "broadcast")
            q = q.order_by(Notification.created_at.desc())
            total = s.scalar(select(func.count()).select_from(q.subquery()))
            rows = s.scalars(q.offset((page - 1) * per_page).limit(per_page)).all()
            return list(rows), int(total or 0)

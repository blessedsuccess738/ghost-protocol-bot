"""database/repositories/audit_repo.py — Audit log persistence (Repository pattern)."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from models import AuditLog
from utils.helpers import ensure_aware

logger = logging.getLogger(__name__)


class AuditRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _session(self) -> Session:
        from database.connection import get_session
        return get_session()

    def add(self, admin_id: int | None, action: str, details: dict | None = None,
            ip_address: str | None = None, user_agent: str | None = None,
            session_id: str | None = None, severity: str = "info") -> AuditLog:
        with self._session() as s:
            entry = AuditLog(admin_id=admin_id, action=action, details=details or {},
                             ip_address=ip_address, user_agent=user_agent,
                             session_id=session_id, severity=severity)
            s.add(entry)
            s.commit()
            s.refresh(entry)
            return entry

    def list_logs(self, admin_id: int | None = None, page: int = 1, per_page: int = 20,
                  action: str | None = None, severity: str | None = None):
        with self._session() as s:
            q = select(AuditLog)
            if admin_id is not None:
                q = q.where(AuditLog.admin_id == admin_id)
            if action:
                q = q.where(AuditLog.action == action)
            if severity:
                q = q.where(AuditLog.severity == severity)
            q = q.order_by(AuditLog.timestamp.desc())
            total = s.scalar(select(func.count()).select_from(q.subquery()))
            rows = s.scalars(q.offset((page - 1) * per_page).limit(per_page)).all()
            return list(rows), int(total or 0)

    def count_all(self) -> int:
        with self._session() as s:
            return int(s.scalar(select(func.count()).select_from(AuditLog)) or 0)

    def count_since(self, days: int) -> int:
        cutoff = datetime.utcnow() - timedelta(days=days)
        with self._session() as s:
            return int(s.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.timestamp >= cutoff)) or 0)

    def cleanup_older_than(self, days: int) -> int:
        cutoff = datetime.utcnow() - timedelta(days=days)
        with self._session() as s:
            result = s.query(AuditLog).filter(AuditLog.timestamp < cutoff).delete()
            s.commit()
            return int(result or 0)

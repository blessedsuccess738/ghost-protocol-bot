"""
database/repositories/attack_log_repo.py — AttackLog persistence (Repository pattern).

Records every target-verification / moderation action performed through the
'Verify Target' tool suite. Provides pagination + per-target history.
"""
import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from models import AttackLog

logger = logging.getLogger(__name__)


class AttackLogRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _session(self) -> Session:
        from database.connection import get_session
        return get_session()

    def create(self, target: str, tool_used: str, status: str = "SUCCESS",
               result: str | None = None, admin_id: int | None = None,
               admin_telegram_id: int | None = None,
               target_id: str | None = None,
               target_type: str | None = None) -> AttackLog:
        with self._session() as s:
            rec = AttackLog(
                admin_id=admin_id,
                admin_telegram_id=admin_telegram_id,
                target=target,
                target_id=target_id,
                target_type=target_type,
                tool_used=tool_used,
                status=status,
                result=result,
            )
            s.add(rec)
            s.commit()
            s.refresh(rec)
            logger.info("AttackLog %s for %s by admin %s -> %s",
                        tool_used, target, admin_telegram_id, status)
            return rec

    def history_for_admin(self, admin_id: int, page: int = 1,
                          per_page: int = 10):
        with self._session() as s:
            q = select(AttackLog).where(AttackLog.admin_id == admin_id)
            q = q.order_by(AttackLog.created_at.desc())
            total = s.scalar(select(func.count()).select_from(q.subquery()))
            rows = s.scalars(q.offset((page - 1) * per_page).limit(per_page)).all()
            return list(rows), int(total or 0)

    def history_for_target(self, target: str, limit: int = 20) -> list[AttackLog]:
        with self._session() as s:
            return list(
                s.scalars(
                    select(AttackLog)
                    .where(AttackLog.target == target)
                    .order_by(AttackLog.created_at.desc())
                    .limit(limit)
                )
            )

    def list_all(self, page: int = 1, per_page: int = 10,
                 tool_used: str | None = None):
        with self._session() as s:
            q = select(AttackLog)
            if tool_used:
                q = q.where(AttackLog.tool_used == tool_used)
            q = q.order_by(AttackLog.created_at.desc())
            total = s.scalar(select(func.count()).select_from(q.subquery()))
            rows = s.scalars(q.offset((page - 1) * per_page).limit(per_page)).all()
            return list(rows), int(total or 0)

    def count_by_tool(self, tool_used: str | None = None) -> int:
        with self._session() as s:
            q = select(func.count()).select_from(AttackLog)
            if tool_used:
                q = q.where(AttackLog.tool_used == tool_used)
            return int(s.scalar(q) or 0)

    def count_total(self) -> int:
        return self.count_by_tool(None)

    def get(self, log_id: int) -> Optional[AttackLog]:
        with self._session() as s:
            return s.get(AttackLog, log_id)

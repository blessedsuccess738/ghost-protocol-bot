"""database/repositories/ban_repo.py — Ban record persistence (Repository pattern)."""
import logging
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from models import BanRecord

logger = logging.getLogger(__name__)


class BanRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _session(self) -> Session:
        from database.connection import get_session
        return get_session()

    def create(self, case_id: str | None, target: str, reason: str, action: str,
               admin_id: int | None = None, admin_telegram_id: int | None = None,
               target_type: str | None = None, evidence_ref: str | None = None,
               note: str | None = None) -> BanRecord:
        with self._session() as s:
            rec = BanRecord(case_id=case_id, target=target, target_type=target_type,
                            reason=reason, action=action, admin_id=admin_id,
                            admin_telegram_id=admin_telegram_id, evidence_ref=evidence_ref, note=note)
            s.add(rec)
            s.commit()
            s.refresh(rec)
            logger.info("BanRecord %s for %s by admin %s", action, target, admin_telegram_id)
            return rec

    def history_for_target(self, target: str, limit: int = 20) -> list[BanRecord]:
        with self._session() as s:
            return list(s.scalars(select(BanRecord).where(BanRecord.target == target)
                                  .order_by(BanRecord.created_at.desc()).limit(limit)))

    def list_by_action(self, action: str, page: int = 1, per_page: int = 10):
        with self._session() as s:
            q = select(BanRecord).where(BanRecord.action == action)
            q = q.order_by(BanRecord.created_at.desc())
            total = s.scalar(select(func.count()).select_from(q.subquery()))
            rows = s.scalars(q.offset((page - 1) * per_page).limit(per_page)).all()
            return list(rows), int(total or 0)

    def count_by_action(self, action: str | None = None) -> int:
        with self._session() as s:
            q = select(func.count()).select_from(BanRecord)
            if action:
                q = q.where(BanRecord.action == action)
            return int(s.scalar(q) or 0)

    def count_total(self) -> int:
        return self.count_by_action(None)

    def get_by_case_id(self, case_id: str) -> Optional[BanRecord]:
        with self._session() as s:
            return s.scalar(select(BanRecord).where(BanRecord.case_id == case_id))

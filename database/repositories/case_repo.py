"""database/repositories/case_repo.py — Case persistence (Repository pattern) for 『𝑮𝑷』 𝑮𝑯𝑶𝑺𝑻 𝑷𝑹𝑶𝑻𝑶𝑪𝑶𝑳 BOT.
Cases use GP-XXXXXX ids (e.g. GP-000124) and moderation statuses (PENDING / BANNED / REJECTED / REVIEWED).
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import func, or_, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
import config
from core import security
from core.constants import STATUS_PENDING
from models import Case

logger = logging.getLogger(__name__)


class CaseRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _session(self) -> Session:
        from database.connection import get_session
        return get_session()

    def create(self, admin_id: int | None = None, submitter_id: int | None = None,
               target_link: str = "", reason: str = "", target_type: str | None = None,
               target_name: str | None = None, description: str | None = None,
               severity: str = "medium", status: str = STATUS_PENDING) -> Case:
        with self._session() as s:
            next_seq = self._next_sequence(s)
            case = Case(case_id=security.generate_case_id(seq=next_seq), admin_id=admin_id,
                        submitter_id=submitter_id, target_link=target_link, target_type=target_type,
                        target_name=target_name, reason=reason, description=description,
                        severity=severity, status=status)
            s.add(case)
            s.commit()
            s.refresh(case)
            logger.info("Case created: %s by admin=%s submitter=%s", case.case_id, admin_id, submitter_id)
            return case

    @staticmethod
    def _next_sequence(session: Session) -> int:
        prefix = "GP-"
        row = session.scalar(select(func.max(Case.case_id)).where(Case.case_id.like(f"{prefix}%")))
        if not row:
            return 1
        try:
            return int(row.rsplit("-", 1)[-1]) + 1
        except ValueError:
            return 1

    def get_by_case_id(self, case_id: str) -> Optional[Case]:
        with self._session() as s:
            return s.scalar(select(Case).where(Case.case_id == case_id))

    def get_by_id(self, case_id_int: int) -> Optional[Case]:
        with self._session() as s:
            return s.get(Case, case_id_int)

    def list_cases(self, admin_id: int | None = None, page: int = 1, per_page: int = 10,
                   status: str | None = None, reason: str | None = None, search: str | None = None,
                   date_from: datetime | None = None, date_to: datetime | None = None,
                   submitter_id: int | None = None):
        with self._session() as s:
            q = select(Case)
            if admin_id is not None:
                q = q.where(Case.admin_id == admin_id)
            if submitter_id is not None:
                q = q.where(Case.submitter_id == submitter_id)
            if status:
                q = q.where(Case.status == status)
            if reason:
                q = q.where(Case.reason == reason)
            if search:
                like = f"%{search}%"
                q = q.where(or_(Case.case_id.ilike(like), Case.target_link.ilike(like)))
            if date_from:
                q = q.where(Case.created_at >= date_from)
            if date_to:
                q = q.where(Case.created_at <= date_to)
            q = q.order_by(Case.created_at.desc())
            total = s.scalar(select(func.count()).select_from(q.subquery()))
            rows = s.scalars(q.offset((page - 1) * per_page).limit(per_page)).all()
            return list(rows), int(total or 0)

    def list_by_status(self, status: str, page: int = 1, per_page: int = 10):
        return self.list_cases(status=status, page=page, per_page=per_page)

    def list_by_submitter(self, submitter_id: int, page: int = 1, per_page: int = 10):
        return self.list_cases(submitter_id=submitter_id, page=page, per_page=per_page)

    def update_status(self, case: Case, new_status: str) -> None:
        with self._session() as s:
            db_case = s.get(Case, case.id)
            db_case.status = new_status
            if new_status in ("BANNED", "REJECTED", "REVIEWED") and db_case.closed_at is None:
                from datetime import datetime as _dt, timezone as _tz
                db_case.closed_at = _dt.now(_tz.utc)
            s.commit()

    def update_reason(self, case: Case, new_reason: str) -> None:
        with self._session() as s:
            db_case = s.get(Case, case.id)
            db_case.reason = new_reason
            s.commit()

    def count_cases(self) -> int:
        with self._session() as s:
            return int(s.scalar(select(func.count()).select_from(Case)) or 0)

    def count_by_status(self) -> dict:
        with self._session() as s:
            rows = s.execute(select(Case.status, func.count()).group_by(Case.status)).all()
            return {status: count for status, count in rows}

    def count_by_admin(self, admin_id: int) -> int:
        with self._session() as s:
            return int(s.scalar(select(func.count()).select_from(Case).where(Case.admin_id == admin_id)) or 0)

    def recent(self, days: int = 7) -> int:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        with self._session() as s:
            return int(s.scalar(select(func.count()).select_from(Case).where(Case.created_at >= since)) or 0)

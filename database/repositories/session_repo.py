"""database/repositories/session_repo.py — Session persistence (Repository pattern)."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import func, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
import config
from models import Session as AdminSession
from utils.helpers import ensure_aware

logger = logging.getLogger(__name__)


class SessionRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _session(self) -> Session:
        from database.connection import get_session
        return get_session()

    def create(self, admin_id: int, token: str, ip_address: str | None = None,
               user_agent: str | None = None) -> AdminSession:
        import uuid
        with self._session() as s:
            sess = AdminSession(session_id=uuid.uuid4().hex, admin_id=admin_id, token=token,
                                ip_address=ip_address, user_agent=user_agent,
                                expires_at=datetime.now(timezone.utc) + timedelta(seconds=config.SESSION_TIMEOUT),
                                is_active=1)
            s.add(sess)
            s.commit()
            s.refresh(sess)
            return sess

    def get_by_session_id(self, session_id: str) -> Optional[AdminSession]:
        with self._session() as s:
            return s.scalar(select(AdminSession).where(AdminSession.session_id == session_id))

    def is_valid(self, session_id: str) -> bool:
        with self._session() as s:
            sess = s.scalar(select(AdminSession).where(AdminSession.session_id == session_id))
            if sess is None or not sess.is_active:
                return False
            if ensure_aware(sess.expires_at) < datetime.now(timezone.utc):
                sess.is_active = 0
                s.commit()
                return False
            return True

    def deactivate(self, session_id: str) -> None:
        with self._session() as s:
            s.execute(update(AdminSession).where(AdminSession.session_id == session_id).values(is_active=0))
            s.commit()

    def deactivate_all_for_admin(self, admin_id: int) -> None:
        with self._session() as s:
            s.execute(update(AdminSession).where(AdminSession.admin_id == admin_id).values(is_active=0))
            s.commit()

    def count_active(self) -> int:
        with self._session() as s:
            return int(s.scalar(select(func.count()).select_from(AdminSession).where(AdminSession.is_active == 1)) or 0)

    def cleanup_expired(self) -> int:
        with self._session() as s:
            result = s.query(AdminSession).filter(AdminSession.expires_at < datetime.utcnow())
            result = result.update({AdminSession.is_active: 0}, synchronize_session=False)
            s.commit()
            return int(result or 0)

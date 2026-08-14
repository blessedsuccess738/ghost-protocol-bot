"""database/repositories/admin_repo.py — Admin persistence (Repository pattern)."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import func, or_, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
import config
from core import security
from models import Admin
from utils.helpers import ensure_aware

logger = logging.getLogger(__name__)


class AdminRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _session(self) -> Session:
        from database.connection import get_session
        return get_session()

    def get_or_create(self, telegram_id: int, username: str | None = None) -> Admin:
        with self._session() as s:
            admin = s.scalar(select(Admin).where(Admin.telegram_id == telegram_id))
            if admin is None:
                admin = Admin(telegram_id=telegram_id, username=username or None)
                s.add(admin)
                s.commit()
                s.refresh(admin)
                logger.info("Admin created: tg=%s", telegram_id)
            elif username and admin.username != username:
                admin.username = username
                s.commit()
            return admin

    def get_by_telegram_id(self, telegram_id: int) -> Optional[Admin]:
        with self._session() as s:
            return s.scalar(select(Admin).where(Admin.telegram_id == telegram_id))

    def get_by_email(self, email: str) -> Optional[Admin]:
        with self._session() as s:
            return s.scalar(select(Admin).where(func.lower(Admin.email) == email.lower()))

    def get_by_id(self, admin_id: int) -> Optional[Admin]:
        with self._session() as s:
            return s.get(Admin, admin_id)

    def list_admins(self, page: int = 1, per_page: int = 10, search: str | None = None,
                    sort_by: str = "created_at", descending: bool = True):
        with self._session() as s:
            q = select(Admin)
            if search:
                like = f"%{search}%"
                q = q.where(or_(Admin.username.ilike(like), Admin.email.ilike(like)))
            col = getattr(Admin, sort_by if hasattr(Admin, sort_by) else "created_at")
            q = q.order_by(col.desc() if descending else col.asc())
            total = s.scalar(select(func.count()).select_from(q.subquery()))
            rows = s.scalars(q.offset((page - 1) * per_page).limit(per_page)).all()
            return list(rows), int(total or 0)

    def count_admins(self) -> int:
        with self._session() as s:
            return int(s.scalar(select(func.count()).select_from(Admin)) or 0)

    def count_active(self) -> int:
        with self._session() as s:
            return int(s.scalar(select(func.count()).select_from(Admin).where(Admin.is_active == 1)) or 0)

    def start_email_verification(self, admin: Admin, email: str) -> str:
        token = security.generate_verification_token()
        with self._session() as s:
            db_admin = s.get(Admin, admin.id)
            db_admin.email = email
            db_admin.email_verified = 0
            db_admin.email_verification_token = security.hash_string(token)
            db_admin.email_verification_expires = datetime.now(timezone.utc) + timedelta(hours=config.EMAIL_VERIFICATION_HOURS)
            s.commit()
        return token

    def verify_email_token(self, admin: Admin, token: str) -> bool:
        with self._session() as s:
            db_admin = s.get(Admin, admin.id)
            if not db_admin.email_verification_token:
                return False
            if not security.constant_time_equals(db_admin.email_verification_token, security.hash_string(token)):
                return False
            exp = ensure_aware(db_admin.email_verification_expires)
            if exp and exp < datetime.now(timezone.utc):
                logger.warning("Verification token expired for tg=%s", admin.telegram_id)
                return False
            db_admin.email_verified = 1
            db_admin.email_verification_token = None
            db_admin.email_verification_expires = None
            s.commit()
            return True

    def regenerate_verification_token(self, admin: Admin) -> str:
        token = security.generate_verification_token()
        with self._session() as s:
            db_admin = s.get(Admin, admin.id)
            db_admin.email_verification_token = security.hash_string(token)
            db_admin.email_verification_expires = datetime.now(timezone.utc) + timedelta(hours=config.EMAIL_VERIFICATION_HOURS)
            s.commit()
        return token

    def record_login_success(self, admin: Admin) -> None:
        with self._session() as s:
            db_admin = s.get(Admin, admin.id)
            db_admin.last_login = datetime.now(timezone.utc)
            db_admin.login_attempts = 0
            db_admin.locked_until = None
            s.commit()

    def record_login_failure(self, admin: Admin) -> bool:
        with self._session() as s:
            db_admin = s.get(Admin, admin.id)
            db_admin.login_attempts = (db_admin.login_attempts or 0) + 1
            locked = db_admin.login_attempts >= config.LOGIN_MAX_ATTEMPTS
            if locked:
                db_admin.locked_until = datetime.now(timezone.utc) + timedelta(minutes=config.LOCKOUT_MINUTES)
            s.commit()
            return locked

    def is_locked(self, admin: Admin) -> bool:
        with self._session() as s:
            db_admin = s.get(Admin, admin.id)
            if not db_admin.locked_until:
                return False
            locked_until = ensure_aware(db_admin.locked_until)
            return locked_until > datetime.now(timezone.utc)

    def set_active(self, admin: Admin, active: bool) -> None:
        with self._session() as s:
            db_admin = s.get(Admin, admin.id)
            db_admin.is_active = 1 if active else 0
            s.commit()

    def set_role(self, admin: Admin, role: str) -> None:
        with self._session() as s:
            db_admin = s.get(Admin, admin.id)
            db_admin.role = role
            db_admin.permissions = config.PERMISSIONS.get(role, [])
            s.commit()

    def change_email(self, admin: Admin, email: str) -> str:
        return self.start_email_verification(admin, email)

    def update_preferences(self, admin: Admin, prefs: dict) -> None:
        with self._session() as s:
            db_admin = s.get(Admin, admin.id)
            db_admin.preferences = prefs
            s.commit()

    def update_notification_settings(self, admin: Admin, settings: dict) -> None:
        with self._session() as s:
            db_admin = s.get(Admin, admin.id)
            db_admin.notification_settings = settings
            s.commit()

    def set_timezone(self, admin: Admin, tz: str) -> None:
        with self._session() as s:
            db_admin = s.get(Admin, admin.id)
            db_admin.timezone = tz
            s.commit()

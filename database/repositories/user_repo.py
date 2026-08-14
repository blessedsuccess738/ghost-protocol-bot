"""database/repositories/user_repo.py — User persistence (Repository pattern)."""
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import func, or_, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
import config
from models import User

logger = logging.getLogger(__name__)


def generate_referral_code(telegram_id: int) -> str:
    return f"GP{telegram_id}"[:32]


class UserRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _session(self) -> Session:
        from database.connection import get_session
        return get_session()

    def get_or_create(self, telegram_id: int, username: str | None = None,
                      first_name: str | None = None) -> User:
        with self._session() as s:
            user = s.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                user = User(telegram_id=telegram_id, username=username or None,
                            first_name=first_name or None, coins=config.COIN_DEFAULT_BALANCE,
                            referral_code=generate_referral_code(telegram_id),
                            moderation_status="NORMAL", is_banned=0, is_active=1)
                s.add(user)
                s.commit()
                s.refresh(user)
                logger.info("User profile created: tg=%s", telegram_id)
            else:
                changed = False
                if username and user.username != username:
                    user.username = username
                    changed = True
                if first_name and user.first_name != first_name:
                    user.first_name = first_name
                    changed = True
                user.last_seen = datetime.now(timezone.utc)
                if changed:
                    s.commit()
            return user

    def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        with self._session() as s:
            return s.scalar(select(User).where(User.telegram_id == telegram_id))

    def get_by_id(self, user_id: int) -> Optional[User]:
        with self._session() as s:
            return s.get(User, user_id)

    def get_by_referral_code(self, code: str) -> Optional[User]:
        with self._session() as s:
            return s.scalar(select(User).where(User.referral_code == code))

    def list_users(self, page: int = 1, per_page: int = 10, search: str | None = None,
                   banned_only: bool = False):
        with self._session() as s:
            q = select(User)
            if banned_only:
                q = q.where(User.is_banned == 1)
            if search:
                like = f"%{search}%"
                q = q.where(or_(User.username.ilike(like), User.first_name.ilike(like)))
            q = q.order_by(User.created_at.desc())
            total = s.scalar(select(func.count()).select_from(q.subquery()))
            rows = s.scalars(q.offset((page - 1) * per_page).limit(per_page)).all()
            return list(rows), int(total or 0)

    def count_users(self) -> int:
        with self._session() as s:
            return int(s.scalar(select(func.count()).select_from(User)) or 0)

    def count_active(self) -> int:
        with self._session() as s:
            return int(s.scalar(select(func.count()).select_from(User).where(User.is_active == 1)) or 0)

    def count_banned(self) -> int:
        with self._session() as s:
            return int(s.scalar(select(func.count()).select_from(User).where(User.is_banned == 1)) or 0)

    def count_referrals(self) -> int:
        with self._session() as s:
            return int(s.scalar(select(func.sum(User.referral_count))) or 0)

    def add_coins(self, user: User, amount: int) -> int:
        with self._session() as s:
            db_user = s.get(User, user.id)
            db_user.coins = (db_user.coins or 0) + amount
            s.commit()
            return db_user.coins

    def get_balance(self, user: User) -> int:
        with self._session() as s:
            db_user = s.get(User, user.id)
            return db_user.coins or 0

    def set_banned(self, user: User, banned: bool, reason: str | None = None) -> None:
        with self._session() as s:
            db_user = s.get(User, user.id)
            db_user.is_banned = 1 if banned else 0
            db_user.moderation_status = "BANNED" if banned else "NORMAL"
            db_user.ban_reason = reason if banned else None
            s.commit()

    def touch(self, user: User) -> None:
        with self._session() as s:
            db_user = s.get(User, user.id)
            db_user.last_seen = datetime.now(timezone.utc)
            s.commit()

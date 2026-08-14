"""database/repositories/referral_repo.py — Referral persistence (Repository pattern)."""
import logging
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from models import Referral, User

logger = logging.getLogger(__name__)


class ReferralRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _session(self) -> Session:
        from database.connection import get_session
        return get_session()

    def get_relationship(self, referrer_id: int, referred_id: int) -> Optional[Referral]:
        with self._session() as s:
            return s.scalar(select(Referral).where(
                Referral.referrer_id == referrer_id, Referral.referred_id == referred_id))

    def create(self, referrer_id: int, referred_id: int) -> Referral:
        with self._session() as s:
            rel = Referral(referrer_id=referrer_id, referred_id=referred_id)
            s.add(rel)
            s.commit()
            s.refresh(rel)
            return rel

    def mark_reward_claimed(self, referral: Referral, amount: int) -> None:
        with self._session() as s:
            db_rel = s.get(Referral, referral.id)
            db_rel.reward_claimed = 1
            db_rel.reward_amount = amount
            s.commit()

    def has_claimed(self, referrer_id: int, referred_id: int) -> bool:
        rel = self.get_relationship(referrer_id, referred_id)
        return bool(rel and rel.reward_claimed)

    def count_for_referrer(self, referrer_id: int) -> int:
        with self._session() as s:
            return int(s.scalar(select(func.count()).select_from(Referral).where(
                Referral.referrer_id == referrer_id)) or 0)

    def list_for_referrer(self, referrer_id: int, page: int = 1, per_page: int = 10):
        with self._session() as s:
            q = select(Referral).where(Referral.referrer_id == referrer_id)
            q = q.order_by(Referral.created_at.desc())
            total = s.scalar(select(func.count()).select_from(q.subquery()))
            rows = s.scalars(q.offset((page - 1) * per_page).limit(per_page)).all()
            return list(rows), int(total or 0)

    def count_total(self) -> int:
        with self._session() as s:
            return int(s.scalar(select(func.count()).select_from(Referral)) or 0)

"""database/repositories/coin_repo.py — Coin transaction ledger (Repository pattern)."""
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
import config
from models import CoinTransaction, User

logger = logging.getLogger(__name__)


class CoinRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _session(self) -> Session:
        from database.connection import get_session
        return get_session()

    def add_transaction(self, user_id: int, amount: int, balance_after: int,
                        tx_type: str = "add", admin_id: int | None = None,
                        note: str | None = None) -> CoinTransaction:
        with self._session() as s:
            tx = CoinTransaction(user_id=user_id, amount=amount, balance_after=balance_after,
                                 tx_type=tx_type, admin_id=admin_id, note=note)
            s.add(tx)
            s.commit()
            s.refresh(tx)
            return tx

    def history_for_user(self, user_id: int, page: int = 1, per_page: int | None = None):
        per_page = per_page or config.COIN_TRANSACTION_PAGE_SIZE
        with self._session() as s:
            q = select(CoinTransaction).where(CoinTransaction.user_id == user_id)
            q = q.order_by(CoinTransaction.created_at.desc())
            total = s.scalar(select(func.count()).select_from(q.subquery()))
            rows = s.scalars(q.offset((page - 1) * per_page).limit(per_page)).all()
            return list(rows), int(total or 0)

    def total_distributed(self, tx_type: str | None = None) -> int:
        with self._session() as s:
            q = select(func.coalesce(func.sum(CoinTransaction.amount), 0)).where(CoinTransaction.amount > 0)
            if tx_type:
                q = q.where(CoinTransaction.tx_type == tx_type)
            return int(s.scalar(q) or 0)

    def count_transactions(self) -> int:
        with self._session() as s:
            return int(s.scalar(select(func.count()).select_from(CoinTransaction)) or 0)

    def last_distribution(self, tx_type: str = "add_all") -> Optional[CoinTransaction]:
        with self._session() as s:
            return s.scalar(select(CoinTransaction).where(CoinTransaction.tx_type == tx_type)
                            .order_by(CoinTransaction.created_at.desc()).limit(1))

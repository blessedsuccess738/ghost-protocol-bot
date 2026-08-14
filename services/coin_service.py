"""services/coin_service.py — coin economy facade (balance, history, add, add_all, referral rewards)."""
import logging

import config
from core.constants import COIN_ADD, COIN_ADD_ALL, COIN_REFERRAL
from database.connection import get_engine
from database.repositories.coin_repo import CoinRepository
from database.repositories.user_repo import UserRepository
from services.audit_service import audit_service

logger = logging.getLogger(__name__)


class CoinService:
    def __init__(self):
        self.user_repo = UserRepository(get_engine())
        self.coin_repo = CoinRepository(get_engine())

    def add_to_user(self, telegram_id: int, amount: int, admin_id: int | None = None) -> dict:
        if amount <= 0 or amount > config.COIN_MAX_ADD:
            return {"ok": False, "error": f"Amount must be between 1 and {config.COIN_MAX_ADD}"}
        user = self.user_repo.get_by_telegram_id(telegram_id)
        if user is None:
            return {"ok": False, "error": "User not found. They must /start the bot first."}
        balance = self.user_repo.add_coins(user, amount)
        self.coin_repo.add_transaction(user.id, amount, balance, tx_type=COIN_ADD, admin_id=admin_id)
        audit_service.log(admin_id, "coin.added", details={"target": telegram_id, "amount": amount})
        return {"ok": True, "balance": balance}

    def add_to_all(self, amount: int, admin_id: int | None = None) -> dict:
        if amount <= 0 or amount > config.COIN_MAX_ADD:
            return {"ok": False, "error": f"Amount must be between 1 and {config.COIN_MAX_ADD}"}
        users, total = self.user_repo.list_users(page=1, per_page=100000)
        updated = 0
        for user in users:
            if user.is_banned or not user.is_active:
                continue
            balance = self.user_repo.add_coins(user, amount)
            self.coin_repo.add_transaction(user.id, amount, balance, tx_type=COIN_ADD_ALL, admin_id=admin_id)
            updated += 1
        audit_service.log(admin_id, "coin.added_all", details={"amount": amount, "updated": updated})
        return {"ok": True, "updated": updated}

    def referral_reward(self, user_id: int, amount: int) -> dict:
        user = self.user_repo.get_by_id(user_id)
        if user is None:
            return {"ok": False, "error": "User not found"}
        balance = self.user_repo.add_coins(user, amount)
        self.coin_repo.add_transaction(user.id, amount, balance, tx_type=COIN_REFERRAL, note="Referral reward")
        return {"ok": True, "balance": balance}

    def history(self, telegram_id: int, page: int = 1, per_page: int = 10):
        user = self.user_repo.get_by_telegram_id(telegram_id)
        if user is None:
            return [], 0
        return self.coin_repo.history_for_user(user.id, page=page, per_page=per_page)

    def balance(self, telegram_id: int) -> int:
        user = self.user_repo.get_by_telegram_id(telegram_id)
        if user is None:
            return 0
        return self.user_repo.get_balance(user)

    def total_distributed(self) -> int:
        return self.coin_repo.total_distributed()


coin_service = CoinService()

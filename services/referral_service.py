"""services/referral_service.py — Referral system facade for 『𝑮𝑷』 𝑮𝑯𝑶𝑺𝑻 𝑷𝑹𝑶𝑻𝑶𝑪𝑶𝑳 BOT.

Each user gets a unique referral link: /start REFERRAL_CODE.
When a new user joins via a referral link, the relationship is recorded and
the reward is granted once — duplicate claiming with the same account is
impossible (unique relationship check + reward_claimed flag).
"""
import logging

from core.constants import REFERRAL_REWARDED
from database.connection import get_engine
from database.repositories.referral_repo import ReferralRepository
from database.repositories.settings_repo import SettingsRepository
from database.repositories.user_repo import UserRepository
from services.audit_service import audit_service

logger = logging.getLogger(__name__)


class ReferralService:
    def __init__(self):
        self.user_repo = UserRepository(get_engine())
        self.referral_repo = ReferralRepository(get_engine())
        self.settings_repo = SettingsRepository(get_engine())

    @property
    def enabled(self) -> bool:
        return self.settings_repo.get_bool("referral.enabled", True)

    @property
    def reward(self) -> int:
        return self.settings_repo.get_int("referral.reward", 100)

    @property
    def min_usage(self) -> int:
        return self.settings_repo.get_int("referral.min_usage", 1)

    def set_reward(self, amount: int) -> None:
        self.settings_repo.set("referral.reward", str(amount), category="referral")

    def set_min_usage(self, amount: int) -> None:
        self.settings_repo.set("referral.min_usage", str(amount), category="referral")

    def set_enabled(self, enabled: bool) -> None:
        self.settings_repo.set("referral.enabled", str(enabled).lower(), category="referral")

    def register_with_code(self, new_user_id: int, code: str) -> dict:
        if not self.enabled:
            return {"ok": False, "reason": "Referral system is disabled."}
        if not code:
            return {"ok": False, "reason": "No code"}
        new_user = self.user_repo.get_by_id(new_user_id)
        referrer = self.user_repo.get_by_referral_code(code)
        if referrer is None:
            return {"ok": False, "reason": "Invalid referral code"}
        if referrer.id == new_user.id:
            return {"ok": False, "reason": "You cannot refer yourself"}
        existing = self.referral_repo.get_relationship(referrer.id, new_user.id)
        if existing:
            return {"ok": False, "reason": "Relationship already recorded"}
        rel = self.referral_repo.create(referrer.id, new_user.id)
        new_user.referred_by_id = referrer.id
        from database.connection import get_session
        with get_session() as s:
            db_user = s.get(__import__("models", fromlist=["User"]).User, new_user.id)
            db_user.referred_by_id = referrer.id
            s.commit()
        usage = self.referral_repo.count_for_referrer(referrer.id)
        if usage >= self.min_usage:
            reward = self.reward
            from services.coin_service import coin_service
            coin_service.referral_reward(referrer.id, reward)
            self.referral_repo.mark_reward_claimed(rel, reward)
            audit_service.log(referrer.telegram_id, REFERRAL_REWARDED,
                              details={"referred": new_user.telegram_id, "amount": reward})
            return {"ok": True, "reward": reward, "referrer": referrer.telegram_id}
        return {"ok": True, "reward": 0, "referrer": referrer.telegram_id}

    def my_link(self, telegram_id: int) -> str:
        user = self.user_repo.get_by_telegram_id(telegram_id)
        if user is None:
            return ""
        return f"https://t.me/{__import__('config').TELEGRAM_BOT_TOKEN.split(':')[0]}?start={user.referral_code}"

    def count(self, telegram_id: int) -> int:
        user = self.user_repo.get_by_telegram_id(telegram_id)
        if user is None:
            return 0
        return self.referral_repo.count_for_referrer(user.id)


referral_service = ReferralService()

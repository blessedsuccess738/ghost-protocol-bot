"""database/repositories/settings_repo.py — System settings persistence (Repository pattern)."""
import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
import config
from models import Setting

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS = {
    "system.name": ("『𝑮𝑷』 𝑮𝑯𝑶𝑺𝑻 𝑷𝑹𝑶𝑻𝑶𝑪𝑶𝑳 BOT", "system", True),
    "system.version": (config.BOT_VERSION, "system", True),
    "auth.verification_required": (str(config.ADMIN_VERIFICATION_REQUIRED), "auth", True),
    "auth.email_verification": (str(config.ADMIN_EMAIL_VERIFICATION), "auth", True),
    "auth.max_admins": (str(config.MAX_ADMINS), "auth", True),
    "auth.session_timeout": (str(config.SESSION_TIMEOUT), "auth", True),
    "auth.login_max_attempts": (str(config.LOGIN_MAX_ATTEMPTS), "auth", True),
    "auth.lockout_minutes": (str(config.LOCKOUT_MINUTES), "auth", True),
    "rate_limit.per_user": (str(config.RATE_LIMIT_PER_USER), "rate_limit", True),
    "rate_limit.per_minute": (str(config.RATE_LIMIT_PER_MINUTE), "rate_limit", True),
    "rate_limit.window": (str(config.RATE_LIMIT_WINDOW), "rate_limit", True),
    "rate_limit.login": (str(config.RATE_LIMIT_LOGIN), "rate_limit", True),
    "rate_limit.uploads": (str(config.RATE_LIMIT_UPLOADS), "rate_limit", True),
    "rate_limit.reports": (str(config.RATE_LIMIT_REPORTS), "rate_limit", True),
    "notifications.enabled": (str(config.NOTIFICATION_ENABLED), "notifications", True),
    "notifications.email_enabled": (str(config.NOTIFICATION_EMAIL_ENABLED), "notifications", True),
    "notifications.telegram_enabled": (str(config.NOTIFICATION_TELEGRAM_ENABLED), "notifications", True),
    "evidence.max_per_case": (str(config.MAX_EVIDENCE_PER_CASE), "evidence", True),
    "evidence.max_screenshot_mb": (str(config.MAX_SCREENSHOT_MB), "evidence", True),
    "logging.level": (config.LOG_LEVEL, "logging", True),
    "logging.retention_days": (str(config.LOG_RETENTION_DAYS), "logging", True),
    "email.from": (config.EMAIL_FROM, "email", True),
    "email.smtp_host": (config.SMTP_HOST, "email", True),
    "email.smtp_port": (str(config.SMTP_PORT), "email", True),
    "coin.default_balance": (str(config.COIN_DEFAULT_BALANCE), "coin", True),
    "coin.max_add": (str(config.COIN_MAX_ADD), "coin", True),
    "referral.reward": (str(config.REFERRAL_REWARD_DEFAULT), "referral", True),
    "referral.min_usage": (str(config.REFERRAL_MIN_USAGE_DEFAULT), "referral", True),
    "referral.enabled": (str(config.REFERRAL_ENABLED_DEFAULT).lower(), "referral", True),
    "force_join.enabled": (str(config.FORCE_JOIN_ENABLED_DEFAULT).lower(), "force_join", True),
    "force_join.channel": (config.FORCE_JOIN_CHANNEL_DEFAULT, "force_join", True),
}


class SettingsRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _session(self) -> Session:
        from database.connection import get_session
        return get_session()

    def ensure_defaults(self) -> None:
        with self._session() as s:
            existing = {row.key for row in s.scalars(select(Setting))}
            added = 0
            for key, (value, category, is_system) in DEFAULT_SETTINGS.items():
                if key not in existing:
                    s.add(Setting(key=key, value=value, category=category, is_system=1 if is_system else 0))
                    added += 1
            if added:
                s.commit()
                logger.info("Seeded %d default settings", added)

    def get(self, key: str) -> Optional[str]:
        with self._session() as s:
            row = s.scalar(select(Setting).where(Setting.key == key))
            return row.value if row else None

    def get_bool(self, key: str, default: bool = False) -> bool:
        val = self.get(key)
        if val is None:
            return default
        return val.strip().lower() in ("1", "true", "yes", "on")

    def get_int(self, key: str, default: int = 0) -> int:
        val = self.get(key)
        try:
            return int(val) if val is not None else default
        except (TypeError, ValueError):
            return default

    def set(self, key: str, value: str, category: str | None = None,
            updated_by: int | None = None, is_system: bool = False) -> None:
        with self._session() as s:
            row = s.scalar(select(Setting).where(Setting.key == key))
            if row is None:
                row = Setting(key=key, category=category, updated_by=updated_by, is_system=1 if is_system else 0)
                s.add(row)
            row.value = str(value)
            if category:
                row.category = category
            if updated_by is not None:
                row.updated_by = updated_by
            s.commit()

    def all(self) -> dict:
        with self._session() as s:
            rows = s.scalars(select(Setting).order_by(Setting.category, Setting.key))
            return {r.key: r.value for r in rows}

    def by_category(self, category: str) -> dict:
        with self._session() as s:
            rows = s.scalars(select(Setting).where(Setting.category == category))
            return {r.key: r.value for r in rows}

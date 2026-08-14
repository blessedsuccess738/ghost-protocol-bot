"""services/notification_service.py — Multi-channel notifications (email + telegram + in-app)."""
import logging

from telegram import Bot

import config
from database.connection import get_engine
from database.repositories.admin_repo import AdminRepository
from database.repositories.notification_repo import NotificationRepository
from .email_service import EmailService

logger = logging.getLogger(__name__)

DEFAULT_NOTIFICATION_SETTINGS = {
    "email": True, "telegram": True, "case_updates": True, "system_alerts": True,
    "broadcasts": True, "daily_digest": False, "email_frequency": "instant",
}


class NotificationService:
    def __init__(self):
        self.email = EmailService()
        self._admin_repo = AdminRepository(get_engine())
        self._notif_repo = NotificationRepository(get_engine())

    def notify(self, admin_id: int | None, type_: str, title: str, message: str) -> None:
        try:
            self._notif_repo.create(admin_id, type_, title, message)
        except Exception as exc:
            logger.error("In-app notification failed: %s", exc)

    def notify_all_admins(self, type_: str, title: str, message: str) -> None:
        admins, _ = self._admin_repo.list_admins(page=1, per_page=config.MAX_ADMINS)
        for admin in admins:
            if admin.is_active:
                self.notify(admin.id, type_, title, message)

    async def send_to_admin(self, bot: Bot, admin_telegram_id: int, message: str,
                            type_: str = "info", title: str = "") -> None:
        admin = self._admin_repo.get_by_telegram_id(admin_telegram_id)
        if admin is not None:
            self.notify(admin.id, type_, title or message[:80], message)
        if config.NOTIFICATION_TELEGRAM_ENABLED:
            try:
                await bot.send_message(chat_id=admin_telegram_id, text=message, parse_mode="Markdown")
            except Exception as exc:
                logger.error("Telegram notify failed for %s: %s", admin_telegram_id, exc)

    async def broadcast(self, bot: Bot, message: str, sender_admin_id: int | None = None) -> int:
        admins, _ = self._admin_repo.list_admins(page=1, per_page=config.MAX_ADMINS)
        delivered = 0
        for admin in admins:
            if not admin.is_active:
                continue
            settings = {**DEFAULT_NOTIFICATION_SETTINGS, **(admin.notification_settings or {})}
            if settings.get("broadcasts", True) and config.NOTIFICATION_TELEGRAM_ENABLED:
                try:
                    await bot.send_message(chat_id=admin.telegram_id, text=f"📢 *Broadcast*\n\n{message}", parse_mode="Markdown")
                    delivered += 1
                except Exception as exc:
                    logger.error("Broadcast Telegram failed for %s: %s", admin.telegram_id, exc)
            if admin.email and settings.get("email", True):
                self.email.send_broadcast(admin.email, message)
            self.notify(admin.id, "broadcast", "Broadcast", message)
        return delivered

    async def send_case_alert(self, bot: Bot, admin_telegram_id: int, case_id: str, message: str) -> None:
        await self.send_to_admin(bot, admin_telegram_id, message, type_="case", title=f"Case {case_id}")

    def get_settings(self, admin_telegram_id: int) -> dict:
        admin = self._admin_repo.get_by_telegram_id(admin_telegram_id)
        if admin is None:
            return dict(DEFAULT_NOTIFICATION_SETTINGS)
        return {**DEFAULT_NOTIFICATION_SETTINGS, **(admin.notification_settings or {})}

    def update_settings(self, admin_telegram_id: int, settings: dict) -> None:
        admin = self._admin_repo.get_by_telegram_id(admin_telegram_id)
        if admin is None:
            return
        current = {**DEFAULT_NOTIFICATION_SETTINGS, **(admin.notification_settings or {})}
        current.update(settings)
        self._admin_repo.update_notification_settings(admin, current)


notification_service = NotificationService()

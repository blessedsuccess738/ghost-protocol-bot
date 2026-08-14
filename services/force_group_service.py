"""services/force_group_service.py — Force-join gate for 『𝑮𝑷』 𝑮𝑯𝑶𝑺𝑻 𝑷𝑹𝑶𝑻𝑶𝑪𝑶𝑳 BOT.

When enabled, users must join the configured group/channel before accessing
protected functions. Membership is verified with getChatMember (bot must be
admin in the target chat). Contains JOIN GROUP / CHECK JOINED buttons.
"""
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from database.connection import get_engine
from database.repositories.force_group_repo import ForceGroupRepository
from database.repositories.settings_repo import SettingsRepository

logger = logging.getLogger(__name__)


class ForceGroupService:
    def __init__(self):
        self.repo = ForceGroupRepository(get_engine())
        self.settings_repo = SettingsRepository(get_engine())

    def is_enabled(self) -> bool:
        row = self.repo.get()
        if row is not None:
            return bool(row.enabled)
        return self.settings_repo.get_bool("force_join.enabled", False)

    def get_config(self):
        return self.repo.get_or_create()

    def configure(self, chat_id: int | None, chat_username: str | None,
                  chat_title: str | None, enabled: bool, updated_by: int | None = None):
        return self.repo.configure(chat_id=chat_id, chat_username=chat_username,
                                   chat_title=chat_title, enabled=enabled, updated_by=updated_by)

    def set_enabled(self, enabled: bool, updated_by: int | None = None):
        self.repo.set_enabled(enabled, updated_by=updated_by)

    def remove(self):
        self.repo.remove()

    async def is_member(self, bot, telegram_id: int) -> bool:
        cfg = self.repo.get()
        if cfg is None or not cfg.enabled:
            return True
        target = cfg.chat_id or cfg.chat_username
        if not target:
            return True
        try:
            member = await bot.get_chat_member(chat_id=target, user_id=telegram_id)
            status = member.status if member else "left"
            return status in ("creator", "administrator", "member", "restricted")
        except Exception as exc:
            logger.warning("Force-join membership check failed: %s", exc)
            return False

    def gate_message(self) -> tuple[str, InlineKeyboardMarkup]:
        cfg = self.repo.get()
        target = cfg.chat_username or cfg.chat_id if cfg else None
        link = f"https://t.me/{cfg.chat_username}" if cfg and cfg.chat_username else None
        text = (
            "👥 *Required Group*\n\n"
            "You must join our required group/channel before using this bot.\n\n"
            f"📢 Channel: {cfg.chat_title or target or '—'}\n"
            f"🔗 {link or ('https://t.me/' + str(target) if target else '—')}"
        )
        buttons = []
        if link:
            buttons.append([InlineKeyboardButton("✅ JOIN GROUP", url=link)])
        buttons.append([InlineKeyboardButton("🔄 CHECK JOINED", callback_data="force_group:check")])
        return text, InlineKeyboardMarkup(buttons)


force_group_service = ForceGroupService()

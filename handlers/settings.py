import logging

from telegram import Update
from telegram.ext import ContextTypes

from core.constants import STATE_AWAIT_EMAIL_CHANGE, SETTINGS_CHANGED
from database.connection import get_engine
from database.repositories.admin_repo import AdminRepository
from keyboards.inline import settings_keyboard, notification_settings_keyboard, main_menu_keyboard
from services.audit_service import audit_service
from services.email_service import email_service
from services.notification_service import notification_service
from utils.decorators import admin_only
from utils.validators import is_valid_email

logger = logging.getLogger(__name__)


@admin_only
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text("⚙️ *Settings*", parse_mode="Markdown", reply_markup=settings_keyboard())


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    action = query.data.split(":", 1)[1]
    if action == "email":
        await query.edit_message_text("📧 *Update Email*\n\nSend your new email address, or /cancel to abort.", parse_mode="Markdown")
        context.user_data["awaiting_email_change"] = True
    elif action == "notifications":
        user = update.effective_user
        settings = notification_service.get_settings(user.id)
        await query.edit_message_text("🔔 *Notification Settings*", parse_mode="Markdown",
                                      reply_markup=notification_settings_keyboard(settings))
    elif action == "profile":
        user = update.effective_user
        repo = AdminRepository(get_engine())
        admin = repo.get_by_telegram_id(user.id)
        if admin:
            text = ("👤 *Profile*\n━━━━━━━━━━━━━━━━━━\n"
                    f"🆔 Telegram ID: `{admin.telegram_id}`\n👤 Username: @{admin.username or '—'}\n"
                    f"📧 Email: {admin.email or '—'} {'✅' if admin.email_verified else '❌'}\n"
                    f"🎖 Role: {admin.role}\n🟢 Active: {'Yes' if admin.is_active else 'No'}\n"
                    f"🕐 Last login: {admin.last_login}")
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=settings_keyboard())
    elif action == "stats":
        from .admin import _show_stats
        await _show_stats(query.message)
    elif action == "menu":
        await query.edit_message_text("⚙️ *Settings*", parse_mode="Markdown", reply_markup=settings_keyboard())


async def email_change_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    if not context.user_data.get("awaiting_email_change"):
        return None
    user = update.effective_user
    text = (update.effective_message.text or "").strip()
    if not is_valid_email(text):
        await update.effective_message.reply_text("❌ Invalid email format. Try again or /cancel.", parse_mode="Markdown")
        return STATE_AWAIT_EMAIL_CHANGE
    repo = AdminRepository(get_engine())
    admin = repo.get_by_telegram_id(user.id)
    if admin is None:
        await update.effective_message.reply_text("❌ Use /start first.", parse_mode="Markdown")
        return -1
    other = repo.get_by_email(text)
    if other and other.id != admin.id:
        await update.effective_message.reply_text("❌ Email already registered to another admin.", parse_mode="Markdown")
        return STATE_AWAIT_EMAIL_CHANGE
    token = repo.change_email(admin, text)
    email_service.send_verification(text, token, 24)
    audit_service.log(user.id, SETTINGS_CHANGED, details={"field": "email", "to": text})
    await update.effective_message.reply_text(
        "📧 *Email updated — re-verification required.*\n\n📩 Token: `" + token + "`\n"
        "Enter the token in Telegram, or use /resend.\nNote: run /start to complete re-verification.",
        parse_mode="Markdown", reply_markup=main_menu_keyboard())
    context.user_data.pop("awaiting_email_change", None)
    return -1

import logging

from telegram import Update
from telegram.ext import ContextTypes

from core.constants import STATE_AWAIT_BROADCAST, BROADCAST_SENT
from database.connection import get_engine
from database.repositories.user_repo import UserRepository
from services.audit_service import audit_service
from utils.decorators import admin_only

logger = logging.getLogger(__name__)


@admin_only
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "📢 *Broadcast*\n\nSend the message you want to broadcast to all users.\nType /cancel to abort.",
        parse_mode="Markdown")
    return STATE_AWAIT_BROADCAST


async def broadcast_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.effective_message.text or "").strip()
    if not text:
        await update.effective_message.reply_text("❌ Empty message. Send text or /cancel.")
        return STATE_AWAIT_BROADCAST
    user = update.effective_user
    repo = UserRepository(get_engine())
    users, total = repo.list_users(page=1, per_page=100000)
    delivered = 0
    failed = 0
    for u in users:
        try:
            await context.bot.send_message(chat_id=u.telegram_id, text=text, parse_mode="Markdown")
            delivered += 1
        except Exception:
            failed += 1
    audit_service.log(user.id, BROADCAST_SENT, details={"chars": len(text), "delivered": delivered, "failed": failed})
    await update.effective_message.reply_text(
        f"✅ *Broadcast complete*\n📨 Delivered: {delivered}\n❌ Failed: {failed}\n👥 Total users: {total}",
        parse_mode="Markdown")
    return -1

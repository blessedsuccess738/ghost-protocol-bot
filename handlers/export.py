import logging
import os

from telegram import Update
from telegram.ext import ContextTypes

from core.constants import EXPORT_RUN
from database.connection import get_engine
from database.repositories.admin_repo import AdminRepository
from keyboards.inline import export_keyboard, main_menu_keyboard
from services.audit_service import audit_service
from services.export_service import export_service
from utils.decorators import admin_only

logger = logging.getLogger(__name__)


@admin_only
async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text("📤 *Export Data*\n\nChoose a format:",
                                              parse_mode="Markdown", reply_markup=export_keyboard())


async def export_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    fmt = parts[1]
    scope = parts[2] if len(parts) > 2 else "all"
    user = update.effective_user
    await query.edit_message_text(f"⏳ Exporting {fmt.upper()}…", parse_mode="Markdown")
    repo = AdminRepository(get_engine())
    admin = repo.get_by_telegram_id(user.id)
    admin_filter = None if (admin and admin.role == "SUPER_ADMIN") else (admin.id if admin else None)
    try:
        if fmt == "json":
            path = export_service.export_json(admin_id=admin_filter)
        elif fmt == "csv":
            kind = scope if scope in ("cases", "admins", "audit") else "cases"
            path = export_service.export_csv(kind, admin_id=admin_filter)
        elif fmt == "pdf":
            path = export_service.export_pdf()
        else:
            await query.edit_message_text("❌ Unknown format.", parse_mode="Markdown")
            return
    except Exception as exc:
        logger.error("Export failed: %s", exc, exc_info=True)
        await query.edit_message_text(f"❌ Export failed: {exc}", parse_mode="Markdown")
        return
    audit_service.log(user.id, EXPORT_RUN, details={"format": fmt, "scope": scope})
    try:
        with open(path, "rb") as f:
            await query.message.reply_document(f, filename=os.path.basename(path))
        await query.message.reply_text("✅ *Export complete.*", parse_mode="Markdown", reply_markup=main_menu_keyboard())
    except Exception as exc:
        logger.error("Export send failed: %s", exc)
        await query.edit_message_text(f"❌ File created at `{path}` but could not send.", parse_mode="Markdown")

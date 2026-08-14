import logging

from telegram import Update
from telegram.ext import ContextTypes

import config
from core.constants import (STATUS_PENDING, STATUS_BANNED, STATUS_REJECTED, STATUS_REVIEWED,
                            CASE_BANNED, CASE_REJECTED, CASE_REVIEWED)
from database.connection import get_engine
from database.repositories.admin_repo import AdminRepository
from database.repositories.case_repo import CaseRepository
from database.repositories.evidence_repo import EvidenceRepository
from keyboards.inline import (case_actions_keyboard, pagination_keyboard, main_menu_keyboard, moderation_keyboard)
from keyboards.reply import user_keyboard, admin_keyboard
from services.audit_service import audit_service
from services.ban_service import ban_service
from services.export_service import export_service
from utils.decorators import admin_only
from utils.formatters import format_case_details, format_case_summary

logger = logging.getLogger(__name__)
PAGE_SIZE = 5


@admin_only
async def cases_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    admin_repo = AdminRepository(get_engine())
    admin = admin_repo.get_by_telegram_id(user.id)
    case_repo = CaseRepository(get_engine())
    if admin is None:
        from database.repositories.user_repo import UserRepository
        urepo = UserRepository(get_engine())
        profile = urepo.get_by_telegram_id(user.id)
        cases, total = case_repo.list_cases(submitter_id=profile.id if profile else None, page=1, per_page=PAGE_SIZE)
        await _render_user_cases(update.effective_message, cases, total, 1)
        return
    cases, total = case_repo.list_cases(page=1, per_page=PAGE_SIZE)
    await _render_cases(update.effective_message, cases, total, 1)


async def _render_user_cases(message, cases, total: int, page: int, edit: bool = False) -> None:
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    if not cases:
        text = "📋 *No cases found.*\n\nUse 🚫 BAN REQUEST to submit your first case."
        markup = user_keyboard()
        if edit:
            await message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
        else:
            await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)
        return
    lines = [f"📋 *MY CASES* — page {page}/{total_pages} ({total} total)\n"]
    for case in cases:
        lines.append(format_case_summary(case))
        lines.append("")
    text = "\n".join(lines)
    markup = pagination_keyboard("user_cases_page", page, total_pages)
    if edit:
        await message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)


async def _render_cases(message, cases, total: int, page: int, edit: bool = False) -> None:
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    if not cases:
        text = "📋 *No cases found.*\n\nUse 🚫 BAN REQUEST to create your first case."
        markup = admin_keyboard()
        if edit:
            await message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
        else:
            await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)
        return
    lines = [f"📋 *ALL CASES* — page {page}/{total_pages} ({total} total)\n"]
    for case in cases:
        lines.append(format_case_summary(case))
        lines.append("")
    text = "\n".join(lines)
    markup = pagination_keyboard("cases_page", page, total_pages)
    if edit:
        await message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)


async def cases_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    page = int(parts[1])
    user = update.effective_user
    admin_repo = AdminRepository(get_engine())
    admin = admin_repo.get_by_telegram_id(user.id)
    case_repo = CaseRepository(get_engine())
    if admin is None:
        from database.repositories.user_repo import UserRepository
        urepo = UserRepository(get_engine())
        profile = urepo.get_by_telegram_id(user.id)
        cases, total = case_repo.list_cases(submitter_id=profile.id if profile else None, page=page, per_page=PAGE_SIZE)
        await _render_user_cases(query.message, cases, total, page, edit=True)
        return
    cases, total = case_repo.list_cases(page=page, per_page=PAGE_SIZE)
    await _render_cases(query.message, cases, total, page, edit=True)


async def moderation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    if user.id not in config.ADMIN_IDS:
        await query.edit_message_text("⛔ Unauthorized.", parse_mode="Markdown")
        return
    parts = query.data.split(":")
    case_id = parts[1]
    action = parts[2].upper()
    admin_repo = AdminRepository(get_engine())
    admin = admin_repo.get_by_telegram_id(user.id)
    if admin is None or not admin.is_active:
        await query.edit_message_text("⛔ Admin not found or deactivated.", parse_mode="Markdown")
        return
    case_repo = CaseRepository(get_engine())
    case = case_repo.get_by_case_id(case_id)
    if case is None:
        await query.edit_message_text("❌ Case not found.", parse_mode="Markdown")
        return
    result = ban_service.act(case, action, admin_id=admin.id, admin_telegram_id=user.id)
    if not result.get("ok"):
        await query.edit_message_text(f"❌ {result.get('error', 'Action failed.')}", parse_mode="Markdown")
        return
    status = result["status"]
    emoji = {"BANNED": "🚫", "REJECTED": "↩️", "PENDING": "⏳", "REVIEWED": "✅"}.get(status, "📋")
    await query.edit_message_text(
        f"{emoji} *Case {case.case_id} updated*\nStatus: *{status}*\nTarget: `{case.target_link}`\n"
        f"Reason: {case.reason}\n\nAction logged in ban records + audit trail.",
        parse_mode="Markdown", reply_markup=moderation_keyboard(case.case_id))


async def case_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    action = parts[1]
    case_id = parts[2]
    case_repo = CaseRepository(get_engine())
    ev_repo = EvidenceRepository(get_engine())
    case = case_repo.get_by_case_id(case_id)
    if case is None:
        await query.edit_message_text("❌ Case not found.", parse_mode="Markdown")
        return
    user = update.effective_user
    admin_repo = AdminRepository(get_engine())
    admin = admin_repo.get_by_telegram_id(user.id)
    if action in ("mod", "ban", "reject", "pending", "reviewed"):
        if admin is None or user.id not in config.ADMIN_IDS:
            await query.edit_message_text("⛔ You do not have permission for this case.", parse_mode="Markdown")
            return
        await moderation_callback(update, context)
        return
    if action == "evidence":
        evidence = ev_repo.list_for_case(case.id)
        if not evidence:
            await query.edit_message_text(f"🧾 *No evidence for {case.case_id}*", parse_mode="Markdown",
                                          reply_markup=case_actions_keyboard(case.case_id))
            return
        lines = [f"🧾 *Evidence for {case.case_id}* ({len(evidence)} items)\n"]
        for idx, ev in enumerate(evidence, 1):
            lines.append(f"{idx}. [{ev.evidence_type}] {ev.reference[:80]}")
        lines.append("")
        lines.append("(Screenshot files are stored locally on the server.)")
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown",
                                      reply_markup=case_actions_keyboard(case.case_id))
    elif action == "export":
        path = export_service.export_pdf([case.case_id])
        try:
            with open(path, "rb") as f:
                await query.message.reply_document(f, filename=f"report_{case.case_id}.pdf")
        except Exception as exc:
            logger.error("PDF send failed: %s", exc)
            await query.edit_message_text("❌ Could not send PDF.", parse_mode="Markdown")
        audit_service.log(user.id, "export.run", details={"case_id": case.case_id, "format": "pdf"})
    else:
        cases, total = case_repo.list_cases(page=1, per_page=PAGE_SIZE)
        await _render_cases(query.message, cases, total, 1, edit=True)

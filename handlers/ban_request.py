import logging

from telegram import Update
from telegram.ext import ContextTypes

import config
from core.constants import (STATE_TARGET, STATE_EVIDENCE_TYPE, STATE_EVIDENCE_LINK, STATE_EVIDENCE_SCREENSHOT,
                            STATE_REASON, STATE_DESCRIPTION, STATE_REVIEW, STATE_EDIT_CHOICE,
                            EVIDENCE_LINK, EVIDENCE_SCREENSHOT, EVIDENCE_BOTH, EVIDENCE_SKIP,
                            STATUS_PENDING, REASONS, CASE_CREATED, EVIDENCE_ADDED)
from database.connection import get_engine
from database.repositories.admin_repo import AdminRepository
from database.repositories.case_repo import CaseRepository
from database.repositories.evidence_repo import EvidenceRepository
from database.repositories.user_repo import UserRepository
from keyboards.inline import (evidence_type_keyboard, reason_keyboard, review_keyboard,
                              edit_choice_keyboard, main_menu_keyboard)
from keyboards.reply import user_keyboard
from services.audit_service import audit_service
from services.email_service import email_service
from utils.decorators import rate_limited
from utils.formatters import format_case_details
from utils.validators import (is_valid_telegram_link, is_valid_message_link, is_valid_screenshot_size,
                              is_valid_description, sanitize_text, parse_target)

logger = logging.getLogger(__name__)


def _new_ban_request() -> dict:
    return {"target": None, "target_type": None, "target_name": None, "evidence_type": None,
            "links": [], "screenshots": [], "reason": None, "description": None, "case_id": None}


async def ban_request_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["ban_request"] = _new_ban_request()
    await update.effective_message.reply_text(
        "🚫 *BAN REQUEST — Step 1/6*\n\n"
        "Send the Telegram channel/group/user *link* or *username* you want to submit for moderation review.\n\n"
        "Accepted formats:\n• `https://t.me/username`\n• `@username`\n• `https://telegram.me/username`\n\n"
        "Type /cancel to abort.", parse_mode="Markdown")
    return STATE_TARGET


async def target_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.effective_message.text or "").strip()
    report = context.user_data.get("ban_request", _new_ban_request())
    if not is_valid_telegram_link(text):
        await update.effective_message.reply_text(
            "❌ Invalid Telegram link. Use `https://t.me/username`, `@username`, or a bare username.\nTry again or /cancel.",
            parse_mode="Markdown")
        return STATE_TARGET
    link, target_type, name = parse_target(text)
    report.update({"target": link, "target_type": target_type, "target_name": name})
    context.user_data["ban_request"] = report
    await update.effective_message.reply_text(
        "✅ Target captured.\n\n🎯 `" + link + "`\n\n*Step 2/6 — Evidence type:*\nWhat kind of evidence do you have?",
        parse_mode="Markdown", reply_markup=evidence_type_keyboard())
    return STATE_EVIDENCE_TYPE


async def evidence_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    query = update.callback_query
    await query.answer()
    choice = query.data.split(":", 1)[1]
    report = context.user_data.get("ban_request", _new_ban_request())
    report["evidence_type"] = choice
    context.user_data["ban_request"] = report
    if choice in (EVIDENCE_LINK, EVIDENCE_BOTH):
        await query.edit_message_text(
            "*Step 3/6 — Message links:*\n\nSend the relevant Telegram message link(s).\n"
            "Format: `https://t.me/channel/12345`\n\nSend multiple links one per message. Type `/done` when finished.",
            parse_mode="Markdown")
        return STATE_EVIDENCE_LINK
    if choice in (EVIDENCE_SCREENSHOT, EVIDENCE_BOTH):
        await query.edit_message_text(
            "*Step 3/6 — Screenshots:*\n\nUpload screenshot(s) of the evidence (max 20MB each).\nType `/done` when finished.",
            parse_mode="Markdown")
        return STATE_EVIDENCE_SCREENSHOT
    return await _ask_reason(query.edit_message_text)


async def _ask_reason(edit_func) -> int:
    await edit_func("*Step 4/6 — Reason:*\nSelect the most appropriate reason:",
                    parse_mode="Markdown", reply_markup=reason_keyboard())
    return STATE_REASON


async def evidence_link_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.effective_message.text or "").strip()
    report = context.user_data.get("ban_request", _new_ban_request())
    if text.lower() in ("/done", "done", "/skip"):
        if not report["links"]:
            await update.effective_message.reply_text(
                "⚠️ No links added yet. Send at least one link, or type /cancel to abort.", parse_mode="Markdown")
            return STATE_EVIDENCE_LINK
        return await _ask_reason(update.effective_message.reply_text)
    if not is_valid_message_link(text):
        await update.effective_message.reply_text(
            "❌ Invalid message link. Format: `https://t.me/channel/12345`\nSend another link or /done when finished.",
            parse_mode="Markdown")
        return STATE_EVIDENCE_LINK
    if len(report["links"]) >= config.MAX_LINKS_PER_CASE:
        await update.effective_message.reply_text("⚠️ Maximum links reached. Type /done to continue.", parse_mode="Markdown")
        return STATE_EVIDENCE_LINK
    report["links"].append(text)
    context.user_data["ban_request"] = report
    await update.effective_message.reply_text(f"✅ Link added ({len(report['links'])}). Send more or type /done.", parse_mode="Markdown")
    return STATE_EVIDENCE_LINK


async def evidence_screenshot_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    report = context.user_data.get("ban_request", _new_ban_request())
    message = update.effective_message
    if message.text and message.text.lower() in ("/done", "done", "/skip"):
        if not report["screenshots"]:
            await update.effective_message.reply_text(
                "⚠️ No screenshots added yet. Upload at least one, or /cancel to abort.", parse_mode="Markdown")
            return STATE_EVIDENCE_SCREENSHOT
        return await _ask_reason(update.effective_message.reply_text)
    if message.photo:
        photo = message.photo[-1]
        size = photo.file_size or 0
        if not is_valid_screenshot_size(size):
            await update.effective_message.reply_text(
                f"❌ File too large ({size // 1024 // 1024}MB). Max {config.MAX_SCREENSHOT_MB}MB.", parse_mode="Markdown")
            return STATE_EVIDENCE_SCREENSHOT
        report["screenshots"].append({"file_id": photo.file_id, "size": size})
        context.user_data["ban_request"] = report
        await update.effective_message.reply_text(f"✅ Screenshot received ({len(report['screenshots'])}). Upload more or type /done.", parse_mode="Markdown")
        return STATE_EVIDENCE_SCREENSHOT
    await update.effective_message.reply_text("📸 Please send an image (photo), or type /done when finished.", parse_mode="Markdown")
    return STATE_EVIDENCE_SCREENSHOT


async def reason_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    query = update.callback_query
    await query.answer()
    reason = query.data.split(":", 1)[1]
    if reason not in REASONS:
        return STATE_REASON
    report = context.user_data.get("ban_request", _new_ban_request())
    report["reason"] = reason
    context.user_data["ban_request"] = report
    await query.edit_message_text(
        "*Step 5/6 — Description:*\n\nProvide additional details (optional).\nSend your description, or type `skip` to skip this step.",
        parse_mode="Markdown")
    return STATE_DESCRIPTION


async def description_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.effective_message.text or "").strip()
    report = context.user_data.get("ban_request", _new_ban_request())
    if text.lower() not in ("skip", "/skip", "-"):
        if not is_valid_description(text):
            await update.effective_message.reply_text(
                f"❌ Description too long. Max {config.MAX_DESCRIPTION_LENGTH} characters.", parse_mode="Markdown")
            return STATE_DESCRIPTION
        report["description"] = sanitize_text(text)
    else:
        report["description"] = None
    context.user_data["ban_request"] = report
    ev = report.get("evidence_type")
    ev_label = {"message_link": "🔗 Links", "screenshot": "📸 Screenshots",
                "both": "📎 Links + Screenshots", "skip": "⏭️ Skipped"}.get(ev, ev)
    preview = ("*Step 6/6 — Review & Confirm*\n━━━━━━━━━━━━━━━━━━\n"
               f"🎯 Target: `{report['target']}`\n🏷 Type: {report['target_type']}\n"
               f"🧾 Evidence: {ev_label}\n🔗 Links: {len(report['links'])} | 📸 Shots: {len(report['screenshots'])}\n"
               f"🚨 Reason: {report['reason']}\n📝 Description: {report.get('description') or '—'}\n"
               "━━━━━━━━━━━━━━━━━━\nConfirm to submit the BAN REQUEST, edit a field, or cancel.")
    await update.effective_message.reply_text(preview, parse_mode="Markdown", reply_markup=review_keyboard())
    return STATE_REVIEW


async def review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    query = update.callback_query
    await query.answer()
    action = query.data.split(":", 1)[1]
    report = context.user_data.get("ban_request", _new_ban_request())
    if action == "cancel":
        context.user_data.pop("ban_request", None)
        await query.edit_message_text("❌ Ban request cancelled.\n\nUse 🚫 BAN REQUEST to start a new one.",
                                      parse_mode="Markdown", reply_markup=main_menu_keyboard())
        return -1
    if action == "edit":
        await query.edit_message_text("*What would you like to edit?*", parse_mode="Markdown",
                                      reply_markup=edit_choice_keyboard())
        return STATE_EDIT_CHOICE
    if action == "back":
        await query.edit_message_text("*Step 6/6 — Review:*\n" + _review_text(report),
                                      parse_mode="Markdown", reply_markup=review_keyboard())
        return STATE_REVIEW
    if action == "confirm":
        return await _create_case(update, context, query)
    return STATE_REVIEW


async def edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    query = update.callback_query
    await query.answer()
    field = query.data.split(":", 1)[1]
    context.user_data["editing_field"] = field
    if field == "target":
        await query.edit_message_text("*Edit Target:*\nSend the new Telegram link.", parse_mode="Markdown")
        return STATE_TARGET
    if field == "reason":
        await query.edit_message_text("*Edit Reason:*", parse_mode="Markdown", reply_markup=reason_keyboard())
        return STATE_REASON
    if field == "description":
        await query.edit_message_text("*Edit Description:*\nSend the new description or `skip`.", parse_mode="Markdown")
        return STATE_DESCRIPTION
    return STATE_EDIT_CHOICE


def _review_text(report: dict) -> str:
    ev_label = {"message_link": "🔗 Links", "screenshot": "📸 Screenshots",
                "both": "📎 Both", "skip": "⏭️ Skipped"}.get(report.get("evidence_type"), report.get("evidence_type"))
    return (f"🎯 Target: `{report['target']}`\n🏷 Type: {report['target_type']}\n"
            f"🧾 Evidence: {ev_label} ({len(report['links'])} links, {len(report['screenshots'])} shots)\n"
            f"🚨 Reason: {report['reason']}\n📝 Description: {report.get('description') or '—'}")


async def _create_case(update: Update, context: ContextTypes.DEFAULT_TYPE, query) -> int:
    report = context.user_data.get("ban_request", _new_ban_request())
    user = update.effective_user
    case_repo = CaseRepository(get_engine())
    ev_repo = EvidenceRepository(get_engine())
    user_repo = UserRepository(get_engine())
    submitter = user_repo.get_by_telegram_id(user.id)
    admin = None
    if user.id in config.ADMIN_IDS:
        admin_repo = AdminRepository(get_engine())
        admin = admin_repo.get_by_telegram_id(user.id)
    case = case_repo.create(admin_id=admin.id if admin else None,
                            submitter_id=submitter.id if submitter else None,
                            target_link=report["target"], target_type=report.get("target_type"),
                            target_name=report.get("target_name"), reason=report["reason"],
                            description=report.get("description"), status=STATUS_PENDING)
    report["case_id"] = case.case_id
    context.user_data["ban_request"] = report
    ev_count = 0
    for link in report.get("links", []):
        ev_repo.add(case.id, EVIDENCE_LINK, link)
        ev_count += 1
    for shot in report.get("screenshots", []):
        ev_repo.add(case.id, EVIDENCE_SCREENSHOT, shot["file_id"], file_id=shot["file_id"], file_size=shot.get("size"))
        ev_count += 1
    audit_service.log(user.id, CASE_CREATED, details={"case_id": case.case_id})
    if ev_count:
        audit_service.log(user.id, EVIDENCE_ADDED, details={"case_id": case.case_id, "count": ev_count})
    if admin and admin.email:
        email_service.send_case_created(admin.email, case.case_id, case.target_link, case.reason)
    await query.edit_message_text(
        f"✅ *BAN REQUEST submitted successfully!*\n\n{format_case_details(case, ev_count)}\n\n"
        "*Status: ⏳ PENDING — awaiting moderation review.*\nAn authorized admin will review the evidence and take action.\n\n"
        "Use the buttons below 👇", parse_mode="Markdown", reply_markup=user_keyboard())
    context.user_data.pop("ban_request", None)
    return -1

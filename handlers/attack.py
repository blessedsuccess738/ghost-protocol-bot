"""
handlers/attack.py — Verify Target tool suite for 『𝑮𝑷』 𝑮𝑯𝑶𝑺𝑻 𝑷𝑹𝑶𝑻𝑶𝑪𝑶𝑳 BOT.

Admin-only, keyboard-first tool menu:

  /attack            → open the Verify Target suite
  /verify <target>   → verify a target immediately (command form)
  /status            → recent activity + tool stats
  /stop              → cancels the current verification session (safe)

Flow: admin enters target → bot extracts + verifies existence/reachability via
public t.me metadata → shows tool buttons → admin picks BAN ACCOUNT (opens a
moderation case through the existing ban_request workflow) or VERIFY AGAIN.

All actions are logged to attack_logs + audit_logs. No DDOS, no bug-exploit,
no off-platform ban functionality exists in this module.

⚠️ WARNING (displayed): These tools are for LEGITIMATE scam removal only.
Misuse will result in permanent ban from this bot. All actions are logged.
"""
import logging

from telegram import Update
from telegram.ext import ContextTypes

import config
from core.constants import (
    STATE_ATTACK_TARGETS,
    ATTACK_LOG,
    ATTACK_STARTED,
    ATTACK_STOPPED,
)
from database.connection import get_engine
from database.repositories.admin_repo import AdminRepository
from database.repositories.user_repo import UserRepository
from keyboards.inline import (
    attack_tools_keyboard,
    attack_verify_options_keyboard,
    attack_ban_reason_keyboard,
    attack_confirm_keyboard,
    attack_recent_pagination_keyboard,
)
from keyboards.reply import admin_keyboard
from services.audit_service import audit_service
from services.target_verify_service import (
    target_verify_service,
    extract_target,
    is_protected,
    TOOL_VERIFY,
)
from utils.decorators import admin_only, rate_limited
from utils.formatters import format_datetime

logger = logging.getLogger(__name__)

WARNING_TEXT = (
    "⚠️ *WARNING:* These tools are for LEGITIMATE scam removal only. "
    "Misuse will result in permanent ban from this bot. "
    "All actions are logged and audited."
)

PAGE_SIZE = 5


def _admin_payload(update: Update) -> dict:
    """Build the admin dict used by target_verify_service."""
    user = update.effective_user
    admin_repo = AdminRepository(get_engine())
    admin = admin_repo.get_by_telegram_id(user.id)
    profile = UserRepository(get_engine()).get_by_telegram_id(user.id)
    return {
        "id": admin.id if admin else None,
        "telegram_id": user.id,
        "user_id": profile.id if profile else None,
    }


# ── Entry / menu ─────────────────────────────────────────────────────────
@admin_only
async def attack_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/attack — open the Verify Target tool suite."""
    await update.effective_message.reply_text(
        "🎯 *VERIFY TARGET — TOOL SUITE*\n\n"
        "Verify a Telegram account/channel/group and open a moderation case.\n\n"
        f"{WARNING_TEXT}",
        parse_mode="Markdown",
        reply_markup=attack_tools_keyboard(),
    )


@admin_only
async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/verify <target> — immediately verify a target."""
    args = context.args
    if not args:
        await update.effective_message.reply_text(
            "🎯 *Verify Target*\n\n"
            "Send the target username or link you want to verify:\n"
            "`@username` · `https://t.me/username` · bare username",
            parse_mode="Markdown",
        )
        return STATE_ATTACK_TARGETS
    target = " ".join(args).strip()
    return await _run_verification(update, context, target)


@admin_only
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ban <target> — verify a target and route into the BAN (moderation case) flow.

    The 'BAN' action is an internal moderation decision: it opens a BAN REQUEST
    case for review by authorized admins. It does NOT mass-report or abuse
    Telegram's reporting system, and it cannot globally ban arbitrary accounts
    (the Bot API has no such capability).
    """
    args = context.args
    if not args:
        await update.effective_message.reply_text(
            "🚫 *BAN ACCOUNT*\n\n"
            "Usage: `/ban @username` or `/ban https://t.me/username`\n\n"
            "The bot will verify the target, then let you open a moderation "
            "case (BAN REQUEST) with reason + confirmation.\n\n"
            f"{WARNING_TEXT}",
            parse_mode="Markdown",
        )
        return
    target = " ".join(args).strip()
    return await _run_verification(update, context, target)


@admin_only
async def bug_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/bug <post_link> — NOT AVAILABLE.

    The originally-requested 'BUG ADMIN' tool targets a third party's Telegram
    account ('extract admin ID from post → trigger bug on admin account').
    That is an exploit against another person's account and is out of scope
    for this bot. This command exists so admins get a clear, honest message
    instead of a silent 404.
    """
    await update.effective_message.reply_text(
        "🐛 *BUG ADMIN — not available*\n\n"
        "This tool would exploit a third-party Telegram account, which is "
        "against Telegram's Terms of Service and out of scope for this bot. "
        "It will not be implemented.\n\n"
        "If you need to report a channel/group admin, use the 🎯 VERIFY TARGET "
        "suite or 🚫 BAN REQUEST to open a documented moderation case — an "
        "authorized admin will review the evidence.",
        parse_mode="Markdown",
        reply_markup=attack_tools_keyboard(),
    )


@admin_only
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/status — recent verification activity + tool stats."""
    user = update.effective_user
    payload = _admin_payload(update)
    rows, total = target_verify_service.recent(payload["id"] or -1, page=1, per_page=PAGE_SIZE)
    stats_total = target_verify_service.count_total()
    lines = [
        "📊 *VERIFY TARGET — STATUS*",
        "━━━━━━━━━━━━━━━━━━",
        f"👤 Admin: {user.full_name or user.id}",
        f"📜 Your recent actions: {total}",
        f"🗄 Total tool actions logged: {stats_total}",
        "",
    ]
    if rows:
        lines.append("*Recent activity:*")
        for r in rows:
            lines.append(
                f"• {r.tool_used} → {r.target} [{r.status}] "
                f"({format_datetime(r.created_at)})"
            )
    else:
        lines.append("No recent activity yet.")
    await update.effective_message.reply_text(
        "\n".join(lines), parse_mode="Markdown", reply_markup=attack_tools_keyboard(),
    )


@admin_only
async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/stop — cancel the current verification session."""
    context.user_data.pop("attack_target", None)
    context.user_data.pop("attack_flow", None)
    await update.effective_message.reply_text(
        "🛑 *Verification session cancelled.*\n\n"
        "No action was taken. All actions are logged for audit.",
        parse_mode="Markdown",
        reply_markup=attack_tools_keyboard(),
    )
    audit_service.log(update.effective_user.id, ATTACK_STOPPED)


# ── Conversation input ────────────────────────────────────────────────────
async def attack_target_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    """Receives the raw target text from the conversation state.

    Global MessageHandler — only acts when the admin explicitly started the
    verify flow (attack_flow == 'verify') to avoid intercepting other text.
    """
    if context.user_data.get("attack_flow") != "verify":
        return None
    user = update.effective_user
    if user is None or user.id not in config.ADMIN_IDS:
        return None
    text = (update.effective_message.text or "").strip()
    context.user_data.pop("attack_flow", None)
    return await _run_verification(update, context, text)


async def _run_verification(update: Update, context: ContextTypes.DEFAULT_TYPE,
                            raw_target: str) -> int | None:
    """Core verification + render result + tool buttons."""
    payload = _admin_payload(update)
    result = await target_verify_service.verify(payload, raw_target)

    if not result.get("ok"):
        await update.effective_message.reply_text(
            f"❌ *Verification failed*\n\n{result.get('error', 'Invalid target')}\n\n"
            f"{WARNING_TEXT}",
            parse_mode="Markdown",
            reply_markup=attack_tools_keyboard(),
        )
        return None

    parsed = result["parsed"]
    reach = result["reach"]
    username = parsed["username"]
    target_type = parsed["target_type"]

    exists_icon = "🟢" if result["exists"] else "🔴"
    active_icon = "🟢" if result["active"] else "🔴"
    reach_icon = "🟢" if result["reachable"] else "🔴"

    text = (
        "🎯 *TARGET VERIFIED*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🔗 Target: `{parsed['link']}`\n"
        f"🏷 Type: {target_type}\n"
        f"{'🆔 ID: not exposed (username-based)' if parsed.get('target_id') is None else '🆔 ID: ' + str(parsed.get('target_id'))}\n"
        f"{exists_icon} Exists: {'Yes' if result['exists'] else 'No'}\n"
        f"{active_icon} Active: {'Yes' if result['active'] else 'No'}\n"
        f"{reach_icon} Reachable: {'Yes' if result['reachable'] else 'No'}\n"
        f"📝 Note: {reach.get('note', '—')}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Select an action below.\n\n"
        f"{WARNING_TEXT}"
    )

    if result["exists"]:
        markup = attack_verify_options_keyboard(username, target_type)
    else:
        markup = attack_tools_keyboard()

    await update.effective_message.reply_text(text, parse_mode="Markdown", reply_markup=markup)
    return None


# ── Callbacks ─────────────────────────────────────────────────────────────
async def attack_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if user.id not in config.ADMIN_IDS:
        await query.answer("Unauthorized", show_alert=True)
        return
    await query.answer()

    data = query.data  # attack:...
    parts = data.split(":")
    action = parts[1]

    if action == "menu":
        await query.edit_message_text(
            "🎯 *VERIFY TARGET — TOOL SUITE*\n\n"
            "Verify a Telegram account/channel/group and open a moderation case.\n\n"
            f"{WARNING_TEXT}",
            parse_mode="Markdown",
            reply_markup=attack_tools_keyboard(),
        )
    elif action == "verify":
        context.user_data["attack_flow"] = "verify"
        await query.edit_message_text(
            "🎯 *Verify Target*\n\n"
            "Send the target username or link you want to verify:\n"
            "`@username` · `https://t.me/username` · bare username\n\n"
            "Type /cancel to abort.",
            parse_mode="Markdown",
        )
        return  # state is handled by conversation handler
    elif action == "recent":
        await _render_recent(update, context, query, page=1)
    elif action == "stats":
        stats = target_verify_service
        await query.edit_message_text(
            "📊 *VERIFY TARGET — STATS*\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🗄 Total actions logged: {stats.count_total()}\n"
            f"✅ Verifications: {stats.attack_log_repo.count_by_tool('verify_target')}\n"
            f"🚫 Ban-request cases: {stats.attack_log_repo.count_by_tool('ban_request')}\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "All actions are logged and audited.",
            parse_mode="Markdown",
            reply_markup=attack_tools_keyboard(),
        )
    elif action == "reverify":
        username = parts[2]
        await _run_verification_callback(update, context, query, username)
    elif action == "ban":
        username = parts[2]
        target_type = parts[3]
        await query.edit_message_text(
            "🚫 *BAN ACCOUNT — reason*\n\n"
            f"Target: `{username}`\n"
            f"Type: {target_type}\n\n"
            "Select the reason for this moderation case:",
            parse_mode="Markdown",
            reply_markup=attack_ban_reason_keyboard(username, target_type),
        )
    elif action == "reason":
        # attack:reason:{username}:{target_type}:{reason}
        username = parts[2]
        target_type = parts[3]
        reason = ":".join(parts[4:])
        await query.edit_message_text(
            f"⚠️ *Confirm action on* `{username}` *?*\n\n"
            f"Type: {target_type}\n"
            f"Reason: {reason}\n\n"
            "This opens a moderation case (BAN REQUEST) — an admin will review "
            "the evidence. This bot does NOT mass-report or abuse Telegram's "
            "reporting system.\n\n"
            f"{WARNING_TEXT}",
            parse_mode="Markdown",
            reply_markup=attack_confirm_keyboard(username, target_type, reason),
        )
    elif action == "confirm":
        # attack:confirm:{username}:{target_type}:{reason}
        username = parts[2]
        target_type = parts[3]
        reason = ":".join(parts[4:])
        await _execute_ban_case(update, context, query, username, target_type, reason)
    elif action == "cancel":
        context.user_data.pop("attack_target", None)
        context.user_data.pop("attack_flow", None)
        await query.edit_message_text(
            "❌ *Cancelled.*\n\nNo action was taken. All actions are logged.",
            parse_mode="Markdown",
            reply_markup=attack_tools_keyboard(),
        )
    elif action == "none":
        pass
    else:
        await query.edit_message_text(
            "❌ Unknown action.", parse_mode="Markdown",
            reply_markup=attack_tools_keyboard(),
        )


async def _render_recent(update: Update, context: ContextTypes.DEFAULT_TYPE,
                         query, page: int = 1) -> None:
    payload = _admin_payload(update)
    rows, total = target_verify_service.recent(payload["id"] or -1, page=page, per_page=PAGE_SIZE)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    lines = [f"📜 *RECENT ACTIVITY* — page {page}/{total_pages} ({total})\n"]
    if rows:
        for r in rows:
            lines.append(
                f"• {r.tool_used} → `{r.target}`\n"
                f"  Status: {r.status} | {format_datetime(r.created_at)}"
            )
    else:
        lines.append("No activity yet.")
    await query.edit_message_text(
        "\n".join(lines), parse_mode="Markdown",
        reply_markup=attack_recent_pagination_keyboard(page, total_pages),
    )


async def _run_verification_callback(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                     query, username: str) -> None:
    """Re-run verification from the tool buttons (callback path)."""
    payload = _admin_payload(update)
    result = await target_verify_service.verify(payload, f"@{username}")
    if not result.get("ok"):
        await query.edit_message_text(
            f"❌ Verification failed: {result.get('error')}",
            parse_mode="Markdown", reply_markup=attack_tools_keyboard(),
        )
        return
    parsed = result["parsed"]
    reach = result["reach"]
    text = (
        "🎯 *TARGET VERIFIED*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🔗 Target: `{parsed['link']}`\n"
        f"🏷 Type: {parsed['target_type']}\n"
        f"{'🟢' if result['exists'] else '🔴'} Exists: {'Yes' if result['exists'] else 'No'}\n"
        f"{'🟢' if result['active'] else '🔴'} Active: {'Yes' if result['active'] else 'No'}\n"
        f"📝 {reach.get('note', '—')}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"{WARNING_TEXT}"
    )
    markup = (attack_verify_options_keyboard(parsed["username"], parsed["target_type"])
              if result["exists"] else attack_tools_keyboard())
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=markup)


async def _execute_ban_case(update: Update, context: ContextTypes.DEFAULT_TYPE,
                            query, username: str, target_type: str, reason: str) -> None:
    """Execute the BAN action = open a moderation case (BAN REQUEST)."""
    payload = _admin_payload(update)
    parsed = extract_target(f"@{username}")
    if parsed is None or is_protected(parsed["username"]):
        await query.edit_message_text(
            "❌ Action failed on target — protected or invalid account.",
            parse_mode="Markdown", reply_markup=attack_tools_keyboard(),
        )
        return
    parsed["target_type"] = target_type or parsed["target_type"]

    try:
        out = target_verify_service.create_moderation_case(
            payload, parsed, reason=reason,
            description="Created via Verify Target tool suite.",
        )
        case = out["case"]
        await query.edit_message_text(
            f"✅ *Action completed on* `{username}`\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"📋 Case: `{case.case_id}`\n"
            f"🚫 Reason: {reason}\n"
            f"📌 Status: ⏳ PENDING — awaiting admin review\n"
            f"🗄 Logged in attack_logs + audit trail.\n\n"
            "This moderation case will be reviewed by an authorized admin.",
            parse_mode="Markdown",
            reply_markup=attack_tools_keyboard(),
        )
    except Exception as exc:
        logger.exception("Ban case creation failed")
        await query.edit_message_text(
            f"❌ *Action failed on* `{username}` — Reason: {exc}",
            parse_mode="Markdown", reply_markup=attack_tools_keyboard(),
        )

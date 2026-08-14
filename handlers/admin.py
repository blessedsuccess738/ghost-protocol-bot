import logging
import os
import time

from telegram import Update
from telegram.ext import ContextTypes

import config
from core.constants import (ADMIN_CREATED, ADMIN_DEACTIVATED, ADMIN_REACTIVATED,
                            STATE_AWAIT_COIN_USER, STATE_AWAIT_COIN_AMOUNT, STATE_AWAIT_COIN_ALL_CONFIRM,
                            STATE_AWAIT_FORCE_GROUP_ID, STATE_AWAIT_REFERRAL_AMOUNT, STATE_AWAIT_REFERRAL_MIN)
from database.connection import get_engine
from database.repositories.admin_repo import AdminRepository
from database.repositories.audit_repo import AuditRepository
from database.repositories.case_repo import CaseRepository
from database.repositories.evidence_repo import EvidenceRepository
from database.repositories.notification_repo import NotificationRepository
from database.repositories.session_repo import SessionRepository
from database.repositories.user_repo import UserRepository
from keyboards.inline import (admin_panel_keyboard, main_menu_keyboard, pagination_keyboard,
                              coin_menu_keyboard, coin_all_confirm_keyboard, referral_menu_keyboard,
                              force_group_menu_keyboard, manage_admins_keyboard, moderation_keyboard)
from keyboards.reply import admin_keyboard
from services.audit_service import audit_service
from services.ban_service import ban_service
from services.coin_service import coin_service
from services.force_group_service import force_group_service
from services.referral_service import referral_service
from utils.decorators import admin_only, owner_only, permission_required
from utils.formatters import format_admin_summary, format_uptime, format_user_summary

logger = logging.getLogger(__name__)
ADMIN_PAGE_SIZE = 10
USER_PAGE_SIZE = 10
_START_TIME = time.monotonic()


@admin_only
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text("👑 *『𝑮𝑷』 ADMIN PANEL*\n\nSelect an option:",
                                              parse_mode="Markdown", reply_markup=admin_panel_keyboard())


async def admin_panel_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await admin_command(update, context)


@admin_only
async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_users(update.effective_message, page=1)


@admin_only
async def banned_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_users(update.effective_message, page=1, banned_only=True)


async def users_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    page = int(parts[1])
    banned = "banned" in parts[0]
    await _render_users(query.message, page=page, banned_only=banned, edit=True)


async def _render_users(message, page: int = 1, banned_only: bool = False, edit: bool = False) -> None:
    repo = UserRepository(get_engine())
    users, total = repo.list_users(page=page, per_page=USER_PAGE_SIZE, banned_only=banned_only)
    total_pages = max(1, (total + USER_PAGE_SIZE - 1) // USER_PAGE_SIZE)
    title = "🚫 *Banned Users*" if banned_only else "👥 *Users*"
    lines = [f"{title} — page {page}/{total_pages} ({total} total)\n"]
    for u in users:
        lines.append(format_user_summary(u))
        lines.append("")
    text = "\n".join(lines)
    markup = pagination_keyboard("banned_page" if banned_only else "users_page", page, total_pages)
    if edit:
        await message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)


async def search_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting_user_search"] = True
    await query.edit_message_text("🔍 *Search User*\n\nSend a username (without @) or Telegram ID:",
                                  parse_mode="Markdown", reply_markup=admin_panel_keyboard())


async def user_search_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get("awaiting_user_search"):
        return
    text = (update.effective_message.text or "").strip().lstrip("@")
    repo = UserRepository(get_engine())
    user = None
    if text.isdigit():
        user = repo.get_by_telegram_id(int(text))
    if user is None:
        users, _ = repo.list_users(page=1, per_page=5, search=text)
        user = users[0] if users else None
    context.user_data.pop("awaiting_user_search", None)
    if user is None:
        await update.effective_message.reply_text("❌ User not found. They must /start the bot first.", parse_mode="Markdown")
        return
    await update.effective_message.reply_text(format_user_summary(user), parse_mode="Markdown",
                                              reply_markup=admin_panel_keyboard())


@admin_only
async def pending_cases_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_pending(update.effective_message, page=1)


async def pending_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[1])
    await _render_pending(query.message, page=page, edit=True)


async def _render_pending(message, page: int = 1, edit: bool = False) -> None:
    from core.constants import STATUS_PENDING
    repo = CaseRepository(get_engine())
    cases, total = repo.list_cases(status=STATUS_PENDING, page=page, per_page=5)
    total_pages = max(1, (total + 5 - 1) // 5)
    if not cases:
        text = "📋 *No pending cases.* 🎉 All clear!"
        markup = admin_panel_keyboard()
        if edit:
            await message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
        else:
            await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)
        return
    from utils.formatters import format_case_summary
    lines = [f"📋 *PENDING CASES* — page {page}/{total_pages} ({total} total)\n"]
    for case in cases:
        lines.append(format_case_summary(case))
        lines.append("")
    text = "\n".join(lines)
    markup = pagination_keyboard("pending_page", page, total_pages)
    if edit:
        await message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)


async def case_review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    if user.id not in config.ADMIN_IDS:
        await query.edit_message_text("⛔ Unauthorized.", parse_mode="Markdown")
        return
    case_id = query.data.split(":")[1]
    repo = CaseRepository(get_engine())
    case = repo.get_by_case_id(case_id)
    if case is None:
        await query.edit_message_text("❌ Case not found.", parse_mode="Markdown")
        return
    from database.repositories.ban_repo import BanRepository
    history = BanRepository(get_engine()).history_for_target(case.target_link, limit=5)
    hist_lines = ""
    if history:
        hist_lines = "\n*Previous moderation history:*\n" + "\n".join(
            f"• {h.action} — {h.created_at.strftime('%Y-%m-%d')}" for h in history[:3]) + "\n"
    text = (f"🚫 *Case Review — {case.case_id}*\n━━━━━━━━━━━━━━━━━━\n"
            f"🎯 Target: `{case.target_link}`\n🏷 Type: {case.target_type or '—'}\n"
            f"🚨 Reason: {case.reason}\n📝 Description: {case.description or '—'}\n"
            f"📅 Submitted: {case.created_at.strftime('%Y-%m-%d %H:%M')}\n📌 Status: {case.status}"
            f"{hist_lines}\n━━━━━━━━━━━━━━━━━━\nChoose a moderation action:")
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=moderation_keyboard(case.case_id))


@admin_only
async def coin_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    action = query.data.split(":", 1)[1]
    if action == "history":
        user = update.effective_user
        txns, total = coin_service.history(user.id, page=1, per_page=5)
        if not txns:
            await query.edit_message_text("📜 *No coin transactions yet.*", parse_mode="Markdown",
                                          reply_markup=coin_menu_keyboard())
            return
        lines = ["📜 *Coin History (last 5)*\n"]
        for t in txns[:5]:
            sign = "+" if t.amount > 0 else ""
            lines.append(f"• {sign}{t.amount} 🪙 — {t.tx_type} — {t.created_at.strftime('%Y-%m-%d %H:%M')}")
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=coin_menu_keyboard())
        return
    await query.edit_message_text("🪙 *Add Coins To User*\n\nSend the user's Telegram ID:",
                                  parse_mode="Markdown", reply_markup=coin_menu_keyboard())
    context.user_data["coin_flow"] = "single"


async def coin_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    if context.user_data.get("coin_flow") != "single":
        return None
    text = (update.effective_message.text or "").strip()
    if not text.isdigit():
        await update.effective_message.reply_text("❌ Invalid Telegram ID. Send a numeric ID or /cancel.", parse_mode="Markdown")
        return STATE_AWAIT_COIN_USER
    context.user_data["coin_target_id"] = int(text)
    context.user_data["coin_flow"] = "amount"
    await update.effective_message.reply_text(f"🪙 Target user: `{text}`\n\nSend the amount of coins to add:", parse_mode="Markdown")
    return STATE_AWAIT_COIN_AMOUNT


async def coin_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    if context.user_data.get("coin_flow") != "amount":
        return None
    text = (update.effective_message.text or "").strip()
    if not text.isdigit():
        await update.effective_message.reply_text("❌ Invalid amount. Send a number or /cancel.", parse_mode="Markdown")
        return STATE_AWAIT_COIN_AMOUNT
    amount = int(text)
    target_id = context.user_data.get("coin_target_id")
    result = coin_service.add_to_user(target_id, amount, admin_id=update.effective_user.id)
    if not result.get("ok"):
        await update.effective_message.reply_text(f"❌ {result.get('error')}", parse_mode="Markdown",
                                                  reply_markup=admin_panel_keyboard())
    else:
        await update.effective_message.reply_text(f"✅ *{amount} 🪙 coins added!*\nUser: `{target_id}`\nNew balance: *{result['balance']} 🪙*",
                                                  parse_mode="Markdown", reply_markup=admin_panel_keyboard())
    context.user_data.pop("coin_flow", None)
    context.user_data.pop("coin_target_id", None)
    return -1


async def coin_all_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    if len(parts) >= 3 and parts[1] == "amount":
        amount = int(parts[2])
        context.user_data["coin_all_amount"] = amount
        repo = UserRepository(get_engine())
        total_users = repo.count_users()
        await query.edit_message_text(
            f"💰 *Confirm Distribution*\n\nAdd *{amount} 🪙* to ALL eligible users?\n👥 Eligible users: ~{total_users}\n\n"
            "This action is logged and cannot be undone.", parse_mode="Markdown",
            reply_markup=coin_all_confirm_keyboard(amount))
        return STATE_AWAIT_COIN_ALL_CONFIRM
    if parts[1] == "cancel":
        context.user_data.pop("coin_all_amount", None)
        await query.edit_message_text("❌ Distribution cancelled.", parse_mode="Markdown", reply_markup=admin_panel_keyboard())
        return -1
    await query.edit_message_text("💰 *Add Coins To All Users*\n\nSend the amount of coins to give every eligible user:",
                                  parse_mode="Markdown", reply_markup=coin_menu_keyboard())
    context.user_data["coin_flow"] = "all_amount"


async def coin_all_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    if context.user_data.get("coin_flow") != "all_amount":
        return None
    text = (update.effective_message.text or "").strip()
    if not text.isdigit():
        await update.effective_message.reply_text("❌ Invalid amount. Send a number or /cancel.", parse_mode="Markdown")
        return STATE_AWAIT_COIN_AMOUNT
    amount = int(text)
    context.user_data.pop("coin_flow", None)
    context.user_data["coin_all_amount"] = amount
    await update.effective_message.reply_text(
        f"💰 *Confirm Distribution*\n\nAdd *{amount} 🪙* to ALL eligible users?\n\nThis action is logged and cannot be undone.",
        parse_mode="Markdown", reply_markup=coin_all_confirm_keyboard(amount))
    return STATE_AWAIT_COIN_ALL_CONFIRM


async def coin_all_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    if user.id not in config.ADMIN_IDS:
        await query.edit_message_text("⛔ Unauthorized.", parse_mode="Markdown")
        return
    parts = query.data.split(":")
    action = parts[1]
    if action != "confirm":
        context.user_data.pop("coin_all_amount", None)
        await query.edit_message_text("❌ Distribution cancelled.", parse_mode="Markdown", reply_markup=admin_panel_keyboard())
        return
    amount = context.user_data.get("coin_all_amount") or int(parts[2])
    result = coin_service.add_to_all(amount, admin_id=user.id)
    context.user_data.pop("coin_all_amount", None)
    if not result.get("ok"):
        await query.edit_message_text(f"❌ {result.get('error')}", parse_mode="Markdown", reply_markup=admin_panel_keyboard())
        return
    await query.edit_message_text(
        f"✅ *Distribution complete!*\n\n💰 {amount} 🪙 added to *{result['updated']}* users.\nEvery transaction was logged.",
        parse_mode="Markdown", reply_markup=admin_panel_keyboard())


@admin_only
async def referral_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    action = query.data.split(":", 1)[1]
    if action == "reward":
        await query.edit_message_text(f"🎁 *Referral Reward*\n\nCurrent reward: *{referral_service.reward} 🪙*\n\nSend the new reward amount:",
                                      parse_mode="Markdown", reply_markup=referral_menu_keyboard())
        context.user_data["referral_flow"] = "reward"
        return
    if action == "min":
        await query.edit_message_text(f"👥 *Minimum Requirement*\n\nCurrent minimum: *{referral_service.min_usage}*\n\nSend the new minimum referrals for reward:",
                                      parse_mode="Markdown", reply_markup=referral_menu_keyboard())
        context.user_data["referral_flow"] = "min"
        return
    if action == "toggle":
        new_state = not referral_service.enabled
        referral_service.set_enabled(new_state)
        await query.edit_message_text(f"🔄 *Referral System {'ENABLED ✅' if new_state else 'DISABLED ❌'}*",
                                      parse_mode="Markdown", reply_markup=referral_menu_keyboard())


async def referral_setting_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    flow = context.user_data.get("referral_flow")
    if flow not in ("reward", "min"):
        return None
    text = (update.effective_message.text or "").strip()
    if not text.isdigit():
        await update.effective_message.reply_text("❌ Invalid number. Try again or /cancel.", parse_mode="Markdown")
        return STATE_AWAIT_REFERRAL_AMOUNT
    value = int(text)
    if flow == "reward":
        referral_service.set_reward(value)
        await update.effective_message.reply_text(f"✅ Referral reward set to *{value} 🪙*.", parse_mode="Markdown",
                                                  reply_markup=referral_menu_keyboard())
    else:
        referral_service.set_min_usage(value)
        await update.effective_message.reply_text(f"✅ Minimum requirement set to *{value}*.", parse_mode="Markdown",
                                                  reply_markup=referral_menu_keyboard())
    context.user_data.pop("referral_flow", None)
    return -1


@admin_only
async def force_group_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    action = query.data.split(":", 1)[1]
    cfg = force_group_service.get_config()
    if action == "add":
        await query.edit_message_text("👥 *Add Required Group/Channel*\n\nSend the group/channel *username* (e.g. `@mygroup`) or ID:",
                                      parse_mode="Markdown", reply_markup=force_group_menu_keyboard())
        context.user_data["force_group_flow"] = "add"
        return
    if action == "toggle":
        new_state = not force_group_service.is_enabled()
        force_group_service.set_enabled(new_state, updated_by=update.effective_user.id)
        await query.edit_message_text(f"🔄 *Force Join {'ENABLED ✅' if new_state else 'DISABLED ❌'}*",
                                      parse_mode="Markdown", reply_markup=force_group_menu_keyboard())
        return
    if action == "remove":
        force_group_service.remove()
        await query.edit_message_text("🗑 Force-join requirement removed.", parse_mode="Markdown",
                                      reply_markup=force_group_menu_keyboard())
        return
    if action == "check":
        user = update.effective_user
        member = await force_group_service.is_member(context.bot, user.id)
        await query.edit_message_text(f"🔍 *Membership check:*\n{'✅ You are a member.' if member else '❌ Not a member.'}",
                                      parse_mode="Markdown", reply_markup=force_group_menu_keyboard())
        return
    status = "✅ Enabled" if cfg and cfg.enabled else "❌ Disabled"
    target = cfg.chat_username or cfg.chat_id if cfg else "—"
    await query.edit_message_text(f"👥 *Force Group*\n\nStatus: {status}\nTarget: {target}\nTitle: {cfg.chat_title or '—' if cfg else '—'}",
                                  parse_mode="Markdown", reply_markup=force_group_menu_keyboard())


async def force_group_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    if context.user_data.get("force_group_flow") != "add":
        return None
    text = (update.effective_message.text or "").strip().lstrip("@")
    if not text:
        await update.effective_message.reply_text("❌ Invalid target. Send a username or ID.", parse_mode="Markdown")
        return STATE_AWAIT_FORCE_GROUP_ID
    chat_id = None
    if text.isdigit():
        chat_id = int(text)
        target_username = None
    else:
        target_username = text
    title = None
    try:
        chat = await context.bot.get_chat(chat_id=chat_id or target_username)
        title = chat.title or chat.username
        if chat_id is None:
            chat_id = chat.id
    except Exception:
        pass
    force_group_service.configure(chat_id=chat_id, chat_username=target_username, chat_title=title,
                                  enabled=True, updated_by=update.effective_user.id)
    context.user_data.pop("force_group_flow", None)
    await update.effective_message.reply_text(f"✅ *Force group configured!*\nTarget: `{target_username or chat_id}`\nTitle: {title or '—'}\nStatus: ✅ Enabled",
                                              parse_mode="Markdown", reply_markup=force_group_menu_keyboard())
    return -1


@admin_only
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _show_stats(update.effective_message)


async def _show_stats(message) -> None:
    admin_repo = AdminRepository(get_engine())
    case_repo = CaseRepository(get_engine())
    ev_repo = EvidenceRepository(get_engine())
    audit_repo = AuditRepository(get_engine())
    notif_repo = NotificationRepository(get_engine())
    session_repo = SessionRepository(get_engine())
    user_repo = UserRepository(get_engine())
    total_admins = admin_repo.count_admins()
    active_admins = admin_repo.count_active()
    total_cases = case_repo.count_cases()
    status_counts = case_repo.count_by_status()
    ev_count = ev_repo.count_all()
    audit_count = audit_repo.count_all()
    sessions = session_repo.count_active()
    db_size = os.path.getsize(config.DATABASE_PATH) if os.path.isfile(config.DATABASE_PATH) else 0
    total_users = user_repo.count_users()
    active_users = user_repo.count_active()
    total_referrals = user_repo.count_referrals()
    coins_distributed = coin_service.total_distributed()
    banned_users = user_repo.count_banned()
    status_line = " | ".join(f"{k}: {v}" for k, v in status_counts.items()) or "—"
    text = ("📊 *『𝑮𝑷』 STATISTICS*\n━━━━━━━━━━━━━━━━━━\n"
            f"👥 Total Users: {total_users}\n🟢 Active Users: {active_users}\n"
            f"🎁 Total Referrals: {total_referrals}\n🪙 Coins Distributed: {coins_distributed}\n"
            f"📋 Total Cases: {total_cases}\n⏳ Pending Cases: {status_counts.get('PENDING', 0)}\n"
            f"🚫 Banned Cases: {status_counts.get('BANNED', 0)}\n👑 Total Admins: {total_admins} ({active_admins} active)\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🚫 Banned Users: {banned_users}\n🧾 Evidence items: {ev_count}\n📜 Audit entries: {audit_count}\n"
            f"🔑 Active sessions: {sessions}\n⏱ Uptime: {format_uptime(time.monotonic() - _START_TIME)}\n"
            f"💾 DB size: {db_size / 1024:.1f} KB\n📦 Version: {config.BOT_VERSION}")
    await message.reply_text(text, parse_mode="Markdown", reply_markup=admin_panel_keyboard())


@admin_only
async def admins_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _render_admins(update.effective_message, page=1)


@owner_only
async def manage_admins_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    action = query.data.split(":", 1)[1]
    if action == "list":
        await _render_admins(query.message, page=1, edit=True)
    elif action == "add":
        await query.edit_message_text("👑 *Add Admin*\n\nSend the Telegram ID of the new admin:",
                                      parse_mode="Markdown", reply_markup=manage_admins_keyboard())
        context.user_data["add_admin_flow"] = True
    elif action == "remove":
        await query.edit_message_text("👑 *Remove Admin*\n\nSend the Telegram ID of the admin to remove (the OWNER cannot be removed):",
                                      parse_mode="Markdown", reply_markup=manage_admins_keyboard())
        context.user_data["remove_admin_flow"] = True


async def add_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get("add_admin_flow"):
        return
    text = (update.effective_message.text or "").strip()
    context.user_data.pop("add_admin_flow", None)
    if not text.isdigit():
        await update.effective_message.reply_text("❌ Invalid ID. Use /admin to retry.", parse_mode="Markdown")
        return
    new_id = int(text)
    if new_id == config.OWNER_TELEGRAM_ID:
        await update.effective_message.reply_text("👑 The owner is already an admin.", parse_mode="Markdown")
        return
    repo = AdminRepository(get_engine())
    existing = repo.get_by_telegram_id(new_id)
    if existing:
        repo.set_active(existing, True)
        await update.effective_message.reply_text(f"✅ Admin {new_id} reactivated.", parse_mode="Markdown")
    else:
        repo.get_or_create(new_id, None)
        audit_service.log(update.effective_user.id, ADMIN_CREATED, details={"target": new_id})
        await update.effective_message.reply_text(f"✅ Admin {new_id} added.", parse_mode="Markdown")
    await update.effective_message.reply_text("👥 Use /admins to view all admins.", parse_mode="Markdown",
                                              reply_markup=manage_admins_keyboard())


async def remove_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get("remove_admin_flow"):
        return
    text = (update.effective_message.text or "").strip()
    context.user_data.pop("remove_admin_flow", None)
    if not text.isdigit():
        await update.effective_message.reply_text("❌ Invalid ID. Use /admin to retry.", parse_mode="Markdown")
        return
    target_id = int(text)
    if target_id == config.OWNER_TELEGRAM_ID:
        await update.effective_message.reply_text("⛔ *The OWNER cannot be removed.*", parse_mode="Markdown")
        return
    repo = AdminRepository(get_engine())
    admin = repo.get_by_telegram_id(target_id)
    if admin is None:
        await update.effective_message.reply_text("❌ Admin not found.", parse_mode="Markdown")
        return
    repo.set_active(admin, False)
    audit_service.log(update.effective_user.id, ADMIN_DEACTIVATED, details={"target": target_id})
    await update.effective_message.reply_text(f"✅ Admin {target_id} deactivated.", parse_mode="Markdown",
                                              reply_markup=manage_admins_keyboard())


async def admins_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[1])
    await _render_admins(query.message, page=page, edit=True)


async def _render_admins(message, page: int = 1, edit: bool = False) -> None:
    repo = AdminRepository(get_engine())
    admins, total = repo.list_admins(page=page, per_page=ADMIN_PAGE_SIZE)
    total_pages = max(1, (total + ADMIN_PAGE_SIZE - 1) // ADMIN_PAGE_SIZE)
    lines = [f"👥 *All Admins* — page {page}/{total_pages} ({total} total)\n"]
    for a in admins:
        lines.append(format_admin_summary(a))
        lines.append("")
    text = "\n".join(lines)
    markup = pagination_keyboard("admins_page", page, total_pages)
    if edit:
        await message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    if user.id not in config.ADMIN_IDS:
        await query.edit_message_text("⛔ Unauthorized.", parse_mode="Markdown")
        return
    action = query.data.split(":", 1)[1]
    if action == "users":
        await _render_users(query.message, page=1, edit=True)
    elif action == "banned":
        await _render_users(query.message, page=1, banned_only=True, edit=True)
    elif action == "pending":
        await _render_pending(query.message, page=1, edit=True)
    elif action == "search":
        await search_user_callback(update, context)
    elif action == "coin":
        await coin_menu_callback(update, context)
    elif action == "coin_all":
        await coin_all_callback(update, context)
    elif action == "referral":
        await query.edit_message_text(f"🎁 *Referral System*\n\nReward: *{referral_service.reward} 🪙*\nMin requirement: *{referral_service.min_usage}*\nStatus: *{'ON ✅' if referral_service.enabled else 'OFF ❌'}*",
                                      parse_mode="Markdown", reply_markup=referral_menu_keyboard())
    elif action == "broadcast":
        from handlers.broadcast import broadcast_command
        await broadcast_command(update, context)
    elif action == "force_group":
        await force_group_menu_callback(update, context)
    elif action == "stats":
        await _show_stats(query.message)
    elif action == "settings":
        from handlers.settings import settings_command
        await settings_command(update, context)
    elif action == "admins":
        await query.edit_message_text("👑 *Manage Admins*", parse_mode="Markdown", reply_markup=manage_admins_keyboard())
    elif action == "menu":
        await query.edit_message_text("👑 *『𝑮𝑷』 ADMIN PANEL*\n\nSelect an option:", parse_mode="Markdown",
                                      reply_markup=admin_panel_keyboard())

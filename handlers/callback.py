import logging

from telegram import Update
from telegram.ext import ContextTypes

import config
from database.connection import get_engine
from database.repositories.user_repo import UserRepository
from keyboards.inline import main_menu_keyboard, force_group_menu_keyboard
from services.force_group_service import force_group_service
from services.referral_service import referral_service
from services.coin_service import coin_service

logger = logging.getLogger(__name__)


async def main_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    action = query.data.split(":", 1)[1]
    if action == "ban":
        from .ban_request import ban_request_command
        await ban_request_command(update, context)
    elif action == "cases":
        from .cases import cases_command
        await cases_command(update, context)
    elif action == "profile":
        await _show_profile(update, context, query)
    elif action == "coins":
        await _show_coins(update, context, query)
    elif action == "referral":
        await _show_referral(update, context, query)
    elif action == "force_group":
        await _show_force_group(update, context, query)
    elif action == "help":
        await _show_help(query)
    elif action == "admin":
        if query.from_user.id not in config.ADMIN_IDS:
            await query.edit_message_text("⛔ Unauthorized Access", parse_mode="Markdown")
            return
        from .admin import admin_command
        await admin_command(update, context)
    elif action in ("menu", "cancel"):
        await query.edit_message_text("*Main Menu*", parse_mode="Markdown", reply_markup=main_menu_keyboard())


async def _show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, query) -> None:
    user = update.effective_user
    repo = UserRepository(get_engine())
    profile = repo.get_or_create(user.id, user.username, user.first_name)
    from utils.formatters import format_user_summary
    await query.edit_message_text(format_user_summary(profile), parse_mode="Markdown", reply_markup=main_menu_keyboard())


async def _show_coins(update: Update, context: ContextTypes.DEFAULT_TYPE, query) -> None:
    user = update.effective_user
    repo = UserRepository(get_engine())
    profile = repo.get_or_create(user.id, user.username, user.first_name)
    txns, total = coin_service.history(user.id, page=1, per_page=5)
    lines = [f"🪙 *MY COINS*\n━━━━━━━━━━━━━━━━━━\nBalance: *{profile.coins} 🪙*\n"]
    if txns:
        lines.append("\n*Recent transactions:*")
        for t in txns[:5]:
            sign = "+" if t.amount > 0 else ""
            lines.append(f"• {sign}{t.amount} 🪙 — {t.tx_type}")
    else:
        lines.append("\nNo transactions yet.")
    await query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=main_menu_keyboard())


async def _show_referral(update: Update, context: ContextTypes.DEFAULT_TYPE, query) -> None:
    user = update.effective_user
    repo = UserRepository(get_engine())
    profile = repo.get_or_create(user.id, user.username, user.first_name)
    link = referral_service.my_link(user.id)
    count = referral_service.count(user.id)
    enabled = "ON ✅" if referral_service.enabled else "OFF ❌"
    await query.edit_message_text(
        f"🎁 *REFERRAL SYSTEM*\n━━━━━━━━━━━━━━━━━━\nStatus: {enabled}\nReward: *{referral_service.reward} 🪙* per referral\n"
        f"Your referrals: *{count}*\n\n🔗 *Your referral link:*\n`{link}`\n\nShare this link — when a new user joins, you earn coins!",
        parse_mode="Markdown", reply_markup=main_menu_keyboard())


async def _show_force_group(update: Update, context: ContextTypes.DEFAULT_TYPE, query) -> None:
    cfg = force_group_service.get_config()
    if not cfg or not cfg.enabled:
        await query.edit_message_text("👥 *REQUIRED GROUP*\n\nNo required group is configured. You have full access to the bot.",
                                      parse_mode="Markdown", reply_markup=main_menu_keyboard())
        return
    text, markup = force_group_service.gate_message()
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=markup)


async def _show_help(query) -> None:
    await query.edit_message_text(
        "ℹ️ *HELP — 『𝑮𝑷』 𝑮𝑯𝑶𝑺𝑻 𝑷𝑹𝑶𝑻𝑶𝑪𝑶𝑳 BOT*\n━━━━━━━━━━━━━━━━━━\n"
        "🚫 *BAN REQUEST* — submit a suspicious account/group/channel/link for moderation review. "
        "Collects target, category, description, evidence and screenshot.\n\n"
        "👤 *MY PROFILE* — view your user profile.\n🪙 *MY COINS* — check your coin balance & history.\n"
        "🎁 *REFERRAL* — get your unique referral link.\n📋 *MY CASES* — track your submitted ban requests.\n"
        "👥 *REQUIRED GROUP* — join the required group to keep using the bot.\n\n"
        "*How moderation works:*\n1. You submit a BAN REQUEST with evidence\n2. Case ID assigned (e.g. `GP-000124`) — status ⏳ PENDING\n"
        "3. Authorized admins review evidence\n4. Decision: 🚫 BAN / ↩️ REJECT / ⏳ PENDING / ✅ REVIEWED\n\n"
        "This bot records moderation decisions internally. It does NOT mass-report or abuse Telegram's reporting system.",
        parse_mode="Markdown", reply_markup=main_menu_keyboard())


async def force_group_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    member = await force_group_service.is_member(context.bot, user.id)
    if member:
        from keyboards.reply import user_keyboard
        await query.edit_message_text("✅ *Membership verified!*\n\nWelcome to 『𝑮𝑷』 𝑮𝑯𝑶𝑺𝑻 𝑷𝑹𝑶𝑻𝑶𝑪𝑶𝑳 BOT. Use the buttons below 👇",
                                      parse_mode="Markdown", reply_markup=user_keyboard())
    else:
        text, markup = force_group_service.gate_message()
        await query.edit_message_text("❌ You haven't joined yet.\n\n" + text, parse_mode="Markdown", reply_markup=markup)


async def generic_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer("Unknown action", show_alert=False)

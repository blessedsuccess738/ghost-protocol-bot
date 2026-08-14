import logging

from telegram import Update
from telegram.ext import ContextTypes

import config
from database.connection import get_engine
from database.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)


async def reply_keyboard_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None or not message.text:
        return
    text = message.text.strip()
    if context.user_data.get("coin_flow") in ("single", "amount", "all_amount"):
        return
    if context.user_data.get("referral_flow"):
        return
    if context.user_data.get("force_group_flow"):
        return
    if context.user_data.get("add_admin_flow") or context.user_data.get("remove_admin_flow"):
        return
    if context.user_data.get("awaiting_user_search"):
        from handlers.admin import user_search_input
        await user_search_input(update, context)
        return

    if text == "🚫 BAN REQUEST":
        from handlers.ban_request import ban_request_command
        await ban_request_command(update, context)
        return
    if text == "👤 MY PROFILE":
        repo = UserRepository(get_engine())
        profile = repo.get_or_create(update.effective_user.id, update.effective_user.username, update.effective_user.first_name)
        from utils.formatters import format_user_summary
        from keyboards.reply import user_keyboard
        await message.reply_text(format_user_summary(profile), parse_mode="Markdown", reply_markup=user_keyboard())
        return
    if text == "🪙 MY COINS":
        from services.coin_service import coin_service
        repo = UserRepository(get_engine())
        profile = repo.get_or_create(update.effective_user.id, update.effective_user.username, update.effective_user.first_name)
        txns, total = coin_service.history(update.effective_user.id, page=1, per_page=5)
        lines = [f"🪙 *MY COINS*\n━━━━━━━━━━━━━━━━━━\nBalance: *{profile.coins} 🪙*\n"]
        if txns:
            lines.append("\n*Recent transactions:*")
            for t in txns[:5]:
                sign = "+" if t.amount > 0 else ""
                lines.append(f"• {sign}{t.amount} 🪙 — {t.tx_type}")
        else:
            lines.append("\nNo transactions yet.")
        from keyboards.reply import user_keyboard as _uk
        await message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=_uk())
        return
    if text == "🎁 REFERRAL":
        from services.referral_service import referral_service
        link = referral_service.my_link(update.effective_user.id)
        count = referral_service.count(update.effective_user.id)
        enabled = "ON ✅" if referral_service.enabled else "OFF ❌"
        from keyboards.reply import user_keyboard as _uk2
        await message.reply_text(
            f"🎁 *REFERRAL SYSTEM*\n━━━━━━━━━━━━━━━━━━\nStatus: {enabled}\nReward: *{referral_service.reward} 🪙* per referral\n"
            f"Your referrals: *{count}*\n\n🔗 *Your referral link:*\n`{link}`",
            parse_mode="Markdown", reply_markup=_uk2())
        return
    if text == "📋 MY CASES":
        from handlers.cases import cases_command
        await cases_command(update, context)
        return
    if text == "👥 REQUIRED GROUP":
        from services.force_group_service import force_group_service
        cfg = force_group_service.get_config()
        if not cfg or not cfg.enabled:
            from keyboards.reply import user_keyboard as _uk3
            await message.reply_text("👥 *REQUIRED GROUP*\n\nNo required group is configured. You have full access to the bot.",
                                     parse_mode="Markdown", reply_markup=_uk3())
            return
        text2, markup = force_group_service.gate_message()
        await message.reply_text(text2, parse_mode="Markdown", reply_markup=markup)
        return
    if text == "ℹ️ HELP":
        from handlers.callback import _show_help
        class _Q:
            async def edit_message_text(self, *a, **k):
                await message.reply_text(*a, **k)
        await _show_help(_Q())
        return

    if update.effective_user.id in config.ADMIN_IDS:
        if text == "👑 ADMIN PANEL":
            from handlers.admin import admin_command
            await admin_command(update, context)
            return
        if text == "👥 USERS":
            from handlers.admin import users_command
            await users_command(update, context)
            return
        if text == "📋 CASES":
            from handlers.cases import cases_command
            await cases_command(update, context)
            return
        if text == "🚫 BANNED":
            from handlers.admin import banned_command
            await banned_command(update, context)
            return
        if text == "🪙 ADD COINS":
            from keyboards.reply import admin_keyboard
            await message.reply_text("🪙 *Add Coins To User*\n\nSend the user's Telegram ID:",
                                      parse_mode="Markdown", reply_markup=admin_keyboard())
            context.user_data["coin_flow"] = "single"
            return
        if text == "💰 COINS FOR ALL":
            from keyboards.reply import admin_keyboard as _ak
            await message.reply_text("💰 *Add Coins To All Users*\n\nSend the amount of coins to give every eligible user:",
                                      parse_mode="Markdown", reply_markup=_ak())
            context.user_data["coin_flow"] = "all_amount"
            return
        if text == "🎁 REFERRALS":
            from keyboards.inline import referral_menu_keyboard
            await message.reply_text(
                f"🎁 *Referral System*\n\nReward: *{referral_service.reward} 🪙*\nMin requirement: *{referral_service.min_usage}*\nStatus: *{'ON ✅' if referral_service.enabled else 'OFF ❌'}*",
                parse_mode="Markdown", reply_markup=referral_menu_keyboard())
            return
        if text == "👥 FORCE GROUP":
            from keyboards.inline import force_group_menu_keyboard
            cfg = force_group_service.get_config()
            status = "✅ Enabled" if cfg and cfg.enabled else "❌ Disabled"
            target = cfg.chat_username or cfg.chat_id if cfg else "—"
            await message.reply_text(f"👥 *Force Group*\n\nStatus: {status}\nTarget: {target}",
                                     parse_mode="Markdown", reply_markup=force_group_menu_keyboard())
            return
        if text == "📢 BROADCAST":
            from handlers.broadcast import broadcast_command
            await broadcast_command(update, context)
            return
        if text == "📊 STATISTICS":
            from handlers.admin import stats_command
            await stats_command(update, context)
            return
        if text == "👑 ADMINS":
            from keyboards.inline import manage_admins_keyboard
            await message.reply_text("👑 *Manage Admins*\n\nUse /admins to view all admins.\n➕ Send the Telegram ID to add an admin.\n🚫 Send the Telegram ID to remove an admin (OWNER protected).",
                                     parse_mode="Markdown", reply_markup=manage_admins_keyboard())
            return
        if text == "⚙️ SETTINGS":
            from handlers.settings import settings_command
            await settings_command(update, context)
            return


async def search_user_input_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get("awaiting_user_search"):
        return
    from handlers.admin import user_search_input
    await user_search_input(update, context)

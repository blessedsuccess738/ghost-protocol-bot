import logging

from telegram import Update
from telegram.ext import ContextTypes

import config
from core.constants import (STATE_AWAIT_EMAIL, STATE_AWAIT_VERIFICATION_TOKEN, AUTH_LOGIN,
                            AUTH_VERIFY_EMAIL_SENT, AUTH_VERIFY_EMAIL, AUTH_LOGIN_FAIL, AUTH_LOCKED, USER_REGISTERED)
from database.connection import get_engine
from database.repositories.admin_repo import AdminRepository
from database.repositories.user_repo import UserRepository
from keyboards.inline import main_menu_keyboard
from keyboards.reply import user_keyboard, admin_keyboard
from services.audit_service import audit_service
from services.email_service import email_service
from services.force_group_service import force_group_service
from services.referral_service import referral_service
from utils.decorators import rate_limited
from utils.validators import is_valid_email, is_valid_verification_token

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    user = update.effective_user
    if user is None:
        return None
    await update.effective_message.reply_chat_action("typing")

    args = context.args or []
    referral_code = args[0] if args else None

    user_repo = UserRepository(get_engine())
    profile = user_repo.get_or_create(user.id, user.username, user.first_name)

    if referral_code:
        result = referral_service.register_with_code(profile.id, referral_code)
        if result.get("ok") and result.get("reward"):
            await update.effective_message.reply_text(
                f"🎁 *Referral reward claimed!* +{result['reward']} 🪙 coins", parse_mode="Markdown")
    audit_service.log(user.id, USER_REGISTERED, details={"new": True})

    if force_group_service.is_enabled():
        if not await force_group_service.is_member(context.bot, user.id):
            text, markup = force_group_service.gate_message()
            await update.effective_message.reply_text(text, parse_mode="Markdown", reply_markup=markup)
            return None

    if user.id in config.ADMIN_IDS:
        return await _admin_start(update, context)
    return await _user_start(update, context)


async def _user_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    user = update.effective_user
    name = user.full_name or "User"
    await update.effective_message.reply_text(
        f"👋 *Welcome to 『𝑮𝑷』 𝑮𝑯𝑶𝑺𝑻 𝑷𝑹𝑶𝑻𝑶𝑪𝑶𝑳 BOT, {name}!*\n\n"
        "This bot is a scam-monitoring & moderation system.\n"
        "You can submit a *🚫 BAN REQUEST* against suspicious accounts, groups, channels or links. "
        "Our moderation team reviews every case.\n\n"
        "Use the buttons below 👇",
        parse_mode="Markdown", reply_markup=user_keyboard())
    return None


async def _admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    user = update.effective_user
    await update.effective_message.reply_chat_action("typing")
    repo = AdminRepository(get_engine())
    admin = repo.get_or_create(user.id, user.username)
    if repo.is_locked(admin):
        await update.effective_message.reply_text(
            "🔒 *Account Locked*\n\nToo many failed verification attempts. Please try again in 30 minutes.",
            parse_mode="Markdown")
        audit_service.log(user.id, AUTH_LOCKED)
        return None
    if admin.email_verified and admin.email:
        await show_admin_menu(update, admin.email)
        audit_service.log(user.id, AUTH_LOGIN)
        return None
    await update.effective_message.reply_text(
        "🔐 *Admin Verification Required*\n\nWelcome! Before you can access the admin panel, "
        "please provide your admin email address.\n\nSend your email address, or /cancel to abort.",
        parse_mode="Markdown")
    return STATE_AWAIT_EMAIL


async def email_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    user = update.effective_user
    text = (update.effective_message.text or "").strip()
    if not is_valid_email(text):
        await update.effective_message.reply_text(
            "❌ *Invalid email format.*\nPlease send a valid email address like `admin@example.com`\nor /cancel to abort.",
            parse_mode="Markdown")
        return STATE_AWAIT_EMAIL
    repo = AdminRepository(get_engine())
    admin = repo.get_by_telegram_id(user.id) or repo.get_or_create(user.id, user.username)
    other = repo.get_by_email(text)
    if other and other.id != admin.id:
        await update.effective_message.reply_text(
            "❌ This email is already registered to another admin.\nSend a different email or /cancel.",
            parse_mode="Markdown")
        return STATE_AWAIT_EMAIL
    token = repo.start_email_verification(admin, text)
    sent = email_service.send_verification(text, token, config.EMAIL_VERIFICATION_HOURS)
    if not sent:
        await update.effective_message.reply_text(
            "⚠️ *Could not send the verification email.*\n\nSMTP is not configured on this server, or the email service is down.\n\n"
            "📩 *Your verification token (simulated email):*\n`" + token + "`\n\nEnter the token below, or /resend for a new one.\n"
            f"⏳ Expires in {config.EMAIL_VERIFICATION_HOURS} hours.", parse_mode="Markdown")
    else:
        await update.effective_message.reply_text(
            f"📧 *Verification email sent to:* `{text}`\n\nEnter the verification token from the email below.\n"
            f"⏳ Token expires in {config.EMAIL_VERIFICATION_HOURS} hours.\n\nUse /resend to get a new token, or /cancel to abort.",
            parse_mode="Markdown")
    audit_service.log(user.id, AUTH_VERIFY_EMAIL_SENT, details={"email": text})
    return STATE_AWAIT_VERIFICATION_TOKEN


async def verification_token_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    user = update.effective_user
    token = (update.effective_message.text or "").strip()
    if not is_valid_verification_token(token):
        await update.effective_message.reply_text(
            "❌ Invalid token format. Please enter the token exactly as shown in the email.", parse_mode="Markdown")
        return STATE_AWAIT_VERIFICATION_TOKEN
    repo = AdminRepository(get_engine())
    admin = repo.get_by_telegram_id(user.id)
    if admin is None:
        await update.effective_message.reply_text("❌ Please restart with /start.")
        return None
    if repo.is_locked(admin):
        await update.effective_message.reply_text("🔒 Account locked. Try again in 30 minutes.", parse_mode="Markdown")
        return None
    if repo.verify_email_token(admin, token):
        repo.record_login_success(admin)
        audit_service.log(user.id, AUTH_VERIFY_EMAIL, details={"email": admin.email})
        await show_admin_menu(update, admin.email)
        return None
    else:
        locked = repo.record_login_failure(admin)
        if locked:
            await update.effective_message.reply_text("🔒 *Too many failed attempts — account locked for 30 minutes.*", parse_mode="Markdown")
            audit_service.log(user.id, AUTH_LOCKED)
        else:
            await update.effective_message.reply_text(
                "❌ Invalid or expired token. Please try again, use /resend for a new token, or /cancel to abort.",
                parse_mode="Markdown")
        return STATE_AWAIT_VERIFICATION_TOKEN


@rate_limited("verify_email")
async def resend_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id not in config.ADMIN_IDS:
        await update.effective_message.reply_text("⛔ Unauthorized Access", parse_mode="Markdown")
        return
    repo = AdminRepository(get_engine())
    admin = repo.get_by_telegram_id(user.id)
    if admin is None or not admin.email:
        await update.effective_message.reply_text("❌ No pending verification. Use /start to begin.", parse_mode="Markdown")
        return
    token = repo.regenerate_verification_token(admin)
    email_service.send_verification(admin.email, token, config.EMAIL_VERIFICATION_HOURS)
    await update.effective_message.reply_text(
        "📧 *New verification token sent.*\n📩 Token: `" + token + "`\n"
        f"⏳ Expires in {config.EMAIL_VERIFICATION_HOURS} hours.", parse_mode="Markdown")
    audit_service.log(user.id, AUTH_VERIFY_EMAIL_SENT, details={"resend": True})


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text("❌ Cancelled.\n\nUse /start to begin again.", parse_mode="Markdown")
    context.user_data.clear()
    return -1


async def show_admin_menu(update: Update, email: str | None) -> None:
    name = update.effective_user.full_name or "Admin"
    role = "👑 OWNER" if update.effective_user.id == config.OWNER_TELEGRAM_ID else "🛡️ ADMIN"
    await update.effective_message.reply_text(
        f"👋 *Welcome, {name}!*\n🎖 Role: {role}\n✅ Email verified: `{email or '—'}`\n\n"
        "*Admin Panel loaded.* Use the admin keyboard below 👇",
        parse_mode="Markdown", reply_markup=admin_keyboard())

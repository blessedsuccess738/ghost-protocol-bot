"""
core/application.py — Application initialization for 『𝑮𝑷』 𝑮𝑯𝑶𝑺𝑻 𝑷𝑹𝑶𝑻𝑶𝑪𝑶𝑳 BOT.

Sets up the PTB Application (v20.7+), registers handlers, wires services
and registers the top-level error handler.
"""
import logging

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

import config
from utils.logger import setup_logging
from utils.decorators import rate_limited
from .constants import (
    STATE_EDIT_CHOICE,
    STATE_AWAIT_EMAIL,
    STATE_AWAIT_VERIFICATION_TOKEN,
    STATE_TARGET,
    STATE_EVIDENCE_TYPE,
    STATE_EVIDENCE_LINK,
    STATE_EVIDENCE_SCREENSHOT,
    STATE_REASON,
    STATE_DESCRIPTION,
    STATE_REVIEW,
    STATE_AWAIT_BROADCAST,
    STATE_AWAIT_EMAIL_CHANGE,
    STATE_AWAIT_COIN_USER,
    STATE_AWAIT_COIN_AMOUNT,
    STATE_AWAIT_COIN_ALL_CONFIRM,
    STATE_AWAIT_FORCE_GROUP_ID,
    STATE_AWAIT_REFERRAL_AMOUNT,
    STATE_AWAIT_REFERRAL_MIN,
)

logger = logging.getLogger(__name__)


async def global_error_handler(update: object, context) -> None:
    """Top-level error handler — logs full traceback, never crashes the bot."""
    logger.error("Unhandled error while processing an update:", exc_info=context.error)
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ An internal error occurred. Our team has been notified. Please try again."
            )
    except Exception:  # pragma: no cover
        logger.error("Failed to notify user about error", exc_info=True)


def build_application() -> Application:
    """Build and return the configured PTB Application."""
    setup_logging(config.LOG_LEVEL)

    app = (
        ApplicationBuilder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_error_handler(global_error_handler)

    # ── Auth handlers ───────────────────────────────────────────────────────
    from handlers.start import (
        start_command,
        cancel_command,
        resend_command,
        email_input,
        verification_token_input,
    )

    auth_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            STATE_AWAIT_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, email_input)],
            STATE_AWAIT_VERIFICATION_TOKEN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, verification_token_input)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
        name="auth_conversation",
        persistent=False,
        per_message=False,
    )
    app.add_handler(auth_conv)
    app.add_handler(CommandHandler("resend", resend_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("help", _help_command))
    app.add_handler(CommandHandler("start", start_command))

    # ── BAN REQUEST workflow (rebranded report flow) ───────────────────────
    from handlers.ban_request import (
        ban_request_command,
        evidence_type_callback,
        reason_callback,
        review_callback,
        edit_callback,
        target_input,
        evidence_link_input,
        evidence_screenshot_input,
        description_input,
    )

    def _ban_request_states():
        return {
            STATE_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, target_input)],
            STATE_EVIDENCE_TYPE: [CallbackQueryHandler(evidence_type_callback, pattern=r"^evidence:")],
            STATE_EVIDENCE_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, evidence_link_input)],
            STATE_EVIDENCE_SCREENSHOT: [
                MessageHandler(filters.PHOTO, evidence_screenshot_input),
                MessageHandler(filters.TEXT & ~filters.COMMAND, evidence_screenshot_input),
            ],
            STATE_REASON: [CallbackQueryHandler(reason_callback, pattern=r"^reason:")],
            STATE_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description_input)],
            STATE_REVIEW: [CallbackQueryHandler(review_callback, pattern=r"^review:")],
            STATE_EDIT_CHOICE: [CallbackQueryHandler(edit_callback, pattern=r"^edit:")],
        }

    app.add_handler(ConversationHandler(
        entry_points=[
            CommandHandler("ban_request", ban_request_command),
            CommandHandler("report", ban_request_command),  # legacy alias
            CallbackQueryHandler(ban_request_command, pattern=r"^main:ban$"),
        ],
        states=_ban_request_states(),
        fallbacks=[CommandHandler("cancel", cancel_command)],
        name="ban_request_conversation",
        persistent=False,
        per_message=False,
    ))

    # ── Cases (moderation) ──────────────────────────────────────────────────
    from handlers.cases import (
        cases_command,
        case_action_callback,
        cases_page_callback,
        moderation_callback,
    )
    app.add_handler(CommandHandler("cases", cases_command))
    app.add_handler(CommandHandler("mycases", cases_command))
    app.add_handler(CallbackQueryHandler(case_action_callback, pattern=r"^case_action:"))
    app.add_handler(CallbackQueryHandler(cases_page_callback, pattern=r"^cases_page:"))
    app.add_handler(CallbackQueryHandler(moderation_callback, pattern=r"^mod:"))

    # ── Admin panel ─────────────────────────────────────────────────────────
    from handlers.admin import (
        admin_command,
        admins_command,
        stats_command,
        admin_callback,
        admins_page_callback,
        users_command,
        banned_command,
        users_page_callback,
        pending_cases_command,
        pending_page_callback,
        case_review_callback,
        coin_menu_callback,
        coin_all_callback,
        coin_all_confirm_callback,
        referral_menu_callback,
        force_group_menu_callback,
        manage_admins_callback,
        admin_panel_button,
    )
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("admins", admins_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("banned", banned_command))
    app.add_handler(CommandHandler("pending", pending_cases_command))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern=r"^admin:"))
    app.add_handler(CallbackQueryHandler(admins_page_callback, pattern=r"^admins_page:"))
    app.add_handler(CallbackQueryHandler(users_page_callback, pattern=r"^users_page:|^banned_page:"))
    app.add_handler(CallbackQueryHandler(pending_page_callback, pattern=r"^pending_page:"))
    app.add_handler(CallbackQueryHandler(case_review_callback, pattern=r"^case_review:"))
    app.add_handler(CallbackQueryHandler(coin_menu_callback, pattern=r"^coin:add$|^coin:history$"))
    app.add_handler(CallbackQueryHandler(coin_all_callback, pattern=r"^coin_all:"))
    app.add_handler(CallbackQueryHandler(coin_all_confirm_callback, pattern=r"^coin_all:confirm:|^coin_all:cancel$"))
    app.add_handler(CallbackQueryHandler(referral_menu_callback, pattern=r"^referral:"))
    app.add_handler(CallbackQueryHandler(force_group_menu_callback, pattern=r"^force_group:"))
    app.add_handler(CallbackQueryHandler(manage_admins_callback, pattern=r"^admins:"))

    # ── Verify Target tool suite (safe attack tools) ───────────────────────
    from handlers.attack import (
        attack_command,
        verify_command,
        ban_command,
        bug_command,
        status_command,
        stop_command,
        attack_target_input,
        attack_callback,
    )
    app.add_handler(CommandHandler("attack", attack_command))
    app.add_handler(CommandHandler("verify", verify_command))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("bug", bug_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, attack_target_input))
    app.add_handler(CallbackQueryHandler(attack_callback, pattern=r"^attack:"))

    # ── Admin conversation states (coins, referral settings, force group) ──
    from handlers.admin import (
        coin_user_input,
        coin_amount_input,
        coin_all_amount_input,
        referral_setting_input,
        force_group_input,
        add_admin_input,
        remove_admin_input,
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, coin_user_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, coin_amount_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, coin_all_amount_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, referral_setting_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, force_group_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_admin_input))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, remove_admin_input))

    # ── Settings ────────────────────────────────────────────────────────────
    from handlers.settings import settings_command, settings_callback, email_change_input
    settings_conv = ConversationHandler(
        entry_points=[CommandHandler("settings", settings_command)],
        states={
            STATE_AWAIT_EMAIL_CHANGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, email_change_input)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
        name="settings_conversation",
        persistent=False,
        per_message=False,
    )
    app.add_handler(settings_conv)
    app.add_handler(CallbackQueryHandler(settings_callback, pattern=r"^settings:"))

    # ── Export ──────────────────────────────────────────────────────────────
    from handlers.export import export_command, export_callback
    app.add_handler(CommandHandler("export", export_command))
    app.add_handler(CallbackQueryHandler(export_callback, pattern=r"^export:"))

    # ── Broadcast ───────────────────────────────────────────────────────────
    from handlers.broadcast import broadcast_command, broadcast_input
    broadcast_conv = ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast_command)],
        states={
            STATE_AWAIT_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
        name="broadcast_conversation",
        persistent=False,
        per_message=False,
    )
    app.add_handler(broadcast_conv)

    # ── Reply-keyboard buttons (keyboard-first design) ─────────────────────
    from handlers.keyboard_router import (
        reply_keyboard_router,
        search_user_input_router,
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_keyboard_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_user_input_router))

    # ── Callbacks (main menu etc.) ─────────────────────────────────────────
    from handlers.callback import main_callback, generic_callback, force_group_check_callback
    app.add_handler(CallbackQueryHandler(main_callback, pattern=r"^main:"))
    app.add_handler(CallbackQueryHandler(force_group_check_callback, pattern=r"^force_group:check$"))
    app.add_handler(CallbackQueryHandler(generic_callback))

    return app


async def _help_command(update: Update, context) -> None:
    await update.effective_message.reply_text(
        "ℹ️ *HELP — 『𝑮𝑷』 𝑮𝑯𝑶𝑺𝑻 𝑷𝑹𝑶𝑻𝑶𝑪𝑶𝑳 BOT*\n\n"
        "Use the buttons on the keyboard:\n"
        "🚫 BAN REQUEST · 👤 MY PROFILE · 🪙 MY COINS · 🎁 REFERRAL · "
        "📋 MY CASES · 👥 REQUIRED GROUP\n\n"
        "Admins: use 👑 ADMIN PANEL for full moderation controls.",
        parse_mode="Markdown",
    )


async def post_init(application: Application) -> None:
    """Run once after the Application is built — ensure DB schema + seed settings."""
    from database.connection import init_db, get_engine
    init_db()
    logger.info("Database schema ready at %s", config.DATABASE_PATH)

    from database.repositories.settings_repo import SettingsRepository
    repo = SettingsRepository(get_engine())
    repo.ensure_defaults()

    logger.info(
        "%s %s — bot ready. Admins: %s",
        config.BOT_NAME,
        config.BOT_ENTERPRISE,
        config.ADMIN_IDS,
    )


async def post_shutdown(application: Application) -> None:
    """Cleanup on shutdown."""
    from database.connection import dispose_engine
    dispose_engine()
    logger.info("Application shutdown complete")


def main() -> None:
    """Entry point (python -m core.application)."""
    app = build_application()
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

"""utils/decorators.py — access-control and rate-limit decorators for 『𝑮𝑷』 𝑮𝑯𝑶𝑺𝑻 𝑷𝑹𝑶𝑻𝑶𝑪𝑶𝑳 BOT."""
import functools
import logging
from datetime import datetime, timedelta, timezone

import config
from database.connection import get_engine
from database.repositories.admin_repo import AdminRepository
from database.repositories.rate_limit_repo import RateLimitRepository

logger = logging.getLogger(__name__)


def rate_limited(action: str = "default", limit: int | None = None, window: int | None = None):
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            update = args[0]
            user_id = getattr(getattr(update, "effective_user", None), "id", None)
            if user_id is None:
                return await fn(*args, **kwargs)
            if user_id in config.ADMIN_IDS:
                return await fn(*args, **kwargs)
            per = limit or config.RATE_LIMIT_PER_USER
            secs = window or config.RATE_LIMIT_WINDOW
            repo = RateLimitRepository(get_engine())
            count = repo.count_in_window(user_id, action, secs)
            if count >= per:
                if update.effective_message:
                    await update.effective_message.reply_text(
                        "⚠️ *Rate limit reached.* Please wait and try again later.", parse_mode="Markdown")
                return None
            repo.record(user_id, action)
            return await fn(*args, **kwargs)
        return wrapper
    return decorator


def admin_only(fn):
    @functools.wraps(fn)
    async def wrapper(update, context, *args, **kwargs):
        user = getattr(update, "effective_user", None)
        if user is None or user.id not in config.ADMIN_IDS:
            if update.effective_message:
                await update.effective_message.reply_text("⛔ *Unauthorized Access*\n\nThis command is restricted to admins.",
                                                          parse_mode="Markdown")
            return None
        return await fn(update, context, *args, **kwargs)
    return wrapper


def owner_only(fn):
    @functools.wraps(fn)
    async def wrapper(update, context, *args, **kwargs):
        user = getattr(update, "effective_user", None)
        if user is None or user.id != config.OWNER_TELEGRAM_ID:
            if update.effective_message:
                await update.effective_message.reply_text("⛔ *Owner only.*", parse_mode="Markdown")
            return None
        return await fn(update, context, *args, **kwargs)
    return wrapper


def permission_required(permission: str):
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(update, context, *args, **kwargs):
            user = getattr(update, "effective_user", None)
            if user is None:
                return None
            if user.id == config.OWNER_TELEGRAM_ID:
                return await fn(update, context, *args, **kwargs)
            repo = AdminRepository(get_engine())
            admin = repo.get_by_telegram_id(user.id)
            allowed = config.PERMISSIONS.get(admin.role if admin else "", [])
            if permission not in allowed and config.PERMISSION_ALL not in allowed:
                if update.effective_message:
                    await update.effective_message.reply_text("⛔ You do not have permission for this action.", parse_mode="Markdown")
                return None
            return await fn(update, context, *args, **kwargs)
        return wrapper
    return decorator

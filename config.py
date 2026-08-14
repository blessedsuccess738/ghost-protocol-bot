"""
config.py — Centralized configuration for 『𝑮𝑷』 𝑮𝑯𝑶𝑺𝑻 𝑷𝑹𝑶𝑻𝑶𝑪𝑶𝑳 BOT.

All secrets come from environment variables / .env file. Never hardcode credentials.
"""
import os
import json

from dotenv import load_dotenv

load_dotenv()


def _env_bool(key: str, default: bool = False) -> bool:
    val = os.environ.get(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


def _env_list(key: str, default: str = "") -> list:
    raw = os.environ.get(key, default)
    return [x.strip() for x in raw.split(",") if x.strip()]


# ─── Bot ────────────────────────────────────────────────────────────────────
BOT_VERSION = "3.0.0"
BOT_NAME = "『𝑮𝑷』 𝑮𝑯𝑶𝑺𝑻 𝑷𝑹𝑶𝑻𝑶𝑪𝑶𝑳 BOT"
BOT_SHORT = "『𝑮𝑷』"
BOT_ENTERPRISE = "Scam Monitoring & Moderation System"

TELEGRAM_BOT_TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN", "8667793167:AAH69QfCeo95TeTC5fUJfzWWGiyuENzRM14"
)
ADMIN_IDS = [int(x) for x in _env_list("ADMIN_IDS", "7590603733") if x.lstrip("-").isdigit()]
ADMIN_EMAILS = _env_list("ADMIN_EMAILS", "admin@example.com")

# ─── Roles ──────────────────────────────────────────────────────────────────
ROLE_OWNER = "OWNER"
ROLE_ADMIN = "ADMIN"

# The owner can NEVER be demoted / removed by another admin.
OWNER_TELEGRAM_ID = _env_int("OWNER_TELEGRAM_ID", 7590603733)

PERMISSION_ALL = "*"
PERMISSIONS = {
    ROLE_OWNER: [PERMISSION_ALL],
    ROLE_ADMIN: [
        "user.view", "case.view", "case.review", "case.ban", "coin.add",
        "stats.view", "broadcast.send", "force_group.view",
    ],
}

# ─── Authentication ─────────────────────────────────────────────────────────
ADMIN_VERIFICATION_REQUIRED = _env_bool("ADMIN_VERIFICATION_REQUIRED", True)
ADMIN_EMAIL_VERIFICATION = _env_bool("ADMIN_EMAIL_VERIFICATION", True)
MAX_ADMINS = _env_int("MAX_ADMINS", 100)
SESSION_TIMEOUT = _env_int("SESSION_TIMEOUT", 3600)
EMAIL_VERIFICATION_HOURS = 24
LOGIN_MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 30

# ─── Security ───────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-jwt-change-me")
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "dev-encryption-key-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY = SESSION_TIMEOUT

# ─── Rate limiting ──────────────────────────────────────────────────────────
RATE_LIMIT_PER_USER = _env_int("RATE_LIMIT_PER_USER", 100)      # per hour
RATE_LIMIT_PER_MINUTE = _env_int("RATE_LIMIT_PER_MINUTE", 60)   # per minute
RATE_LIMIT_WINDOW = _env_int("RATE_LIMIT_WINDOW", 60)           # sliding window seconds
RATE_LIMIT_LOGIN = 5            # login attempts / hour
RATE_LIMIT_UPLOADS = 10         # file uploads / hour
RATE_LIMIT_REPORTS = 20         # ban-request creations / day
RATE_LIMIT_VERIFY_EMAIL = 3     # verification emails / hour

# ─── Notifications ──────────────────────────────────────────────────────────
NOTIFICATION_ENABLED = _env_bool("NOTIFICATION_ENABLED", True)
NOTIFICATION_EMAIL_ENABLED = _env_bool("NOTIFICATION_EMAIL_ENABLED", True)
NOTIFICATION_TELEGRAM_ENABLED = _env_bool("NOTIFICATION_TELEGRAM_ENABLED", True)

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = _env_int("SMTP_PORT", 587)
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "noreply@ghostprotocolbot.com")

# ─── Database / storage ─────────────────────────────────────────────────────
DATABASE_PATH = os.environ.get("DATABASE_PATH", "ghost_protocol.db")
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATABASE_PATH}")
DB_POOL_SIZE = 20
DB_POOL_TIMEOUT = 30
DB_POOL_RECYCLE = 3600
BACKUP_DIR = os.environ.get("BACKUP_DIR", "backups")
STORAGE_DIR = os.environ.get("STORAGE_DIR", "storage")
EXPORT_DIR = os.environ.get("EXPORT_DIR", "exports")

# ─── Logging ────────────────────────────────────────────────────────────────
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_DIR = os.environ.get("LOG_DIR", "logs")
LOG_RETENTION_DAYS = 30

# ─── Evidence limits ────────────────────────────────────────────────────────
MAX_SCREENSHOT_MB = 20
MAX_EVIDENCE_PER_CASE = 20
MAX_DESCRIPTION_LENGTH = 1000
MAX_TARGET_LENGTH = 256
MAX_LINKS_PER_CASE = 20

# ─── Coin system ────────────────────────────────────────────────────────────
COIN_DEFAULT_BALANCE = _env_int("COIN_DEFAULT_BALANCE", 0)
COIN_MAX_ADD = _env_int("COIN_MAX_ADD", 1000000)
COIN_TRANSACTION_PAGE_SIZE = 10

# ─── Referral system ────────────────────────────────────────────────────────
REFERRAL_REWARD_DEFAULT = _env_int("REFERRAL_REWARD_DEFAULT", 100)
REFERRAL_MIN_USAGE_DEFAULT = _env_int("REFERRAL_MIN_USAGE_DEFAULT", 1)
REFERRAL_ENABLED_DEFAULT = _env_bool("REFERRAL_ENABLED_DEFAULT", True)

# ─── Force join ─────────────────────────────────────────────────────────────
FORCE_JOIN_ENABLED_DEFAULT = _env_bool("FORCE_JOIN_ENABLED_DEFAULT", False)
FORCE_JOIN_CHANNEL_DEFAULT = os.environ.get("FORCE_JOIN_CHANNEL_DEFAULT", "")

# ─── Cache ──────────────────────────────────────────────────────────────────
CACHE_TTL = 300
BATCH_SIZE = 100


def to_dict() -> dict:
    """Snapshot of key config for DevTools / diagnostics (secrets masked)."""
    return {
        "version": BOT_VERSION,
        "bot_name": BOT_NAME,
        "max_admins": MAX_ADMINS,
        "session_timeout": SESSION_TIMEOUT,
        "email_verification": ADMIN_EMAIL_VERIFICATION,
        "verification_required": ADMIN_VERIFICATION_REQUIRED,
        "rate_limit_per_user": RATE_LIMIT_PER_USER,
        "database": DATABASE_PATH,
        "smtp_host": SMTP_HOST,
        "smtp_configured": bool(SMTP_USER and SMTP_PASSWORD),
        "notifications_enabled": NOTIFICATION_ENABLED,
        "admins": ADMIN_IDS,
        "owner": OWNER_TELEGRAM_ID,
        "referral_reward": REFERRAL_REWARD_DEFAULT,
        "force_join_enabled": FORCE_JOIN_ENABLED_DEFAULT,
        "roles": list(PERMISSIONS.keys()),
    }

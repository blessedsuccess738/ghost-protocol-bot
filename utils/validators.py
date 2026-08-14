"""utils/validators.py — input validation helpers."""
import re
import config

TELEGRAM_LINK_RE = re.compile(r"^(?:https?://)?(?:t\.me|telegram\.me)/([A-Za-z0-9_]{5,32})$")
MESSAGE_LINK_RE = re.compile(r"^https?://t\.me/([A-Za-z0-9_]{5,32}|\+[A-Za-z0-9_-]+)/(\d+)$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(value: str) -> bool:
    return bool(value and EMAIL_RE.match(value.strip()))


def is_valid_verification_token(value: str) -> bool:
    return bool(value) and len(value) <= 128


def is_valid_telegram_link(value: str) -> bool:
    value = value.strip()
    if value.startswith("@"):
        return bool(re.match(r"^@[A-Za-z0-9_]{5,32}$", value))
    return bool(TELEGRAM_LINK_RE.match(value))


def is_valid_message_link(value: str) -> bool:
    return bool(MESSAGE_LINK_RE.match(value.strip()))


def is_valid_screenshot_size(size: int) -> bool:
    return size <= config.MAX_SCREENSHOT_MB * 1024 * 1024


def is_valid_description(value: str) -> bool:
    return len(value) <= config.MAX_DESCRIPTION_LENGTH


def is_valid_target(value: str) -> bool:
    return is_valid_telegram_link(value) or is_valid_message_link(value)


def sanitize_text(value: str) -> str:
    return value.strip()[: config.MAX_DESCRIPTION_LENGTH]


def parse_target(value: str):
    value = value.strip()
    if value.startswith("@"):
        username = value[1:]
        return f"https://t.me/{username}", "user", username
    m = TELEGRAM_LINK_RE.match(value)
    if m:
        username = m.group(1)
        return f"https://t.me/{username}", "channel", username
    return value, "link", None

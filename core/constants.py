"""
core/constants.py — Shared constants for 『𝑮𝑷』 𝑮𝑯𝑶𝑺𝑻 𝑷𝑹𝑶𝑻𝑶𝑪𝑶𝑳 BOT.
"""
import config

# ─── Case (ban request) statuses ────────────────────────────────────────────
STATUS_PENDING = "PENDING"
STATUS_BANNED = "BANNED"
STATUS_REJECTED = "REJECTED"
STATUS_REVIEWED = "REVIEWED"

CASE_STATUSES = [STATUS_PENDING, STATUS_BANNED, STATUS_REJECTED, STATUS_REVIEWED]

# ─── Target types ───────────────────────────────────────────────────────────
TARGET_CHANNEL = "channel"
TARGET_GROUP = "group"
TARGET_USER = "user"
TARGET_TYPES = [TARGET_CHANNEL, TARGET_GROUP, TARGET_USER]

# ─── Reasons / categories ───────────────────────────────────────────────────
REASON_SCAM = "Scam/Fraud"
REASON_PHISHING = "Phishing"
REASON_IMPERSONATION = "Impersonation"
REASON_FAKE_INVESTMENT = "Fake Investment/Casino"
REASON_MALICIOUS_LINK = "Malicious Link"
REASON_OTHER = "Other"

REASONS = [
    REASON_SCAM,
    REASON_PHISHING,
    REASON_IMPERSONATION,
    REASON_FAKE_INVESTMENT,
    REASON_MALICIOUS_LINK,
    REASON_OTHER,
]

# ─── Severity ───────────────────────────────────────────────────────────────
SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"
SEVERITY_CRITICAL = "critical"
SEVERITIES = [SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL]

# ─── Evidence types ─────────────────────────────────────────────────────────
EVIDENCE_LINK = "message_link"
EVIDENCE_SCREENSHOT = "screenshot"
EVIDENCE_BOTH = "both"
EVIDENCE_SKIP = "skip"

# ─── Moderation status (users) ──────────────────────────────────────────────
USER_STATUS_NORMAL = "NORMAL"
USER_STATUS_BANNED = "BANNED"
USER_STATUS_WATCHED = "WATCHED"

# ─── Coin transaction types ─────────────────────────────────────────────────
COIN_ADD = "add"
COIN_ADD_ALL = "add_all"
COIN_REFERRAL = "referral"
COIN_ADJUST = "adjust"

# ─── Conversation states ────────────────────────────────────────────────────
STATE_TARGET = 1
STATE_EVIDENCE_TYPE = 2
STATE_EVIDENCE_LINK = 3
STATE_EVIDENCE_SCREENSHOT = 4
STATE_REASON = 5
STATE_DESCRIPTION = 6
STATE_REVIEW = 7
STATE_EDIT_CHOICE = 8
STATE_AWAIT_EMAIL = 20
STATE_AWAIT_VERIFICATION_TOKEN = 21
STATE_AWAIT_BROADCAST = 30
STATE_AWAIT_EMAIL_CHANGE = 31
STATE_AWAIT_COIN_USER = 40      # admin entering telegram_id for coin add
STATE_AWAIT_COIN_AMOUNT = 41    # admin entering coin amount
STATE_AWAIT_COIN_ALL_CONFIRM = 42  # confirm distribution to all users
STATE_AWAIT_FORCE_GROUP_ID = 43 # admin entering force-join group/channel
STATE_AWAIT_REFERRAL_AMOUNT = 44  # admin setting referral reward
STATE_AWAIT_REFERRAL_MIN = 45     # admin setting referral min requirement
STATE_AWAIT_BAN_TARGET = 46       # (reserved)
STATE_ATTACK_TARGETS = 47         # admin entering target for Verify Target tool

# ─── Callback data prefixes ─────────────────────────────────────────────────
CB_MAIN = "main"
CB_BAN = "ban"                    # 🚫 BAN REQUEST entry
CB_CATEGORY = "category"          # reason selection
CB_REVIEW = "review"
CB_CASES = "cases"
CB_CASE_ACTION = "case_action"
CB_ADMIN = "admin"
CB_ADMINS = "admins"
CB_SETTINGS = "settings"
CB_NOTIF = "notif"
CB_EXPORT = "export"
CB_EDIT = "edit"
CB_PAGE = "page"
CB_BROADCAST = "broadcast"
CB_USERS = "users"
CB_BANNED = "banned"
CB_COIN = "coin"
CB_COIN_ALL = "coin_all"
CB_REFERRAL = "referral"
CB_FORCE_GROUP = "force_group"
CB_STATS = "stats"
CB_HELP = "help"
CB_PROFILE = "profile"
CB_COINS = "coins"

# ─── Audit actions ──────────────────────────────────────────────────────────
AUTH_LOGIN = "auth.login"
AUTH_LOGIN_FAIL = "auth.login_fail"
AUTH_VERIFY_EMAIL = "auth.verify_email"
AUTH_VERIFY_EMAIL_SENT = "auth.verify_email_sent"
AUTH_LOGOUT = "auth.logout"
AUTH_LOCKED = "auth.locked"
CASE_CREATED = "case.created"
CASE_UPDATED = "case.updated"
CASE_SUBMITTED = "case.submitted"
CASE_CLOSED = "case.closed"
CASE_BANNED = "case.banned"
CASE_REJECTED = "case.rejected"
CASE_REVIEWED = "case.reviewed"
EVIDENCE_ADDED = "evidence.added"
EXPORT_RUN = "export.run"
SETTINGS_CHANGED = "settings.changed"
ADMIN_CREATED = "admin.created"
ADMIN_DEACTIVATED = "admin.deactivated"
ADMIN_REACTIVATED = "admin.reactivated"
BROADCAST_SENT = "broadcast.sent"
COIN_ADDED = "coin.added"
COIN_ADDED_ALL = "coin.added_all"
REFERRAL_REWARDED = "referral.rewarded"
FORCE_GROUP_CHANGED = "force_group.changed"
USER_REGISTERED = "user.registered"
TARGET_VERIFIED = "attack.verified"
ATTACK_BAN_REQUEST = "attack.ban_request"
ATTACK_LOG = "attack.log"
ATTACK_STARTED = "attack.started"
ATTACK_STOPPED = "attack.stopped"

# ─── Misc ───────────────────────────────────────────────────────────────────
APP_NAME = config.BOT_NAME
APP_VERSION = config.BOT_VERSION

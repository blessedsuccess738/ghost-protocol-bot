"""
keyboards/inline.py — Inline keyboard builders for 『𝑮𝑷』 𝑮𝑯𝑶𝑺𝑻 𝑷𝑹𝑶𝑻𝑶𝑪𝑶𝑳 BOT.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core.constants import (
    REASONS,
    EVIDENCE_BOTH,
    EVIDENCE_LINK,
    EVIDENCE_SCREENSHOT,
    EVIDENCE_SKIP,
)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """User main menu (keyboard-first)."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🚫 BAN REQUEST", callback_data="main:ban")],
            [InlineKeyboardButton("👤 MY PROFILE", callback_data="main:profile"),
             InlineKeyboardButton("🪙 MY COINS", callback_data="main:coins")],
            [InlineKeyboardButton("🎁 REFERRAL", callback_data="main:referral"),
             InlineKeyboardButton("📋 MY CASES", callback_data="main:cases")],
            [InlineKeyboardButton("👥 REQUIRED GROUP", callback_data="main:force_group")],
            [InlineKeyboardButton("ℹ️ HELP", callback_data="main:help")],
        ]
    )


def user_main_keyboard() -> InlineKeyboardMarkup:
    """Reply keyboard for regular users."""
    from keyboards.reply import user_keyboard
    return user_keyboard()


def evidence_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔗 Message/Chat Link", callback_data="evidence:link"),
             InlineKeyboardButton("📸 Screenshot", callback_data="evidence:screenshot")],
            [InlineKeyboardButton("📎 Both", callback_data="evidence:both"),
             InlineKeyboardButton("⏭️ Skip Evidence", callback_data="evidence:skip")],
            [InlineKeyboardButton("❌ Cancel", callback_data="main:cancel")],
        ]
    )


def reason_keyboard() -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(label, callback_data=f"reason:{label}") for label in REASONS]
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton("❌ Cancel", callback_data="main:cancel")])
    return InlineKeyboardMarkup(rows)


def review_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Confirm", callback_data="review:confirm")],
            [InlineKeyboardButton("✏️ Edit", callback_data="review:edit"),
             InlineKeyboardButton("❌ Cancel", callback_data="review:cancel")],
        ]
    )


def edit_choice_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🎯 Edit Target", callback_data="edit:target")],
            [InlineKeyboardButton("📋 Edit Reason", callback_data="edit:reason")],
            [InlineKeyboardButton("📝 Edit Description", callback_data="edit:description")],
            [InlineKeyboardButton("🔙 Back to Review", callback_data="review:back")],
        ]
    )


# ── Admin panel (keyboard-first) ─────────────────────────────────────────────
def admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("👥 USERS", callback_data="admin:users"),
             InlineKeyboardButton("🚫 BANNED USERS", callback_data="admin:banned")],
            [InlineKeyboardButton("📋 PENDING CASES", callback_data="admin:pending"),
             InlineKeyboardButton("🔎 SEARCH USER", callback_data="admin:search")],
            [InlineKeyboardButton("🪙 ADD COINS", callback_data="admin:coin"),
             InlineKeyboardButton("💰 COINS FOR ALL", callback_data="admin:coin_all")],
            [InlineKeyboardButton("🎁 REFERRAL SYSTEM", callback_data="admin:referral"),
             InlineKeyboardButton("📢 BROADCAST", callback_data="admin:broadcast")],
            [InlineKeyboardButton("👥 FORCE GROUP", callback_data="admin:force_group"),
             InlineKeyboardButton("🎯 VERIFY TARGET", callback_data="admin:attack")],
            [InlineKeyboardButton("📊 STATISTICS", callback_data="admin:stats")],
            [InlineKeyboardButton("⚙️ BOT SETTINGS", callback_data="admin:settings"),
             InlineKeyboardButton("👑 MANAGE ADMINS", callback_data="admin:admins")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main:menu")],
        ]
    )


# ── Moderation decision buttons ─────────────────────────────────────────────
def moderation_keyboard(case_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🚫 BAN", callback_data=f"mod:{case_id}:BAN"),
             InlineKeyboardButton("↩️ REJECT", callback_data=f"mod:{case_id}:REJECT")],
            [InlineKeyboardButton("⏳ PENDING", callback_data=f"mod:{case_id}:PENDING"),
             InlineKeyboardButton("✅ MARK REVIEWED", callback_data=f"mod:{case_id}:REVIEWED")],
            [InlineKeyboardButton("📋 View Evidence", callback_data=f"case_action:evidence:{case_id}")],
            [InlineKeyboardButton("🔙 Back to Pending", callback_data="admin:pending")],
        ]
    )


def ban_request_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🚫 Submit Ban Request", callback_data="main:ban")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main:menu")],
        ]
    )


# ── Coin / referral / force group menus ─────────────────────────────────────
def coin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🪙 Add Coins To User", callback_data="coin:add")],
            [InlineKeyboardButton("💰 Add Coins To All Users", callback_data="coin:all")],
            [InlineKeyboardButton("📜 Coin History", callback_data="coin:history")],
            [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin:menu")],
        ]
    )


def coin_all_confirm_keyboard(amount: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ CONFIRM", callback_data=f"coin_all:confirm:{amount}")],
            [InlineKeyboardButton("❌ CANCEL", callback_data="coin_all:cancel")],
        ]
    )


def referral_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🎁 Referral Reward", callback_data="referral:reward")],
            [InlineKeyboardButton("👥 Minimum Requirement", callback_data="referral:min")],
            [InlineKeyboardButton("🔄 Referral Status ON/OFF", callback_data="referral:toggle")],
            [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin:menu")],
        ]
    )


def force_group_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ Add Required Group", callback_data="force_group:add")],
            [InlineKeyboardButton("✏️ Change Group", callback_data="force_group:add")],
            [InlineKeyboardButton("🔄 Enable/Disable", callback_data="force_group:toggle")],
            [InlineKeyboardButton("🗑 Remove Requirement", callback_data="force_group:remove")],
            [InlineKeyboardButton("🔍 Check Membership", callback_data="force_group:check")],
            [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin:menu")],
        ]
    )


def manage_admins_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("👥 View All Admins", callback_data="admins:list")],
            [InlineKeyboardButton("➕ Add Admin", callback_data="admins:add")],
            [InlineKeyboardButton("🚫 Remove Admin", callback_data="admins:remove")],
            [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin:menu")],
        ]
    )


# ── Legacy / shared ─────────────────────────────────────────────────────────
def case_actions_keyboard(case_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🚫 BAN", callback_data=f"mod:{case_id}:BAN"),
             InlineKeyboardButton("↩️ REJECT", callback_data=f"mod:{case_id}:REJECT")],
            [InlineKeyboardButton("⏳ PENDING", callback_data=f"mod:{case_id}:PENDING"),
             InlineKeyboardButton("✅ REVIEWED", callback_data=f"mod:{case_id}:REVIEWED")],
            [InlineKeyboardButton("📋 View Evidence", callback_data=f"case_action:evidence:{case_id}")],
            [InlineKeyboardButton("📤 Export Report", callback_data=f"case_action:export:{case_id}")],
            [InlineKeyboardButton("🔙 Back to Cases", callback_data="cases:list")],
        ]
    )


def settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📧 Update Email", callback_data="settings:email")],
            [InlineKeyboardButton("🔔 Notifications", callback_data="settings:notifications")],
            [InlineKeyboardButton("👤 Profile", callback_data="settings:profile")],
            [InlineKeyboardButton("📊 Stats", callback_data="settings:stats")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main:menu")],
        ]
    )


def notification_settings_keyboard(settings: dict | None = None) -> InlineKeyboardMarkup:
    s = settings or {}
    email = "ON" if s.get("email", True) else "OFF"
    tg = "ON" if s.get("telegram", True) else "OFF"
    case = "ON" if s.get("case_updates", True) else "OFF"
    alerts = "ON" if s.get("system_alerts", True) else "OFF"
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"📧 Email: {email}", callback_data="notif:email")],
            [InlineKeyboardButton(f"📱 Telegram: {tg}", callback_data="notif:telegram")],
            [InlineKeyboardButton(f"📋 Case Updates: {case}", callback_data="notif:case_updates")],
            [InlineKeyboardButton(f"⚠️ System Alerts: {alerts}", callback_data="notif:system_alerts")],
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="settings:menu")],
        ]
    )


def export_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📄 JSON (Complete)", callback_data="export:json:all")],
            [InlineKeyboardButton("📊 CSV (Cases)", callback_data="export:csv:cases")],
            [InlineKeyboardButton("👥 CSV (Admins)", callback_data="export:csv:admins")],
            [InlineKeyboardButton("🧾 CSV (Audit)", callback_data="export:csv:audit")],
            [InlineKeyboardButton("📕 PDF (Report)", callback_data="export:pdf:all")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main:menu")],
        ]
    )


def pagination_keyboard(prefix: str, page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton("◀️ Previous", callback_data=f"page:{prefix}:{page - 1}"))
    buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="page:none"))
    if page < total_pages:
        buttons.append(InlineKeyboardButton("▶️ Next", callback_data=f"page:{prefix}:{page + 1}"))
    row = [InlineKeyboardButton("🔙 Back", callback_data="main:menu")]
    return InlineKeyboardMarkup([buttons, row])


def confirm_keyboard(prefix: str, item_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Yes", callback_data=f"{prefix}:yes:{item_id}"),
             InlineKeyboardButton("❌ No", callback_data=f"{prefix}:no:{item_id}")],
        ]
    )


# ── Verify Target (safe attack-tools suite) ────────────────────────────────
def attack_tools_keyboard() -> InlineKeyboardMarkup:
    """Entry menu for the Verify Target suite (admin-only)."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🎯 Verify Target", callback_data="attack:verify")],
            [InlineKeyboardButton("📜 Recent Activity", callback_data="attack:recent")],
            [InlineKeyboardButton("📊 Tool Stats", callback_data="attack:stats")],
            [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin:menu")],
        ]
    )


def attack_verify_options_keyboard(username: str, target_type: str) -> InlineKeyboardMarkup:
    """Buttons shown after a target is verified.

    🔴 BAN ACCOUNT → opens a moderation case (BAN REQUEST) for this target
    🔍 VERIFY AGAIN → re-run reachability check
    ❌ CANCEL       → close the tool
    (No BUG / DDOS tools exist — those are out of scope for this suite.)
    """
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🚫 BAN ACCOUNT",
                                  callback_data=f"attack:ban:{username}:{target_type}")],
            [InlineKeyboardButton("🔍 VERIFY AGAIN",
                                  callback_data=f"attack:reverify:{username}")],
            [InlineKeyboardButton("❌ CANCEL", callback_data="attack:cancel")],
        ]
    )


def attack_ban_reason_keyboard(username: str, target_type: str) -> InlineKeyboardMarkup:
    """Reason selection for the BAN (moderation case) action."""
    reasons = [
        ("🚨 Scam/Fraud", "Scam/Fraud"),
        ("🎣 Phishing", "Phishing"),
        ("👤 Impersonation", "Impersonation"),
        ("💰 Fake Investment", "Fake Investment/Casino"),
        ("🔗 Malicious Link", "Malicious Link"),
        ("⚠️ Other", "Other"),
    ]
    rows = []
    for label, value in reasons:
        rows.append([InlineKeyboardButton(
            label, callback_data=f"attack:reason:{username}:{target_type}:{value}")])
    rows.append([InlineKeyboardButton("❌ Cancel", callback_data="attack:cancel")])
    return InlineKeyboardMarkup(rows)


def attack_confirm_keyboard(username: str, target_type: str, reason: str) -> InlineKeyboardMarkup:
    """Confirmation step before any action executes."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ YES", callback_data=f"attack:confirm:{username}:{target_type}:{reason}")],
            [InlineKeyboardButton("❌ NO", callback_data="attack:cancel")],
        ]
    )


def attack_recent_pagination_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton("◀️ Previous",
                                            callback_data=f"attack:recent:{page - 1}"))
    buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="attack:none"))
    if page < total_pages:
        buttons.append(InlineKeyboardButton("▶️ Next",
                                            callback_data=f"attack:recent:{page + 1}"))
    row = [InlineKeyboardButton("🔙 Back to Tools", callback_data="attack:menu")]
    return InlineKeyboardMarkup([buttons, row])

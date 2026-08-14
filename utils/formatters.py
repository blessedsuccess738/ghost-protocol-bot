"""utils/formatters.py — display formatting helpers."""
import datetime


def format_case_summary(case) -> str:
    emoji = {"PENDING": "⏳", "BANNED": "🚫", "REJECTED": "↩️", "REVIEWED": "✅"}.get(case.status, "📋")
    created = case.created_at.strftime("%Y-%m-%d %H:%M") if case.created_at else "—"
    return (f"{emoji} *{case.case_id}* — {case.reason}\n"
            f"🎯 `{case.target_link[:50]}`\n"
            f"📌 {case.status} · 📅 {created}")


def format_case_details(case, evidence_count: int = 0) -> str:
    return (f"📋 *Case ID:* `{case.case_id}`\n"
            f"🎯 Target: `{case.target_link}`\n"
            f"🚨 Reason: {case.reason}\n"
            f"🧾 Evidence items: {evidence_count}\n"
            f"📌 Status: {case.status}")


def format_user_summary(user) -> str:
    status_emoji = "🚫" if user.is_banned else ("👁" if user.moderation_status == "WATCHED" else "🟢")
    return (f"{status_emoji} *{user.first_name or 'User'}*\n"
            f"🆔 ID: `{user.telegram_id}`\n"
            f"👤 Username: @{user.username or '—'}\n"
            f"🪙 Coins: *{user.coins or 0}*\n"
            f"🎁 Referrals: {user.referral_count or 0}\n"
            f"📅 Joined: {user.created_at.strftime('%Y-%m-%d') if user.created_at else '—'}")


def format_admin_summary(admin) -> str:
    return (f"👑 *{admin.username or admin.telegram_id}*\n"
            f"🆔 ID: `{admin.telegram_id}`\n"
            f"📧 Email: {admin.email or '—'} {'✅' if admin.email_verified else '❌'}\n"
            f"🎖 Role: {admin.role}\n🟢 Active: {'Yes' if admin.is_active else 'No'}")


def format_uptime(seconds: float) -> str:
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{days}d {hours}h {minutes}m {secs}s"

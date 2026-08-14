from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove


def user_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [KeyboardButton("🚫 BAN REQUEST")],
        [KeyboardButton("👤 MY PROFILE"), KeyboardButton("🪙 MY COINS")],
        [KeyboardButton("🎁 REFERRAL"), KeyboardButton("📋 MY CASES")],
        [KeyboardButton("👥 REQUIRED GROUP"), KeyboardButton("ℹ️ HELP")],
    ], resize_keyboard=True)


def admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [KeyboardButton("👑 ADMIN PANEL")],
        [KeyboardButton("👥 USERS"), KeyboardButton("📋 CASES"), KeyboardButton("🚫 BANNED")],
        [KeyboardButton("🪙 ADD COINS"), KeyboardButton("💰 COINS FOR ALL")],
        [KeyboardButton("🎁 REFERRALS"), KeyboardButton("👥 FORCE GROUP")],
        [KeyboardButton("📢 BROADCAST"), KeyboardButton("📊 STATISTICS")],
        [KeyboardButton("👑 ADMINS"), KeyboardButton("⚙️ SETTINGS")],
    ], resize_keyboard=True)


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()

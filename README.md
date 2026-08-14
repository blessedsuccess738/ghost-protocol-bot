# 『𝑮𝑷』 𝑮𝑯𝑶𝑺𝑻 𝑷𝑹𝑶𝑻𝑶𝑪𝑶𝑳 BOT — v2.0.0

**Short identity:** 『𝑮𝑷』
A production-grade Telegram scam-monitoring & moderation system.

## Features

- **BAN REQUEST workflow** — submit suspicious channels/groups/users/links with evidence (message links + screenshots) and a case ID (`GP-000NNN`) is assigned
- **Moderation panel** — admins review cases and act: 🚫 BAN / ↩️ REJECT / ⏳ PENDING / ✅ MARK REVIEWED; every decision is logged in `ban_records`
- **Admin panel (keyboard-first)** — Users, Banned Users, Pending Cases, Search User, Add Coins, Coins For All, Referral System, Broadcast, Force Group, Statistics, Bot Settings, Manage Admins
- **Coin system** — balance, history ledger, add-to-user, add-to-all distribution
- **Referral system** — unique GP referral code per user, reward coins on signup via link, duplicate-reward prevention
- **Force-join gate** — require users to join a group/channel before use, with JOIN/CHECK buttons
- **Admin email verification** — token-based (SMTP, with in-chat fallback token), account lockout after 5 failures
- **Audit trail + export** — JSON/CSV/PDF exports, per-action audit logs, notifications
- **Rate limiting, backup, storage** — sliding-window rate limits, SQLite WAL + backups, hashed evidence storage

## Quick Start

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in TELEGRAM_BOT_TOKEN, ADMIN_IDS, OWNER_TELEGRAM_ID
python3 bot.py
```

## Commands

| Command | Access | Purpose |
|---|---|---|
| `/start` | All | Onboarding, force-join gate, referral capture, admin/user paths |
| `/ban_request` (alias `/report`) | All | Start the BAN REQUEST workflow |
| `/cases`, `/mycases` | All | List cases (own for users, all for admins) |
| `/admin`, `/admins`, `/stats`, `/users`, `/banned`, `/pending` | Admin | Admin panel |
| `/broadcast` | Admin | Broadcast to all users |
| `/export` | Admin | Export JSON/CSV/PDF |
| `/settings` | Admin | Email, notifications, profile |

## Project Structure

```
bot.py                 # entry point
config.py              # env-based configuration
core/                  # application, constants, security
models/                # SQLAlchemy models
handlers/              # PTB handlers (start, ban_request, cases, admin, ...)
keyboards/             # inline + reply keyboard builders
services/              # audit, ban, coin, email, export, force_group, referral, ...
database/repositories/ # repository pattern (case, ban, user, coin, referral, ...)
middleware/            # logging + error middleware
utils/                 # decorators, formatters, validators, logger, helpers
tests/                 # unit tests
```

## Security Notes

- Admin access is by Telegram user ID only (`ADMIN_IDS`), never username.
- The OWNER can never be removed by another admin.
- Secrets come from environment variables; `.env.example` documents them.
- BAN actions record internal moderation decisions — the bot does not abuse Telegram's reporting API.

## License

Private / internal use.

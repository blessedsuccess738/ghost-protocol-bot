# 『𝑮𝑷』 𝑮𝑯𝑶𝑺𝑻 𝑷𝑹𝑶𝑻𝑶𝑪𝑶𝑳 BOT — v3.0.0

**Short identity:** 『𝑮𝑷』
A production-grade Telegram scam-monitoring and moderation system.
Built on the enterprise architecture of the Scam Report Assistant (multi-admin
auth, SQLAlchemy repository pattern, services, keyboards, middleware, tests)
transformed from a "REPORT" flow into a **BAN REQUEST** moderation workflow.

> ⚠️ The 🚫 BAN action is an **administrative moderation decision** recorded
> after reviewing submitted evidence. It does NOT mass-report or abuse
> Telegram's reporting system.

---

## 🧱 Architecture

```
ghost_protocol_bot/
├── bot.py                    # Entry point
├── config.py                 # Configuration (env-driven)
├── requirements.txt
├── .env.example              # Environment template
├── startup.sh                # Deployment script
├── README.md
├── core/
│   ├── application.py        # App init + handler registration
│   ├── security.py           # Encryption, hashing, case IDs (GP-000001)
│   └── constants.py          # Statuses, states, callback prefixes
├── database/
│   ├── connection.py         # Connection pooling
│   ├── migrations.py         # Schema creation + migrations
│   └── repositories/         # Admin, Case, Evidence, Audit, Session,
│                             # Notification, Analytics, Settings, RateLimit,
│                             # User, Coin, Referral, Ban, ForceGroup, AttackLog
├── handlers/                 # start, ban_request, cases, admin, settings,
│                             # export, broadcast, callback, keyboard_router, attack
├── services/                 # coin, referral, force_group, ban, email,
│                             # notification, export, storage, backup, audit,
│                             # target_verify
├── models/                   # ORM classes (User, Case, Evidence, BanRecord…)
├── middleware/               # auth (telegram-ID only), logging, rate limit
├── keyboards/                # main, admin, report, cases, settings, pagination
├── utils/                    # validators, formatters, helpers, decorators
└── tests/                    # Unit + integration tests
```

## 👑 Roles

| Role | Access |
|------|--------|
| 👑 OWNER | Full control: add/remove admins, bot settings, coins, referrals, force-join, users, stats |
| 🛡️ ADMIN | Manage users, review cases, use BAN/UNBAN moderation, view stats |

**Security:** access is authorized by **Telegram user ID only** — never by
username. The OWNER is protected and can never be removed by normal admins.
Users cannot reach the admin panel by manipulating callback data.

## 🚫 BAN SYSTEM

1. User sends `🚫 BAN REQUEST` (or `/ban`)
2. Bot collects: target link/username → category → description → evidence → screenshot
3. Case created: `CASE ID: GP-000124`, status `⏳ PENDING`
4. Admin reviews and chooses: `🚫 BAN` `↩️ REJECT` `⏳ PENDING` `✅ MARK REVIEWED`
5. A **BanRecord** is persisted: target, reason, admin, datetime, case ID, evidence ref
6. Moderation history per target is queryable (`/bans`)

## 🪙 COIN SYSTEM

- Admin: `🪙 Add Coins To User`, `💰 Add Coins To All Users`, `📜 Coin History`
- "Coins For All" asks **confirmation** (`✅ CONFIRM` / `❌ CANCEL`) before distributing
- Every change is written to `coin_transactions` ledger

## 🎁 REFERRAL SYSTEM

- Every user gets a unique link: `https://t.me/<bot>?start=<CODE>`
- Reward (default 100 coins), min-usage threshold and ON/OFF are admin-configurable
- Duplicate reward claiming with the same account/relationship is blocked

## 👥 FORCE GROUP / CHANNEL

- Admin sets required group/channel, enables/disables, or removes the requirement
- When enabled, users must join before using protected functions
- Buttons: `✅ JOIN GROUP` `🔄 CHECK JOINED`

## 📊 STATISTICS

Users · Active Users · Referrals · Coins Distributed · Cases · Pending ·
Banned · Admins — shown in the admin panel (`/stats`).

## 📢 BROADCAST

`📢 Send To All` · `🎁 Referral Users` · `🟢 Active Users` — with delivery
success/failure counts.

## 🎯 VERIFY TARGET — TOOL SUITE (v3.0.0)

Admin-only, keyboard-first tool menu (`/attack` or Admin Panel → 🎯 VERIFY TARGET):

- **Verify Target** — enter a Telegram username/link; the bot extracts the
  target, checks existence & reachability via public `t.me` metadata
- **BAN ACCOUNT** — after verification, opens a documented moderation case
  (BAN REQUEST) with reason + confirmation; the decision is recorded in
  `attack_logs` + `ban_records` for full audit
- **Recent Activity / Tool Stats** — per-admin action history & counters

Commands: `/attack` · `/verify <target>` · `/ban <target>` · `/status` · `/stop`

> ⚠️ **WARNING:** These tools are for LEGITIMATE scam removal only. Misuse
> results in permanent ban from this bot. All actions are logged and audited.
>
> 🔒 **Scope:** There is NO DDOS tool, NO bug-exploit tool, and no off-platform
> ban capability in this suite. The official Bot API cannot globally ban
> arbitrary accounts, and this bot does not mass-report or abuse Telegram's
> reporting system. `/bug` exists only to clearly explain that the requested
> exploit is not implemented.

## 🔧 Deployment

1. `pip install -r requirements.txt`
2. Copy `.env.example` → `.env`, set `TELEGRAM_BOT_TOKEN` and `ADMIN_TELEGRAM_ID`
3. `python3 bot.py` (or `bash startup.sh`)

## 🔑 Environment Variables

See `.env.example` for the full list: `TELEGRAM_BOT_TOKEN`, `ADMIN_TELEGRAM_ID`,
`SECRET_KEY`, `JWT_SECRET`, `ENCRYPTION_KEY`, `DATABASE_PATH`, rate-limit
settings, SMTP notification settings.

## 🧪 Tests

```bash
cd ghost_protocol_bot
python3 -m compileall -q .
python3 tests/test_attack_tools.py   # Verify Target suite (8 tests)
python3 tests/test_validators.py     # Input validators + security (10 tests)
python3 tests/test_repositories.py   # DB + repositories + exports (4 tests)
```

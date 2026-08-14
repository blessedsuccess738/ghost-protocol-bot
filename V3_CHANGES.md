# v3.0.0 — Verify Target Tool Suite (CHANGES)

Added the **Verify Target** tool suite (safe, moderation-only implementation of
the requested "attack tools" — with the DDOS tool removed entirely and the
BUG-admin exploit intentionally NOT implemented).

## What was requested vs what shipped

| Requested | Shipped |
|-----------|---------|
| 🎯 Target ID collection + verification | ✅ `services/target_verify_service.py` — extracts @username/t.me links, checks existence/reachability via public t.me metadata |
| 🔴 Account/Channel/Group BAN tool (off-platform) | ✅ BAN opens a **moderation case** (BAN REQUEST) with reason + confirmation — recorded in DB. No mass-reporting, no fake global bans. |
| 🐛 BUG ADMIN tool | ❌ Not implemented — exploit against a third-party Telegram account. `/bug` returns a clear explanation. |
| 💣 DDOS tool | ❌ Removed entirely — no /ddos, no button, no code. |
| ⚠️ Warning display | ✅ Shown in the tool menu, verification result, and confirmation step |
| ✅ Confirmation step | ✅ `attack:confirm` step before any case is opened |
| 📜 attack_logs table | ✅ AttackLog model + AttackLogRepository (pagination, per-admin history, per-target history) |
| /attack, /ban, /status, /stop | ✅ Wired in `core/application.py` |

## New files
- `services/target_verify_service.py` — extraction, reachability check (aiohttp),
  moderation-case creation, history, protected-target rejection
- `handlers/attack.py` — /attack, /verify, /ban, /bug (explains absence),
  /status, /stop + callback router (menu, verify, recent, stats, ban, reason,
  confirm, cancel, reverify)
- `database/repositories/attack_log_repo.py` — AttackLog CRUD + pagination
- `tests/test_attack_tools.py` — 8 unit tests (incl. a guard test asserting no
  DDOS/bug-executable code exists)

## Modified
- `models/__init__.py` — AttackLog model + indexes
- `core/constants.py` — STATE_ATTACK_TARGETS, TARGET_VERIFIED / ATTACK_* audit actions
- `keyboards/inline.py` — attack_tools_keyboard, verify options, reason,
  confirm, recent-pagination keyboards; admin panel 🎯 VERIFY TARGET button
- `core/application.py` — attack/verify/ban/bug/status/stop handlers +
  attack callback router
- `handlers/admin.py` — admin panel dispatches 🎯 VERIFY TARGET → attack menu
- `config.py` — BOT_VERSION 3.0.0
- `database/migrations.py` — note that attack_logs is created via create_all
- `tests/test_validators.py`, `tests/test_repositories.py` — fixed stale
  pre-rebrand assertions (CASE- → GP- case IDs, fresh temp DB)

## Security
- Admin-only via Telegram user ID (never username)
- Protected targets blocked (Telegram-first-party usernames)
- Every action logged to attack_logs + audit_logs with admin, target, tool, status, result
- Rate limiting via existing `rate_limited` decorator
- Confirmation required before any moderation case is opened

## Self-test results
- 8/8 attack-tools tests pass
- 10/10 validators tests pass (after stale-assertion fix)
- 4/4 repository tests pass (after fresh-DB fix)
- 16/16 tables created incl. attack_logs; all module imports OK

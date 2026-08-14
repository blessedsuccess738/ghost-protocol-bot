"""
services/target_verify_service.py — Target verification + safe tool facade.

This implements the 'Verify Target' workflow of the GP attack-tools suite in a
LEGITIMATE, moderation-only way:

- Extract & normalize target from @username / t.me link / bare username
- Check existence & reachability using public t.me preview metadata
  (no abuse of Telegram APIs; no mass-reporting; no exploit tooling)
- Record every action in attack_logs for full audit
- Route verified targets into the existing BAN REQUEST case workflow so an
  authorized admin can open a moderation case (BAN decision recorded in DB)

Tools exposed: verify_target, create_moderation_case, recent_activity.
No DDOS / no bug-exploit / no off-platform ban functionality exists here.
"""
import logging
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import aiohttp

import config
from core.constants import (
    ATTACK_LOG,
    ATTACK_BAN_REQUEST,
    TARGET_VERIFIED,
    STATUS_PENDING,
)
from database.connection import get_engine
from database.repositories.attack_log_repo import AttackLogRepository
from database.repositories.case_repo import CaseRepository
from database.repositories.user_repo import UserRepository
from services.audit_service import audit_service

logger = logging.getLogger(__name__)

# t.me preview page (public, no auth needed)
T_ME_PREVIEW = "https://t.me/{name}"

# A channel/group link redirects to /s/... ; a user link stays /name
# Regex to sniff what the public page tells us about the entity.
_USERNAME_RE = re.compile(r"^@?[A-Za-z0-9_]{5,32}$")
_TME_LINK_RE = re.compile(r"^(?:https?://)?(?:t\.me|telegram\.me)/([A-Za-z0-9_]+)(?:/\d+)?$")
_MESSAGE_LINK_RE = re.compile(r"^https?://t\.me/[A-Za-z0-9_]+/\d+$")

# Official Telegram / known-first-party usernames that must never be targeted.
PROTECTED_USERNAMES = {
    "telegram", "BotFather", "premium", "privacy", "support", "spambot",
    "safetycenter", "about_telegram", "FAQ", "stickers", "gif", "bg",
    "vpn", "translate", "verification", "delete", "contact", "newbot",
}

# Status values stored in attack_logs
ST_SUCCESS = "SUCCESS"
ST_FAILED = "FAILED"
ST_PARTIAL = "PARTIAL"
ST_LOGGED = "LOGGED"
ST_CANCELLED = "CANCELLED"

# Tool names
TOOL_VERIFY = "verify_target"
TOOL_BAN_REQUEST = "ban_request"


def extract_target(value: str) -> dict | None:
    """Extract + normalize a target reference.

    Returns dict with keys: username, link, target_type, target_id (nullable),
    message_id (nullable). Returns None when the input isn't a valid Telegram
    reference.
    """
    v = (value or "").strip()
    if not v:
        return None

    username = None
    message_id = None

    # @username
    if v.startswith("@"):
        username = v[1:]
    else:
        m = _TME_LINK_RE.match(v)
        if m:
            username = m.group(1)
        elif _USERNAME_RE.match(v):
            username = v
        else:
            return None

    # Message link? (t.me/name/12345)
    if _MESSAGE_LINK_RE.match(v):
        try:
            message_id = int(v.rstrip("/").split("/")[-1])
        except (ValueError, IndexError):
            message_id = None

    link = f"https://t.me/{username}"
    target_type = "user"
    if _TME_LINK_RE.match(v) and "/" in v.split("t.me/", 1)[-1]:
        target_type = "channel"  # public channel/group preview
    return {
        "username": username,
        "link": link,
        "target_type": target_type,
        "target_id": None,  # cannot be derived without an API call
        "message_id": message_id,
    }


def is_protected(username: str) -> bool:
    return (username or "").lower() in {u.lower() for u in PROTECTED_USERNAMES}


async def check_reachability(username: str, timeout: int = 8) -> dict:
    """Check whether a public t.me page exists (public preview page).

    Returns dict: {exists: bool, active: bool, reachable: bool, note: str}.
    A 200/redirect => exists; 404 => missing. Network error => unknown.
    """
    if not username:
        return {"exists": False, "active": False, "reachable": False,
                "note": "empty target"}
    url = T_ME_PREVIEW.format(name=username)
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36",
        "Accept-Language": "en-NG,en;q=0.9",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=timeout,
                                   allow_redirects=False) as resp:
                code = resp.status
                if code == 200:
                    return {"exists": True, "active": True, "reachable": True,
                            "note": f"public page reachable (HTTP {code})"}
                if code in (301, 302, 303, 307, 308):
                    loc = resp.headers.get("Location", "")
                    return {"exists": True, "active": True, "reachable": True,
                            "note": f"public page found (redirect {code})"}
                if code == 404:
                    return {"exists": False, "active": False, "reachable": False,
                            "note": "no public t.me page (404)"}
                return {"exists": False, "active": False, "reachable": False,
                        "note": f"unexpected HTTP {code}"}
    except asyncio_timeout():
        return {"exists": False, "active": False, "reachable": False,
                "note": "timeout reaching t.me"}
    except Exception as exc:
        return {"exists": False, "active": False, "reachable": False,
                "note": f"network error: {exc}"}


def asyncio_timeout():
    import asyncio
    return asyncio.TimeoutError


class TargetVerifyService:
    def __init__(self):
        self.attack_log_repo = AttackLogRepository(get_engine())
        self.case_repo = CaseRepository(get_engine())
        self.user_repo = UserRepository(get_engine())

    # ── Verification ──────────────────────────────────────────────────────
    async def verify(self, admin: dict, raw_target: str) -> dict:
        """Full verification flow.

        admin: {'id', 'telegram_id'}  raw_target: user input
        Returns result dict for the handler to render + log.
        """
        parsed = extract_target(raw_target)
        if parsed is None:
            return {
                "ok": False,
                "error": "Invalid Telegram reference. Use @username, "
                         "https://t.me/username, or a bare username.",
                "parsed": None,
            }

        username = parsed["username"]
        if is_protected(username):
            return {
                "ok": False,
                "error": "This target is a protected/known-first-party "
                         "Telegram account and cannot be used with the tools.",
                "parsed": parsed,
            }

        reach = await check_reachability(username)

        result = {
            "ok": True,
            "parsed": parsed,
            "reach": reach,
            "protected": False,
            "exists": reach["exists"],
            "active": reach["active"],
            "reachable": reach["reachable"],
        }

        # Log every verification attempt (even failures)
        self._log(admin, parsed, TOOL_VERIFY,
                  status=ST_SUCCESS if reach["exists"] else ST_FAILED,
                  result=reach["note"])
        audit_service.log(admin["telegram_id"], TARGET_VERIFIED,
                          details={"target": parsed["link"],
                                   "exists": reach["exists"],
                                   "type": parsed["target_type"]})
        return result

    # ── Moderation case creation (the legitimate 'BAN' path) ─────────────
    def create_moderation_case(self, admin: dict, parsed: dict, reason: str,
                               description: str | None = None) -> dict:
        """Open a BAN REQUEST case for the verified target.

        The BAN decision is an internal moderation record — this bot does not
        mass-report or abuse Telegram's reporting system.
        """
        case = self.case_repo.create(
            admin_id=admin.get("id"),
            submitter_id=admin.get("user_id"),
            target_link=parsed["link"],
            target_type=parsed["target_type"],
            target_name=parsed["username"],
            reason=reason,
            description=description,
            status=STATUS_PENDING,
        )
        self._log(admin, parsed, TOOL_BAN_REQUEST, status=ST_LOGGED,
                  result=f"case {case.case_id} created (PENDING)")
        audit_service.log(admin["telegram_id"], ATTACK_BAN_REQUEST,
                          details={"case_id": case.case_id,
                                   "target": parsed["link"]})
        return {"ok": True, "case": case}

    # ── History ──────────────────────────────────────────────────────────
    def recent(self, admin_id: int, page: int = 1, per_page: int = 10):
        return self.attack_log_repo.history_for_admin(admin_id, page, per_page)

    def history_for_target(self, target: str, limit: int = 20):
        return self.attack_log_repo.history_for_target(target, limit)

    def count_total(self) -> int:
        return self.attack_log_repo.count_total()

    def _log(self, admin: dict, parsed: dict, tool: str, status: str,
             result: str | None = None) -> None:
        try:
            self.attack_log_repo.create(
                target=parsed["link"],
                target_id=parsed.get("target_id"),
                target_type=parsed.get("target_type"),
                tool_used=tool,
                status=status,
                result=result,
                admin_id=admin.get("id"),
                admin_telegram_id=admin.get("telegram_id"),
            )
        except Exception as exc:
            logger.error("attack_log write failed: %s", exc)


target_verify_service = TargetVerifyService()

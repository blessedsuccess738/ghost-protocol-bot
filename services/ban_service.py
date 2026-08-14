"""services/ban_service.py — moderation decision engine for 『𝑮𝑷』 𝑮𝑯𝑶𝑺𝑻 𝑷𝑹𝑶𝑻𝑶𝑪𝑶𝑳 BOT.

Admins act on ban requests; every action is persisted in ban_records
and an audit trail entry is written. The bot records internal moderation
decisions only — it never mass-reports or abuses Telegram's reporting API.
"""
import logging

from core.constants import (STATUS_PENDING, STATUS_BANNED, STATUS_REJECTED, STATUS_REVIEWED,
                            CASE_BANNED, CASE_REJECTED, CASE_REVIEWED)
from database.connection import get_engine
from database.repositories.ban_repo import BanRepository
from database.repositories.case_repo import CaseRepository
from services.audit_service import audit_service

logger = logging.getLogger(__name__)


class BanService:
    def __init__(self):
        self.case_repo = CaseRepository(get_engine())
        self.ban_repo = BanRepository(get_engine())

    def act(self, case, action: str, admin_id: int | None = None,
            admin_telegram_id: int | None = None, note: str | None = None) -> dict:
        action = action.upper()
        if action not in (STATUS_PENDING, STATUS_BANNED, STATUS_REJECTED, STATUS_REVIEWED):
            return {"ok": False, "error": f"Unknown action {action}"}
        self.case_repo.update_status(case, action)
        self.ban_repo.create(case_id=case.case_id, target=case.target_link, reason=case.reason,
                             action=action, admin_id=admin_id, admin_telegram_id=admin_telegram_id,
                             target_type=case.target_type, note=note)
        audit_action = {STATUS_BANNED: CASE_BANNED, STATUS_REJECTED: CASE_REJECTED,
                        STATUS_REVIEWED: CASE_REVIEWED}.get(action, "case.updated")
        audit_service.log(admin_telegram_id, audit_action,
                          details={"case_id": case.case_id, "target": case.target_link})
        logger.info("Case %s -> %s by admin %s", case.case_id, action, admin_telegram_id)
        return {"ok": True, "status": action}


ban_service = BanService()

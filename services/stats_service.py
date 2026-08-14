"""services/stats_service.py — statistics aggregation facade."""
import logging

from database.connection import get_engine
from database.repositories.admin_repo import AdminRepository
from database.repositories.audit_repo import AuditRepository
from database.repositories.case_repo import CaseRepository
from database.repositories.evidence_repo import EvidenceRepository
from database.repositories.session_repo import SessionRepository
from database.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)


class StatsService:
    def __init__(self):
        self.admin_repo = AdminRepository(get_engine())
        self.case_repo = CaseRepository(get_engine())
        self.ev_repo = EvidenceRepository(get_engine())
        self.audit_repo = AuditRepository(get_engine())
        self.session_repo = SessionRepository(get_engine())
        self.user_repo = UserRepository(get_engine())

    def overview(self) -> dict:
        return {
            "admins": self.admin_repo.count_admins(),
            "active_admins": self.admin_repo.count_active(),
            "users": self.user_repo.count_users(),
            "active_users": self.user_repo.count_active(),
            "banned_users": self.user_repo.count_banned(),
            "cases": self.case_repo.count_cases(),
            "case_status": self.case_repo.count_by_status(),
            "evidence": self.ev_repo.count_all(),
            "audit": self.audit_repo.count_all(),
            "sessions": self.session_repo.count_active(),
        }


stats_service = StatsService()

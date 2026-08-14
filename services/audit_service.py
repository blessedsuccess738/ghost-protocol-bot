"""services/audit_service.py — audit trail facade."""
import logging
from typing import Optional
from database.connection import get_engine
from database.repositories.audit_repo import AuditRepository

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self):
        self.repo = AuditRepository(get_engine())

    def log(self, admin_telegram_id: int | None, action: str, details: dict | None = None,
            severity: str = "info", ip: str | None = None, user_agent: str | None = None,
            session_id: str | None = None) -> None:
        from database.repositories.admin_repo import AdminRepository
        admin_id = None
        if admin_telegram_id is not None:
            admin = AdminRepository(get_engine()).get_by_telegram_id(admin_telegram_id)
            admin_id = admin.id if admin else None
        try:
            self.repo.add(admin_id=admin_id, action=action, details=details or {},
                          ip_address=ip, user_agent=user_agent, session_id=session_id,
                          severity=severity)
        except Exception as exc:
            logger.error("Audit log failed: %s", exc)


# module-level singleton for convenience
import functools


class _Singleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


class AuditServiceSingleton(AuditService, _Singleton):
    pass


audit_service = AuditServiceSingleton()

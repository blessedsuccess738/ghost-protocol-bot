"""services/search_service.py — search facade over users/cases/admins."""
import logging

from database.connection import get_engine
from database.repositories.admin_repo import AdminRepository
from database.repositories.case_repo import CaseRepository
from database.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(self):
        self.user_repo = UserRepository(get_engine())
        self.case_repo = CaseRepository(get_engine())
        self.admin_repo = AdminRepository(get_engine())

    def search_users(self, query: str, page: int = 1, per_page: int = 10):
        return self.user_repo.list_users(page=page, per_page=per_page, search=query)

    def search_cases(self, query: str, page: int = 1, per_page: int = 10):
        return self.case_repo.list_cases(page=page, per_page=per_page, search=query)

    def search_admins(self, query: str, page: int = 1, per_page: int = 10):
        return self.admin_repo.list_admins(page=page, per_page=per_page, search=query)


search_service = SearchService()

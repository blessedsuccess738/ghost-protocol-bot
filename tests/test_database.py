import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Base
from database.connection import get_engine, init_db
from database.repositories.admin_repo import AdminRepository
from database.repositories.user_repo import UserRepository
from database.repositories.case_repo import CaseRepository
from database.repositories.settings_repo import SettingsRepository


class DatabaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_schema_creation(self):
        from sqlalchemy import inspect
        inspector = inspect(get_engine())
        tables = set(inspector.get_table_names())
        for t in ("admins", "cases", "evidence", "users", "coin_transactions",
                  "referrals", "ban_records", "force_group_settings", "audit_logs"):
            self.assertIn(t, tables, f"table {t} missing")

    def test_admin_repo(self):
        repo = AdminRepository(get_engine())
        admin = repo.get_or_create(123456789)
        self.assertIsNotNone(admin.id)
        self.assertEqual(repo.get_by_telegram_id(123456789).id, admin.id)

    def test_user_repo(self):
        repo = UserRepository(get_engine())
        user = repo.get_or_create(987654321, "tester", "Test User")
        self.assertIsNotNone(user.referral_code)
        self.assertEqual(user.coins, 0)
        balance = repo.add_coins(user, 50)
        self.assertEqual(balance, 50)

    def test_case_repo_generates_gp_id(self):
        repo = CaseRepository(get_engine())
        case = repo.create(target_link="https://t.me/scamchannel", reason="Scam/Fraud")
        self.assertTrue(case.case_id.startswith("GP-"))
        self.assertEqual(case.status, "PENDING")

    def test_settings_defaults(self):
        repo = SettingsRepository(get_engine())
        repo.ensure_defaults()
        self.assertIsNotNone(repo.get("referral.reward"))
        self.assertTrue(repo.get_bool("referral.enabled", True))


if __name__ == "__main__":
    unittest.main()

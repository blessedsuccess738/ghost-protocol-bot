"""
tests/test_repositories.py — Smoke tests for DB init + repositories + exports.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Fresh temp DB for each run (avoids stale schema from prior versions)
_TEST_DB = os.path.join(tempfile.gettempdir(), "test_ghost_protocol.db")
if os.path.exists(_TEST_DB):
    os.remove(_TEST_DB)
os.environ["DATABASE_PATH"] = _TEST_DB
os.environ["SECRET_KEY"] = "test-secret"
os.environ["JWT_SECRET"] = "test-jwt"
os.environ["ENCRYPTION_KEY"] = "test-encryption-key"

from database.connection import get_engine, init_db, dispose_engine
from database.repositories.admin_repo import AdminRepository
from database.repositories.case_repo import CaseRepository
from database.repositories.evidence_repo import EvidenceRepository
from database.repositories.rate_limit_repo import RateLimitRepository
from services.export_service import ExportService


class TestDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    @classmethod
    def tearDownClass(cls):
        dispose_engine()

    def test_admin_crud(self):
        repo = AdminRepository(get_engine())
        admin = repo.get_or_create(999000111, "tester")
        self.assertEqual(admin.telegram_id, 999000111)
        token = repo.start_email_verification(admin, "tester@example.com")
        self.assertTrue(token)
        self.assertTrue(repo.verify_email_token(admin, token))
        self.assertEqual(repo.get_by_email("tester@example.com").email_verified, 1)

    def test_case_flow(self):
        admin_repo = AdminRepository(get_engine())
        case_repo = CaseRepository(get_engine())
        ev_repo = EvidenceRepository(get_engine())

        admin = admin_repo.get_or_create(999000222, "casemaker")
        case = case_repo.create(
            admin_id=admin.id,
            target_link="https://t.me/fake_scam",
            reason="Scam/Fraud",
            description="Test case",
        )
        self.assertTrue(case.case_id.startswith("GP-"))
        ev_repo.add(case.id, "message_link", "https://t.me/fake_scam/123")
        self.assertEqual(ev_repo.count_for_case(case.id), 1)
        case_repo.update_status(case, "Ready for Submission")
        self.assertEqual(case_repo.get_by_case_id(case.case_id).status, "Ready for Submission")

    def test_rate_limit(self):
        repo = RateLimitRepository(get_engine())
        repo.record(777, "login")
        self.assertGreaterEqual(repo.count_in_window(777, "login", 60), 1)

    def test_export_json(self):
        path = ExportService().export_json()
        self.assertTrue(os.path.isfile(path))
        os.remove(path)


if __name__ == "__main__":
    unittest.main()

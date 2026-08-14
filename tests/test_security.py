import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import security


class SecurityTest(unittest.TestCase):
    def test_encrypt_decrypt_roundtrip(self):
        plain = "secret-value-123"
        enc = security.encrypt_text(plain)
        self.assertTrue(enc)
        self.assertEqual(security.decrypt_text(enc), plain)

    def test_hash_string_deterministic(self):
        h1 = security.hash_string("abc")
        h2 = security.hash_string("abc")
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, security.hash_string("abd"))

    def test_constant_time_equals(self):
        self.assertTrue(security.constant_time_equals("token", "token"))
        self.assertFalse(security.constant_time_equals("token", "other"))

    def test_generate_case_id(self):
        self.assertEqual(security.generate_case_id(seq=1), "GP-000001")
        self.assertEqual(security.generate_case_id(seq=124), "GP-000124")

    def test_create_and_decode_session_token(self):
        token = security.create_session_token(1, 123456, "ADMIN")
        payload = security.decode_session_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["telegram_id"], 123456)
        self.assertEqual(payload["role"], "ADMIN")


if __name__ == "__main__":
    unittest.main()

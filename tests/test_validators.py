"""
tests/test_validators.py — Smoke tests for input validators + formatters + security.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.validators import (
    is_valid_email,
    is_valid_telegram_link,
    is_valid_message_link,
    is_valid_description,
    is_valid_screenshot_size,
    parse_target,
)
from core.security import (
    encrypt_text,
    decrypt_text,
    generate_token,
    generate_case_id,
    create_session_token,
    decode_session_token,
)


class TestValidators(unittest.TestCase):
    def test_email(self):
        self.assertTrue(is_valid_email("admin@example.com"))
        self.assertFalse(is_valid_email("not-an-email"))
        self.assertFalse(is_valid_email(""))

    def test_telegram_links(self):
        self.assertTrue(is_valid_telegram_link("https://t.me/username"))
        self.assertTrue(is_valid_telegram_link("@username"))
        self.assertTrue(is_valid_telegram_link("https://telegram.me/username"))
        self.assertTrue(is_valid_telegram_link("username"))
        self.assertFalse(is_valid_telegram_link("https://example.com/foo"))

    def test_message_links(self):
        self.assertTrue(is_valid_message_link("https://t.me/channel/12345"))
        self.assertFalse(is_valid_message_link("https://t.me/channel"))

    def test_parse_target(self):
        link, ttype, name = parse_target("@scam_channel")
        self.assertEqual(link, "https://t.me/scam_channel")
        self.assertEqual(name, "scam_channel")

    def test_description_limit(self):
        self.assertTrue(is_valid_description("short"))
        self.assertFalse(is_valid_description("x" * 1001))

    def test_screenshot_size(self):
        self.assertTrue(is_valid_screenshot_size(5 * 1024 * 1024))
        self.assertFalse(is_valid_screenshot_size(25 * 1024 * 1024))


class TestSecurity(unittest.TestCase):
    def test_encrypt_roundtrip(self):
        secret = "sensitive-data-123"
        cipher = encrypt_text(secret)
        self.assertNotEqual(cipher, secret)
        self.assertEqual(decrypt_text(cipher), secret)

    def test_token(self):
        self.assertTrue(len(generate_token()) >= 20)

    def test_case_id(self):
        cid = generate_case_id(seq=42)
        self.assertEqual(cid, "GP-000042")

    def test_jwt(self):
        token = create_session_token(1, 7590603733, "ADMIN")
        payload = decode_session_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["role"], "ADMIN")


if __name__ == "__main__":
    unittest.main()

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.validators import (is_valid_email, is_valid_telegram_link, is_valid_message_link,
                              parse_target, is_valid_description)


class ValidatorTest(unittest.TestCase):
    def test_emails(self):
        self.assertTrue(is_valid_email("admin@example.com"))
        self.assertFalse(is_valid_email("not-an-email"))
        self.assertFalse(is_valid_email(""))

    def test_telegram_links(self):
        self.assertTrue(is_valid_telegram_link("https://t.me/somechannel"))
        self.assertTrue(is_valid_telegram_link("@someuser"))
        self.assertTrue(is_valid_telegram_link("t.me/abcde"))
        self.assertFalse(is_valid_telegram_link("https://google.com"))
        self.assertFalse(is_valid_telegram_link("short"))

    def test_message_links(self):
        self.assertTrue(is_valid_message_link("https://t.me/somechannel/12345"))
        self.assertFalse(is_valid_message_link("https://t.me/somechannel"))

    def test_parse_target(self):
        link, ttype, name = parse_target("https://t.me/mychannel")
        self.assertEqual(link, "https://t.me/mychannel")
        self.assertIn(ttype, ("channel", "group", "user"))
        self.assertEqual(name, "mychannel")

    def test_description_limit(self):
        self.assertTrue(is_valid_description("x" * 100))
        self.assertFalse(is_valid_description("x" * 1001))


if __name__ == "__main__":
    unittest.main()

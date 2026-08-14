#!/usr/bin/env python3
"""
bot.py — Entry point for 『𝑮𝑷』 𝑮𝑯𝑶𝑺𝑻 𝑷𝑹𝑶𝑻𝑶𝑪𝑶𝑳 BOT.

Usage:
    python3 bot.py
"""
import logging

import config
from core.application import build_application
from utils.logger import setup_logging

logger = logging.getLogger(__name__)


def main() -> None:
    setup_logging()
    logger.info("Starting %s v%s (%s)...", config.BOT_NAME, config.BOT_VERSION, config.BOT_ENTERPRISE)
    app = build_application()
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()

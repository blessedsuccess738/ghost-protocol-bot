"""utils/logger.py — logging setup (console + rotating file)."""
import logging
import os
from logging.handlers import RotatingFileHandler

import config
from utils.helpers import ensure_dir


def setup_logging(level: str | None = None) -> None:
    level = level or config.LOG_LEVEL
    root = logging.getLogger()
    if root.handlers:
        return
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)
    ensure_dir(config.LOG_DIR)
    try:
        file_handler = RotatingFileHandler(
            os.path.join(config.LOG_DIR, "ghost_protocol.log"),
            maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)
    except OSError:
        pass

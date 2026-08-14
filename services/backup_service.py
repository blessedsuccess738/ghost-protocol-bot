"""services/backup_service.py — periodic database backup."""
import logging
import os
import shutil
from datetime import datetime

import config
from utils.helpers import ensure_dir

logger = logging.getLogger(__name__)


class BackupService:
    def __init__(self):
        self.backup_dir = config.BACKUP_DIR
        ensure_dir(self.backup_dir)

    def backup(self) -> str | None:
        if not os.path.isfile(config.DATABASE_PATH):
            logger.warning("No database file to back up")
            return None
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(self.backup_dir, f"ghost_protocol_{stamp}.db")
        shutil.copy2(config.DATABASE_PATH, dest)
        logger.info("Database backed up to %s", dest)
        self._cleanup()
        return dest

    def _cleanup(self, keep: int = 7) -> None:
        try:
            files = sorted(
                f for f in os.listdir(self.backup_dir) if f.startswith("ghost_protocol_") and f.endswith(".db"))
            for old in files[:-keep]:
                os.remove(os.path.join(self.backup_dir, old))
        except OSError as exc:
            logger.error("Backup cleanup failed: %s", exc)

    def list_backups(self) -> list[str]:
        try:
            return sorted(os.listdir(self.backup_dir))
        except OSError:
            return []


backup_service = BackupService()

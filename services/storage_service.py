"""services/storage_service.py — Secure local file storage for evidence uploads."""
import logging
import os
import uuid

import config
from core import security
from utils.helpers import ensure_dir, sha256_file

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


class StorageService:
    def __init__(self, base_dir: str | None = None):
        self.base_dir = base_dir or config.STORAGE_DIR
        ensure_dir(self.base_dir)

    def _safe_name(self, original: str) -> str:
        ext = os.path.splitext(original or "")[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            ext = ".bin"
        return f"{uuid.uuid4().hex}{ext}"

    def save_bytes(self, data: bytes, original_name: str = "evidence.bin") -> dict:
        fname = self._safe_name(original_name)
        path = os.path.join(self.base_dir, fname)
        with open(path, "wb") as f:
            f.write(data)
        return {"path": path, "filename": fname, "size": len(data),
                "hash": sha256_file(path), "type": os.path.splitext(fname)[1].lstrip(".")}

    def save_telegram_file(self, file, original_name: str = "evidence.bin") -> dict | None:
        try:
            data = file.download_as_bytearray()
            if not data:
                logger.error("Empty file download")
                return None
            return self.save_bytes(bytes(data), original_name)
        except Exception as exc:
            logger.error("Failed to save telegram file: %s", exc, exc_info=True)
            return None

    def exists(self, filename: str) -> bool:
        safe = os.path.basename(filename)
        return os.path.isfile(os.path.join(self.base_dir, safe))

    def get_path(self, filename: str) -> str | None:
        safe = os.path.basename(filename)
        path = os.path.join(self.base_dir, safe)
        return path if os.path.isfile(path) else None

    def delete(self, filename: str) -> bool:
        safe = os.path.basename(filename)
        path = os.path.join(self.base_dir, safe)
        try:
            os.remove(path)
            return True
        except OSError:
            return False


storage_service = StorageService()

import base64
import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.fernet import Fernet

import config

logger = logging.getLogger(__name__)


def _fernet_key() -> bytes:
    digest = hashlib.sha256(config.ENCRYPTION_KEY.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)

_fernet = Fernet(_fernet_key())


def encrypt_text(plaintext: str) -> str:
    if not plaintext:
        return ""
    try:
        return _fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")
    except Exception as exc:
        logger.error("Encryption failed: %s", exc, exc_info=True)
        return ""


def decrypt_text(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        return _fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except Exception as exc:
        logger.error("Decryption failed: %s", exc, exc_info=True)
        return ""


def hash_string(value: str) -> str:
    if not value:
        return ""
    salt = config.SECRET_KEY.encode("utf-8")
    return hmac.new(salt, value.encode("utf-8"), hashlib.sha256).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(str(a or ""), str(b or ""))


def generate_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def generate_verification_token() -> str:
    return secrets.token_urlsafe(32)


def generate_case_id(year: int | None = None, seq: int = 1) -> str:
    return f"GP-{seq:06d}"


def create_session_token(admin_id: int, telegram_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(admin_id), "telegram_id": telegram_id, "role": role,
                "iat": now, "exp": now + timedelta(seconds=config.JWT_EXPIRY)}
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def decode_session_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        logger.info("JWT expired")
        return None
    except jwt.InvalidTokenError as exc:
        logger.info("Invalid JWT: %s", exc)
        return None


def generate_encryption_key() -> str:
    return Fernet.generate_key().decode("utf-8")

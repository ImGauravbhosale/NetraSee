"""Symmetric encryption for connection credentials (e.g. GitHub PATs) at
rest. Fernet (AES-128-CBC + HMAC) rather than hashing — unlike a password,
the plaintext token must be recoverable to call the provider's API."""
from __future__ import annotations

from cryptography.fernet import Fernet

from app.core.config import settings

_fernet = Fernet(settings.connection_encryption_key.encode("utf-8"))


def encrypt_secret(plain: str) -> str:
    return _fernet.encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    return _fernet.decrypt(token.encode("utf-8")).decode("utf-8")

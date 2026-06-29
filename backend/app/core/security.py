"""Secret encryption helpers.

BYO-keys principle: API keys (Anthropic, Firecrawl, Ahrefs, ...) are supplied by
the tenant via Settings and stored **encrypted at rest** using Fernet. The Fernet
key is derived deterministically from ``SECRET_KEY`` so the same master secret can
decrypt previously stored values across restarts.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _derive_fernet_key(secret: str) -> bytes:
    """Derive a urlsafe-base64 32-byte Fernet key from an arbitrary secret string."""
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


_fernet = Fernet(_derive_fernet_key(settings.SECRET_KEY))


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a plaintext secret, returning a urlsafe token string."""
    if plaintext is None:
        raise ValueError("Cannot encrypt None")
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    """Decrypt a token produced by :func:`encrypt_secret`."""
    try:
        return _fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:  # pragma: no cover - defensive
        raise ValueError("Could not decrypt secret (wrong SECRET_KEY?)") from exc


def mask_secret(plaintext: str, visible: int = 4) -> str:
    """Return a masked preview (e.g. ``****abcd``) safe to send to the client."""
    if not plaintext:
        return ""
    if len(plaintext) <= visible:
        return "*" * len(plaintext)
    return "*" * (len(plaintext) - visible) + plaintext[-visible:]

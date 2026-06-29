"""BYO API keys, stored encrypted at rest (Fernet)."""

from __future__ import annotations

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.security import decrypt_secret, encrypt_secret, mask_secret
from app.db.base import Base, TimestampMixin


class ApiKey(Base, TimestampMixin):
    """One row per provider (anthropic | firecrawl | ahrefs | ...).

    The plaintext key is never stored — only the Fernet ciphertext.
    """

    __tablename__ = "api_keys"
    __table_args__ = (UniqueConstraint("provider", name="uq_api_keys_provider"),)

    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)

    @classmethod
    def from_plaintext(cls, provider: str, value: str, label: str | None = None) -> ApiKey:
        return cls(provider=provider, label=label, encrypted_value=encrypt_secret(value))

    def set_value(self, value: str) -> None:
        self.encrypted_value = encrypt_secret(value)

    @property
    def value(self) -> str:
        """Decrypted plaintext — only use server-side, never serialize to client."""
        return decrypt_secret(self.encrypted_value)

    @property
    def masked(self) -> str:
        return mask_secret(self.value)

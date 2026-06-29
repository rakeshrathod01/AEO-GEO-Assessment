"""Tenant + User models for multi-tenant isolation.

A Tenant is the isolation boundary: projects and BYO API keys belong to a tenant,
and every request resolves to exactly one tenant. Users authenticate into a tenant.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"
DEFAULT_TENANT_SLUG = "default"


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)

    users: Mapped[list[User]] = relationship(back_populates="tenant", cascade="all, delete-orphan")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default=ROLE_ADMIN)

    tenant: Mapped[Tenant] = relationship(back_populates="users")

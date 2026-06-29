"""Project = a client target site plus its tracked competitors."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    competitors: Mapped[list["Competitor"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class Competitor(Base, TimestampMixin):
    """3–5 competitors are compared against the target on comparable pages."""

    __tablename__ = "competitors"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)

    project: Mapped["Project"] = relationship(back_populates="competitors")

"""Target prompts (module 7) grouped into intent buckets.

Generated from Ahrefs PAA/snippet queries + crawled content; consumed by the GEO
Audit (module 8) which queries each prompt across the AI assistants.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

# Intent buckets.
INTENT_INFORMATIONAL = "informational"
INTENT_COMMERCIAL = "commercial"
INTENT_TRANSACTIONAL = "transactional"
INTENT_NAVIGATIONAL = "navigational"
INTENT_COMPARISON = "comparison"
INTENT_BUCKETS = [
    INTENT_INFORMATIONAL,
    INTENT_COMMERCIAL,
    INTENT_TRANSACTIONAL,
    INTENT_NAVIGATIONAL,
    INTENT_COMPARISON,
]


class Prompt(Base, TimestampMixin):
    __tablename__ = "prompts"
    __table_args__ = (
        UniqueConstraint("project_id", "text", name="uq_prompt_project_text"),
    )

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(String(1024), nullable=False)
    intent_bucket: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # paa | featured | content | template | llm
    source: Mapped[str] = mapped_column(String(32), default="template")

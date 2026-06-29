"""Create all tables (local-first bootstrap).

For production migrations use Alembic; for local/SQLite this create_all is enough.
"""

from __future__ import annotations

# Importing the models package registers every table on Base.metadata.
import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import engine


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Database initialized.")

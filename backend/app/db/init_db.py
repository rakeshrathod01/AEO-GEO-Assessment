"""Create all tables (local-first bootstrap).

For production migrations use Alembic; for local/SQLite this create_all is enough.
"""

from __future__ import annotations

from app.db.base import Base
from app.db.session import engine

# Importing the models package registers every table on Base.metadata.
import app.models  # noqa: F401


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Database initialized.")

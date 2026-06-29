from app.db.session import SessionLocal
from app.services.benchmarks import get_benchmark, seed_default_benchmarks


def test_seed_is_idempotent():
    db = SessionLocal()
    try:
        first = seed_default_benchmarks(db)
        assert first > 0
        second = seed_default_benchmarks(db)
        assert second == 0  # nothing added the second time
    finally:
        db.close()


def test_get_benchmark_carries_source():
    db = SessionLocal()
    try:
        b = get_benchmark(db, "title_length_max")
        assert b is not None
        assert b.value == 60
        assert "Moz" in b.source
    finally:
        db.close()


def test_unknown_benchmark_returns_none():
    db = SessionLocal()
    try:
        assert get_benchmark(db, "does_not_exist") is None
    finally:
        db.close()

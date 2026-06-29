"""ORM models. Import all here so Base.metadata.create_all() sees them."""

from app.models.analysis import AnalysisRun  # noqa: F401
from app.models.api_cache import ApiCache  # noqa: F401
from app.models.benchmark_source import BenchmarkSource  # noqa: F401
from app.models.project import Competitor, Project  # noqa: F401
from app.models.setting import ApiKey  # noqa: F401

__all__ = [
    "AnalysisRun",
    "ApiCache",
    "ApiKey",
    "BenchmarkSource",
    "Competitor",
    "Project",
]

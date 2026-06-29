"""Raw HTML disk storage.

Raw HTML is kept on disk (cleaned text + signals live in the DB) under
``RAW_HTML_DIR/<project_id>/<job_id>/<sha1(url)>.html``.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.core.config import settings


def url_hash(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def save_raw_html(project_id: int, job_id: int, url: str, html: str) -> str:
    """Persist raw HTML and return the relative path stored on the Page row."""
    base = Path(settings.RAW_HTML_DIR) / str(project_id) / str(job_id)
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{url_hash(url)}.html"
    path.write_text(html or "", encoding="utf-8")
    return str(path)

"""Map module keys to analyzers. Modules land here as their phase implements them."""

from __future__ import annotations

from app.services.analysis import on_page, technical_seo

ANALYZERS = {
    technical_seo.MODULE: technical_seo.analyze,
    on_page.MODULE: on_page.analyze,
}


def get_analyzer(module_key: str):
    return ANALYZERS.get(module_key)

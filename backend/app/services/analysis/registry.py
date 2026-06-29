"""Map module keys to analyzers. Modules land here as their phase implements them."""

from __future__ import annotations

from app.services.analysis import (
    backlinks,
    internal_linking,
    keyword_universe,
    on_page,
    technical_seo,
)

ANALYZERS = {
    technical_seo.MODULE: technical_seo.analyze,
    on_page.MODULE: on_page.analyze,
    internal_linking.MODULE: internal_linking.analyze,
    backlinks.MODULE: backlinks.analyze,
    keyword_universe.MODULE: keyword_universe.analyze,
}


def get_analyzer(module_key: str):
    return ANALYZERS.get(module_key)

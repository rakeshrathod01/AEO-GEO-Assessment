"""Map module keys to analyzers. Modules land here as their phase implements them."""

from __future__ import annotations

from app.services.analysis import (
    aeo_audit,
    backlinks,
    geo_audit,
    internal_linking,
    keyword_universe,
    on_page,
    prompt_identification,
    technical_seo,
)

ANALYZERS = {
    technical_seo.MODULE: technical_seo.analyze,
    on_page.MODULE: on_page.analyze,
    internal_linking.MODULE: internal_linking.analyze,
    backlinks.MODULE: backlinks.analyze,
    keyword_universe.MODULE: keyword_universe.analyze,
    aeo_audit.MODULE: aeo_audit.analyze,
    prompt_identification.MODULE: prompt_identification.analyze,
    geo_audit.MODULE: geo_audit.analyze,
}


def get_analyzer(module_key: str):
    return ANALYZERS.get(module_key)

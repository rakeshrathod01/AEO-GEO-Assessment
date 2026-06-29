"""Canonical registry of the 9 assessment modules (sidebar order).

Backend and frontend both derive from this list so naming stays consistent.
Each module gets a real analyzer in its dedicated phase; for now the registry
drives routing and the (placeholder) module endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel


class ModuleMeta(BaseModel):
    key: str
    order: int
    title: str
    layer: str  # SEO | AEO | GEO | Leadership
    phase: int  # build-order phase that implements it


MODULES: list[ModuleMeta] = [
    ModuleMeta(key="technical_seo", order=1, title="Technical SEO", layer="SEO", phase=2),
    ModuleMeta(key="on_page", order=2, title="On-Page SEO", layer="SEO", phase=2),
    ModuleMeta(key="internal_linking", order=3, title="Internal Linking", layer="SEO", phase=3),
    ModuleMeta(key="backlinks", order=4, title="Backlinks", layer="SEO", phase=3),
    ModuleMeta(key="keyword_universe", order=5, title="Keyword Universe", layer="SEO", phase=3),
    ModuleMeta(key="aeo_audit", order=6, title="AEO Audit", layer="AEO", phase=4),
    ModuleMeta(
        key="prompt_identification", order=7, title="Prompt Identification", layer="GEO", phase=5
    ),
    ModuleMeta(key="geo_audit", order=8, title="GEO Audit", layer="GEO", phase=5),
    ModuleMeta(
        key="leadership", order=9, title="Leadership Dashboard", layer="Leadership", phase=6
    ),
]

MODULE_KEYS = {m.key for m in MODULES}


def get_module(key: str) -> ModuleMeta | None:
    return next((m for m in MODULES if m.key == key), None)

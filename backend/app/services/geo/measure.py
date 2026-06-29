"""Brand mention / citation / position detection in a GEO response."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


def domain_of(url: str) -> str:
    net = urlparse(url if "//" in url else "https://" + url).netloc.lower()
    if not net:
        net = (url or "").lower()
    return net[4:] if net.startswith("www.") else net


def _domain_match(cited: str, domain: str) -> bool:
    return cited == domain or cited.endswith("." + domain) or (
        domain != "" and domain in cited
    )


@dataclass
class Hit:
    mentioned: bool
    cited: bool
    position: int | None  # 1-based rank in the response's cited domains


def detect(text: str, domains: list[str], brand: str, domain: str) -> Hit:
    """Detect a brand by name (in text) and by domain (in the cited domains)."""
    text_l = (text or "").lower()
    mentioned_by_name = bool(brand) and brand.lower() in text_l
    position = None
    cited = False
    for i, d in enumerate(domains, start=1):
        if domain and _domain_match(d, domain):
            cited = True
            position = i
            break
    return Hit(
        mentioned=mentioned_by_name or cited,
        cited=cited,
        position=position,
    )

"""E-E-A-T (Experience, Expertise, Authoritativeness, Trust) + content structure.

Detection is heuristic + deterministic so it runs without an API key. When an
Anthropic key is configured, Haiku refines the flags (extraction tier) from the
cleaned page text — Haiku is the cheapest tier and this is a classification task.
"""

from __future__ import annotations

import re

_AUTHOR_RE = re.compile(r"\b(by|written by|author|reviewed by|edited by)\b[:\s]", re.IGNORECASE)
_CREDENTIAL_RE = re.compile(
    r"\b(ph\.?d|m\.?d|expert|certified|accredited|fellow|years of experience|board[- ]certified)\b",
    re.IGNORECASE,
)
_CITATION_RE = re.compile(
    r"(according to|source:|references?\b|\[\d+\]|cited|study|research|survey)", re.IGNORECASE
)
_DATE_RE = re.compile(r"\b(20\d{2})\b|\b(updated|published|last modified)\b", re.IGNORECASE)
_TRUST_RE = re.compile(
    r"\b(about us|contact us|privacy policy|terms|testimonials?|reviews?|trusted by|customers?)\b",
    re.IGNORECASE,
)

EEAT_FLAGS = ["has_author", "has_credentials", "has_citations", "has_dates", "has_trust_signals"]


def detect_eeat(cleaned_text: str, signals: dict, llm=None) -> dict:
    """Return E-E-A-T flags + a 0..1 score and a structure assessment."""
    text = cleaned_text or ""
    flags = {
        "has_author": bool(_AUTHOR_RE.search(text)),
        "has_credentials": bool(_CREDENTIAL_RE.search(text)),
        "has_citations": bool(_CITATION_RE.search(text)) or (signals.get("external_links", 0) >= 3),
        "has_dates": bool(_DATE_RE.search(text)),
        "has_trust_signals": bool(_TRUST_RE.search(text)),
    }

    # Optional Haiku refinement (extraction tier).
    if llm is not None and getattr(llm, "enabled", False):
        refined = _llm_refine(llm, text)
        if refined:
            for k in EEAT_FLAGS:
                if k in refined:
                    flags[k] = bool(refined[k])

    score = round(sum(1 for v in flags.values() if v) / len(EEAT_FLAGS), 4)

    # Content structure from extracted signals.
    h1 = signals.get("h1_count", 0)
    h2 = signals.get("h2_count", 0)
    structure_ok = h1 == 1 and h2 >= 1
    return {"flags": flags, "score": score, "structure_ok": structure_ok}


def _llm_refine(llm, text: str) -> dict | None:
    system = (
        "You are an SEO content analyst. Classify the page text for E-E-A-T signals. "
        "Respond ONLY with compact JSON having boolean keys: "
        "has_author, has_credentials, has_citations, has_dates, has_trust_signals."
    )
    from app.core.config import settings

    user = f"PAGE TEXT (truncated):\n{text[: settings.LLM_TEXT_CHAR_LIMIT]}"
    return llm.extract_json(system, user, max_tokens=200)

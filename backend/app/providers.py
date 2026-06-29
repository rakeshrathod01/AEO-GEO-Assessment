"""Catalog of BYO provider credentials managed in Settings.

Single source of truth for which providers exist, whether they're required, and
whether the stored value is a secret (masked on read) or a URL (config, returned
in full). Backend routes and the frontend Settings page both derive from this.
"""

from __future__ import annotations

from pydantic import BaseModel


class ProviderMeta(BaseModel):
    key: str
    label: str
    kind: str  # "secret" | "url"
    required: bool
    group: str  # "core" | "optional_llm"
    help: str | None = None


PROVIDERS: list[ProviderMeta] = [
    ProviderMeta(
        key="ahrefs_mcp_url",
        label="Ahrefs MCP URL",
        kind="url",
        required=True,
        group="core",
        help="Base URL of the Ahrefs MCP server used for keywords/backlinks pulls.",
    ),
    ProviderMeta(
        key="firecrawl",
        label="Firecrawl API Key",
        kind="secret",
        required=True,
        group="core",
        help="Primary crawler. Playwright-stealth is the fallback.",
    ),
    ProviderMeta(
        key="anthropic",
        label="Anthropic API Key",
        kind="secret",
        required=True,
        group="core",
        help="Claude models (Haiku/Sonnet/Opus tiering).",
    ),
    ProviderMeta(
        key="openai",
        label="OpenAI API Key",
        kind="secret",
        required=False,
        group="optional_llm",
        help="Optional — used by the GEO audit (ChatGPT) module.",
    ),
    ProviderMeta(
        key="gemini",
        label="Google Gemini API Key",
        kind="secret",
        required=False,
        group="optional_llm",
        help="Optional — used by the GEO audit (Gemini) module.",
    ),
    ProviderMeta(
        key="perplexity",
        label="Perplexity API Key",
        kind="secret",
        required=False,
        group="optional_llm",
        help="Optional — used by the GEO audit (Perplexity) module.",
    ),
]

PROVIDERS_BY_KEY = {p.key: p for p in PROVIDERS}
SUPPORTED_PROVIDERS = set(PROVIDERS_BY_KEY)


def get_provider(key: str) -> ProviderMeta | None:
    return PROVIDERS_BY_KEY.get(key)

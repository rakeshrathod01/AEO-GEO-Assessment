# eClerx — SEO / AEO / GEO Enterprise Assessment Platform

A production, self-hostable, multi-tenant SaaS for enterprise **SEO**, **AEO**
(Answer Engine Optimization) and **GEO** (Generative Engine Optimization)
assessments. Local-first (SQLite) and cloud-ready (Postgres), BYO-keys, with
client-ready Excel/PDF/PPTX deliverables.

> **Build status:** Phase 0 (scaffold) + Phase 1 (ingestion pipeline) complete.
> Modules 1–9 land in later phases per the build order below.

---

## Principles (non-negotiable)

- **Local-first, cloud-ready** — SQLite by default; set `DATABASE_URL` to a
  Postgres DSN to swap with zero code changes.
- **BYO-keys** — no hardcoded credentials. Provider keys (Anthropic, Firecrawl,
  Ahrefs) are entered in **Settings** and stored **encrypted at rest (Fernet)**.
- **Two scopes everywhere** — every analysis runs at whole-site (top-50 pages)
  and single-page scope.
- **Competitors** — every module compares the client target against 3–5
  competitors on comparable pages.
- **Cached externals** — every external API call is cached in the DB; Ahrefs
  pulls use a trailing 6-month window.
- **Cited benchmarks** — industry benchmarks always carry a source, persisted in
  `benchmark_sources` and reused (never re-derived).

## Tech stack

| Layer     | Tech |
|-----------|------|
| Backend   | FastAPI, Celery, Redis, SQLAlchemy 2, Pydantic v2, SQLite/Postgres |
| Frontend  | React + Vite + TypeScript, Tailwind, Recharts, TanStack Query/Table |
| Crawl     | Firecrawl (primary), Playwright-stealth fallback |
| Data      | Ahrefs MCP client (keywords/links) |
| AI        | Anthropic SDK with model switcher (Haiku → Sonnet → Opus tiering) |
| Exports   | openpyxl (Excel), reportlab (PDF), python-pptx (deck) |

### Model tiering (cost control)

| Model | Use |
|-------|-----|
| `claude-haiku-4-5`  | HTML/text extraction, schema detection, classification |
| `claude-sonnet-4-6` | per-module analysis + recommendations |
| `claude-opus-4-8`   | leadership synthesis + cross-module prioritization only |

---

## Repository layout

```
.
├── backend/                 FastAPI app
│   ├── app/
│   │   ├── core/            config, Fernet security, Celery
│   │   ├── db/              SQLAlchemy base / session / init
│   │   ├── models/          projects, api_keys, benchmark_sources, api_cache, analysis
│   │   ├── schemas/         the shared DATA CONTRACT + request/response models
│   │   ├── services/        external-call cache helper
│   │   │   └── ingest/      sitemap, ranking, fetcher, extract, match, pipeline, progress
│   │   ├── api/routes/      health, settings, projects, modules, ingest
│   │   ├── providers.py     BYO credential catalog (Ahrefs MCP, Firecrawl, LLMs)
│   │   ├── modules_registry.py   the 9 modules (sidebar order)
│   │   └── main.py
│   ├── alembic/             migrations (env + initial schema)
│   └── tests/
├── frontend/                React + Vite app (dark navy/red theme)
│   ├── src/                 9-module sidebar, Dashboard, Settings, module routes
│   ├── Dockerfile           nginx static serve + /api proxy
│   └── nginx.conf
├── docker/
│   └── docker-compose.yml   api, worker, redis, frontend (cloud-ready)
├── Makefile                 common dev tasks
└── .env.example             every BYO key documented
```

### The data contract

Every module — at `site` and `page` scope — returns the same shape
(`backend/app/schemas/contract.py`):

```json
{
  "scope": "site|page", "target_url": "...", "score": 0-100,
  "status": "pass|warn|fail",
  "findings": [{ "signal", "status", "value", "benchmark", "source", "evidence" }],
  "recommendations": [{ "priority", "layer", "action", "how_to", "effort", "impact" }],
  "competitor_delta": [{ "competitor", "signal", "them", "us", "gap" }]
}
```

### The 9 modules (sidebar order)

1. Technical SEO 2. On-Page SEO 3. Internal Linking 4. Backlinks
5. Keyword Universe 6. AEO Audit 7. Prompt Identification 8. GEO Audit
9. Leadership Dashboard

### Ingestion pipeline (Phase 1)

Three input modes feed one pipeline (`app/services/ingest/`):

| Mode | Endpoint |
|------|----------|
| Sitemap URL (auto-ranks top-50) | `POST /api/v1/projects/{id}/ingest/sitemap` |
| Excel upload (URL column)       | `POST /api/v1/projects/{id}/ingest/excel` |
| Paste up to 50 URLs             | `POST /api/v1/projects/{id}/ingest/paste` |

Flow: **resolve URLs → rank → select top-50 → crawl → extract → store**.

- **Ranking heuristic** (`ranking.py`) scores by URL depth, money-page patterns
  (`/pricing`, `/demo`, `/solutions`, …), structural link prominence (hub pages),
  and sitemap `<priority>`, with penalties for assets/legal/tag/paginated URLs.
- **Crawl** uses **Firecrawl** first and falls back to **Playwright-stealth** when
  a result is blocked (403/429/503), shows a bot-challenge interstitial, or renders
  near-empty (JS-heavy). The decision is the pure function `fetcher.needs_fallback`.
- **Storage**: raw HTML → disk (`RAW_HTML_DIR`); cleaned text + on-page/technical
  signals → DB (`pages.signals_json`).
- **Competitors**: each tracked competitor is crawled on pages **comparable** to the
  client's 50 — by mirroring client paths onto the competitor domain, or by path
  similarity when a competitor sitemap is supplied (`competitor_match.py`).
- **Progress**: a Celery task streams progress; the UI consumes it via SSE
  (`GET /api/v1/crawl/jobs/{id}/stream`) with a DB snapshot fallback. Local-first
  runs execute inline (`INGEST_INLINE=true`) so no Redis/worker is required.

---

## Quickstart (local-first)

### Backend

```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # then set a strong SECRET_KEY
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs · health: http://localhost:8000/api/v1/health

### Frontend

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173 (proxies /api to :8000)
```

### Make targets

```bash
make backend-install   # venv + deps
make backend-dev       # uvicorn --reload
make backend-test      # pytest
make frontend-install
make frontend-dev
make frontend-build
```

### Database migrations (Alembic)

```bash
cd backend && . .venv/bin/activate
alembic upgrade head                         # apply migrations
alembic revision --autogenerate -m "change"  # generate a new migration
```

> The app also `create_all`s tables on startup for zero-config local runs; use
> Alembic for controlled schema changes in staging/production.

### Run with Docker (api + worker + redis + frontend)

```bash
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))") \
  docker compose -f docker/docker-compose.yml up --build
# frontend: http://localhost:5173   ·   api: http://localhost:8000
```

Postgres is included (commented) in the compose file — uncomment the service and
set `DATABASE_URL` to switch from the default SQLite volume.

---

## Testing

```bash
cd backend && . .venv/bin/activate && python -m pytest -q
```

Phase 0 covers: health/readiness, Fernet encrypt/decrypt/masking, the data
contract validation, BYO-key upsert/masking, the module registry, and project CRUD.

Phase 1 covers: URL normalization + paste/Excel parsing, sitemap (urlset +
index) parsing, the ranking heuristic, HTML signal extraction, the
Firecrawl→Playwright fallback decision, competitor matching, and the full
ingestion pipeline + API end-to-end with a fake fetcher (no network).

```bash
cd frontend && npm run build   # tsc type-check + production build
```

---

## Build order (one phase per session)

| Phase | Scope |
|-------|-------|
| **0** | **Scaffold: backend + frontend skeleton, data contract, DB models, BYO-key encryption, caching, tests, CI hook** ✅ |
| **1** | **Ingestion pipeline: sitemap/Excel/paste input, top-50 ranking, Firecrawl + Playwright-stealth fallback, signal extraction, competitor matching, Celery progress stream** ✅ |
| 2 | SEO modules (Technical, On-Page) |
| 3 | Ahrefs modules (Internal Linking, Backlinks, Keyword Universe) |
| 4 | AEO Audit |
| 5 | Prompt Identification + GEO Audit |
| 6 | Leadership Dashboard + exports |
| 7 | AEO/GEO pitch deck (25–30 slides) |
| 8 | Settings + deploy |

## Configuration

All config is environment-driven (`backend/app/core/config.py`). See
`.env.example`. Provider credentials are **not** environment variables — they are
managed in the Settings UI and encrypted at rest.

### BYO credentials (Settings page)

| Provider | Kind | Required | Used by |
|----------|------|----------|---------|
| Ahrefs MCP URL | url | ✅ | Internal Linking, Backlinks, Keyword Universe |
| Firecrawl API key | secret | ✅ | Crawler (primary) |
| Anthropic API key | secret | ✅ | All AI analysis (Haiku/Sonnet/Opus) |
| OpenAI API key | secret | optional | GEO audit (ChatGPT) |
| Gemini API key | secret | optional | GEO audit (Gemini) |
| Perplexity API key | secret | optional | GEO audit (Perplexity) |

Secret-kind values are returned only as a masked preview (`****abcd`); the
URL-kind value (Ahrefs MCP URL) is returned in full since it is configuration,
not a credential. The catalog is served at `GET /api/v1/settings/providers`.

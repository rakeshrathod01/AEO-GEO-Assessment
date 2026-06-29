# eClerx — SEO / AEO / GEO Enterprise Assessment Platform

A production, self-hostable, multi-tenant SaaS for enterprise **SEO**, **AEO**
(Answer Engine Optimization) and **GEO** (Generative Engine Optimization)
assessments. Local-first (SQLite) and cloud-ready (Postgres), BYO-keys, with
client-ready Excel/PDF/PPTX deliverables.

> **Build status: v1.0 — all phases complete.** Scaffold, ingestion, all nine
> modules (SEO 1–2, Ahrefs 3–5, AEO 6, Prompt Identification 7, GEO 8, Leadership
> Dashboard 9), master Excel + leadership PDF + pitch deck, and production hardening
> (JWT auth + multi-tenant isolation, per-provider external-call rate limiting,
> GitHub Actions CI, one-click deploy, and a seed/demo dataset).

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
│   │   ├── core/            config, Fernet security, Celery, auth (bcrypt + JWT)
│   │   ├── db/              SQLAlchemy base / session / init
│   │   ├── models/          tenants, users, projects, api_keys, crawl, analysis, prompt, geo
│   │   ├── schemas/         the shared DATA CONTRACT + request/response models
│   │   ├── seed.py          idempotent demo tenant + project + synthetic crawl
│   │   ├── services/        external-call cache + per-provider rate limiter + key resolver
│   │   │   ├── ingest/      sitemap, ranking, fetcher, extract, match, pipeline, progress
│   │   │   ├── analysis/    base, signals, eeat, internal_graph, aeo_features, technical_seo,
│   │   │   │                on_page, internal_linking, backlinks, keyword_universe, aeo_audit,
│   │   │   │                prompt_identification, geo_audit, leadership, runner, registry
│   │   │   ├── ahrefs/      Ahrefs MCP client (6-month window, cached)
│   │   │   ├── prompts/     module 7 prompt generator (intent buckets)
│   │   │   ├── geo/         module 8 swappable providers (api|serp) + brand matching
│   │   │   ├── llm/         Anthropic client + model tiering (Haiku/Sonnet/Opus)
│   │   │   ├── exports/     excel, pdf (+ radar), prompts, master (workbook), deck (pptx)
│   │   │   └── benchmarks.py  cited benchmark seeding + lookup
│   │   ├── api/
│   │   │   ├── deps.py      get_current_tenant / owned_project (tenant isolation)
│   │   │   └── routes/      health, auth, settings, projects, modules, ingest, analysis, leadership
│   │   ├── providers.py     BYO credential catalog (Ahrefs MCP, Firecrawl, LLMs)
│   │   ├── modules_registry.py   the 9 modules (sidebar order)
│   │   └── main.py
│   ├── alembic/             migrations (env + revisions)
│   ├── Procfile             web / worker / release process commands
│   └── tests/
├── deploy/                  render.yaml · fly.toml · railway.json (one-click)
├── .github/workflows/ci.yml ruff + migrations + pytest + frontend build
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

### SEO modules (Phase 2)

Modules **1 Technical SEO** and **2 On-Page SEO** analyze the latest crawl and
return the **data contract** (`ModuleResult`) at both `site` and `page` scope,
including `competitor_delta` against the tracked competitors.

```
POST /api/v1/projects/{id}/modules/{technical_seo|on_page}/analyze?scope=site|page
GET  /api/v1/projects/{id}/modules/{key}/export.xlsx?scope=site|page   # Excel
GET  /api/v1/projects/{id}/modules/{key}/report.pdf?scope=site|page    # PDF
```

- **Technical SEO**: indexability, canonical, HTTPS, mobile viewport, HTTP status
  health, structured-data presence, declared language.
- **On-Page SEO**: title/meta length, single-H1 + heading **structure**, content
  depth, image alt coverage, Open Graph, **schema** markup, and **E-E-A-T**
  signals (author, credentials, citations, dates, trust).
- **Scoring** is deterministic and weighted (pass=full / warn=half / fail=0); every
  finding carries a **cited benchmark** from `benchmark_sources` (seeded with
  Moz / Google Search Central / Backlinko citations, reused never re-derived).
- **Model tiering** (`app/services/llm`): **Haiku** refines E-E-A-T extraction
  (page scope), **Sonnet** upgrades recommendation how-to prose; calls are
  prompt-cached + DB-cached and **degrade gracefully to deterministic logic when
  no Anthropic key is set** — so the platform runs (and tests pass) without keys.
- **Exports**: every result has **Export Excel** (multi-sheet) and **Generate PDF**
  (font-11 wrap-text tables + an **industry-benchmark radar** with cited sources).

### Ahrefs modules (Phase 3)

The **Ahrefs MCP client** (`app/services/ahrefs/client.py`) pulls from the tenant's
Ahrefs MCP server (URL in Settings) using a **trailing 6-month window**, with every
call **cached** in `api_cache`. Missing/unreachable MCP → modules degrade to a
"configure Ahrefs" finding rather than failing.

- **3 Internal Linking** — builds an internal-link graph from the crawl's raw HTML:
  orphan pages, inbound/outbound distribution, click depth, and money-page links.
  (On-site, so crawl-derived; competitor delta uses crawl link counts.)
- **4 Backlinks** — Ahrefs Domain Rating, referring domains, total backlinks,
  dofollow ratio; competitor delta on DR / referring domains / backlinks.
- **5 Keyword Universe** — organic keywords: totals, top-3/top-10 share, traffic,
  striking-distance (pos 4-10) wins, SERP-feature coverage, and competitor keyword
  gaps. It also **persists PAA + featured-snippet conversational queries**
  (`serp_queries`, exposed at `GET /api/v1/projects/{id}/serp-queries`) as the seed
  set for Phase 5 (Prompt Identification / GEO).

All three return the data contract at site + page scope with `competitor_delta`
and the same Excel/PDF exports.

### AEO Audit (Phase 4)

Module **6 AEO Audit** scores how ready the crawled content is to be surfaced/cited
by AI answer engines, from an AEO feature pass over the raw HTML
(`app/services/analysis/aeo_features.py`):

- **AI Overview readiness** — concise lead answer + answer schema (FAQ/HowTo/Article)
  + question-led headings.
- **People Also Ask readiness** — question H2/H3 + FAQ schema, scored against the
  **PAA queries persisted in Phase 3** (coverage = share of tracked PAA questions the
  content addresses).
- **Knowledge Panel readiness** — Organization schema / entity signals.
- **Voice search readiness** — Speakable schema + conversational concise answers.
- **Answer-paragraph readiness** — a direct ~40-60 word answer near the top.
- **Content-structure readiness** — lists/tables for extractability.

Each finding carries a cited benchmark (Google Search Central, Backlinko). Returns
the data contract at site + page scope with `competitor_delta` and Excel/PDF exports.

### Prompt Identification + GEO Audit (Phase 5)

**Module 7 — Prompt Identification** generates ~60-70 target prompts from the
persisted PAA/featured-snippet queries (Phase 3) plus crawled content, grouped into
intent buckets (`informational`, `commercial`, `transactional`, `navigational`,
`comparison`). Prompts are persisted and exportable:

```
GET /api/v1/projects/{id}/prompts              # list (used by module 8)
GET /api/v1/projects/{id}/prompts/export.xlsx  # Prompt Targets report
GET /api/v1/projects/{id}/prompts/export.pdf
```

**Module 8 — GEO Audit** queries each target prompt across a **swappable
data-source layer** (`app/services/geo/providers.py`) and measures brand
**mention / citation / position** for the client vs competitors, per source:

| Provider | `source_kind` | Key |
|----------|---------------|-----|
| ChatGPT / Gemini / Claude / Perplexity | `api` | openai / gemini / anthropic / perplexity |
| Google AI Overview (SERP capture) | `serp` | firecrawl |

Every signal is **clearly flagged API vs SERP capture** (in findings evidence and
the persisted `geo_results.source_kind`). Providers read BYO keys, cache every
call, and degrade gracefully when unconfigured — adding/swapping a provider is a
one-line edit to `build_providers`. Per-prompt results: `GET /projects/{id}/geo-results`.
Cost is bounded by `GEO_MAX_PROMPTS` (sampling is disclosed in the result).

### Leadership Dashboard (Phase 6)

**Module 9** runs all eight modules at the requested scope and synthesizes one
**prioritized roadmap sequenced foundational SEO → AEO → GEO**. **Opus is used here
(and only here)** for cross-module prioritization + the executive summary, degrading
to deterministic ordering with no key.

```
POST /api/v1/projects/{id}/leadership?scope=site|page&page_id=   # synthesis
GET  /api/v1/projects/{id}/leadership/export.xlsx?scope=         # master workbook
GET  /api/v1/projects/{id}/leadership/report.pdf?scope=          # leadership PDF
GET  /api/v1/projects/{id}/pages                                 # page-selector source
```

- **Page-selector re-scoping** — pass `scope=page&page_id=…` to re-scope the entire
  dashboard (every module + roadmap) to a single page.
- **Benchmark markers with sourced tooltips** — the report carries every
  `benchmark_sources` entry (metric/value/unit + citation + URL); the dashboard
  renders each as a marker whose hover tooltip names the source.
- **Master Excel workbook** — Executive Summary tab + Module Scores, Roadmap, All
  Findings, All Recommendations, Competitor Delta, and Benchmarks tabs.
- **Leadership PDF** — honors the PDF table rules (font-11 wrap-text) and includes
  the industry-benchmark **radar** (client vs benchmark across readiness rates) with
  cited sources.

### AEO/GEO Pitch Deck (Phase 7)

`GET /api/v1/projects/{id}/leadership/deck.pptx?scope=` builds a **28-slide**,
client-ready PowerPoint (`app/services/exports/deck.py`) from the latest leadership
synthesis — surfaced as the **Download Pitch Deck** button on the dashboard.

- **Storytelling arc**: Context → Current state → Gaps vs competitors →
  SEO/AEO/GEO opportunity → Roadmap → Why eClerx → CTA (section dividers between).
- **eClerx navy/red brand** on every slide; **client logo fetched from the web**
  (Clearbit → Google favicon fallback, injectable, degrades gracefully offline).
- **One "Key Takeaway" callout per content slide**; **native pptx charts** (readiness
  scorecard, module bars, competitor us-vs-them, AEO surfaces, GEO citation rate)
  instead of walls of text.

---

## Run it in your browser — no installs (GitHub Codespaces)

For locked-down machines that can't install Python/Node, run the whole app in the
cloud from your browser. The repo ships a **devcontainer** that auto-installs
everything, seeds demo data, and starts both servers.

1. Open the repo on GitHub and switch to the `claude/eclerx-seo-aeo-geo-6ijs5k` branch.
2. Click **Code → Codespaces → Create codespace on this branch**.
3. Wait for the one-time setup (a few minutes). When the **eClerx Web App** port
   (5173) is forwarded, click **Open in Browser** (PORTS tab or the popup).

That's a private, authenticated URL only you can open — no local install required.
Requires GitHub Codespaces to be enabled for your account/org.

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

### Seed / demo data

```bash
cd backend && . .venv/bin/activate && python -m app.seed
# -> demo tenant + login (demo@eclerx.com / demo-password), a "Acme Demo" project
#    and a completed synthetic crawl, so every module + the Leadership Dashboard
#    run immediately — no live crawl or API keys required.
```

The seed is idempotent (safe to re-run).

### One-click deploy (Render / Railway / Fly)

Configs live in `deploy/` and `backend/Procfile`. Set a strong `SECRET_KEY` and
`AUTH_REQUIRED=true` on every platform; attach managed Postgres + Redis and run a
second process for the Celery worker.

- **Render** — New → Blueprint → point at `deploy/render.yaml` (provisions API +
  worker + Redis + Postgres; `SECRET_KEY` auto-generated).
- **Railway** — New Project → Deploy from repo, Root Directory `backend`; add the
  Redis + Postgres plugins; see `deploy/railway.json` for the start/worker commands.
- **Fly.io** — `cd backend && fly launch --dockerfile Dockerfile` using
  `deploy/fly.toml`; `fly secrets set SECRET_KEY=… AUTH_REQUIRED=true`; attach
  `fly postgres`/`fly redis`; `fly deploy` runs `alembic upgrade head` automatically.

All three run `alembic upgrade head` on release. CI (`.github/workflows/ci.yml`)
runs ruff + migrations + pytest and the frontend type-check/build on every push.

---

## Auth & multi-tenancy

- **Tenant = isolation boundary.** Projects and BYO API keys belong to a tenant;
  every request resolves to exactly one tenant and only ever sees that tenant's data.
- **Local-first default** (`AUTH_REQUIRED=false`): requests resolve to a shared
  `default` tenant with no login — so the app and tests run out of the box.
- **Production** (`AUTH_REQUIRED=true`): a JWT bearer token is required.

```bash
# Register a tenant + admin (bootstrap), then log in.
curl -X POST :8000/api/v1/auth/register -H 'Content-Type: application/json' \
  -d '{"email":"you@co.com","password":"supersecret","tenant_name":"Your Co"}'
curl -X POST :8000/api/v1/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"you@co.com","password":"supersecret"}'   # -> {access_token, ...}
# Then call protected routes with:  Authorization: Bearer <access_token>
```

Passwords are bcrypt-hashed; tokens are HS256 JWTs signed with `SECRET_KEY`. BYO
keys remain Fernet-encrypted at rest **and** scoped per tenant.

### External-call rate limiting

Outbound calls to paid APIs (Ahrefs, Firecrawl, the LLM/GEO providers) pass through
a per-provider, process-global throttle (`EXTERNAL_RATE_LIMIT_PER_SEC`, default 5/s;
`0` disables) applied at the cached-call choke point — cache hits are never throttled.

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

Phase 2 covers: benchmark seeding/lookup, the Technical SEO + On-Page analyzers
(scoring, findings, recommendations, competitor_delta), E-E-A-T heuristics, the
Excel + PDF builders, and the analyze + export API end-to-end (no network/keys).

Phase 3 covers: the Ahrefs client (6-month window math, caching, graceful
disable), the internal-link graph, the Internal Linking / Backlinks / Keyword
Universe analyzers (incl. SERP-query persistence + dedupe), and the modules +
serp-queries API end-to-end with a fake Ahrefs client (no network/keys).

Phase 4 covers: AEO feature extraction (question headings, concise answer, schema
detection), the AEO Audit analyzer across all six readiness surfaces, PAA coverage
vs persisted serp_queries, and the module + export API end-to-end.

Phase 5 covers: intent classification + prompt generation (volume/buckets/dedupe),
GEO domain extraction + brand mention/citation/position detection, the GEO analyzer
with fake providers (API + SERP), graceful no-provider degradation, and the
prompts/geo API + exports end-to-end (no network/keys).

Phase 6-7 cover: leadership synthesis (8-module aggregation, SEO→AEO→GEO ordering,
sourced benchmarks, page re-scoping), the master Excel + leadership PDF, and the
pitch deck (slide count in range, ≥1 Key Takeaway per content slide, charts, logo
embed + offline degrade) — all end-to-end with fakes.

Phase 8 covers: register/login/me, AUTH_REQUIRED enforcement, cross-tenant
isolation of projects + BYO keys, the per-provider rate limiter, and the seed
dataset (idempotency + a seeded leadership run). **121 tests pass.**

```bash
cd frontend && npm run build   # tsc type-check + production build
```

---

## Build order (one phase per session)

| Phase | Scope |
|-------|-------|
| **0** | **Scaffold: backend + frontend skeleton, data contract, DB models, BYO-key encryption, caching, tests, CI hook** ✅ |
| **1** | **Ingestion pipeline: sitemap/Excel/paste input, top-50 ranking, Firecrawl + Playwright-stealth fallback, signal extraction, competitor matching, Celery progress stream** ✅ |
| **2** | **SEO modules 1–2 (Technical SEO, On-Page incl. schema/E-E-A-T/structure) to the data contract at site+page scope with competitor_delta; Haiku/Sonnet tiering; Excel + PDF exports** ✅ |
| **3** | **Ahrefs MCP client (6-month window, cached) + modules 3 Internal Linking, 4 Backlinks, 5 Keyword Universe; PAA + featured-snippet queries persisted for Phase 5** ✅ |
| **4** | **AEO Audit (module 6): AI Overview / PAA / Knowledge Panel / Voice + answer-paragraph & structure readiness from crawled content; PAA coverage vs persisted queries; data contract + competitor_delta + exports** ✅ |
| **5** | **Prompt Identification (7): ~60-70 target prompts in intent buckets from PAA/snippets + content. GEO Audit (8): per-prompt query across ChatGPT/Gemini/Claude/Perplexity + SERP AI-Overview capture; brand mention/citation/position vs competitors per LLM; API vs SERP source flagged** ✅ |
| **6** | **Leadership Dashboard (9): Opus cross-module synthesis → one prioritized SEO→AEO→GEO roadmap; benchmark markers with sourced tooltips; page-selector re-scoping; master Excel workbook + leadership PDF (table rules + radar)** ✅ |
| **7** | **AEO/GEO pitch deck (28 slides): storytelling arc Context→Current state→Gaps→Opportunity→Roadmap→eClerx value→CTA; navy/red brand, web-fetched client logo, one Key Takeaway per slide, native charts; Download Pitch Deck button** ✅ |
| **8** | **Hardening: JWT auth + multi-tenant isolation (per-tenant projects + BYO keys), per-provider external-call rate limiting, GitHub Actions CI, one-click deploy (Render/Railway/Fly), and an idempotent seed/demo dataset** ✅ |

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

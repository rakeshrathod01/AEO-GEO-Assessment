# eClerx — SEO / AEO / GEO Enterprise Assessment Platform

A production, self-hostable, multi-tenant SaaS for enterprise **SEO**, **AEO**
(Answer Engine Optimization) and **GEO** (Generative Engine Optimization)
assessments. Local-first (SQLite) and cloud-ready (Postgres), BYO-keys, with
client-ready Excel/PDF/PPTX deliverables.

> **Build status:** Phase 0 (scaffold) complete. Modules 1–9 land in later phases
> per the build order below.

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
│   │   ├── api/routes/      health, settings, projects, modules
│   │   ├── modules_registry.py   the 9 modules (sidebar order)
│   │   └── main.py
│   └── tests/
├── frontend/                React + Vite app (9-module sidebar, Dashboard, Settings)
├── docker-compose.yml       Postgres + Redis + api + worker (cloud-ready)
├── Makefile                 common dev tasks
└── .env.example
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

### Run with Docker (Postgres + Redis)

```bash
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))") \
  docker compose up --build
```

---

## Testing

```bash
cd backend && . .venv/bin/activate && python -m pytest -q
```

Phase 0 covers: health/readiness, Fernet encrypt/decrypt/masking, the data
contract validation, BYO-key upsert/masking, the module registry, and project CRUD.

```bash
cd frontend && npm run build   # tsc type-check + production build
```

---

## Build order (one phase per session)

| Phase | Scope |
|-------|-------|
| **0** | **Scaffold (this session): backend + frontend skeleton, data contract, DB models, BYO-key encryption, caching, tests, CI hook** |
| 1 | Crawler (Firecrawl + Playwright fallback) |
| 2 | SEO modules (Technical, On-Page) |
| 3 | Ahrefs modules (Internal Linking, Backlinks, Keyword Universe) |
| 4 | AEO Audit |
| 5 | Prompt Identification + GEO Audit |
| 6 | Leadership Dashboard + exports |
| 7 | AEO/GEO pitch deck (25–30 slides) |
| 8 | Settings + deploy |

## Configuration

All config is environment-driven (`backend/app/core/config.py`). See
`.env.example`. Provider API keys are **not** environment variables — they are
managed in the Settings UI and encrypted at rest.

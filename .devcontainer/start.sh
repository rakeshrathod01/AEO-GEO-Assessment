#!/usr/bin/env bash
# Runs every time the Codespace starts: launch the engine + website in the
# background. The web app is on port 5173 (auto-opens); it proxies /api to :8000.
cd "$(dirname "$0")/.."

# Engine (FastAPI) — only start if not already running.
if ! pgrep -f "uvicorn app.main:app" >/dev/null 2>&1; then
  ( cd backend && . .venv/bin/activate \
      && SECRET_KEY=dev-codespace EXTERNAL_RATE_LIMIT_PER_SEC=0 \
         nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 >/tmp/engine.log 2>&1 & )
fi

# Website (Vite dev server).
if ! pgrep -f "vite" >/dev/null 2>&1; then
  ( cd frontend && nohup npm run dev >/tmp/web.log 2>&1 & )
fi

echo "eClerx is starting. Open the forwarded port 5173 (the PORTS tab / popup)."

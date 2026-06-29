#!/usr/bin/env bash
# SessionStart setup for Claude Code on the web.
# Idempotent: prepares the backend venv and frontend deps so tests/linters run.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# --- Backend ---
if [ -d backend ]; then
  cd backend
  if [ ! -d .venv ]; then
    python3 -m venv .venv
  fi
  . .venv/bin/activate
  pip install -q --upgrade pip
  pip install -q -r requirements.txt
  deactivate
  cd "$ROOT"
fi

# --- Frontend ---
if [ -d frontend ] && [ ! -d frontend/node_modules ]; then
  cd frontend
  npm install --no-audit --no-fund
  cd "$ROOT"
fi

echo "eClerx assessment platform: setup complete."

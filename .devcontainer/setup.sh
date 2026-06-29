#!/usr/bin/env bash
# One-time setup when the Codespace is created: install deps, migrate, seed demo.
set -e
echo ">> Setting up the analysis engine (Python)…"
cd "$(dirname "$0")/../backend"
python -m venv .venv
. .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -r requirements.txt
export SECRET_KEY=dev-codespace
alembic upgrade head
python -m app.seed

echo ">> Setting up the website (Node)…"
cd ../frontend
npm install

echo ">> Setup complete."

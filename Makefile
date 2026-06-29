.PHONY: help backend-install backend-dev backend-test frontend-install frontend-dev frontend-build lint

help:
	@echo "Targets:"
	@echo "  backend-install   Create venv + install backend deps"
	@echo "  backend-dev       Run FastAPI dev server (port 8000)"
	@echo "  backend-test      Run backend test suite"
	@echo "  frontend-install  Install frontend deps"
	@echo "  frontend-dev      Run Vite dev server (port 5173)"
	@echo "  frontend-build    Type-check + production build"

backend-install:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

backend-dev:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000

backend-test:
	cd backend && . .venv/bin/activate && python -m pytest -q

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

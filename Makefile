.PHONY: help backend-install backend-dev backend-test migrate makemigration \
        frontend-install frontend-dev frontend-build docker-up docker-down

help:
	@echo "Targets:"
	@echo "  backend-install   Create venv + install backend deps"
	@echo "  backend-dev       Run FastAPI dev server (port 8000)"
	@echo "  backend-test      Run backend test suite"
	@echo "  migrate           Apply Alembic migrations (alembic upgrade head)"
	@echo "  makemigration m=… Autogenerate a migration with message m"
	@echo "  frontend-install  Install frontend deps"
	@echo "  frontend-dev      Run Vite dev server (port 5173)"
	@echo "  frontend-build    Type-check + production build"
	@echo "  docker-up         Build + start full stack (api, worker, redis, frontend)"
	@echo "  docker-down       Stop the stack"

backend-install:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

backend-dev:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000

backend-test:
	cd backend && . .venv/bin/activate && python -m pytest -q

migrate:
	cd backend && . .venv/bin/activate && alembic upgrade head

makemigration:
	cd backend && . .venv/bin/activate && alembic revision --autogenerate -m "$(m)"

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

docker-up:
	docker compose -f docker/docker-compose.yml up --build

docker-down:
	docker compose -f docker/docker-compose.yml down

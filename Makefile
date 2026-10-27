PY ?= $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)

.PHONY: install dev backend frontend test seed build typecheck docker

install:
	$(PY) -m pip install -r backend/requirements.txt
	cd frontend && npm ci

dev:
	@echo "Backend on http://localhost:8000, frontend on http://localhost:5173"
	@trap 'trap - INT TERM EXIT; kill 0' INT TERM EXIT; \
	(cd backend && DEV_CORS=true ../$(PY) -m uvicorn app.main:app --reload --port 8000) & \
	(cd frontend && npm run dev -- --host 0.0.0.0) & \
	wait

backend:
	cd backend && DEV_CORS=true ../$(PY) -m uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && ../$(PY) -m pytest

seed:
	cd backend && ../$(PY) -m app.seed

typecheck:
	cd frontend && npx tsc --noEmit

build:
	cd frontend && npm run build

docker:
	docker compose up --build

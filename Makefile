# Sonic Postcards. `make dev` is the one command: database in Docker, API and web on the host.
#
# Ports are fixed defaults that can be overridden from the environment or a .env file:
#   WEB_PORT=4106  API_PORT=8106  DB_PORT=5506

-include .env
export

WEB_PORT ?= 4106
API_PORT ?= 8106
DB_PORT  ?= 5506
DATABASE_URL ?= postgresql://sonic:sonic@127.0.0.1:$(DB_PORT)/sonic
API_URL ?= http://127.0.0.1:$(API_PORT)
PYTHON ?= $(shell command -v python3.12 || command -v python3)
PY := api/.venv/bin/python
DB_CONTAINER := sonic-postcards-db
DB_IMAGE := sonic-postcards-db

.PHONY: dev start setup db db-stop seed seed-pins clear-pins test lint e2e perf fetch-real eval interim shots demo help

help:
	@grep -E '^[a-z0-9-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-12s %s\n", $$1, $$2}'

dev: setup db seed ## Run everything with hot reload: http://localhost:4106
	@echo "\n  Sonic Postcards: http://localhost:$(WEB_PORT)   (API on $(API_PORT), Postgres on $(DB_PORT))\n"
	@trap 'kill 0' INT TERM EXIT; \
	(cd api && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $(API_PORT) --reload --reload-dir app) & \
	(cd web && npx next dev -p $(WEB_PORT)) & \
	wait

start: setup db seed ## Run the production build (what the measurements use)
	cd web && npx next build
	@trap 'kill 0' INT TERM EXIT; \
	(cd api && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $(API_PORT)) & \
	(cd web && npx next start -p $(WEB_PORT)) & \
	wait

setup: api/.venv/.installed web/node_modules/.installed ## Install Python and Node dependencies

api/.venv/.installed: api/requirements.txt api/requirements-dev.txt
	$(PYTHON) -m venv api/.venv
	api/.venv/bin/pip install --quiet --upgrade pip
	api/.venv/bin/pip install --quiet -r api/requirements-dev.txt
	@touch $@

web/node_modules/.installed: web/package.json web/package-lock.json
	cd web && npm ci --no-audit --no-fund
	@touch $@

db: api/.venv/.installed ## Start Postgres with PostGIS and pgvector on DB_PORT
	@docker image inspect $(DB_IMAGE) >/dev/null 2>&1 || docker build -t $(DB_IMAGE) ./db
	@if [ -z "$$(docker ps -q -f name=^$(DB_CONTAINER)$$)" ]; then \
	  if [ -n "$$(docker ps -aq -f name=^$(DB_CONTAINER)$$)" ]; then docker start $(DB_CONTAINER) >/dev/null; \
	  else \
	    if lsof -nP -iTCP:$(DB_PORT) -sTCP:LISTEN >/dev/null 2>&1; then echo "Port $(DB_PORT) is already in use. Set DB_PORT to a free one."; exit 1; fi; \
	    docker run -d --name $(DB_CONTAINER) -e POSTGRES_USER=sonic -e POSTGRES_PASSWORD=sonic -e POSTGRES_DB=sonic \
	      -p 127.0.0.1:$(DB_PORT):5432 -v sonic-postcards-pgdata:/var/lib/postgresql/data $(DB_IMAGE) >/dev/null; \
	  fi; \
	fi
	@cd api && .venv/bin/python -m app.db

db-stop: ## Stop the database container (data is kept in a volume)
	-docker stop $(DB_CONTAINER)

seed: db ## Add the demo postcards if the map is empty
	@cd api && .venv/bin/python -m app.seed demo 2>&1 | grep -v XNNPACK

seed-pins: db ## Add 5,000 synthetic pins for the clustering test
	@cd api && .venv/bin/python -m app.seed pins 5000 2>&1 | grep -v XNNPACK

clear-pins: ## Remove the synthetic pins again
	@cd api && .venv/bin/python -m app.seed clear-pins 2>&1 | grep -v XNNPACK

test: setup db ## Run every automated test
	cd api && .venv/bin/python -m pytest
	cd web && npx tsc --noEmit && npx vitest run

lint: setup ## Ruff, mypy and the TypeScript compiler
	cd api && .venv/bin/ruff check app tests ../scripts && .venv/bin/mypy app
	cd web && npx tsc --noEmit

e2e: ## Browser test with a WAV file as the microphone (needs the app running)
	@cd api && .venv/bin/python -m app.fixtures.export ../.run/fixtures >/dev/null
	cd web && npx tsx scripts/e2e.ts

perf: ## Measure the 5,000 pin map load (needs `make start` running and `make seed-pins`)
	cd web && npx tsx scripts/perf-map.ts

fetch-real: setup ## Download a small labelled set of real clips from ESC-50 (CC BY-NC, not committed)
	$(PY) scripts/fetch_esc50.py

eval: db ## "Sounds like this" on the fetched ESC-50 clips
	@$(PY) scripts/eval_similarity.py 2>&1 | grep -v XNNPACK

interim: setup ## Redraw the code-drawn art in assets/interim and the image request log
	$(PY) scripts/draw_interim.py
	$(PY) scripts/write_prompts.py

shots: ## Screenshots for docs/ (needs the app running)
	cd web && npx tsx scripts/screenshots.ts

demo: ## Record docs/demo.gif (needs the app running)
	@cd api && .venv/bin/python -m app.fixtures.export ../.run/fixtures >/dev/null
	cd web && npx tsx scripts/record-demo.ts

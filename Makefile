# Sehat Saathi developer commands. See README.md.
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
# User-space toolchains (uv, Node LTS) take precedence when present.
export PATH := $(HOME)/.local/node/bin:$(HOME)/.local/bin:$(PATH)

BACKEND := backend
FRONTEND := frontend
UV := uv --directory $(BACKEND)

PHONY_DEMO := demo demo-reset asr llm
.PHONY: $(PHONY_DEMO) setup dev check check-backend check-frontend check-content check-generated e2e eval seed migrate bundle api-types format clean

setup:  ## install backend + frontend dependencies
	$(UV) sync --frozen
	cd $(FRONTEND) && npm ci
	cd $(FRONTEND) && npx playwright install chromium

dev: migrate  ## run API (port 8000) and web app (port 5173) with mock providers
	@trap 'kill 0' EXIT INT TERM; \
	$(UV) run uvicorn app.main:app --reload --port 8000 & \
	(cd $(FRONTEND) && npm run dev -- --host 127.0.0.1) & \
	wait

check: check-content check-generated check-backend check-frontend e2e  ## lint + typecheck + all tests
	@echo "make check: all passed"

check-content:
	$(UV) run python -m app.content.validate

check-generated:  ## generated files (content bundle, API types) must be up to date
	$(UV) run python -m app.content.bundle --check
	$(UV) run python -m app.openapi_dump > $(FRONTEND)/node_modules/.openapi.check.json
	cd $(FRONTEND) && npx openapi-typescript node_modules/.openapi.check.json -o node_modules/.schema.check.d.ts >/dev/null
	cmp -s $(FRONTEND)/node_modules/.schema.check.d.ts $(FRONTEND)/src/api/schema.d.ts || (echo "src/api/schema.d.ts is out of date: run make api-types" && exit 1)

check-backend:
	$(UV) run ruff check app tests
	$(UV) run ruff format --check app tests
	$(UV) run mypy
	$(UV) run pytest
	$(UV) run pytest ../services/asr/tests -q -p no:cacheprovider
	$(UV) run ruff check ../services/asr ../evals

check-frontend:
	cd $(FRONTEND) && npm run lint
	cd $(FRONTEND) && npm run typecheck
	cd $(FRONTEND) && npm run i18n:check
	cd $(FRONTEND) && npm test

e2e:
	cd $(FRONTEND) && npm run e2e

eval:  ## run the evaluation harness against the configured providers
	$(UV) run python ../evals/run.py --note "$(EVAL_NOTE)"

seed: migrate  ## load synthetic demo data
	$(UV) run python -m app.seed

migrate:  ## apply database migrations
	$(UV) run alembic upgrade head

bundle:  ## regenerate the frontend content bundle from rules/ and knowledge/
	$(UV) run python -m app.content.bundle

api-types:  ## regenerate TypeScript API types from the OpenAPI document
	$(UV) run python -m app.openapi_dump > $(FRONTEND)/node_modules/.openapi.json
	cd $(FRONTEND) && npx openapi-typescript node_modules/.openapi.json -o src/api/schema.d.ts

format:
	$(UV) run ruff format app tests
	$(UV) run ruff check --fix app tests

clean:
	rm -rf $(BACKEND)/.venv $(FRONTEND)/node_modules $(FRONTEND)/dist

# --- demo with real models on the GPU server (see scripts/demo.sh) -----------------------
asr:  ## speech service only (GPU 0, half its memory)
	services/asr/run.sh

llm:  ## language model only (vLLM on GPU 1, half its memory)
	services/llm/run.sh

demo-reset:  ## fresh demo database with synthetic accounts and people
	rm -f $(BACKEND)/demo.db
	cd $(BACKEND) && DATABASE_URL=sqlite:///./demo.db uv run alembic upgrade head
	cd $(BACKEND) && DATABASE_URL=sqlite:///./demo.db uv run python -m app.seed

demo:  ## real speech + language models, app on :8000/:5173
	scripts/demo.sh

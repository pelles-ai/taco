.PHONY: install lint format typecheck test test-verbose check-all clean
.PHONY: demo demo-docker demo-stop demo-install demo-env help

# ── Development ──────────────────────────────────────────────
install:                            ## Install SDK with dev dependencies
	pip install -e sdk[dev]

lint:                               ## Run ruff linter
	cd sdk && ruff check taco/ tests/

format:                             ## Run ruff formatter
	cd sdk && ruff format taco/ tests/

typecheck:                          ## Run mypy type checker
	cd sdk && mypy taco/

test:                               ## Run tests
	cd sdk && pytest

test-verbose:                       ## Run tests with verbose output
	cd sdk && pytest -v

check-all: lint                     ## Run all checks (mirrors CI)
	cd sdk && ruff format --check taco/ tests/
	cd sdk && mypy taco/
	cd sdk && pytest -v

clean:                              ## Remove caches and build artifacts
	find sdk -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf sdk/.pytest_cache sdk/.mypy_cache sdk/.ruff_cache
	rm -rf sdk/*.egg-info sdk/taco/*.egg-info

# ── Demo (local) ─────────────────────────────────────────────
demo-install:                       ## Install TACO SDK + demo dependencies
	pip install -e sdk[server]
	pip install -r examples/requirements.txt

demo-env:                           ## Create .env from template (won't overwrite existing)
	@test -f examples/.env || cp examples/.env.example examples/.env
	@echo "Edit examples/.env and set your API key."

demo: demo-env                      ## Run the demo locally (agents + dashboard)
	cd examples && python run_demo.py

# ── Demo (Docker) ────────────────────────────────────────────
demo-docker: demo-env               ## Run the demo via Docker Compose
	docker compose -f examples/docker-compose.yml --env-file examples/.env up --build

demo-stop:                          ## Stop Docker Compose services
	docker compose -f examples/docker-compose.yml down

# ── Help ─────────────────────────────────────────────────────
help:                               ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

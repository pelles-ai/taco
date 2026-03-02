.PHONY: demo demo-docker demo-stop demo-install demo-env

# ── Local demo ────────────────────────────────────────────────
demo-install:                        ## Install CAIP SDK + demo dependencies
	pip install -e sdk[server]
	pip install -r examples/requirements.txt

demo-env:                            ## Create .env from template (won't overwrite existing)
	@test -f examples/.env || cp examples/.env.example examples/.env
	@echo "Edit examples/.env and set your API key."

demo: demo-env                       ## Run the demo locally (agents + dashboard)
	cd examples && python run_demo.py

# ── Docker demo ───────────────────────────────────────────────
demo-docker: demo-env                ## Run the demo via Docker Compose
	docker compose -f examples/docker-compose.yml --env-file examples/.env up --build

demo-stop:                           ## Stop Docker Compose services
	docker compose -f examples/docker-compose.yml down

# ── Help ──────────────────────────────────────────────────────
help:                                ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

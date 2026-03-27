.DEFAULT_GOAL := help

.PHONY: help up down logs smoke test

help: ## Show available targets
	@printf "EDGE-AGENT targets:\n\n"
	@awk 'BEGIN {FS = ": ## "}; /^[a-zA-Z_-]+: ## / {printf "  %-10s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

up: ## Start the local Hummingbot dev infrastructure
	@./infra/scripts/up.sh

down: ## Stop the local Hummingbot dev infrastructure
	@./infra/scripts/down.sh

logs: ## Tail infrastructure logs
	@./infra/scripts/logs.sh

smoke: ## Verify the local infrastructure health
	@./infra/scripts/smoke.sh

test: ## Run the Python test suite
	python3 -m pytest

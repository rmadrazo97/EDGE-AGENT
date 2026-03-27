.DEFAULT_GOAL := help

.PHONY: help up down logs smoke test

help: ## Show available targets
	@printf "EDGE-AGENT targets:\n\n"
	@awk 'BEGIN {FS = ": ## "}; /^[a-zA-Z_-]+: ## / {printf "  %-10s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

up: ## Start local infrastructure (stub for Phase 1.1)
	@echo "Phase 1.1 will wire this target to Docker Compose."

down: ## Stop local infrastructure (stub for Phase 1.1)
	@echo "Phase 1.1 will wire this target to Docker Compose."

logs: ## Tail local infrastructure logs (stub for Phase 1.1)
	@echo "Phase 1.1 will wire this target to Docker Compose logs."

smoke: ## Run smoke checks (stub for Phase 1.2)
	@echo "Phase 1.2 will add infrastructure smoke checks."

test: ## Run the Python test suite
	python3 -m pytest

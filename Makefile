.DEFAULT_GOAL := help

.PHONY: help up down logs smoke test test-trade analyst-once trader-once reporter integration-test integration-report

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

test-trade: ## Run the hardcoded BTC-USDT short pipeline on testnet
	@python3 -m strategies.controllers.test_short

analyst-once: ## Run a single market analyst cycle
	@python3 -m agents.analyst.agent --once

trader-once: ## Run a single trader cycle
	@python3 -m agents.trader.agent --once

reporter: ## Start the Telegram reporter/approval agent
	@python3 -m agents.reporter.agent

integration-test: ## Run the 24-48h testnet integration test
	@./infra/scripts/integration-test.sh

integration-report: ## Generate post-run integration test report
	@./infra/scripts/integration-test-report.sh

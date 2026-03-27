.DEFAULT_GOAL := help

.PHONY: help up down logs smoke test test-trade analyst-once trader-once reporter scan-altcoins integration-test integration-report signal-export signal-metrics signal-journal

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

scan-altcoins: ## Scan altcoin perps for trading opportunities
	@python3 -m agents.scanner.agent --top 10

integration-test: ## Run the 24-48h testnet integration test
	@./infra/scripts/integration-test.sh

integration-report: ## Generate post-run integration test report
	@./infra/scripts/integration-test-report.sh

signal-export: ## Export analyst signals to CSV
	@python3 -m tools.signal_export --output signals.csv

signal-metrics: signal-export ## Export signals then print metrics
	@python3 -m tools.signal_metrics --input signals.csv

signal-journal: ## Run full signal pipeline and update OpenClaw journal
	@python3 -m tools.signal_journal_update

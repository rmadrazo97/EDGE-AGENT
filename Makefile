.DEFAULT_GOAL := help

.PHONY: help up down logs smoke test test-trade analyst-once trader-once reporter advisor-once risk-monitor scan-altcoins integration-test integration-test-short integration-report signal-export signal-metrics signal-journal deploy rollback backup health

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

advisor-once: ## Run a single portfolio advisory cycle
	@python3 -m agents.advisor.agent --once

risk-monitor: ## Start the continuous risk monitor
	@python3 -m agents.risk_monitor.agent

scan-altcoins: ## Scan altcoin perps for trading opportunities
	@python3 -m agents.scanner.agent --top 10

integration-test: ## Run the 24-48h testnet integration test
	@./infra/scripts/integration-test.sh

integration-test-short: ## Run a quick 2-cycle integration test (~5 min)
	@./infra/scripts/integration-test-short.sh

integration-report: ## Generate post-run integration test report
	@./infra/scripts/integration-test-report.sh

signal-export: ## Export analyst signals to CSV
	@python3 -m tools.signal_export --output signals.csv

signal-metrics: signal-export ## Export signals then print metrics
	@python3 -m tools.signal_metrics --input signals.csv

signal-journal: ## Run full signal pipeline and update OpenClaw journal
	@python3 -m tools.signal_journal_update

deploy: ## Deploy to VPS (usage: make deploy VPS=user@host)
	@./infra/scripts/deploy.sh $(VPS)

rollback: ## Rollback VPS to previous version (usage: make rollback VPS=user@host)
	@./infra/scripts/rollback.sh $(VPS)

backup: ## Backup from VPS (usage: make backup VPS=user@host)
	@./infra/scripts/backup.sh $(VPS)

health: ## Check VPS health (usage: make health VPS=user@host)
	@./infra/scripts/health-check.sh $(VPS)

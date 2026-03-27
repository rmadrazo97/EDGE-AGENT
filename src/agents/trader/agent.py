"""Policy-wired trader agent for testnet short execution and review."""

from __future__ import annotations

import argparse
import json
import logging
import time
from contextlib import ExitStack
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable

from agents.analyst.agent import MarketAnalystAgent
from agents.analyst.signals import ShortSignal
from agents.reporter.approvals import ApprovalStore
from agents.reporter.notifier import TelegramNotifier
from agents.trader.position_manager import PositionManager
from agents.trader.prompts import TRADER_SYSTEM_PROMPT, build_trader_review_prompt
from clients.market_data import MarketDataClient
from clients.portfolio import PortfolioClient
from clients.trading import TradingClient
from policy.engine import PolicyEngine
from policy.models import PolicyDecision, TradeProposal
from shared.config import ClientSettings
from shared.moonshot import MoonshotAPIError, MoonshotClient


LOGGER = logging.getLogger("agents.trader")


class TraderAgent:
    close_tool = {
        "type": "function",
        "function": {
            "name": "close_position",
            "description": "Close an existing short position immediately.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pair": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["pair", "reason"],
            },
        },
    }

    def __init__(
        self,
        settings: ClientSettings | None = None,
        *,
        policy_engine: PolicyEngine | None = None,
        position_manager: PositionManager | None = None,
        approval_store: ApprovalStore | None = None,
        notifier: TelegramNotifier | None = None,
        analyst_agent: MarketAnalystAgent | None = None,
        trading_client: TradingClient | None = None,
        portfolio_client: PortfolioClient | None = None,
        market_data_client: MarketDataClient | None = None,
        moonshot_client: MoonshotClient | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings or ClientSettings.from_env()
        self.policy_engine = policy_engine or PolicyEngine()
        self.position_manager = position_manager or PositionManager()
        self.approval_store = approval_store or ApprovalStore()
        self.notifier = notifier or TelegramNotifier(
            settings=self.settings,
            approval_store=self.approval_store,
        )
        self.analyst_agent = analyst_agent
        self.trading_client = trading_client
        self.portfolio_client = portfolio_client
        self.market_data_client = market_data_client
        self.moonshot_client = moonshot_client
        self.sleep_fn = sleep_fn
        self.runtime_dir = Path("runtime/trader")
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.runtime_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.jsonl"

    def _record(self, event: str, **details: object) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "details": details,
        }
        with self.log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, default=str) + "\n")
        LOGGER.info("%s %s", event, details)

    def _build_trade_proposal(self, signal: ShortSignal, account_state) -> TradeProposal:
        config = self.policy_engine.config
        leverage = min(float(self.settings.trader_default_leverage), float(config.max_leverage))
        stop_distance = signal.stop_loss_price - signal.entry_price
        if stop_distance <= 0:
            raise ValueError("Signal stop loss must be above entry price for a short.")

        risk_budget = account_state.total_equity * config.max_risk_per_trade_pct
        size_by_risk = risk_budget / stop_distance
        size_by_margin = 0.0
        if signal.entry_price > 0 and leverage > 0:
            size_by_margin = (account_state.available_margin * leverage) / signal.entry_price

        requested_size = min(size_by_risk, size_by_margin) if size_by_margin > 0 else size_by_risk
        requested_size = min(requested_size, float(TradingClient.max_test_position_size))

        return TradeProposal(
            pair=signal.pair,
            side="short",
            size=max(requested_size, 0.0),
            leverage=leverage,
            entry_price=signal.entry_price,
            stop_loss_price=signal.stop_loss_price,
            signal_confidence=signal.confidence,
            reasoning=signal.reasoning,
        )

    def _current_prices(self, market: MarketDataClient, pairs: list[str]) -> dict[str, float]:
        return {pair: market.get_price(pair).price for pair in pairs}

    def process_signal(
        self,
        signal: ShortSignal,
        *,
        trading: TradingClient,
        portfolio: PortfolioClient,
        market: MarketDataClient,
        require_approval: bool = True,
    ) -> PolicyDecision:
        balances = portfolio.get_balances()
        live_positions = trading.get_positions()
        current_prices = self._current_prices(market, [signal.pair, *{position.trading_pair for position in live_positions}])
        self.position_manager.sync_live_positions(live_positions)
        account_state = self.position_manager.build_account_state(
            balances=balances,
            live_positions=live_positions,
            current_prices=current_prices,
        )
        proposal = self._build_trade_proposal(signal, account_state)
        decision = self.policy_engine.evaluate(proposal, account_state)

        if not decision.approved:
            if any("daily loss limit exceeded" in violation for violation in decision.violations):
                self.notifier.send_daily_loss_halt(
                    current_daily_pnl=account_state.daily_realized_pnl,
                    loss_limit_pct=self.policy_engine.config.max_daily_loss_pct,
                )
            if require_approval and signal.confidence > 0.8:
                resolution = self.notifier.request_approval(signal, proposal, decision)
                self._record(
                    "approval_resolved",
                    request_pair=signal.pair,
                    status=resolution.status,
                    approved=resolution.approved,
                )
                if resolution.approved:
                    return self.process_signal(
                        signal,
                        trading=trading,
                        portfolio=portfolio,
                        market=market,
                        require_approval=False,
                    )
            self._record(
                "trade_rejected",
                pair=signal.pair,
                violations=decision.violations,
                warnings=decision.warnings,
            )
            return decision

        if require_approval and (
            decision.warnings or decision.adjusted_size is not None
        ):
            resolution = self.notifier.request_approval(signal, proposal, decision)
            self._record(
                "approval_resolved",
                pair=signal.pair,
                status=resolution.status,
                warnings=decision.warnings,
            )
            if not resolution.approved:
                return PolicyDecision(
                    approved=False,
                    violations=[f"operator {resolution.status} approval request"],
                    warnings=decision.warnings,
                    adjusted_size=decision.adjusted_size,
                )

        size_to_execute = decision.adjusted_size or proposal.size
        if size_to_execute <= 0:
            self._record("trade_rejected", pair=signal.pair, violations=["calculated trade size was zero"])
            return PolicyDecision(approved=False, violations=["calculated trade size was zero"], warnings=[])

        trading.set_position_mode("ONEWAY")
        submission = trading.open_short(signal.pair, Decimal(str(size_to_execute)), int(proposal.leverage))
        stop_loss = trading.set_stop_loss(signal.pair, signal.stop_loss_price)
        self.position_manager.record_open(
            signal=signal,
            size=size_to_execute,
            leverage=proposal.leverage,
            order_id=submission.order_id,
        )
        self._record(
            "trade_opened",
            pair=signal.pair,
            side="short",
            size=size_to_execute,
            entry_price=signal.entry_price,
            leverage=proposal.leverage,
            order_id=submission.order_id,
            reasoning=signal.reasoning,
            stop_loss=stop_loss.model_dump(mode="json"),
            warnings=decision.warnings,
        )
        self.notifier.send_trade_alert(
            pair=signal.pair,
            side="short",
            size=size_to_execute,
            entry_price=signal.entry_price,
            leverage=proposal.leverage,
            reasoning=signal.reasoning,
        )
        return decision

    def _review_position_for_exit(
        self,
        pair: str,
        *,
        trading: TradingClient,
        market: MarketDataClient,
        moonshot: MoonshotClient,
    ) -> bool:
        managed_position = self.position_manager.get_open_position(pair)
        if managed_position is None:
            return False

        price = market.get_price(pair)
        ticker = market.get_ticker_24h(pair)
        funding = market.get_funding_rate(pair)
        completion = moonshot.chat_completion(
            system_prompt=TRADER_SYSTEM_PROMPT,
            user_prompt=build_trader_review_prompt(
                managed_position,
                price=price,
                ticker=ticker,
                funding=funding,
            ),
            tools=[self.close_tool],
        )
        if not completion.choices or not completion.choices[0].message.tool_calls:
            self._record("position_held", pair=pair, reason="model_declined_to_close")
            return False

        tool_call = completion.choices[0].message.tool_calls[0]
        if tool_call.function.name != "close_position":
            raise MoonshotAPIError(f"Unexpected tool call: {tool_call.function.name}")

        arguments = MoonshotClient.parse_tool_arguments(tool_call)
        if arguments.get("pair") != pair:
            self._record("position_held", pair=pair, reason="model_returned_mismatched_pair")
            return False

        submission = trading.close_position(pair)
        closed_trade = self.position_manager.record_close(
            pair,
            exit_price=price.price,
            reason=str(arguments["reason"]),
        )
        self._record(
            "position_closed",
            pair=pair,
            order_id=submission.order_id,
            reason=arguments["reason"],
            realized_pnl=closed_trade.realized_pnl,
            entry_price=closed_trade.entry_price,
            exit_price=closed_trade.exit_price,
            duration_seconds=(closed_trade.closed_at - closed_trade.opened_at).total_seconds(),
        )
        if "stop" in str(arguments["reason"]).lower():
            self.notifier.send_stop_loss_alert(
                pair=pair,
                realized_pnl=closed_trade.realized_pnl,
            )
        else:
            self.notifier.send_close_alert(
                pair=pair,
                realized_pnl=closed_trade.realized_pnl,
                duration_seconds=(closed_trade.closed_at - closed_trade.opened_at).total_seconds(),
                reason=str(arguments["reason"]),
            )
        return True

    def review_positions(self, *, trading: TradingClient, market: MarketDataClient, moonshot: MoonshotClient) -> None:
        live_positions = trading.get_positions()
        self.position_manager.sync_live_positions(live_positions)
        for position in live_positions:
            self._review_position_for_exit(
                position.trading_pair,
                trading=trading,
                market=market,
                moonshot=moonshot,
            )

    def run_once(self, signals: list[ShortSignal] | None = None) -> list[PolicyDecision]:
        with ExitStack() as stack:
            trading = self.trading_client or stack.enter_context(TradingClient(settings=self.settings))
            portfolio = self.portfolio_client or stack.enter_context(PortfolioClient(settings=self.settings))
            market = self.market_data_client or stack.enter_context(MarketDataClient(settings=self.settings))
            moonshot = self.moonshot_client or stack.enter_context(MoonshotClient(settings=self.settings))

            current_signals = signals
            if current_signals is None:
                if self.analyst_agent is None:
                    raise ValueError("run_once requires signals or an analyst agent.")
                current_signals = self.analyst_agent.run_once()

            decisions = [
                self.process_signal(signal, trading=trading, portfolio=portfolio, market=market)
                for signal in current_signals
            ]
            self.review_positions(trading=trading, market=market, moonshot=moonshot)
            return decisions

    def run_forever(self) -> None:
        interval_seconds = self.settings.trader_review_interval_minutes * 60
        while True:
            self.run_once()
            self.sleep_fn(interval_seconds)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one trader review cycle.")
    parser.add_argument("--once", action="store_true", help="Run a single trader cycle and exit.")
    return parser


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    args = build_arg_parser().parse_args()
    trader = TraderAgent(analyst_agent=MarketAnalystAgent())
    if args.once:
        trader.run_once()
        return 0
    trader.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Portfolio advisor agent backed by Moonshot structured outputs."""

from __future__ import annotations

import argparse
import json
import logging
import time
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from agents.advisor.models import PortfolioAdvisory
from agents.advisor.prompts import ADVISOR_SYSTEM_PROMPT, build_advisor_user_prompt
from agents.reporter.notifier import TelegramNotifier
from agents.trader.position_manager import ClosedTrade, ManagedPosition, PositionManager
from clients.market_data import MarketDataClient
from clients.portfolio import PortfolioClient
from shared.config import ClientSettings
from shared.models import OpenPosition
from shared.moonshot import MoonshotAPIError, MoonshotClient


LOGGER = logging.getLogger("agents.advisor")


class PortfolioAdvisorAgent:
    advisory_tool = {
        "type": "function",
        "function": {
            "name": "emit_advisory",
            "description": "Emit a structured portfolio advisory with health assessment and recommendations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "portfolio_health": {
                        "type": "string",
                        "enum": ["healthy", "caution", "warning"],
                    },
                    "recommendations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "High-level recommendations for the operator.",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Detailed reasoning behind the assessment.",
                    },
                    "suggested_actions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific actionable items the operator should consider.",
                    },
                },
                "required": ["portfolio_health", "recommendations", "reasoning", "suggested_actions"],
            },
        },
    }

    def __init__(
        self,
        settings: ClientSettings | None = None,
        *,
        position_manager: PositionManager | None = None,
        portfolio_client: PortfolioClient | None = None,
        market_data_client: MarketDataClient | None = None,
        moonshot_client: MoonshotClient | None = None,
        notifier: TelegramNotifier | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings or ClientSettings.from_env()
        self.position_manager = position_manager or PositionManager()
        self.portfolio_client = portfolio_client
        self.market_data_client = market_data_client
        self.moonshot_client = moonshot_client
        self.notifier = notifier
        self.sleep_fn = sleep_fn
        self.runtime_dir = Path("runtime/advisor")
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

    @staticmethod
    def _summarize_positions(positions: list[OpenPosition]) -> str:
        if not positions:
            return "No open positions."
        lines: list[str] = []
        for pos in positions:
            lines.append(
                f"- {pos.trading_pair}: amount={pos.amount:.6f} entry={pos.entry_price:.2f} "
                f"upnl={pos.unrealized_pnl:.2f} leverage={pos.leverage}"
            )
        return "\n".join(lines)

    @staticmethod
    def _summarize_closed_trades(trades: list[ClosedTrade]) -> str:
        if not trades:
            return "No closed trades in the last 7 days."
        wins = sum(1 for t in trades if t.realized_pnl > 0)
        total_pnl = sum(t.realized_pnl for t in trades)
        win_rate = (wins / len(trades) * 100.0) if trades else 0.0
        lines = [
            f"Total trades: {len(trades)}, Wins: {wins}, Win rate: {win_rate:.1f}%",
            f"Total realized PnL: {total_pnl:.2f}",
        ]
        for trade in trades[-5:]:
            lines.append(
                f"- {trade.pair}: pnl={trade.realized_pnl:.2f} "
                f"entry={trade.entry_price:.2f} exit={trade.exit_price:.2f} reason={trade.reason}"
            )
        return "\n".join(lines)

    @staticmethod
    def _summarize_risk_usage(
        positions: list[OpenPosition],
        total_equity: float,
        daily_pnl: float,
        max_daily_loss_pct: float,
        max_exposure_pct: float,
    ) -> str:
        total_exposure = sum(abs(p.amount) * p.entry_price for p in positions)
        exposure_pct = (total_exposure / total_equity * 100.0) if total_equity > 0 else 0.0
        daily_loss_pct = (abs(daily_pnl) / total_equity * 100.0) if total_equity > 0 and daily_pnl < 0 else 0.0
        return (
            f"Total equity: {total_equity:.2f}\n"
            f"Total exposure: {total_exposure:.2f} ({exposure_pct:.1f}% of equity, limit {max_exposure_pct * 100:.0f}%)\n"
            f"Daily realized PnL: {daily_pnl:.2f} (loss usage: {daily_loss_pct:.1f}%, limit {max_daily_loss_pct * 100:.0f}%)"
        )

    @staticmethod
    def _summarize_market_conditions(
        market: MarketDataClient,
        pairs: list[str],
    ) -> str:
        lines: list[str] = []
        for pair in pairs:
            try:
                price = market.get_price(pair)
                ticker = market.get_ticker_24h(pair)
                funding = market.get_funding_rate(pair)
                lines.append(
                    f"- {pair}: price={price.price:.2f} 24h_change={ticker.price_change_percent:.2f}% "
                    f"funding={funding.funding_rate:.6f} volume={ticker.quote_volume:.0f}"
                )
            except Exception as exc:
                lines.append(f"- {pair}: data unavailable ({exc})")
        return "\n".join(lines) if lines else "No market data available."

    def request_advisory(
        self,
        *,
        positions_summary: str,
        trades_summary: str,
        risk_summary: str,
        market_summary: str,
        moonshot: MoonshotClient,
    ) -> PortfolioAdvisory | None:
        completion = moonshot.chat_completion(
            system_prompt=ADVISOR_SYSTEM_PROMPT,
            user_prompt=build_advisor_user_prompt(
                open_positions_summary=positions_summary,
                closed_trades_summary=trades_summary,
                risk_usage_summary=risk_summary,
                market_conditions_summary=market_summary,
            ),
            tools=[self.advisory_tool],
        )
        if not completion.choices:
            raise MoonshotAPIError("Moonshot returned no choices.")

        message = completion.choices[0].message
        if not message.tool_calls:
            return None

        tool_call = message.tool_calls[0]
        if tool_call.function.name != "emit_advisory":
            raise MoonshotAPIError(f"Unexpected tool call: {tool_call.function.name}")

        arguments = MoonshotClient.parse_tool_arguments(tool_call)
        return PortfolioAdvisory(
            portfolio_health=arguments["portfolio_health"],
            recommendations=arguments["recommendations"],
            reasoning=arguments["reasoning"],
            suggested_actions=arguments["suggested_actions"],
        )

    def run_once(self) -> PortfolioAdvisory | None:
        with ExitStack() as stack:
            portfolio = self.portfolio_client or stack.enter_context(PortfolioClient(settings=self.settings))
            market = self.market_data_client or stack.enter_context(MarketDataClient(settings=self.settings))
            moonshot = self.moonshot_client or stack.enter_context(MoonshotClient(settings=self.settings))

            positions = portfolio.get_positions()
            balances = portfolio.get_balances()
            total_equity = sum(b.value for b in balances)

            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            recent_trades = [
                t for t in self.position_manager.state.closed_trades
                if t.closed_at >= cutoff
            ]
            daily_pnl = self.position_manager.daily_realized_pnl()

            positions_summary = self._summarize_positions(positions)
            trades_summary = self._summarize_closed_trades(recent_trades)
            risk_summary = self._summarize_risk_usage(
                positions, total_equity, daily_pnl,
                max_daily_loss_pct=0.05, max_exposure_pct=0.30,
            )
            market_summary = self._summarize_market_conditions(market, self.settings.analyst_pairs)

            self._record(
                "advisory_started",
                positions_summary=positions_summary,
                trades_summary=trades_summary,
                risk_summary=risk_summary,
                market_summary=market_summary,
            )

            try:
                advisory = self.request_advisory(
                    positions_summary=positions_summary,
                    trades_summary=trades_summary,
                    risk_summary=risk_summary,
                    market_summary=market_summary,
                    moonshot=moonshot,
                )
            except (MoonshotAPIError, ValueError) as exc:
                self._record("advisory_failed", error=str(exc))
                return None

            if advisory is None:
                self._record("advisory_skipped", reason="model_declined_to_emit_advisory")
                return None

            self._record(
                "advisory_generated",
                advisory=advisory.model_dump(mode="json"),
            )

            if self.notifier is not None:
                self.notifier.send_advisory(advisory)

            return advisory

    def run_forever(self) -> None:
        interval_seconds = self.settings.advisor_interval_days * 86400
        while True:
            cycle_started_at = time.monotonic()
            self.run_once()
            elapsed = time.monotonic() - cycle_started_at
            sleep_seconds = max(0.0, interval_seconds - elapsed)
            self.sleep_fn(sleep_seconds)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the EDGE-AGENT portfolio advisor.")
    parser.add_argument("--once", action="store_true", help="Run a single advisory cycle and exit.")
    return parser


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    args = build_arg_parser().parse_args()
    agent = PortfolioAdvisorAgent()
    if args.once:
        agent.run_once()
        return 0

    agent.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

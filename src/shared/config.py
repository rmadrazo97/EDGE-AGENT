"""Local configuration helpers for EDGE-AGENT clients."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel, Field


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _is_placeholder(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().lower()
    return normalized.startswith("your_") and normalized.endswith("_here")


def _first_nonempty(keys: Iterable[str], values: dict[str, str]) -> str | None:
    for key in keys:
        value = values.get(key)
        if value and not _is_placeholder(value):
            return value
    return None


def _parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


class ClientSettings(BaseModel):
    api_base_url: str = Field(default="http://localhost:8000")
    api_username: str = Field(default="admin")
    api_password: str = Field(default="admin")
    api_timeout: float = Field(default=10.0)
    account_name: str = Field(default="master_account")
    market_data_connector: str = Field(default="binance_perpetual_testnet")
    candles_connector: str = Field(default="binance_perpetual")
    binance_testnet_api_key: str | None = Field(default=None)
    binance_testnet_api_secret: str | None = Field(default=None)
    moonshot_api_key: str | None = Field(default=None)
    moonshot_api_base_url: str = Field(default="https://api.moonshot.ai/v1")
    moonshot_model: str = Field(default="kimi-k2.5")
    analyst_interval_minutes: int = Field(default=15)
    analyst_pairs: list[str] = Field(default_factory=lambda: ["BTC-USDT", "ETH-USDT"])
    analyst_confidence_threshold: float = Field(default=0.7)
    analyst_max_retries: int = Field(default=3)
    analyst_retry_backoff_seconds: float = Field(default=2.0)
    trader_default_leverage: int = Field(default=2)
    trader_review_interval_minutes: int = Field(default=5)
    telegram_bot_token: str | None = Field(default=None)
    telegram_operator_chat_id: int | None = Field(default=None)
    report_interval_hours: int = Field(default=4)
    daily_report_hour_utc: int = Field(default=21)
    approval_timeout_seconds: int = Field(default=300)

    @classmethod
    def from_env(cls) -> "ClientSettings":
        repo_root = _repo_root()
        file_values: dict[str, str] = {}
        for path in (
            repo_root / ".env",
            repo_root / "infra" / "env" / "api.env",
        ):
            file_values.update(_parse_env_file(path))

        env_values = {**file_values, **os.environ}

        return cls(
            api_base_url=_first_nonempty(
                ("EDGE_AGENT_API_URL", "HUMMINGBOT_API_BASE_URL"),
                env_values,
            )
            or "http://localhost:8000",
            api_username=_first_nonempty(
                ("EDGE_AGENT_API_USERNAME", "HUMMINGBOT_API_USERNAME", "USERNAME"),
                env_values,
            )
            or "admin",
            api_password=_first_nonempty(
                ("EDGE_AGENT_API_PASSWORD", "HUMMINGBOT_API_PASSWORD", "PASSWORD"),
                env_values,
            )
            or "admin",
            api_timeout=float(
                _first_nonempty(("EDGE_AGENT_API_TIMEOUT",), env_values) or "10.0"
            ),
            account_name=_first_nonempty(("EDGE_AGENT_ACCOUNT_NAME",), env_values)
            or "master_account",
            market_data_connector=_first_nonempty(
                ("EDGE_AGENT_MARKET_DATA_CONNECTOR",),
                env_values,
            )
            or "binance_perpetual_testnet",
            candles_connector=_first_nonempty(
                ("EDGE_AGENT_CANDLES_CONNECTOR",),
                env_values,
            )
            or "binance_perpetual",
            binance_testnet_api_key=_first_nonempty(
                ("BINANCE_TESTNET_API_KEY", "BINANCE_API_KEY"),
                env_values,
            ),
            binance_testnet_api_secret=_first_nonempty(
                ("BINANCE_TESTNET_API_SECRET", "BINANCE_SECRET"),
                env_values,
            ),
            moonshot_api_key=_first_nonempty(("MOONSHOT_API_KEY",), env_values),
            moonshot_api_base_url=_first_nonempty(
                ("MOONSHOT_API_BASE_URL",),
                env_values,
            )
            or "https://api.moonshot.ai/v1",
            moonshot_model=_first_nonempty(
                ("MOONSHOT_MODEL",),
                env_values,
            )
            or "kimi-k2.5",
            analyst_interval_minutes=int(
                _first_nonempty(("EDGE_AGENT_ANALYST_INTERVAL_MINUTES",), env_values)
                or "15"
            ),
            analyst_pairs=_parse_csv(
                _first_nonempty(("EDGE_AGENT_ANALYST_PAIRS",), env_values)
            )
            or ["BTC-USDT", "ETH-USDT"],
            analyst_confidence_threshold=float(
                _first_nonempty(("EDGE_AGENT_ANALYST_CONFIDENCE_THRESHOLD",), env_values)
                or "0.7"
            ),
            analyst_max_retries=int(
                _first_nonempty(("EDGE_AGENT_ANALYST_MAX_RETRIES",), env_values)
                or "3"
            ),
            analyst_retry_backoff_seconds=float(
                _first_nonempty(
                    ("EDGE_AGENT_ANALYST_RETRY_BACKOFF_SECONDS",),
                    env_values,
                )
                or "2.0"
            ),
            trader_default_leverage=int(
                _first_nonempty(("EDGE_AGENT_TRADER_DEFAULT_LEVERAGE",), env_values)
                or "2"
            ),
            trader_review_interval_minutes=int(
                _first_nonempty(("EDGE_AGENT_TRADER_REVIEW_INTERVAL_MINUTES",), env_values)
                or "5"
            ),
            telegram_bot_token=_first_nonempty(("TELEGRAM_BOT_TOKEN",), env_values),
            telegram_operator_chat_id=(
                int(_first_nonempty(("TELEGRAM_OPERATOR_CHAT_ID",), env_values))
                if _first_nonempty(("TELEGRAM_OPERATOR_CHAT_ID",), env_values)
                else None
            ),
            report_interval_hours=int(
                _first_nonempty(
                    ("EDGE_AGENT_REPORT_INTERVAL_HOURS", "EDGE_AGENT_TELEGRAM_REPORT_INTERVAL_HOURS"),
                    env_values,
                )
                or "4"
            ),
            daily_report_hour_utc=int(
                _first_nonempty(("EDGE_AGENT_DAILY_REPORT_HOUR_UTC",), env_values)
                or "21"
            ),
            approval_timeout_seconds=int(
                _first_nonempty(("EDGE_AGENT_APPROVAL_TIMEOUT_SECONDS",), env_values)
                or "300"
            ),
        )

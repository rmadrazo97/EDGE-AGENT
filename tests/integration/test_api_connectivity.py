"""Integration checks for the local Hummingbot API stack."""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest


API_BASE_URL = os.getenv("EDGE_AGENT_API_URL", "http://localhost:8000")
API_USERNAME = os.getenv("EDGE_AGENT_API_USERNAME")
API_PASSWORD = os.getenv("EDGE_AGENT_API_PASSWORD")
API_ENV_PATH = Path(__file__).resolve().parents[2] / "infra" / "env" / "api.env"


def _load_local_api_credentials() -> tuple[str, str]:
    if API_USERNAME and API_PASSWORD:
        return API_USERNAME, API_PASSWORD

    if API_ENV_PATH.exists():
        values: dict[str, str] = {}
        for line in API_ENV_PATH.read_text().splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()

        username = values.get("USERNAME")
        password = values.get("PASSWORD")
        if username and password:
            return username, password

    return "admin", "admin"


def _require_live_api() -> tuple[str, str]:
    username, password = _load_local_api_credentials()

    try:
        response = httpx.get(
            f"{API_BASE_URL}/health",
            timeout=2.0,
        )
    except httpx.HTTPError as exc:
        pytest.skip(f"Hummingbot API is not reachable: {exc}")

    if response.status_code != 200:
        pytest.skip(f"Hummingbot API health check returned {response.status_code}")

    return username, password


@pytest.fixture(scope="module")
def api_client() -> httpx.Client:
    username, password = _require_live_api()

    with httpx.Client(
        base_url=API_BASE_URL,
        auth=(username, password),
        timeout=10.0,
    ) as client:
        yield client


def test_accounts_endpoint_returns_account_names(api_client: httpx.Client) -> None:
    response = api_client.get("/accounts/")
    response.raise_for_status()

    payload = response.json()
    assert isinstance(payload, list)
    assert all(isinstance(account_name, str) for account_name in payload)


def test_market_data_prices_endpoint_returns_expected_shape(api_client: httpx.Client) -> None:
    response = api_client.post(
        "/market-data/prices",
        json={
            "connector_name": "binance_perpetual_testnet",
            "trading_pairs": ["BTC-USDT", "ETH-USDT"],
        },
    )
    response.raise_for_status()

    payload = response.json()
    assert payload["connector"] == "binance_perpetual_testnet"
    assert isinstance(payload["prices"], dict)
    assert set(payload["prices"]) == {"BTC-USDT", "ETH-USDT"}
    assert all(isinstance(price, (int, float)) for price in payload["prices"].values())
    assert isinstance(payload["timestamp"], (int, float))


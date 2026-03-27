"""Thin wrappers around the Hummingbot market data API."""

from __future__ import annotations

from clients.base import HummingbotAPIClient
from shared.models import Candle, FundingRateInfo, MarketPrice, OrderBookSnapshot, Ticker24h


class MarketDataClient(HummingbotAPIClient):
    def get_price(self, pair: str) -> MarketPrice:
        payload = self._request_json(
            "POST",
            "/market-data/prices",
            json={
                "connector_name": self.settings.market_data_connector,
                "trading_pairs": [pair],
            },
        )
        return MarketPrice(
            connector_name=payload["connector"],
            trading_pair=pair,
            price=float(payload["prices"][pair]),
            timestamp=float(payload["timestamp"]),
        )

    def get_funding_rate(self, pair: str) -> FundingRateInfo:
        payload = self._request_json(
            "POST",
            "/market-data/funding-info",
            json={
                "connector_name": self.settings.market_data_connector,
                "trading_pair": pair,
            },
        )
        return FundingRateInfo.model_validate(payload)

    def get_order_book(self, pair: str, depth: int = 10) -> OrderBookSnapshot:
        payload = self._request_json(
            "POST",
            "/market-data/order-book",
            json={
                "connector_name": self.settings.market_data_connector,
                "trading_pair": pair,
                "depth": depth,
            },
        )
        return OrderBookSnapshot.model_validate(payload)

    def get_klines(self, pair: str, interval: str = "1m", limit: int = 100) -> list[Candle]:
        payload = self._request_json(
            "POST",
            "/market-data/candles",
            json={
                "connector_name": self.settings.candles_connector,
                "trading_pair": pair,
                "interval": interval,
                "max_records": limit,
            },
        )
        return [Candle.model_validate(candle) for candle in payload]

    def get_ticker_24h(self, pair: str) -> Ticker24h:
        candles = self.get_klines(pair, interval="1h", limit=24)
        if not candles:
            raise ValueError(f"No candle data returned for {pair}")

        open_price = candles[0].open
        last_price = candles[-1].close
        high_price = max(candle.high for candle in candles)
        low_price = min(candle.low for candle in candles)
        base_volume = sum(candle.volume for candle in candles)
        quote_volume = sum(candle.quote_asset_volume for candle in candles)
        price_change = last_price - open_price
        price_change_percent = 0.0 if open_price == 0 else (price_change / open_price) * 100

        return Ticker24h(
            connector_name=self.settings.candles_connector,
            trading_pair=pair,
            open_price=open_price,
            last_price=last_price,
            high_price=high_price,
            low_price=low_price,
            base_volume=base_volume,
            quote_volume=quote_volume,
            price_change=price_change,
            price_change_percent=price_change_percent,
        )


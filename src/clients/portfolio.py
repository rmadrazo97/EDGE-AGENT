"""Portfolio and positions wrappers for the Hummingbot API."""

from __future__ import annotations

from clients.base import HummingbotAPIClient
from shared.models import Balance, OpenPosition, Pagination, PositionsResponse


class PortfolioClient(HummingbotAPIClient):
    def get_balances(self) -> list[Balance]:
        payload = self._request_json(
            "POST",
            "/portfolio/state",
            json={
                "account_names": [self.settings.account_name],
                "connector_names": [self.settings.market_data_connector],
                "skip_gateway": True,
                "refresh": True,
            },
        )

        balances: list[Balance] = []
        for account_name, connectors in payload.items():
            for connector_name, connector_balances in connectors.items():
                for raw_balance in connector_balances:
                    balances.append(
                        Balance(
                            account_name=account_name,
                            connector_name=connector_name,
                            token=str(raw_balance["token"]),
                            units=float(raw_balance["units"]),
                            available_units=float(raw_balance["available_units"]),
                            price=float(raw_balance["price"]),
                            value=float(raw_balance["value"]),
                        )
                    )
        return balances

    def get_positions(self) -> list[OpenPosition]:
        payload = self._request_json(
            "POST",
            "/trading/positions",
            json={
                "account_names": [self.settings.account_name],
                "connector_names": [self.settings.market_data_connector],
            },
        )

        typed_response = PositionsResponse(
            data=[OpenPosition.model_validate(position) for position in payload["data"]],
            pagination=Pagination.model_validate(payload["pagination"]),
        )
        return typed_response.data


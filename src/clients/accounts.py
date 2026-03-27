"""Accounts and credential bootstrap helpers for Hummingbot API."""

from __future__ import annotations

from typing import Any

from clients.base import HummingbotAPIClient


class AccountsClient(HummingbotAPIClient):
    connector_name = "binance_perpetual_testnet"

    def list_accounts(self) -> list[str]:
        payload = self._request_json("GET", "/accounts/")
        return [str(account_name) for account_name in payload]

    def ensure_account(self, account_name: str | None = None) -> str:
        target_account = account_name or self.settings.account_name
        if target_account in self.list_accounts():
            return target_account

        self._request_json(
            "POST",
            "/accounts/add-account",
            params={"account_name": target_account},
            expected_statuses=(200, 201),
        )
        return target_account

    def get_connector_config_map(self, connector_name: str | None = None) -> dict[str, Any]:
        target_connector = connector_name or self.connector_name
        return self._request_json("GET", f"/connectors/{target_connector}/config-map")

    def add_credentials(
        self,
        account_name: str,
        connector_name: str,
        credentials: dict[str, Any],
    ) -> Any:
        return self._request_json(
            "POST",
            f"/accounts/add-credential/{account_name}/{connector_name}",
            json=credentials,
            expected_statuses=(200, 201),
        )

    def connect_binance_testnet(self, account_name: str | None = None) -> dict[str, str]:
        api_key = self.settings.binance_testnet_api_key
        api_secret = self.settings.binance_testnet_api_secret

        if not api_key or not api_secret:
            raise ValueError(
                "Missing Binance testnet credentials. Set BINANCE_TESTNET_API_KEY and "
                "BINANCE_TESTNET_API_SECRET in your local environment."
            )

        target_account = self.ensure_account(account_name)
        config_map = self.get_connector_config_map(self.connector_name)
        payload = {
            "binance_perpetual_testnet_api_key": api_key,
            "binance_perpetual_testnet_api_secret": api_secret,
        }
        required_keys = {name for name, field in config_map.items() if field.get("required")}
        missing_keys = [key for key in required_keys if not payload.get(key)]
        if missing_keys:
            raise ValueError(
                f"Missing required connector credential values for {self.connector_name}: {missing_keys}"
            )

        self.add_credentials(target_account, self.connector_name, payload)
        return {
            "account_name": target_account,
            "connector_name": self.connector_name,
            "status": "connected",
        }


def main() -> None:
    with AccountsClient() as client:
        result = client.connect_binance_testnet()
        print(
            f"Configured {result['connector_name']} on account {result['account_name']} "
            f"with environment-provided credentials."
        )


if __name__ == "__main__":
    main()


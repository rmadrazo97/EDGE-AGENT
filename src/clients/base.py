"""Reusable Hummingbot API client primitives."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import httpx

from shared.config import ClientSettings


class HummingbotAPIError(RuntimeError):
    """Raised when the Hummingbot API returns an error response."""

    def __init__(self, message: str, *, status_code: int | None = None, detail: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class HummingbotAPIConnectionError(HummingbotAPIError):
    """Raised when the Hummingbot API cannot be reached."""


class HummingbotAPIClient:
    def __init__(
        self,
        settings: ClientSettings | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings or ClientSettings.from_env()
        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.Client(
            base_url=self.settings.api_base_url.rstrip("/"),
            auth=(self.settings.api_username, self.settings.api_password),
            timeout=self.settings.api_timeout,
        )

    def close(self) -> None:
        if self._owns_http_client:
            self._http_client.close()

    def __enter__(self) -> "HummingbotAPIClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        expected_statuses: Iterable[int] = (200,),
        **kwargs: Any,
    ) -> Any:
        try:
            response = self._http_client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise HummingbotAPIConnectionError(
                f"Failed to reach Hummingbot API at {self.settings.api_base_url}: {exc}"
            ) from exc

        if response.status_code not in set(expected_statuses):
            detail: Any
            try:
                payload = response.json()
                detail = payload.get("detail", payload)
            except ValueError:
                detail = response.text

            raise HummingbotAPIError(
                f"Hummingbot API error {response.status_code} for {method} {path}",
                status_code=response.status_code,
                detail=detail,
            )

        if not response.content:
            return None
        return response.json()


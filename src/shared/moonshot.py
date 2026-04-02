"""Minimal Moonshot API client for structured analyst outputs."""

from __future__ import annotations

import json
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

from shared.config import ClientSettings


class MoonshotAPIError(RuntimeError):
    """Raised when the Moonshot API returns an error or invalid output."""


class MoonshotToolCallFunction(BaseModel):
    name: str
    arguments: str


class MoonshotToolCall(BaseModel):
    id: str | None = None
    type: str
    function: MoonshotToolCallFunction


class MoonshotMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: str
    content: str | None = None
    tool_calls: list[MoonshotToolCall] = Field(default_factory=list)


class MoonshotChoice(BaseModel):
    index: int
    message: MoonshotMessage
    finish_reason: str | None = None


class MoonshotCompletion(BaseModel):
    id: str | None = None
    choices: list[MoonshotChoice]


class MoonshotClient:
    def __init__(
        self,
        settings: ClientSettings | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings or ClientSettings.from_env()
        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.Client(
            base_url=self.settings.moonshot_api_base_url.rstrip("/"),
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self.settings.moonshot_api_key}",
                "Content-Type": "application/json",
            },
        )

    def close(self) -> None:
        if self._owns_http_client:
            self._http_client.close()

    def __enter__(self) -> "MoonshotClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def chat_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict[str, Any]],
        tool_choice: str = "auto",
        temperature: float = 1.0,
    ) -> MoonshotCompletion:
        if not self.settings.moonshot_api_key:
            raise MoonshotAPIError("Missing MOONSHOT_API_KEY in local environment.")

        try:
            response = self._http_client.post(
                "/chat/completions",
                json={
                    "model": self.settings.moonshot_model,
                    "temperature": temperature,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "tools": tools,
                    "tool_choice": tool_choice,
                },
            )
        except httpx.TimeoutException as exc:
            raise MoonshotAPIError(f"Moonshot API request timed out: {exc}") from exc
        except httpx.NetworkError as exc:
            raise MoonshotAPIError(f"Moonshot API network error: {exc}") from exc
        if response.status_code != 200:
            detail = response.text
            try:
                detail = response.json()
            except ValueError:
                pass
            raise MoonshotAPIError(
                f"Moonshot API error {response.status_code}: {detail}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise MoonshotAPIError("Moonshot API returned invalid JSON.") from exc

        return MoonshotCompletion.model_validate(payload)

    @staticmethod
    def parse_tool_arguments(tool_call: MoonshotToolCall) -> dict[str, Any]:
        try:
            return json.loads(tool_call.function.arguments)
        except json.JSONDecodeError as exc:
            raise MoonshotAPIError(
                f"Moonshot tool call returned invalid JSON arguments: {tool_call.function.arguments}"
            ) from exc

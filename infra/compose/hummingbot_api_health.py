"""Extend the upstream Hummingbot API app with a lightweight health endpoint."""

from main import app


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


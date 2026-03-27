"""Unit coverage for local configuration helpers."""

from __future__ import annotations

from pathlib import Path

from shared.config import ClientSettings, _first_nonempty, _is_placeholder, _parse_env_file


def test_parse_env_file_ignores_comments_and_blank_lines(tmp_path: Path) -> None:
    env_file = tmp_path / "sample.env"
    env_file.write_text(
        "\n".join(
            [
                "# comment",
                "",
                "USERNAME=admin",
                "PASSWORD=secret-value",
            ]
        )
    )

    parsed = _parse_env_file(env_file)

    assert parsed == {
        "USERNAME": "admin",
        "PASSWORD": "secret-value",
    }


def test_placeholder_detection_matches_example_format() -> None:
    assert _is_placeholder("your_binance_api_key_here") is True
    assert _is_placeholder("real-looking-value") is False
    assert _is_placeholder(None) is False


def test_first_nonempty_skips_placeholders() -> None:
    values = {
        "PRIMARY": "your_primary_here",
        "SECONDARY": "actual-value",
    }

    selected = _first_nonempty(("PRIMARY", "SECONDARY"), values)

    assert selected == "actual-value"


def test_client_settings_reads_telegram_fields_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:token")
    monkeypatch.setenv("TELEGRAM_OPERATOR_CHAT_ID", "12345")
    monkeypatch.setenv("EDGE_AGENT_TELEGRAM_REPORT_INTERVAL_HOURS", "6")
    monkeypatch.setenv("EDGE_AGENT_TELEGRAM_DAILY_REPORT_TIME", "22:15")
    monkeypatch.setenv("EDGE_AGENT_TIMEZONE", "Europe/Madrid")

    settings = ClientSettings.from_env()

    assert settings.telegram_bot_token == "123456:token"
    assert settings.telegram_operator_chat_id == 12345
    assert settings.telegram_report_interval_hours == 6
    assert settings.telegram_daily_report_time == "22:15"
    assert str(settings.timezone) == "Europe/Madrid"

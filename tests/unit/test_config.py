"""Unit coverage for local configuration helpers."""

from __future__ import annotations

from pathlib import Path

from shared.config import _first_nonempty, _is_placeholder, _parse_env_file


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

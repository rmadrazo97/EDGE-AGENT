"""Unit tests for the signal_export and signal_metrics CLI tools."""

from __future__ import annotations

import csv
from pathlib import Path

from tools.signal_export import main as export_main
from tools.signal_metrics import main as metrics_main


def test_signal_export_empty_runtime_dirs(tmp_path: Path) -> None:
    """signal_export should not crash when runtime directories are empty and
    should produce a CSV containing only headers."""
    analyst_dir = tmp_path / "analyst"
    trader_dir = tmp_path / "trader"
    analyst_dir.mkdir()
    trader_dir.mkdir()

    output_csv = tmp_path / "out.csv"
    export_main([
        "--analyst-dir", str(analyst_dir),
        "--trader-dir", str(trader_dir),
        "--output", str(output_csv),
    ])

    assert output_csv.exists()
    with output_csv.open(newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    assert rows == []
    # Headers should still be present
    with output_csv.open() as fh:
        header_line = fh.readline()
    assert "pair" in header_line
    assert "side" in header_line


def test_signal_metrics_empty_csv(tmp_path: Path, capsys: object) -> None:
    """signal_metrics should print a 'no data' message when fed an empty CSV."""
    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("pair,side,confidence\n")  # headers only

    metrics_main(["--input", str(empty_csv)])

    captured = capsys.readouterr()  # type: ignore[union-attr]
    assert "no data" in captured.out.lower() or "No data" in captured.out

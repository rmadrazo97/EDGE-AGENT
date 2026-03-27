"""Export analyst signals and matched trade outcomes to CSV.

Usage:
    python3 -m tools.signal_export --output signals.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Defaults -----------------------------------------------------------------

RUNTIME_DIR = Path(__file__).resolve().parent.parent / "runtime"
ANALYST_DIR = RUNTIME_DIR / "analyst"
TRADER_DIR = RUNTIME_DIR / "trader"

CSV_COLUMNS = [
    "timestamp",
    "pair",
    "side",
    "confidence",
    "entry_price",
    "stop_loss_price",
    "reasoning",
    "was_executed",
    "realized_pnl",
    "exit_reason",
    "duration_minutes",
]

# Maximum seconds between signal and trade to consider them matched.
MATCH_WINDOW_SECONDS = 300  # 5 minutes


# Helpers ------------------------------------------------------------------

def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file, skipping malformed lines."""
    records: list[dict[str, Any]] = []
    try:
        with path.open() as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return records


def _parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    # Support both with and without timezone
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


# Core logic ---------------------------------------------------------------

def collect_signals(analyst_dir: Path) -> list[dict[str, Any]]:
    """Return all signal_generated and signal_filtered events."""
    signals: list[dict[str, Any]] = []
    if not analyst_dir.is_dir():
        return signals
    for path in sorted(analyst_dir.glob("*.jsonl")):
        for record in _read_jsonl(path):
            status = record.get("status")
            if status not in ("signal_generated", "signal_filtered"):
                continue
            signals.append(record)
    return signals


def collect_trades(trader_dir: Path) -> list[dict[str, Any]]:
    """Return trade_opened and position_closed events."""
    trades: list[dict[str, Any]] = []
    if not trader_dir.is_dir():
        return trades
    for path in sorted(trader_dir.glob("*.jsonl")):
        for record in _read_jsonl(path):
            event = record.get("event")
            if event in ("trade_opened", "position_closed"):
                trades.append(record)
    return trades


def _match_trade(
    signal: dict[str, Any],
    opens: list[dict[str, Any]],
    closes: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Find a trade_opened event matching the signal by pair + timestamp proximity."""
    sig_ts = _parse_ts(signal.get("timestamp"))
    sig_pair = signal.get("pair")
    sig_signal = signal.get("signal") or {}
    sig_side = sig_signal.get("side")

    if sig_ts is None or sig_pair is None:
        return None

    best: dict[str, Any] | None = None
    best_delta = float("inf")

    for opened in opens:
        details = opened.get("details", {})
        if details.get("pair") != sig_pair:
            continue
        if sig_side and details.get("side") != sig_side:
            continue
        open_ts = _parse_ts(opened.get("timestamp"))
        if open_ts is None:
            continue
        delta = abs((open_ts - sig_ts).total_seconds())
        if delta <= MATCH_WINDOW_SECONDS and delta < best_delta:
            best_delta = delta
            best = opened

    if best is None:
        return None

    # Try to find a matching close
    open_ts = _parse_ts(best.get("timestamp"))
    open_pair = best.get("details", {}).get("pair")
    for closed in closes:
        details = closed.get("details", {})
        if details.get("pair") != open_pair:
            continue
        close_ts = _parse_ts(closed.get("timestamp"))
        if close_ts is None or open_ts is None:
            continue
        if close_ts >= open_ts:
            return {
                "was_executed": True,
                "realized_pnl": details.get("realized_pnl"),
                "exit_reason": details.get("reason"),
                "entry_price_actual": best.get("details", {}).get("entry_price"),
                "exit_price": details.get("exit_price"),
                "duration_seconds": details.get("duration_seconds"),
            }

    # Opened but not yet closed
    return {
        "was_executed": True,
        "realized_pnl": None,
        "exit_reason": None,
        "entry_price_actual": best.get("details", {}).get("entry_price"),
        "exit_price": None,
        "duration_seconds": None,
    }


def build_rows(
    signals: list[dict[str, Any]],
    trades: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build CSV-ready rows by matching signals to trades."""
    opens = [t for t in trades if t.get("event") == "trade_opened"]
    closes = [t for t in trades if t.get("event") == "position_closed"]

    rows: list[dict[str, Any]] = []
    for sig in signals:
        sig_data = sig.get("signal") or {}
        status = sig.get("status")

        # For filtered signals there is no signal payload
        pair = sig.get("pair") or sig_data.get("pair", "")
        side = sig_data.get("side", "")
        confidence = sig_data.get("confidence", "")
        entry_price = sig_data.get("entry_price", "")
        stop_loss_price = sig_data.get("stop_loss_price", "")
        reasoning = sig_data.get("reasoning", sig.get("reason", ""))

        row: dict[str, Any] = {
            "timestamp": sig.get("timestamp", ""),
            "pair": pair,
            "side": side,
            "confidence": confidence,
            "entry_price": entry_price,
            "stop_loss_price": stop_loss_price,
            "reasoning": reasoning,
            "was_executed": False,
            "realized_pnl": "",
            "exit_reason": "",
            "duration_minutes": "",
        }

        if status == "signal_generated":
            match = _match_trade(sig, opens, closes)
            if match:
                row["was_executed"] = match["was_executed"]
                if match["realized_pnl"] is not None:
                    row["realized_pnl"] = match["realized_pnl"]
                if match["exit_reason"]:
                    row["exit_reason"] = match["exit_reason"]
                if match["duration_seconds"] is not None:
                    row["duration_minutes"] = round(match["duration_seconds"] / 60, 2)

        rows.append(row)
    return rows


def export_csv(rows: list[dict[str, Any]], output: Path) -> None:
    with output.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


# CLI ----------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Export analyst signals to CSV with matched trade outcomes.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="signals.csv",
        help="Output CSV path (default: signals.csv)",
    )
    parser.add_argument(
        "--analyst-dir",
        type=str,
        default=str(ANALYST_DIR),
        help="Path to analyst JSONL directory",
    )
    parser.add_argument(
        "--trader-dir",
        type=str,
        default=str(TRADER_DIR),
        help="Path to trader JSONL directory",
    )
    args = parser.parse_args(argv)

    analyst_dir = Path(args.analyst_dir)
    trader_dir = Path(args.trader_dir)
    output = Path(args.output)

    signals = collect_signals(analyst_dir)
    if not signals:
        print("No signal data found in", analyst_dir)
        print("CSV written with headers only.")
        export_csv([], output)
        return

    trades = collect_trades(trader_dir)
    rows = build_rows(signals, trades)
    export_csv(rows, output)
    print(f"Exported {len(rows)} signals to {output}")


if __name__ == "__main__":
    main()

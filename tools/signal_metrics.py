"""Calculate signal quality metrics from exported CSV.

Usage:
    python3 -m tools.signal_metrics --input signals.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any


# Helpers ------------------------------------------------------------------

def _safe_float(val: Any) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes")
    return bool(val)


def _confidence_bucket(conf: float | None) -> str:
    if conf is None:
        return "unknown"
    if conf < 0.8:
        return "0.70-0.80"
    if conf < 0.9:
        return "0.80-0.90"
    return "0.90-1.00"


# Metrics ------------------------------------------------------------------

class MetricsGroup:
    """Holds metrics for a subset of signals."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.total_signals = 0
        self.executed = 0
        self.wins = 0
        self.losses = 0
        self.win_pnls: list[float] = []
        self.loss_pnls: list[float] = []
        self.durations: list[float] = []
        self.cumulative_pnls: list[float] = []

    def add(self, row: dict[str, str]) -> None:
        self.total_signals += 1
        was_exec = _safe_bool(row.get("was_executed", ""))
        if was_exec:
            self.executed += 1
        pnl = _safe_float(row.get("realized_pnl"))
        if pnl is not None:
            running = (self.cumulative_pnls[-1] if self.cumulative_pnls else 0.0) + pnl
            self.cumulative_pnls.append(running)
            if pnl >= 0:
                self.wins += 1
                self.win_pnls.append(pnl)
            else:
                self.losses += 1
                self.loss_pnls.append(pnl)
        dur = _safe_float(row.get("duration_minutes"))
        if dur is not None:
            self.durations.append(dur)

    def execution_rate(self) -> str:
        if self.total_signals == 0:
            return "-"
        return f"{self.executed / self.total_signals * 100:.1f}%"

    def win_rate(self) -> str:
        total_closed = self.wins + self.losses
        if total_closed == 0:
            return "-"
        return f"{self.wins / total_closed * 100:.1f}%"

    def avg_win(self) -> str:
        if not self.win_pnls:
            return "-"
        return f"{sum(self.win_pnls) / len(self.win_pnls):.4f}"

    def avg_loss(self) -> str:
        if not self.loss_pnls:
            return "-"
        return f"{sum(self.loss_pnls) / len(self.loss_pnls):.4f}"

    def reward_to_risk(self) -> str:
        if not self.win_pnls or not self.loss_pnls:
            return "-"
        avg_w = sum(self.win_pnls) / len(self.win_pnls)
        avg_l = abs(sum(self.loss_pnls) / len(self.loss_pnls))
        if avg_l == 0:
            return "-"
        return f"{avg_w / avg_l:.2f}"

    def max_drawdown(self) -> str:
        if not self.cumulative_pnls:
            return "-"
        peak = self.cumulative_pnls[0]
        dd = 0.0
        for val in self.cumulative_pnls:
            if val > peak:
                peak = val
            dd = min(dd, val - peak)
        return f"{dd:.4f}"

    def avg_duration(self) -> str:
        if not self.durations:
            return "-"
        return f"{sum(self.durations) / len(self.durations):.2f} min"

    def summary_dict(self) -> dict[str, str]:
        return {
            "signal_count": str(self.total_signals),
            "execution_rate": self.execution_rate(),
            "win_rate": self.win_rate(),
            "avg_win": self.avg_win(),
            "avg_loss": self.avg_loss(),
            "reward_to_risk": self.reward_to_risk(),
            "max_drawdown": self.max_drawdown(),
            "avg_duration": self.avg_duration(),
        }


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader)


def compute_metrics(rows: list[dict[str, str]]) -> dict[str, MetricsGroup]:
    """Return metrics groups keyed by label."""
    groups: dict[str, MetricsGroup] = {}

    def _get(label: str) -> MetricsGroup:
        if label not in groups:
            groups[label] = MetricsGroup(label)
        return groups[label]

    overall = _get("OVERALL")
    for row in rows:
        overall.add(row)

        # By pair
        pair = row.get("pair", "unknown")
        _get(f"pair:{pair}").add(row)

        # By side
        side = row.get("side", "unknown")
        if side:
            _get(f"side:{side}").add(row)

        # By confidence bucket
        conf = _safe_float(row.get("confidence"))
        bucket = _confidence_bucket(conf)
        _get(f"conf:{bucket}").add(row)

    return groups


# Display ------------------------------------------------------------------

METRIC_LABELS = [
    ("signal_count", "Signals"),
    ("execution_rate", "Exec Rate"),
    ("win_rate", "Win Rate"),
    ("avg_win", "Avg Win"),
    ("avg_loss", "Avg Loss"),
    ("reward_to_risk", "R:R"),
    ("max_drawdown", "Max DD"),
    ("avg_duration", "Avg Dur"),
]


def format_table(groups: dict[str, MetricsGroup]) -> str:
    """Return a formatted text table."""
    # Sort: OVERALL first, then alphabetically
    keys = sorted(groups.keys(), key=lambda k: ("0" if k == "OVERALL" else "1") + k)
    summaries = {k: groups[k].summary_dict() for k in keys}

    # Column widths
    label_w = max(len(k) for k in keys) + 2
    col_widths: dict[str, int] = {}
    for key, header in METRIC_LABELS:
        w = len(header)
        for s in summaries.values():
            w = max(w, len(s[key]))
        col_widths[key] = w + 2

    # Header
    header_parts = [f"{'Group':<{label_w}}"]
    for key, header in METRIC_LABELS:
        header_parts.append(f"{header:>{col_widths[key]}}")
    header_line = "".join(header_parts)
    sep = "-" * len(header_line)

    lines = [sep, header_line, sep]
    for k in keys:
        parts = [f"{k:<{label_w}}"]
        for key, _ in METRIC_LABELS:
            parts.append(f"{summaries[k][key]:>{col_widths[key]}}")
        lines.append("".join(parts))
    lines.append(sep)
    return "\n".join(lines)


# CLI ----------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Calculate signal quality metrics from exported CSV.",
    )
    parser.add_argument(
        "--input",
        type=str,
        default="signals.csv",
        help="Input CSV path (default: signals.csv)",
    )
    args = parser.parse_args(argv)

    rows = load_csv(Path(args.input))
    if not rows:
        print("No data found. Run signal_export first to generate the CSV.")
        return

    groups = compute_metrics(rows)
    print(format_table(groups))


if __name__ == "__main__":
    main()

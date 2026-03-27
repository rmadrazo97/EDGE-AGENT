"""Append a dated signal quality entry to the OpenClaw memory journal.

Runs the full pipeline: export signals -> compute metrics -> append summary.

Usage:
    python3 -m tools.signal_journal_update
"""

from __future__ import annotations

import argparse
import tempfile
from datetime import date
from pathlib import Path

from tools.signal_export import (
    ANALYST_DIR,
    TRADER_DIR,
    build_rows,
    collect_signals,
    collect_trades,
    export_csv,
)
from tools.signal_metrics import compute_metrics, load_csv

JOURNAL_PATH = (
    Path(__file__).resolve().parent.parent
    / "openclaw"
    / "workspace"
    / "memory"
    / "signals.md"
)


def _build_entry(groups: dict) -> str:
    """Build a Markdown journal entry from metrics groups."""
    overall = groups.get("OVERALL")
    if overall is None:
        return ""

    s = overall.summary_dict()
    today = date.today().isoformat()

    lines = [
        f"### {today} -- Automated metrics snapshot",
        "",
        f"- **Signals**: {s['signal_count']}",
        f"- **Execution rate**: {s['execution_rate']}",
        f"- **Win rate**: {s['win_rate']}",
        f"- **Avg win**: {s['avg_win']}",
        f"- **Avg loss**: {s['avg_loss']}",
        f"- **Reward-to-risk**: {s['reward_to_risk']}",
        f"- **Max drawdown**: {s['max_drawdown']}",
        f"- **Avg duration**: {s['avg_duration']}",
        "",
    ]

    # Breakdowns
    pair_keys = sorted(k for k in groups if k.startswith("pair:"))
    if pair_keys:
        lines.append("**By pair:**")
        for k in pair_keys:
            d = groups[k].summary_dict()
            lines.append(
                f"- {k}: signals={d['signal_count']}, "
                f"win_rate={d['win_rate']}, R:R={d['reward_to_risk']}"
            )
        lines.append("")

    side_keys = sorted(k for k in groups if k.startswith("side:"))
    if side_keys:
        lines.append("**By side:**")
        for k in side_keys:
            d = groups[k].summary_dict()
            lines.append(
                f"- {k}: signals={d['signal_count']}, "
                f"win_rate={d['win_rate']}, R:R={d['reward_to_risk']}"
            )
        lines.append("")

    conf_keys = sorted(k for k in groups if k.startswith("conf:"))
    if conf_keys:
        lines.append("**By confidence bucket:**")
        for k in conf_keys:
            d = groups[k].summary_dict()
            lines.append(
                f"- {k}: signals={d['signal_count']}, "
                f"win_rate={d['win_rate']}, R:R={d['reward_to_risk']}"
            )
        lines.append("")

    lines.append("**What to try next:** Review worst-performing pair/side and consider adjusting confidence threshold or prompt tuning.")
    lines.append("")

    return "\n".join(lines)


def append_to_journal(entry: str, journal_path: Path) -> None:
    """Append entry to the signals journal, replacing the placeholder if present."""
    if not journal_path.exists():
        journal_path.parent.mkdir(parents=True, exist_ok=True)
        journal_path.write_text(f"# Signal Quality Notes\n\n## Entries\n\n{entry}\n")
        return

    content = journal_path.read_text()

    # Remove placeholder line if present
    placeholder = "_No entries yet. Will be populated after live trading begins._"
    content = content.replace(placeholder, "")

    # Append under ## Entries
    if "## Entries" in content:
        content = content.rstrip() + "\n\n" + entry + "\n"
    else:
        content = content.rstrip() + "\n\n## Entries\n\n" + entry + "\n"

    journal_path.write_text(content)


# CLI ----------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Update OpenClaw signal journal with latest metrics.",
    )
    parser.add_argument(
        "--journal",
        type=str,
        default=str(JOURNAL_PATH),
        help="Path to signals.md journal",
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
    journal_path = Path(args.journal)

    # Step 1: export
    signals = collect_signals(analyst_dir)
    if not signals:
        print("No signal data found. Nothing to add to journal.")
        return

    trades = collect_trades(trader_dir)
    rows = build_rows(signals, trades)

    # Step 2: write temp CSV and compute metrics
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    export_csv(rows, tmp_path)
    csv_rows = load_csv(tmp_path)
    tmp_path.unlink(missing_ok=True)

    if not csv_rows:
        print("No signals to report.")
        return

    groups = compute_metrics(csv_rows)

    # Step 3: build entry and append
    entry = _build_entry(groups)
    if not entry:
        print("Could not build metrics entry.")
        return

    append_to_journal(entry, journal_path)
    print(f"Journal updated: {journal_path}")


if __name__ == "__main__":
    main()

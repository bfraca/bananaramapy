"""Persistent cost log stored at ``~/.bananarama/cost-log.csv``.

Each generation run appends one row per model used.  The
``bananarama costs`` CLI command reads this file back to show
spend summaries.
"""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

_LOG_DIR = Path.home() / ".bananarama"
_LOG_PATH = _LOG_DIR / "cost-log.csv"
_FIELDNAMES = ["timestamp", "config_path", "model", "images_generated", "total_cost"]


# ------------------------------------------------------------------
# Writing
# ------------------------------------------------------------------


def _ensure_log_file() -> Path:
    """Create the log directory and CSV header if they don't exist."""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not _LOG_PATH.exists():
        with open(_LOG_PATH, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
            writer.writeheader()
    return _LOG_PATH


def append_run(
    config_path: str,
    model: str,
    images_generated: int,
    total_cost: float,
) -> None:
    """Append a single run entry to the cost log."""
    path = _ensure_log_file()
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
        writer.writerow(
            {
                "timestamp": datetime.now(tz=UTC).isoformat(timespec="seconds"),
                "config_path": config_path,
                "model": model,
                "images_generated": images_generated,
                "total_cost": f"{total_cost:.6f}",
            }
        )


# ------------------------------------------------------------------
# Reading
# ------------------------------------------------------------------


def _read_rows() -> list[dict[str, str]]:
    """Read all rows from the cost log CSV."""
    if not _LOG_PATH.exists():
        return []
    with open(_LOG_PATH, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def total_spend() -> float:
    """Return the total spend across all logged runs."""
    return sum(float(row["total_cost"]) for row in _read_rows())


def spend_by_model() -> dict[str, float]:
    """Return a dict mapping model name to cumulative spend."""
    totals: dict[str, float] = {}
    for row in _read_rows():
        model = row["model"]
        totals[model] = totals.get(model, 0.0) + float(row["total_cost"])
    return totals


def last_runs(n: int = 10) -> list[dict[str, str]]:
    """Return the last *n* log entries (most recent first)."""
    rows = _read_rows()
    return list(reversed(rows[-n:]))


def log_path() -> Path:
    """Return the path to the cost log file."""
    return _LOG_PATH


def set_log_path(path: Path) -> None:
    """Override the log path (used for testing)."""
    global _LOG_DIR, _LOG_PATH
    _LOG_DIR = path.parent
    _LOG_PATH = path

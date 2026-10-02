"""Fetch/refresh all series into the local SQLite database.

Usage:  python scripts/refresh.py [--force]
Schedule it with cron (e.g. hourly) or let the dashboard refresh on load.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from oil_tracker.data import database as db  # noqa: E402
from oil_tracker.data.pipeline import refresh  # noqa: E402
from oil_tracker.service import build_context  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="ignore freshness and refetch everything")
    args = ap.parse_args()
    rep = refresh(force=args.force)
    for k, n in rep.updated.items():
        print(f"  updated  {k:<16} {n:>6} rows")
    for k, e in rep.errors.items():
        print(f"  ERROR    {k:<16} {e}")
    print(f"  skipped (fresh): {len(rep.skipped)}")
    db.save_alerts(build_context()["alerts"])
    sys.exit(0 if rep.ok else 1)

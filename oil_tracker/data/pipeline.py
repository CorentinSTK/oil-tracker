"""Refresh pipeline: fetch -> normalise -> store.

Incremental: each series is refetched from a little before its last stored
date (to pick up revisions) and only when its refresh interval has elapsed.
A failing source is logged and skipped; the dashboard keeps serving stored
data and shows the error in the data-status panel.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from oil_tracker.data import database as db
from oil_tracker.data.fetchers import FetchError, fetch_series, fetch_snapshot
from oil_tracker.sources import REFRESH_HOURS, SERIES

# Overlap re-fetched on incremental updates so provider revisions are captured.
REVISION_WINDOW = {"D": pd.Timedelta(days=10), "W": pd.Timedelta(weeks=8), "M": pd.DateOffset(months=24)}
MAX_WORKERS = 6  # polite concurrency towards the EIA/FRED APIs


@dataclass
class RefreshReport:
    updated: dict[str, int] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


def _is_fresh(conn, key: str, hours: int) -> bool:
    row = conn.execute("SELECT last_success FROM fetch_log WHERE series_key=?", (key,)).fetchone()
    if not row or not row[0]:
        return False
    age = pd.Timestamp.now(tz="UTC") - pd.Timestamp(row[0])
    return age < pd.Timedelta(hours=hours)


def refresh(force: bool = False, keys: list[str] | None = None, snapshot: bool = True) -> RefreshReport:
    report = RefreshReport()
    with db.connect() as conn:
        todo: dict[str, date | None] = {}
        for key in keys or list(SERIES):
            s = SERIES[key]
            if not force and _is_fresh(conn, key, REFRESH_HOURS[s.frequency]):
                report.skipped.append(key)
                continue
            last = db.last_date(conn, key)
            # First load pulls the full history (a few thousand rows per series).
            todo[key] = (last - REVISION_WINDOW[s.frequency]).date() if last is not None else None

        # Network calls in parallel (I/O bound); all DB writes stay on this thread.
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(fetch_series, SERIES[k], start): k for k, start in todo.items()}
            for fut in as_completed(futures):
                key = futures[fut]
                try:
                    report.updated[key] = db.upsert_observations(conn, key, fut.result())
                    db.log_fetch(conn, key, None)
                except FetchError as exc:
                    report.errors[key] = str(exc)
                    db.log_fetch(conn, key, str(exc))
        conn.commit()

        if snapshot and (force or not _is_fresh(conn, "snapshot", 1)):
            try:
                db.insert_snapshots(conn, fetch_snapshot())
                db.log_fetch(conn, "snapshot", None)
                report.updated["snapshot"] = 1
            except FetchError as exc:
                report.errors["snapshot"] = str(exc)
                db.log_fetch(conn, "snapshot", str(exc))
        db.prune(conn)
    return report

"""Refresh pipeline: fetch -> normalise -> store.

Incremental: each series is refetched from a little before its last stored
date (to pick up revisions) and only when it is stale. "Stale" means:
- its refresh interval has elapsed (sources.REFRESH_HOURS), or
- for EIA weekly series, a new Weekly Petroleum Status Report has been
  released since the last successful fetch (Wed 10:30 ET, holiday-shifted).

There is no background scheduler: Streamlit Community Cloud apps sleep when
idle, so each visit triggers a staleness check instead. ``scripts/refresh.py``
can be put on cron for an always-on deployment.

A failing source is logged and skipped; the dashboard keeps serving stored
data and shows the error in the data-status panel.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import pandas as pd

from oil_tracker.catalysts import ET, eia_wpsr_dates
from oil_tracker.data import database as db
from oil_tracker.data.fetchers import (
    FetchError, fetch_futures, fetch_gpr, fetch_series, fetch_snapshot, fetch_steo_bulk,
)
from oil_tracker.sources import FUTURES_MONTHS_AHEAD, FUTURES_ROOTS, REFRESH_HOURS, SERIES

# Overlap re-fetched on incremental updates so provider revisions are captured.
REVISION_WINDOW = {"D": pd.Timedelta(days=10), "W": pd.Timedelta(weeks=8), "M": pd.DateOffset(months=24)}
MAX_WORKERS = 6  # polite concurrency towards the providers
STEO_TASK = "steo_bulk"
SOURCE_HOURS = {"gpr": 12, "futures": 6, "snapshot": 1}


@dataclass
class RefreshReport:
    updated: dict[str, int] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


def last_wpsr_release(now: datetime | None = None) -> pd.Timestamp:
    now = now or datetime.now(ET)
    past = [d for d in eia_wpsr_dates(now.date() - timedelta(days=14), now.date()) if d <= now]
    return pd.Timestamp(past[-1]).tz_convert("UTC")


def _last_success(conn, key: str) -> pd.Timestamp | None:
    row = conn.execute("SELECT last_success FROM fetch_log WHERE series_key=?", (key,)).fetchone()
    return pd.Timestamp(row[0]) if row and row[0] else None


def _is_fresh(conn, key: str, hours: float, not_before: pd.Timestamp | None = None) -> bool:
    last = _last_success(conn, key)
    if last is None:
        return False
    if not_before is not None and last < not_before:
        return False
    return pd.Timestamp.now(tz="UTC") - last < pd.Timedelta(hours=hours)


def _start(conn, key: str, freq: str) -> date | None:
    last = db.last_date(conn, key)
    # First load pulls the full history (a few thousand rows per series).
    return (last - REVISION_WINDOW[freq]).date() if last is not None else None


def refresh(force: bool = False, keys: list[str] | None = None, snapshot: bool = True) -> RefreshReport:
    report = RefreshReport()
    wpsr = last_wpsr_release()
    with db.connect() as conn:
        # Each task: name -> (fetch callable, store callable(result) -> rows, log keys)
        tasks: dict[str, tuple[Callable, Callable, list[str]]] = {}
        steo_due = []
        for key in keys or list(SERIES):
            s = SERIES[key]
            hours = SOURCE_HOURS.get(s.source, REFRESH_HOURS[s.frequency])
            not_before = None
            if s.source == "eia" and s.frequency == "W":
                not_before = wpsr
                # Released but not in our DB yet (fetched seconds too early): retry every 15 min.
                expected = (wpsr.tz_convert(ET) - pd.Timedelta(days=5)).normalize().tz_localize(None)
                last_obs = db.last_date(conn, key)
                if last_obs is not None and last_obs < expected - pd.Timedelta(days=1):
                    hours = 0.25
            if not force and _is_fresh(conn, key, hours, not_before):
                report.skipped.append(key)
                continue
            if s.source == "eia_steo":
                steo_due.append(s)
            elif s.source == "gpr":
                tasks[key] = (lambda k=key: fetch_gpr(k),
                              lambda df, k=key: db.upsert_observations(conn, k, df), [key])
            else:
                start = _start(conn, key, s.frequency)
                tasks[key] = (lambda s=s, st=start: fetch_series(s, st),
                              lambda df, k=key: db.upsert_observations(conn, k, df), [key])

        if steo_due:
            # One bulk query from the earliest start needed (full history if any series is new).
            starts = [_start(conn, s.key, "M") for s in steo_due]
            start = None if any(x is None for x in starts) else min(starts)

            def store_steo(frames: dict[str, pd.DataFrame]) -> int:
                return sum(db.upsert_observations(conn, k, df) for k, df in frames.items())

            tasks[STEO_TASK] = (lambda: fetch_steo_bulk(steo_due, start), store_steo, [s.key for s in steo_due])

        if keys is None:
            for name, root in FUTURES_ROOTS.items():
                tk = f"futures_{name}"
                if force or not _is_fresh(conn, tk, SOURCE_HOURS["futures"]):
                    tasks[tk] = (lambda r=root: fetch_futures(r, FUTURES_MONTHS_AHEAD),
                                 lambda df, n=name: db.upsert_futures(conn, n, df), [tk])
            if snapshot and (force or not _is_fresh(conn, "snapshot", SOURCE_HOURS["snapshot"])):
                tasks["snapshot"] = (fetch_snapshot, lambda snaps: (db.insert_snapshots(conn, snaps), len(snaps))[1],
                                     ["snapshot"])

        # Network calls in parallel (I/O bound); all DB writes stay on this thread.
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(fetch): name for name, (fetch, _, _) in tasks.items()}
            for fut in as_completed(futures):
                name = futures[fut]
                _, store, log_keys = tasks[name]
                try:
                    report.updated[name] = store(fut.result())
                    for k in log_keys:
                        db.log_fetch(conn, k, None)
                except FetchError as exc:
                    report.errors[name] = str(exc)
                    for k in log_keys:
                        db.log_fetch(conn, k, str(exc))
                except Exception as exc:  # never let one source take the dashboard down
                    report.errors[name] = f"{exc.__class__.__name__}: {exc}"[:200]
                    for k in log_keys:
                        db.log_fetch(conn, k, report.errors[name])
        conn.commit()
        db.prune(conn)
    return report

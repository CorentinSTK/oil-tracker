"""SQLite persistence.

Observations are stored in long format (one row per series/date) so adding a
series never needs a migration. Spreads and indicators are *derived* on read:
they are cheap to compute and storing them would only create stale copies.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from oil_tracker import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    series_key TEXT NOT NULL,
    date       TEXT NOT NULL,          -- ISO date of the observation period
    value      REAL NOT NULL,
    fetched_at TEXT NOT NULL,          -- UTC timestamp of the fetch
    PRIMARY KEY (series_key, date)
);

CREATE TABLE IF NOT EXISTS price_snapshots (
    code       TEXT NOT NULL,          -- wti | brent | dubai | opec_basket
    quoted_at  TEXT NOT NULL,          -- provider timestamp
    price      REAL NOT NULL,
    change_24h REAL,
    name       TEXT,
    source     TEXT NOT NULL DEFAULT 'oilpriceapi',
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (code, quoted_at)
);

CREATE TABLE IF NOT EXISTS futures_prices (
    root       TEXT NOT NULL,          -- wti | brent
    contract   TEXT NOT NULL,          -- e.g. CLZ26.NYM
    delivery   TEXT NOT NULL,          -- delivery month, YYYY-MM-01
    date       TEXT NOT NULL,
    close      REAL NOT NULL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (contract, date)
);

CREATE TABLE IF NOT EXISTS fetch_log (
    series_key   TEXT PRIMARY KEY,
    last_attempt TEXT NOT NULL,
    last_success TEXT,
    last_error   TEXT
);

CREATE TABLE IF NOT EXISTS alerts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    as_of      TEXT NOT NULL,          -- data date the alert refers to
    alert_type TEXT NOT NULL,
    severity   TEXT NOT NULL,          -- HIGH | MEDIUM | LOW
    message    TEXT NOT NULL,
    created_at TEXT NOT NULL,
    read       INTEGER NOT NULL DEFAULT 0,
    UNIQUE (as_of, alert_type)
);
"""


def utcnow() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@contextmanager
def connect(path: Path | None = None):
    path = path or config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------- observations

def upsert_observations(conn: sqlite3.Connection, key: str, df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    now = utcnow()
    rows = [(key, d.strftime("%Y-%m-%d"), float(v), now) for d, v in zip(df["date"], df["value"])]
    conn.executemany(
        "INSERT INTO observations (series_key, date, value, fetched_at) VALUES (?,?,?,?) "
        "ON CONFLICT(series_key, date) DO UPDATE SET value=excluded.value, fetched_at=excluded.fetched_at",
        rows,
    )
    return len(rows)


def last_date(conn: sqlite3.Connection, key: str) -> pd.Timestamp | None:
    row = conn.execute("SELECT MAX(date) FROM observations WHERE series_key=?", (key,)).fetchone()
    return pd.Timestamp(row[0]) if row and row[0] else None


def read_series(keys: list[str], conn: sqlite3.Connection | None = None) -> pd.DataFrame:
    """Wide frame indexed by date with one column per requested series."""
    def _read(c: sqlite3.Connection) -> pd.DataFrame:
        q = f"SELECT series_key, date, value FROM observations WHERE series_key IN ({','.join('?' * len(keys))})"
        long = pd.read_sql_query(q, c, params=keys, parse_dates=["date"])
        if long.empty:
            return pd.DataFrame(columns=keys, index=pd.DatetimeIndex([], name="date"), dtype=float)
        wide = long.pivot(index="date", columns="series_key", values="value").sort_index()
        return wide.reindex(columns=keys)

    if conn is not None:
        return _read(conn)
    with connect() as c:
        return _read(c)


# ------------------------------------------------------------------- fetch log

def log_fetch(conn: sqlite3.Connection, key: str, error: str | None) -> None:
    now = utcnow()
    conn.execute(
        "INSERT INTO fetch_log (series_key, last_attempt, last_success, last_error) VALUES (?,?,?,?) "
        "ON CONFLICT(series_key) DO UPDATE SET last_attempt=excluded.last_attempt, "
        "last_success=COALESCE(excluded.last_success, fetch_log.last_success), last_error=excluded.last_error",
        (key, now, None if error else now, error),
    )


def read_fetch_log() -> pd.DataFrame:
    with connect() as c:
        log = pd.read_sql_query("SELECT * FROM fetch_log", c)
        last = pd.read_sql_query(
            "SELECT series_key, MAX(date) AS last_obs, COUNT(*) AS n_obs FROM observations GROUP BY series_key", c
        )
    return log.merge(last, on="series_key", how="outer")


# ---------------------------------------------------------------------- futures

def upsert_futures(conn: sqlite3.Connection, root: str, df: pd.DataFrame) -> int:
    now = utcnow()
    rows = [(root, c, d.strftime("%Y-%m-%d"), t.strftime("%Y-%m-%d"), float(v), now)
            for c, d, t, v in zip(df["contract"], df["delivery"], df["date"], df["close"])]
    conn.executemany(
        "INSERT INTO futures_prices (root, contract, delivery, date, close, fetched_at) VALUES (?,?,?,?,?,?) "
        "ON CONFLICT(contract, date) DO UPDATE SET close=excluded.close, fetched_at=excluded.fetched_at",
        rows,
    )
    return len(rows)


def read_futures(root: str) -> pd.DataFrame:
    with connect() as c:
        return pd.read_sql_query(
            "SELECT contract, delivery, date, close FROM futures_prices WHERE root=? ORDER BY date, delivery",
            c, params=[root], parse_dates=["delivery", "date"],
        )


# ------------------------------------------------------------------- snapshots

def insert_snapshots(conn: sqlite3.Connection, snaps: list[dict]) -> None:
    now = utcnow()
    conn.executemany(
        "INSERT OR IGNORE INTO price_snapshots (code, quoted_at, price, change_24h, name, fetched_at) "
        "VALUES (?,?,?,?,?,?)",
        [(s["code"], s["quoted_at"] or now, s["price"], s.get("change_24h"), s.get("name"), now) for s in snaps],
    )


def latest_snapshots() -> pd.DataFrame:
    with connect() as c:
        return pd.read_sql_query(
            "SELECT s.* FROM price_snapshots s JOIN (SELECT code, MAX(quoted_at) q FROM price_snapshots GROUP BY code) m "
            "ON s.code=m.code AND s.quoted_at=m.q",
            c,
        )


def snapshot_history(code: str) -> pd.DataFrame:
    with connect() as c:
        return pd.read_sql_query(
            "SELECT quoted_at, price FROM price_snapshots WHERE code=? ORDER BY quoted_at", c, params=[code]
        )


# ---------------------------------------------------------------------- alerts

def save_alerts(alerts: list[dict]) -> None:
    now = utcnow()
    with connect() as c:
        c.executemany(
            "INSERT OR IGNORE INTO alerts (as_of, alert_type, severity, message, created_at) VALUES (?,?,?,?,?)",
            [(a["as_of"], a["type"], a["severity"], a["message"], now) for a in alerts],
        )


def read_alerts(limit: int = 200) -> pd.DataFrame:
    with connect() as c:
        return pd.read_sql_query("SELECT * FROM alerts ORDER BY as_of DESC, id DESC LIMIT ?", c, params=[limit])


def prune(conn: sqlite3.Connection) -> None:
    """Retention policy: snapshots 3y, alerts 1y. Official series are kept
    in full (they are small and the seasonal maths needs the history)."""
    conn.execute("DELETE FROM price_snapshots WHERE quoted_at < date('now', '-3 years')")
    conn.execute("DELETE FROM alerts WHERE as_of < date('now', '-1 year')")

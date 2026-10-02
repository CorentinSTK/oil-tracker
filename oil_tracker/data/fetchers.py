"""Thin HTTP clients for EIA, FRED and OilPriceAPI.

Each fetcher returns a tidy ``DataFrame[date, value]`` (or a list of snapshot
dicts) and raises ``FetchError`` with a readable message on failure, so the
pipeline can log the problem and keep serving the last stored data.
"""

from __future__ import annotations

import io
import logging
from datetime import date

import pandas as pd
import requests

from oil_tracker import config
from oil_tracker.sources import SNAPSHOT_CODES, Series


class FetchError(RuntimeError):
    pass


def _get(url: str, params: dict | None = None, headers: dict | None = None) -> dict:
    hdrs = {"User-Agent": config.USER_AGENT, **(headers or {})}
    try:
        resp = requests.get(url, params=params, headers=hdrs, timeout=config.HTTP_TIMEOUT)
    except requests.RequestException as exc:
        raise FetchError(f"network error: {exc.__class__.__name__}") from exc
    if resp.status_code != 200:
        raise FetchError(f"HTTP {resp.status_code} from {url.split('?')[0]}")
    try:
        return resp.json()
    except ValueError as exc:
        raise FetchError("invalid JSON response") from exc


def _tidy(rows: list[tuple[str, object]], scale: float) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["date", "value"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce") * scale
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df.dropna().drop_duplicates("date").sort_values("date").reset_index(drop=True)


# --------------------------------------------------------------------------- EIA

EIA_BASE = "https://api.eia.gov/v2"
EIA_PAGE = 5000  # API maximum rows per request


def fetch_eia(series: Series, start: date | None = None) -> pd.DataFrame:
    key = config.eia_key()
    if not key:
        raise FetchError("EIA_API_KEY is not set")
    if series.source == "eia_steo":
        url = f"{EIA_BASE}/steo/data/"
        base = {
            "frequency": "monthly",
            "data[0]": "value",
            "facets[seriesId][]": series.remote_id,
        }
    else:
        url = f"{EIA_BASE}/seriesid/{series.remote_id}"
        base = {}
    params = {
        **base,
        "api_key": key,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "length": EIA_PAGE,
    }
    if start is not None:
        # The /seriesid route ignores ``start``; an incremental update instead
        # asks for the newest N rows, N being enough to reach back to ``start``.
        days = (date.today() - start).days
        n = {"D": days, "W": days // 7, "M": days // 28 + 30}[series.frequency] + 5  # STEO: +forecast months
        params |= {"sort[0][direction]": "desc", "length": min(n, EIA_PAGE)}
        payload = _get(url, params)
        resp = payload.get("response")
        if resp is None:
            raise FetchError(str(payload.get("error", "unexpected EIA payload"))[:200])
        df = _tidy([(r["period"], r.get("value")) for r in resp.get("data", [])], series.scale)
        return df[df["date"] >= pd.Timestamp(start)].reset_index(drop=True)

    rows: list[tuple[str, object]] = []
    offset = 0
    while True:
        payload = _get(url, {**params, "offset": offset})
        resp = payload.get("response")
        if resp is None:
            raise FetchError(str(payload.get("error", "unexpected EIA payload"))[:200])
        data = resp.get("data", [])
        rows += [(r["period"], r.get("value")) for r in data]
        offset += len(data)
        if not data or offset >= int(resp.get("total", 0)):
            break
    return _tidy(rows, series.scale)


# -------------------------------------------------------------------------- FRED

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"


def fetch_fred(series: Series, start: date | None = None) -> pd.DataFrame:
    key = config.fred_key()
    if not key:
        raise FetchError("FRED_API_KEY is not set")
    params = {"series_id": series.remote_id, "api_key": key, "file_type": "json"}
    if start is not None:
        params["observation_start"] = start.isoformat()
    payload = _get(FRED_URL, params)
    if "observations" not in payload:
        raise FetchError(str(payload.get("error_message", "unexpected FRED payload"))[:200])
    # FRED encodes missing values as "." -> coerced to NaN and dropped.
    rows = [(o["date"], o["value"]) for o in payload["observations"]]
    return _tidy(rows, series.scale)


def fetch_series(series: Series, start: date | None = None) -> pd.DataFrame:
    if series.source in ("eia", "eia_steo"):
        return fetch_eia(series, start)
    if series.source == "fred":
        return fetch_fred(series, start)
    raise FetchError(f"unknown source {series.source}")


def fetch_steo_bulk(series: list[Series], start: date | None = None) -> dict[str, pd.DataFrame]:
    """Many STEO series in one paginated query (one request per 5000 rows
    instead of one per series)."""
    key = config.eia_key()
    if not key:
        raise FetchError("EIA_API_KEY is not set")
    by_id = {s.remote_id: s for s in series}
    params: list[tuple[str, object]] = [
        ("api_key", key), ("frequency", "monthly"), ("data[0]", "value"),
        ("sort[0][column]", "period"), ("sort[0][direction]", "asc"), ("length", EIA_PAGE),
    ] + [("facets[seriesId][]", sid) for sid in by_id]
    if start is not None:
        params.append(("start", start.strftime("%Y-%m")))

    rows: dict[str, list] = {sid: [] for sid in by_id}
    offset = 0
    while True:
        payload = _get(f"{EIA_BASE}/steo/data/", params + [("offset", offset)])
        resp = payload.get("response")
        if resp is None:
            raise FetchError(str(payload.get("error", "unexpected EIA payload"))[:200])
        data = resp.get("data", [])
        for r in data:
            if r.get("seriesId") in rows:
                rows[r["seriesId"]].append((r["period"], r.get("value")))
        offset += len(data)
        if not data or offset >= int(resp.get("total", 0)):
            break
    return {by_id[sid].key: _tidy(r, by_id[sid].scale) for sid, r in rows.items()}


# --------------------------------------------------------------------------- GPR

GPR_FILES = {
    "gpr_daily": ("https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls", "date", "GPRD"),
    "gpr_m": ("https://www.matteoiacoviello.com/gpr_files/data_gpr_export.xls", "month", "GPR"),
}


def fetch_gpr(key: str) -> pd.DataFrame:
    """Caldara & Iacoviello Geopolitical Risk index, from the authors' site
    (it is not on FRED). Daily file ~3 MB, monthly ~3 MB."""
    url, date_col, value_col = GPR_FILES[key]
    try:
        resp = requests.get(url, headers={"User-Agent": config.USER_AGENT}, timeout=60)
    except requests.RequestException as exc:
        raise FetchError(f"network error: {exc.__class__.__name__}") from exc
    if resp.status_code != 200:
        raise FetchError(f"HTTP {resp.status_code} from matteoiacoviello.com")
    try:
        raw = pd.read_excel(io.BytesIO(resp.content), usecols=[date_col, value_col])
    except Exception as exc:  # xlrd/format changes upstream
        raise FetchError(f"could not parse GPR file: {exc.__class__.__name__}") from exc
    return _tidy(list(zip(raw[date_col], raw[value_col])), 1.0)


# ------------------------------------------------------------- futures (Yahoo)

MONTH_CODES = "FGHJKMNQUVXZ"


def contract_ticker(root: str, delivery: pd.Timestamp) -> str:
    return f"{root}{MONTH_CODES[delivery.month - 1]}{delivery.year % 100:02d}.NYM"


def fetch_futures(root: str, months_ahead: int, period: str = "2y") -> pd.DataFrame:
    """Daily settlements of individual futures contracts from Yahoo Finance.

    Yahoo is unofficial and only lists *live* contracts, so expired months
    disappear from the source. We store everything we fetch, so the stored
    history keeps them. Returns long ``[contract, delivery, date, close]``.
    """
    try:
        import yfinance as yf
    except ImportError as exc:
        raise FetchError("yfinance is not installed") from exc
    # Far months that are not listed yet are expected misses; keep the log quiet.
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    first = pd.Timestamp.today().to_period("M").to_timestamp()
    deliveries = [first + pd.DateOffset(months=i) for i in range(months_ahead + 1)]
    tickers = {contract_ticker(root, d): d for d in deliveries}
    try:
        raw = yf.download(list(tickers), period=period, progress=False, auto_adjust=False, threads=True)
    except Exception as exc:
        raise FetchError(f"Yahoo download failed: {exc.__class__.__name__}") from exc
    if raw is None or raw.empty or "Close" not in raw:
        raise FetchError("Yahoo returned no futures data")
    close = raw["Close"]
    if isinstance(close, pd.Series):  # single ticker
        close = close.to_frame(next(iter(tickers)))
    long = close.reset_index().melt(id_vars=close.index.name or "Date", var_name="contract", value_name="close")
    long = long.rename(columns={close.index.name or "Date": "date"}).dropna(subset=["close"])
    long["date"] = pd.to_datetime(long["date"]).dt.tz_localize(None).dt.normalize()
    long["delivery"] = long["contract"].map(tickers)
    if long.empty:
        raise FetchError("Yahoo returned no futures data")
    return long[["contract", "delivery", "date", "close"]]


# ------------------------------------------------------------------ OilPriceAPI

OPA_BASE = "https://api.oilpriceapi.com/v1"


def fetch_snapshot() -> list[dict]:
    """Latest indicative prices from OilPriceAPI.

    With ``OILPRICEAPI_KEY`` set we query the authenticated endpoint; without
    one we fall back to the public demo endpoint (same quotes, rate limited).
    WTI and Brent here are *front-month futures*, while history uses *spot*
    assessments, so snapshot and history are never mixed in one calculation.
    """
    key = config.oilpriceapi_key()
    if key:
        out = []
        for code in SNAPSHOT_CODES:
            payload = _get(
                f"{OPA_BASE}/prices/latest",
                {"by_code": code},
                {"Authorization": f"Token {key}"},
            )
            d = payload.get("data") or {}
            if "price" in d:
                out.append(d | {"code": d.get("code", code)})
        prices = out
    else:
        payload = _get(f"{OPA_BASE}/demo/prices")
        prices = (payload.get("data") or {}).get("prices", [])

    snaps = []
    for p in prices:
        code = p.get("code")
        if code not in SNAPSHOT_CODES or p.get("price") is None:
            continue
        snaps.append(
            {
                "code": SNAPSHOT_CODES[code],
                "price": float(p["price"]),
                "name": p.get("name", code),
                "change_24h": p.get("change_24h"),
                "quoted_at": p.get("updated_at") or p.get("created_at"),
            }
        )
    if not snaps:
        raise FetchError("OilPriceAPI returned no usable prices")
    return snaps

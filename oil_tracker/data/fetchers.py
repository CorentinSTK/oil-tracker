"""Thin HTTP clients for EIA, FRED and OilPriceAPI.

Each fetcher returns a tidy ``DataFrame[date, value]`` (or a list of snapshot
dicts) and raises ``FetchError`` with a readable message on failure, so the
pipeline can log the problem and keep serving the last stored data.
"""

from __future__ import annotations

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

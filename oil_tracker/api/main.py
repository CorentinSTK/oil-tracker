"""Optional REST API over the same analytics as the dashboard.

Run:  uvicorn oil_tracker.api.main:app --reload
Docs: http://localhost:8000/docs
"""

from __future__ import annotations

import math
import time
from datetime import datetime

import numpy as np
import pandas as pd
from fastapi import BackgroundTasks, FastAPI, Query

from oil_tracker.analytics.brief import build_brief
from oil_tracker.catalysts import upcoming
from oil_tracker.data import database as db
from oil_tracker.data.pipeline import refresh
from oil_tracker.service import build_context

app = FastAPI(title="Oil Market Tracker API", version="0.1.0")

_CACHE: dict = {"ctx": None, "at": 0.0}
TTL = 900  # seconds


def ctx() -> dict:
    if _CACHE["ctx"] is None or time.time() - _CACHE["at"] > TTL:
        _CACHE["ctx"], _CACHE["at"] = build_context(), time.time()
    return _CACHE["ctx"]


def clean(obj):
    """Make numpy/pandas values JSON-safe (NaN -> null, Timestamps -> ISO)."""
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    if isinstance(obj, (np.floating, float)):
        return None if math.isnan(obj) else float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def records(df: pd.DataFrame) -> list[dict]:
    out = df.reset_index().rename(columns={"index": "date"})
    return clean(out.to_dict(orient="records"))


@app.get("/api/v1/prices/latest")
def prices_latest():
    c = ctx()
    snap = c["snapshot"]
    return clean({
        "spot": {k: {"price": m["last"], "date": m["date"], "chg_1d_pct": m["chg_1d_pct"]}
                 for k, m in c["momentum"].items() if m},
        "snapshot": snap.to_dict(orient="records") if not snap.empty else [],
        "notes": "spot = EIA daily (WTI, Brent) and IMF monthly (Dubai); snapshot = OilPriceAPI indicative",
    })


@app.get("/api/v1/prices/history")
def prices_history(days: int = Query(365, ge=1, le=20000)):
    px = ctx()["frames"]["prices"]
    return records(px.loc[px.index > px.index.max() - pd.Timedelta(days=days)])


@app.get("/api/v1/spreads/latest")
def spreads_latest():
    c = ctx()
    return clean({"stats": c["spread_stats"], "snapshot": c["snapshot_spreads"],
                  "ranking": c["ranking"][["key", "current", "z_5y", "status"]].to_dict(orient="records")
                  if not c["ranking"].empty else []})


@app.get("/api/v1/inventory/latest")
def inventory_latest():
    return clean(ctx()["inventory"])


@app.get("/api/v1/inventory/history")
def inventory_history(weeks: int = Query(104, ge=1, le=2000)):
    w = ctx()["frames"]["weekly"]
    w = w.loc[w.index > w.index.max() - pd.Timedelta(weeks=weeks)]
    out = w.copy()
    out["us_crude_change"] = w["us_crude"].diff()
    out["signal"] = np.where(out["us_crude_change"] < 0, "DRAW", "BUILD")
    return records(out)


@app.get("/api/v1/refinery/latest")
def refinery_latest():
    return clean(ctx()["refinery"])


@app.get("/api/v1/analytics/sd-balance")
def sd_balance():
    return clean(ctx()["score"])


@app.get("/api/v1/analytics/summary")
def summary():
    return clean(build_brief(ctx()))


@app.get("/api/v1/analytics/global")
def global_balance():
    return clean(ctx()["global"])


@app.get("/api/v1/curve")
def futures_curve():
    out = {}
    for name, cv in ctx()["curves"].items():
        if cv:
            out[name] = {k: v for k, v in cv.items() if k not in ("dec_spread", "history", "contracts", "curve")}
            out[name]["curve"] = cv["curve"].to_dict()
    return clean(out)


@app.get("/api/v1/refining")
def refining():
    c = ctx()
    return clean({"cracks": c["crack_summary"], "implied_demand": c["demand"], "demand_score": c["demand_score"]})


@app.get("/api/v1/oecd")
def oecd():
    return clean(ctx()["oecd_summary"])


@app.get("/api/v1/surprises")
def inventory_surprises(weeks: int = Query(12, ge=1, le=520)):
    c = ctx()
    return clean({k: records(v.iloc[-weeks:].drop(columns=["release"])) for k, v in c["surprises"].items()}
                 | {"streak": c["surprise_streak"]})


@app.get("/api/v1/opec/countries")
def opec_countries():
    c = ctx()
    return clean({"month": c["opec_month"], "countries": c["opec_table"].to_dict(orient="records")})


@app.get("/api/v1/disruptions")
def supply_disruptions():
    d = dict(ctx()["disruptions"])
    if "by_country" in d:
        d["by_country"] = d["by_country"].to_dict(orient="records")
    return clean(d)


@app.get("/api/v1/risk")
def risk_gauges():
    return clean(ctx()["gauges"])


@app.get("/api/v1/alerts")
def alerts(limit: int = Query(100, ge=1, le=1000)):
    return clean(db.read_alerts(limit).to_dict(orient="records"))


@app.get("/api/v1/calendar")
def calendar(days: int = Query(35, ge=1, le=120)):
    return clean([{"when": e.when, "name": e.name, "source": e.source, "estimated": e.estimated, "url": e.url}
                  for e in upcoming(days=days)])


@app.post("/api/v1/refresh")
def trigger_refresh(background: BackgroundTasks, force: bool = False):
    def job():
        refresh(force=force)
        _CACHE["ctx"] = None
    background.add_task(job)
    return {"status": "scheduled", "force": force}

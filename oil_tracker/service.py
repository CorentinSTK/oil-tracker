"""One function that turns the database into everything the UI/API shows.

Both the Streamlit app and the FastAPI service call :func:`build_context`, so
a number on the dashboard and the same number on the API can never differ.
"""

from __future__ import annotations

import pandas as pd

from oil_tracker.analytics import balance, fundamentals, prices, spreads
from oil_tracker.analytics.alerts import generate_alerts
from oil_tracker.data import database as db
from oil_tracker.sources import SERIES

WEEKLY_KEYS = ["us_crude", "cushing", "us_gasoline", "us_distillates", "spr", "refinery_util", "us_production"]
STEO_KEYS = [k for k, s in SERIES.items() if s.source == "eia_steo"]
MACRO_KEYS = ["usd_broad", "t10y2y"]
STALE_DAYS = {"D": 5, "W": 9, "M": 45}


def load_frames() -> dict[str, pd.DataFrame]:
    with db.connect() as c:
        return {
            "prices": db.read_series(["wti", "brent"], c).dropna(how="all"),
            "dubai_m": db.read_series(["dubai_m"], c)["dubai_m"].dropna(),
            "weekly": db.read_series(WEEKLY_KEYS, c).dropna(how="all"),
            "steo": db.read_series(STEO_KEYS, c).dropna(how="all"),
            "macro": db.read_series(MACRO_KEYS, c).dropna(how="all"),
        }


def _staleness(frames: dict) -> dict:
    today = pd.Timestamp.today().normalize()
    checks = {
        "prices": ("Spot prices (EIA)", frames["prices"].index, "D"),
        "weekly": ("EIA weekly fundamentals", frames["weekly"].index, "W"),
    }
    out = {}
    for key, (label, idx, freq) in checks.items():
        if len(idx) == 0:
            out[key] = {"label": label, "last": None, "age_days": None, "stale": True}
            continue
        age = (today - idx.max()).days
        # Weekly data is dated to the Friday week-end and published the next Wednesday.
        out[key] = {"label": label, "last": idx.max(), "age_days": age, "stale": age > STALE_DAYS[freq]}
    return out


def build_context() -> dict:
    f = load_frames()
    px, weekly = f["prices"], f["weekly"]

    momentum = {k: prices.momentum(px[k]) for k in ("wti", "brent") if k in px}
    momentum["dubai"] = prices.momentum(f["dubai_m"]) if len(f["dubai_m"]) > 2 else {}
    levels = {k: prices.technical_levels(px[k]) for k in ("wti", "brent") if px[k].notna().sum() > 30}

    d_spreads = spreads.daily_spreads(px) if not px.empty else pd.DataFrame()
    m_spreads = spreads.monthly_spreads(px, f["dubai_m"]) if not px.empty else pd.DataFrame()
    spread_stats = {
        "brent_wti": spreads.spread_stats(d_spreads["brent_wti"], "D") if not d_spreads.empty else {},
        "brent_dubai": spreads.spread_stats(m_spreads["brent_dubai"], "M") if not m_spreads.empty else {},
        "wti_dubai": spreads.spread_stats(m_spreads["wti_dubai"], "M") if not m_spreads.empty else {},
    }

    inventory = {
        k: fundamentals.inventory_summary(weekly[k])
        for k in ("us_crude", "cushing", "us_gasoline", "us_distillates", "spr")
        if k in weekly
    }
    total = fundamentals.total_commercial_stocks(weekly) if not weekly.empty else pd.Series(dtype=float)
    inventory["total"] = fundamentals.inventory_summary(total) if len(total) > 2 else {}

    gb = fundamentals.global_balance(f["steo"]) if not f["steo"].empty else pd.DataFrame()
    score_hist = balance.score_history(weekly, px) if not weekly.empty and not px.empty else pd.DataFrame()

    snap = db.latest_snapshots()
    ctx = {
        "frames": f,
        "momentum": momentum,
        "levels": levels,
        "daily_spreads": d_spreads,
        "monthly_spreads": m_spreads,
        "spread_stats": spread_stats,
        "ranking": spreads.dislocation_ranking(spread_stats),
        "snapshot": snap,
        "snapshot_spreads": spreads.snapshot_spreads(snap),
        "inventory": inventory,
        "refinery": fundamentals.refinery_summary(weekly["refinery_util"]) if "refinery_util" in weekly else {},
        "production": fundamentals.production_summary(weekly["us_production"]) if "us_production" in weekly else {},
        "global_balance": gb,
        "global": fundamentals.balance_summary(gb) if not gb.empty else {},
        "score_history": score_hist,
        "score": balance.latest_score(score_hist),
        "staleness": _staleness(f),
    }
    ctx["alerts"] = generate_alerts(ctx)
    return ctx

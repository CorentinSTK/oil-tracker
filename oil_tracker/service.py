"""One function that turns the database into everything the UI/API shows.

Both the Streamlit app and the FastAPI service call :func:`build_context`, so
a number on the dashboard and the same number on the API can never differ.
"""

from __future__ import annotations

import pandas as pd

from oil_tracker import manual
from oil_tracker.analytics import balance, curve, demand, fundamentals, opec, prices, risk, spreads, surprises
from oil_tracker.analytics.alerts import generate_alerts
from oil_tracker.data import database as db
from oil_tracker.sources import SERIES

WEEKLY_KEYS = ["us_crude", "cushing", "us_gasoline", "us_distillates", "spr", "refinery_util", "us_production",
               "crude_imports", "crude_exports", "ps_total", "ps_gasoline", "ps_distillate", "ps_jet"]
PRODUCT_KEYS = ["gas_nyh", "gas_usgc", "ulsd_nyh", "ulsd_usgc", "jet_usgc"]
STEO_KEYS = [k for k, s in SERIES.items() if s.source == "eia_steo"]
MARKET_KEYS = ["usd_broad", "t10y2y", "ust10y", "sp500", "ovx", "vix"]
RISK_KEYS = ["gpr_daily", "gpr_m", "gepu", "gas_retail"]
STALE_DAYS = {"D": 5, "W": 9, "M": 45}


def load_frames() -> dict[str, pd.DataFrame]:
    with db.connect() as c:
        frames = {
            "prices": db.read_series(["wti", "brent"], c).dropna(how="all"),
            "dubai_m": db.read_series(["dubai_m"], c)["dubai_m"].dropna(),
            "products": db.read_series(PRODUCT_KEYS, c).dropna(how="all"),
            "weekly": db.read_series(WEEKLY_KEYS, c).dropna(how="all"),
            "steo": db.read_series(STEO_KEYS, c).dropna(how="all"),
            "markets": db.read_series(MARKET_KEYS, c).dropna(how="all"),
            "risk": db.read_series(RISK_KEYS, c).dropna(how="all"),
        }
    frames["futures"] = {name: db.read_futures(name) for name in ("wti", "brent")}
    return frames


def _staleness(frames: dict) -> dict:
    today = pd.Timestamp.today().normalize()
    fut = frames["futures"]["wti"]
    checks = {
        "prices": ("Spot prices (EIA)", frames["prices"].index, "D"),
        "weekly": ("EIA weekly fundamentals", frames["weekly"]["us_crude"].dropna().index, "W"),
        "futures": ("Futures curve (Yahoo)", pd.DatetimeIndex(fut["date"]) if not fut.empty else pd.DatetimeIndex([]), "D"),
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
    px, weekly, steo = f["prices"], f["weekly"], f["steo"]

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
    refinery = fundamentals.refinery_summary(weekly["refinery_util"]) if "refinery_util" in weekly else {}

    gb = fundamentals.global_balance(steo) if not steo.empty else pd.DataFrame()
    oecd = fundamentals.oecd_stocks(gb) if not gb.empty else pd.DataFrame()
    score_hist = balance.score_history(weekly, px) if not weekly.empty and not px.empty else pd.DataFrame()

    # Downstream demand
    cracks = demand.crack_spreads(px.join(f["products"], how="inner")) if not f["products"].empty else pd.DataFrame()
    crack_sum = demand.crack_summary(cracks) if not cracks.empty else {}
    demand_sum = demand.implied_demand(weekly)

    # Surprises (seasonal baseline always; consensus when entered)
    level_series = {k: weekly[k] for k in ("us_crude", "us_gasoline", "us_distillates") if k in weekly}
    level_series["total"] = total
    surp = {k: surprises.seasonal_surprises(s) for k, s in level_series.items() if len(s.dropna()) > 300}
    consensus = manual.load("consensus")

    # Futures curve
    curves = {k: curve.summary(fut, k) for k, fut in f["futures"].items()}

    # OPEC+ by country and disruptions
    quotas = manual.load("opec_quotas")
    opec_month, opec_table = opec.country_table(steo, quotas) if not steo.empty else (None, pd.DataFrame())

    rk = f["risk"].join(f["markets"][["ovx", "vix"]], how="outer")
    gauges = {k: risk.gauge_summary(rk[k], smooth) for k, (_, smooth) in risk.GAUGES.items() if k in rk}

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
        "refinery": refinery,
        "production": fundamentals.production_summary(weekly["us_production"]) if "us_production" in weekly else {},
        "global_balance": gb,
        "global": fundamentals.balance_summary(gb) if not gb.empty else {},
        "oecd": oecd,
        "oecd_summary": fundamentals.oecd_summary(oecd) if not oecd.empty else {},
        "iea_oecd": manual.load("iea_oecd"),
        "score_history": score_hist,
        "score": balance.latest_score(score_hist),
        "cracks": cracks,
        "crack_summary": crack_sum,
        "demand": demand_sum,
        "demand_score": demand.demand_composite(crack_sum, demand_sum, refinery),
        "surprises": surp,
        "surprise_streak": surprises.streak(surp["total"]["surprise"]) if "total" in surp else {},
        "consensus": consensus,
        "consensus_surprises": surprises.consensus_surprises(weekly, consensus),
        "curves": curves,
        "opec_month": opec_month,
        "opec_table": opec_table,
        "quotas": quotas,
        "disruptions": opec.disruption_summary(steo) if not steo.empty else {},
        "gauges": gauges,
        "staleness": _staleness(f),
    }
    ctx["alerts"] = generate_alerts(ctx)
    return ctx

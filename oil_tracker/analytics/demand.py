"""Downstream demand: refinery cracks, US implied demand, demand composite.

Crack spreads (all in $/bbl, products converted from $/gal x 42):
- USGC 3-2-1 vs WTI: (2 x Gulf Coast gasoline + 1 x Gulf Coast ULSD) / 3 - WTI.
  The classic US refining margin.
- NYH 3-2-1 vs Brent: NY Harbor products against Dated Brent. NYH is the
  Atlantic basin's price-setting import market for European barrels, so this
  is the closest *free* proxy for a European margin - it is not a European
  margin. No free daily source exists for Rotterdam or Singapore products,
  so Asian margins are not shown at all rather than guessed.
- Single-product cracks: NYH gasoline vs Brent, NYH ULSD vs Brent, USGC jet vs WTI.

Implied demand = EIA "product supplied" (disappearance from the primary
system), shown as a 4-week average because the weekly prints are noisy.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from oil_tracker.analytics.seasonal import seasonal_stats

CRACKS = {
    "usgc_321": "USGC 3-2-1 vs WTI",
    "nyh_321": "NYH 3-2-1 vs Brent (Atlantic proxy)",
    "gas_crack": "NYH gasoline vs Brent",
    "ulsd_crack": "NYH ULSD vs Brent",
    "jet_crack": "USGC jet vs WTI",
}
DEMAND = {
    "ps_total": "Total products",
    "ps_gasoline": "Gasoline",
    "ps_distillate": "Distillate",
    "ps_jet": "Jet fuel",
}


def crack_spreads(p: pd.DataFrame) -> pd.DataFrame:
    """Daily cracks from a frame holding crude and product prices in $/bbl."""
    out = pd.DataFrame(index=p.index)
    out["usgc_321"] = (2 * p["gas_usgc"] + p["ulsd_usgc"]) / 3 - p["wti"]
    out["nyh_321"] = (2 * p["gas_nyh"] + p["ulsd_nyh"]) / 3 - p["brent"]
    out["gas_crack"] = p["gas_nyh"] - p["brent"]
    out["ulsd_crack"] = p["ulsd_nyh"] - p["brent"]
    out["jet_crack"] = p["jet_usgc"] - p["wti"]
    return out.dropna(how="all")


def crack_summary(cracks: pd.DataFrame) -> dict[str, dict]:
    """Latest value, 4-week change and seasonal comparison (weekly averages,
    since gasoline cracks peak every spring/summer)."""
    out = {}
    for k in CRACKS:
        s = cracks[k].dropna()
        if len(s) < 300:
            continue
        weekly = s.resample("W-FRI").mean().dropna()
        st = seasonal_stats(weekly)
        dev = st["dev"].dropna()
        sd = dev.loc[dev.index > dev.index[-1] - pd.Timedelta(days=5 * 365)].std()
        last_dev = float(st["dev"].iloc[-1])
        z = last_dev / sd if sd and sd > 0 else np.nan
        signal = "N/A" if np.isnan(z) else "STRONG" if z >= 0.5 else "WEAK" if z <= -0.5 else "NORMAL"
        out[k] = {
            "label": CRACKS[k],
            "date": s.index[-1],
            "current": float(s.iloc[-1]),
            "chg_4w": float(s.iloc[-1] - s.asof(s.index[-1] - pd.Timedelta(days=28))),
            "week_avg": float(weekly.iloc[-1]),
            "seasonal_avg": float(st["avg"].iloc[-1]),
            "vs_seasonal": last_dev,
            "z": z,
            "signal": signal,
        }
    return out


def implied_demand(weekly: pd.DataFrame) -> dict[str, dict]:
    out = {}
    for k, label in DEMAND.items():
        s = weekly[k].dropna() if k in weekly else pd.Series(dtype=float)
        if len(s) < 300:
            continue
        avg4 = s.rolling(4).mean().dropna()
        st = seasonal_stats(avg4)
        sd = st["dev"].dropna().iloc[-260:].std()
        out[k] = {
            "label": label,
            "date": s.index[-1],
            "week": float(s.iloc[-1]),
            "avg_4w": float(avg4.iloc[-1]),
            "seasonal_4w": float(st["avg"].iloc[-1]),
            "vs_seasonal": float(st["dev"].iloc[-1]),
            "vs_seasonal_pct": float(st["dev"].iloc[-1] / st["avg"].iloc[-1] * 100),
            "yoy_4w": float(avg4.iloc[-1] - avg4.asof(avg4.index[-1] - pd.Timedelta(days=364))),
            "z": float(st["dev"].iloc[-1] / sd) if sd > 0 else np.nan,
        }
    return out


def demand_composite(crack_sum: dict, demand_sum: dict, refinery: dict) -> dict:
    """0-100 "demand strength": equal-weight tanh(z/2) of US implied demand,
    the USGC 3-2-1 crack and refinery runs, each vs its seasonal norm.
    50 = seasonal normal. Descriptive, like the S&D score."""
    parts = {}
    if "ps_total" in demand_sum and not np.isnan(demand_sum["ps_total"]["z"]):
        parts["implied demand"] = demand_sum["ps_total"]["z"]
    if "usgc_321" in crack_sum and not np.isnan(crack_sum["usgc_321"]["z"]):
        parts["3-2-1 crack"] = crack_sum["usgc_321"]["z"]
    if refinery and refinery.get("z") is not None and not np.isnan(refinery["z"]):
        parts["refinery runs"] = refinery["z"]
    if not parts:
        return {}
    sig = {k: float(np.tanh(v / 2)) for k, v in parts.items()}
    score = 50 + 50 * float(np.mean(list(sig.values())))
    return {"score": score, "components": sig,
            "label": "STRONG" if score >= 55 else "WEAK" if score <= 45 else "NORMAL"}

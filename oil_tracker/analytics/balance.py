"""Supply-demand balance score (0-100).

50 = balanced, > 50 = market tightening / deficit, < 50 = loosening / surplus.

Each component is turned into a z-score against its own history, then
squashed to [-1, 1] with ``tanh(z / 2)`` (so z = +/-2 maps to about +/-0.76
and outliers cannot dominate). Positive always means bullish/tight:

| component | weight | input                                                                 |
|-----------|--------|-----------------------------------------------------------------------|
| inventory | 0.40   | US crude+gasoline+distillates: weekly change vs seasonal norm (flow)  |
|           |        | and level vs 5Y same-week average (stock), sign flipped               |
| refinery  | 0.30   | refinery utilisation vs 5Y same-week average                           |
| momentum  | 0.20   | WTI & Brent price vs their 30-day average                              |
| spread    | 0.10   | Brent-WTI vs its 1Y average (a wide Brent premium = seaborne market    |
|           |        | tighter than the US). Weakest component: a curve-structure signal     |
|           |        | (M1-M3 backwardation) would be better but has no free daily source.   |

The whole history is computed in one pass so the same numbers drive both
the dashboard and the backtest. Each weekly row is dated at the EIA *release*
(Wednesday after the Friday week-ending date) and only uses data available
at that release.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from oil_tracker.analytics.fundamentals import STOCK_KEYS
from oil_tracker.analytics.seasonal import seasonal_stats

WEIGHTS = {"inventory": 0.40, "refinery": 0.30, "momentum": 0.20, "spread": 0.10}
RELEASE_LAG = pd.Timedelta(days=5)  # week ending Friday -> Wednesday release
Z_WINDOW = 156                       # weeks (3 years) for rolling z-scores


def _squash(z: pd.Series) -> pd.Series:
    return np.tanh(z / 2.0)


def _rolling_z(s: pd.Series, window: int, min_periods: int | None = None) -> pd.Series:
    mp = min_periods or window // 3
    sd = s.rolling(window, min_periods=mp).std()
    return s / sd.replace(0, np.nan)


def score_history(weekly: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """Weekly S&D score with its components, indexed by release date."""
    stocks = weekly[STOCK_KEYS].dropna().sum(axis=1)
    if len(stocks) < 60:
        return pd.DataFrame()

    # Inventory: flow surprise (change vs seasonal change) + level vs seasonal level.
    flow = seasonal_stats(stocks.diff().dropna())["dev"]
    level = seasonal_stats(stocks)["dev"]
    z_flow = _rolling_z(flow, Z_WINDOW)
    z_level = level / level.rolling(Z_WINDOW, min_periods=52).std()
    inv = -_squash(0.5 * z_flow + 0.5 * z_level.reindex(z_flow.index))

    util_dev = seasonal_stats(weekly["refinery_util"].dropna())["dev"]
    ref = _squash(util_dev / util_dev.rolling(Z_WINDOW, min_periods=52).std())

    comp = pd.DataFrame({"inventory": inv, "refinery": ref.reindex(inv.index)})
    comp.index = comp.index + RELEASE_LAG

    # Price-based components, sampled as of each release date.
    px = prices[["wti", "brent"]].dropna()
    mom_pct = ((px / px.rolling(21, min_periods=15).mean() - 1) * 100).mean(axis=1)
    mom_z = mom_pct / mom_pct.rolling(252, min_periods=126).std()
    bw = px["brent"] - px["wti"]
    bw_z = (bw - bw.rolling(252, min_periods=126).mean()) / bw.rolling(252, min_periods=126).std()

    comp["momentum"] = _squash(mom_z).reindex(comp.index, method="ffill")
    comp["spread"] = _squash(bw_z).reindex(comp.index, method="ffill")
    comp = comp.dropna()

    comp["score"] = (50 + 50 * sum(comp[k] * w for k, w in WEIGHTS.items())).clip(0, 100)
    comp["regime"] = comp["score"].map(regime)
    return comp


def regime(score: float) -> str:
    if score >= 55:
        return "DEFICIT"
    if score <= 45:
        return "SURPLUS"
    return "BALANCED"


def latest_score(hist: pd.DataFrame) -> dict:
    if hist.empty:
        return {}
    row = hist.iloc[-1]
    return {
        "release_date": hist.index[-1],
        "score": float(row["score"]),
        "regime": row["regime"],
        "components": {k: float(row[k]) for k in WEIGHTS},
        "contributions": {k: float(row[k] * w * 50) for k, w in WEIGHTS.items()},
        "prev_score": float(hist["score"].iloc[-2]) if len(hist) > 1 else np.nan,
    }

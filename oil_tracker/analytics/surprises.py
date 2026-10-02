"""Weekly EIA inventory surprises and how the price reacts to them.

Markets move on the gap between the print and what was expected. The EIA
does not publish an expectation, and the analyst surveys (Reuters/WSJ/
Bloomberg) are not free, so two "expected" baselines are used:

1. Seasonal norm (always available, back to the 1990s): the 5-year average
   change for the same week. Captures "unusual for the time of year".
2. Analyst consensus (optional): entered by hand in data/manual/consensus.csv.

Surprises are in Mbbl, never in % of the forecast: a % of a forecast near
zero (e.g. -0.2 Mbbl) explodes and changes sign meaninglessly.
Sign convention: positive surprise = more barrels than expected = bearish.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from oil_tracker.analytics.seasonal import seasonal_stats

RELEASE_LAG = pd.Timedelta(days=5)  # week ending Friday -> Wednesday release
ITEMS = {"us_crude": "Crude", "us_gasoline": "Gasoline", "us_distillates": "Distillates", "total": "Crude+products"}


def seasonal_surprises(level: pd.Series) -> pd.DataFrame:
    """Per week: actual change, seasonal expected change, surprise, z-score."""
    chg = level.dropna().diff().dropna()
    st = seasonal_stats(chg)
    df = pd.DataFrame({"actual": chg, "expected": st["avg"], "surprise": st["dev"]}).dropna()
    sd = df["surprise"].rolling(156, min_periods=52).std()
    df["z"] = df["surprise"] / sd
    df["release"] = df.index + RELEASE_LAG
    return df


def consensus_surprises(weekly: pd.DataFrame, consensus: pd.DataFrame) -> pd.DataFrame:
    """Actual change minus the hand-entered analyst consensus, by item."""
    if consensus.empty:
        return pd.DataFrame()
    cons = consensus.set_index("week_ending")
    rows = []
    for item, col in (("us_crude", "crude"), ("us_gasoline", "gasoline"), ("us_distillates", "distillates")):
        chg = weekly[item].dropna().diff()
        for wk, exp in cons[col].dropna().items():
            if wk in chg.index:
                rows.append({"week_ending": wk, "item": ITEMS[item], "expected": exp, "actual": chg[wk],
                             "surprise": chg[wk] - exp})
    return pd.DataFrame(rows)


def streak(surprise: pd.Series, threshold: float = 0.0) -> dict:
    """Length and direction of the current run of same-sign surprises."""
    s = surprise.dropna()
    if s.empty:
        return {"length": 0, "direction": "none"}
    sign = np.sign(s.where(s.abs() > threshold, 0))
    last = sign.iloc[-1]
    if last == 0:
        return {"length": 0, "direction": "in line"}
    n = 0
    for v in sign.iloc[::-1]:
        if v != last:
            break
        n += 1
    return {"length": n, "direction": "builds above norm" if last > 0 else "draws below norm"}


def price_reaction(surp: pd.DataFrame, price: pd.Series, years: int = 10) -> tuple[pd.DataFrame, dict]:
    """Release-day price change vs the surprise.

    Release-day change = close on release day - previous close. Spot closes
    include everything else that happened that day, so this is a noisy but
    honest read of whether the market cares.
    """
    px = price.dropna()
    px = px[px > 0]
    rel = surp.copy()
    rel = rel[rel["release"] >= px.index[-1] - pd.DateOffset(years=years)]
    on = px.reindex(rel["release"])
    prev = px.shift(1).reindex(rel["release"])
    rel["px_chg"] = on.to_numpy() - prev.to_numpy()
    rel["px_chg_pct"] = (on.to_numpy() / prev.to_numpy() - 1) * 100
    rel = rel.dropna(subset=["px_chg_pct", "surprise"])
    if len(rel) < 30:
        return rel, {}
    x, y = rel["surprise"], rel["px_chg_pct"]
    slope = float(np.polyfit(x, y, 1)[0])
    big = rel[rel["z"].abs() >= 1.5]
    return rel, {
        "n": len(rel),
        "corr": float(x.corr(y)),
        "slope_pct_per_10mb": slope * 10,
        "hit_rate_big": float((np.sign(big["surprise"]) != np.sign(big["px_chg_pct"])).mean() * 100) if len(big) else np.nan,
        "n_big": len(big),
    }

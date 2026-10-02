"""Inter-benchmark spreads and how dislocated they are.

Basis discipline: every spread uses two prices of the *same type*.
- Brent-WTI: daily, Dated Brent spot vs WTI Cushing spot (EIA).
- Brent-Dubai / WTI-Dubai: monthly averages (Dubai has no free daily
  history; IMF monthly via FRED). Brent/WTI are averaged to the same months.
The OilPriceAPI snapshot gives an *indicative* same-provider read for today.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SPREAD_LABELS = {
    "brent_wti": "Brent - WTI",
    "brent_dubai": "Brent - Dubai",
    "wti_dubai": "WTI - Dubai",
}

SPREAD_DRIVERS = {
    "brent_wti": (
        "Transatlantic arb. Normally Brent > WTI by roughly the cost of moving US crude to "
        "Europe/Asia (pipeline to the Gulf Coast + freight). A wide spread means US crude is "
        "backed up (Cushing/Gulf Coast surplus, export or pipeline bottleneck) or seaborne "
        "crude is bid (OPEC+ cuts, geopolitical risk). A narrow/negative spread pulls US exports down."
    ),
    "brent_dubai": (
        "Light-sweet vs medium-sour, Atlantic vs Middle East. Wide Brent premium: sour "
        "crude is abundant (OPEC+ adding barrels) and Asian buyers favour Dubai-linked grades; "
        "it opens the arb for Middle East crude into Europe. Narrow/negative (Dubai over Brent): "
        "sour tightness - OPEC+ cuts, Gulf supply disruption - and Atlantic barrels flow East."
    ),
    "wti_dubai": (
        "US light-sweet vs Gulf medium-sour delivered to Asia. Negative = WTI cheap vs Dubai: "
        "US exports to Asia are favoured. A move towards zero or positive closes that arb."
    ),
}


def daily_spreads(prices: pd.DataFrame) -> pd.DataFrame:
    p = prices[["wti", "brent"]].dropna()
    return pd.DataFrame({"brent_wti": p["brent"] - p["wti"]})


def monthly_spreads(prices: pd.DataFrame, dubai_m: pd.Series) -> pd.DataFrame:
    m = prices[["wti", "brent"]].resample("MS").mean()
    d = dubai_m.dropna()
    d.index = d.index.to_period("M").to_timestamp()
    df = m.join(d.rename("dubai"), how="inner").dropna()
    # The current month is a partial average; drop it unless it's in the Dubai data too (it never is).
    return pd.DataFrame(
        {"brent_dubai": df["brent"] - df["dubai"], "wti_dubai": df["wti"] - df["dubai"]},
        index=df.index,
    )


def spread_stats(s: pd.Series, freq: str = "D") -> dict:
    """Current value vs its own history: averages, 5Y z-score and percentile."""
    s = s.dropna()
    if s.empty:
        return {}
    end = s.index[-1]
    y5 = s.loc[s.index > end - pd.Timedelta(days=5 * 365)]
    y1 = s.loc[s.index > end - pd.Timedelta(days=365)]
    d30 = s.loc[s.index > end - pd.Timedelta(days=30)]
    cur = float(s.iloc[-1])
    sd = float(y5.std())
    z = (cur - y5.mean()) / sd if sd > 0 else 0.0
    return {
        "date": end,
        "freq": freq,
        "current": cur,
        "avg_30d": float(d30.mean()) if freq == "D" else np.nan,
        "avg_1y": float(y1.mean()),
        "avg_5y": float(y5.mean()),
        "std_5y": sd,
        "z_5y": float(z),
        "pctile_5y": float((y5 < cur).mean() * 100),
        "status": classify(z),
    }


def classify(z: float) -> str:
    if abs(z) >= 2:
        return "ANOMALY"
    if z >= 1:
        return "WIDE"
    if z <= -1:
        return "NARROW"
    return "NORMAL"


def dislocation_ranking(stats: dict[str, dict]) -> pd.DataFrame:
    rows = [
        {"spread": SPREAD_LABELS[k], "key": k, **v}
        for k, v in stats.items()
        if v
    ]
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["abs_z"] = df["z_5y"].abs()
    return df.sort_values("abs_z", ascending=False).reset_index(drop=True)


def snapshot_spreads(snap: pd.DataFrame) -> dict[str, float]:
    """Indicative spreads from one provider's latest quotes."""
    px = dict(zip(snap["code"], snap["price"])) if not snap.empty else {}
    out = {}
    if {"brent", "wti"} <= px.keys():
        out["brent_wti"] = px["brent"] - px["wti"]
    if {"brent", "dubai"} <= px.keys():
        out["brent_dubai"] = px["brent"] - px["dubai"]
    if {"wti", "dubai"} <= px.keys():
        out["wti_dubai"] = px["wti"] - px["dubai"]
    return out

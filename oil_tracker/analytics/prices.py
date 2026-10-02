"""Price statistics, momentum and technical levels."""

from __future__ import annotations

import numpy as np
import pandas as pd


def momentum(px: pd.Series) -> dict:
    """Headline stats for one daily price series (NaNs dropped)."""
    px = px.dropna()
    if len(px) < 2:
        return {}
    last, prev = px.iloc[-1], px.iloc[-2]
    window = px.loc[px.index > px.index[-1] - pd.Timedelta(days=30)]
    yr = px.loc[px.index > px.index[-1] - pd.Timedelta(days=365)]
    y5 = px.loc[px.index > px.index[-1] - pd.Timedelta(days=5 * 365)]
    avg30 = window.mean()
    month_ago = px.asof(px.index[-1] - pd.Timedelta(days=30))
    return {
        "date": px.index[-1],
        "last": last,
        "chg_1d": last - prev,
        "chg_1d_pct": (last / prev - 1) * 100 if prev else np.nan,
        "chg_30d_pct": (last / month_ago - 1) * 100 if month_ago and not np.isnan(month_ago) else np.nan,
        "avg_30d": avg30,
        "vs_30d_avg_pct": (last / avg30 - 1) * 100,
        "avg_1y": yr.mean(),
        "avg_5y": y5.mean(),
        "high_52w": yr.max(),
        "low_52w": yr.min(),
        "vs_52w_high_pct": (last / yr.max() - 1) * 100,
        "trend": "up" if last > avg30 else "down",
        # 30-day realised volatility, annualised, from log returns (positive prices only)
        "vol_30d": float(np.log(window[window > 0]).diff().std() * np.sqrt(252) * 100),
    }


def technical_levels(px: pd.Series, lookback_days: int = 180, swing: int = 5, tol_pct: float = 1.5) -> dict:
    """Nearest support/resistance from clustered swing highs and lows.

    A swing high/low is a bar that is the max/min of its +/-``swing`` bar
    neighbourhood. Pivots within ``tol_pct`` of each other are merged; the
    level touched most often wins ties. Returns the nearest level below and
    above the last price.
    """
    px = px.dropna()
    px = px.loc[px.index > px.index[-1] - pd.Timedelta(days=lookback_days)]
    if len(px) < 2 * swing + 2:
        return {"support": np.nan, "resistance": np.nan}
    roll_max = px.rolling(2 * swing + 1, center=True).max()
    roll_min = px.rolling(2 * swing + 1, center=True).min()
    pivots = pd.concat([px[px == roll_max], px[px == roll_min]]).sort_values()

    clusters: list[list[float]] = []
    for p in pivots:
        if clusters and abs(p / np.mean(clusters[-1]) - 1) * 100 <= tol_pct:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    levels = [(float(np.mean(c)), len(c)) for c in clusters]
    last = px.iloc[-1]
    below = [lv for lv in levels if lv[0] < last * (1 - 0.002)]
    above = [lv for lv in levels if lv[0] > last * (1 + 0.002)]
    support = max(below, key=lambda lv: (lv[0], lv[1]))[0] if below else float(px.min())
    resistance = min(above, key=lambda lv: (lv[0], -lv[1]))[0] if above else float(px.max())
    return {"support": support, "resistance": resistance}

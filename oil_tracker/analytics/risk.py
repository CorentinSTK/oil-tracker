"""Risk gauges and cross-asset correlations.

- GPR (Caldara & Iacoviello): share of articles in 10 major newspapers on
  geopolitical tensions; 1985-2019 average = 100. Daily and monthly.
- OVX: implied volatility of USO options (the "oil VIX"). More relevant to
  oil than VIX; VIX is kept for the risk-on/off backdrop.
- GEPU: global economic policy uncertainty (monthly).

Correlations are computed on daily *returns* (log changes; first differences
for yields), never on price levels: two trending series correlate at ~1
regardless of any relationship.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

GAUGES = {
    "gpr_daily": ("GPR (daily, 7d avg)", 7),
    "ovx": ("OVX - oil implied vol", 1),
    "vix": ("VIX - equity implied vol", 1),
    "gepu": ("Global policy uncertainty", 1),
}

CORR_ASSETS = {
    "wti": "WTI",
    "brent": "Brent",
    "sp500": "S&P 500",
    "usd_broad": "USD (broad)",
    "ust10y": "US 10Y yield",
    "ovx": "OVX",
}


def gauge_summary(s: pd.Series, smooth: int = 1) -> dict:
    s = s.dropna()
    if s.empty:
        return {}
    if smooth > 1:
        s = s.rolling(smooth).mean().dropna()
    y5 = s.loc[s.index > s.index[-1] - pd.Timedelta(days=5 * 365)]
    cur = float(s.iloc[-1])
    pct = float((y5 < cur).mean() * 100)
    return {
        "date": s.index[-1],
        "current": cur,
        "avg_5y": float(y5.mean()),
        "pctile_5y": pct,
        "chg_1m": cur - float(s.asof(s.index[-1] - pd.Timedelta(days=30))),
        "status": "EXTREME" if pct >= 95 else "ELEVATED" if pct >= 80 else "LOW" if pct <= 20 else "NORMAL",
    }


def returns(frame: pd.DataFrame) -> pd.DataFrame:
    """Daily returns aligned on common trading days."""
    out = {}
    for c in frame:
        s = frame[c].dropna()
        if c in ("ust10y",):
            out[c] = s.diff()            # yields: change in percentage points
        else:
            s = s[s > 0]                 # WTI printed negative in April 2020
            out[c] = np.log(s).diff()
    return pd.DataFrame(out).dropna()


def correlation_matrix(frame: pd.DataFrame, days: int) -> pd.DataFrame:
    r = returns(frame)
    r = r.loc[r.index > r.index.max() - pd.Timedelta(days=days)]
    return r.corr()


def rolling_corr(frame: pd.DataFrame, a: str, b: str, window: int = 63) -> pd.Series:
    r = returns(frame[[a, b]])
    return r[a].rolling(window, min_periods=window // 2).corr(r[b]).dropna()

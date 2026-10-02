"""Historical test of the S&D score as a directional signal.

Rules: at each EIA release (Wednesday), go long 1 bbl if score >= ``long_at``,
short 1 bbl if score <= ``short_at``, flat otherwise; hold until the next
release. Entry/exit at that day's spot close (the signal is known at 10:30 ET,
before the close).

P&L is in $/bbl rather than % so the April-2020 negative WTI print does not
break the maths. Caveats shown in the UI: spot prices are not directly
tradable (no roll yield / carry), EIA weekly data are used as last revised
(minor revisions), and the score weights were not fitted on this sample but
were also not tested out-of-sample.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def run_backtest(
    score: pd.Series,
    price: pd.Series,
    long_at: float = 55,
    short_at: float = 45,
    cost_per_trade: float = 0.05,
) -> tuple[pd.DataFrame, dict]:
    px = price.dropna()
    sig = score.dropna()
    sig = sig[(sig.index >= px.index[0]) & (sig.index <= px.index[-1])]
    if len(sig) < 10:
        return pd.DataFrame(), {}

    entry_px = px.reindex(sig.index, method="ffill")
    pos = pd.Series(np.where(sig >= long_at, 1, np.where(sig <= short_at, -1, 0)), index=sig.index)

    move = entry_px.shift(-1) - entry_px          # next release close - this release close
    turnover = pos.diff().abs().fillna(pos.abs())  # contracts traded at this release
    pnl = (pos * move - turnover * cost_per_trade).iloc[:-1]
    bh = move.iloc[:-1]

    df = pd.DataFrame(
        {"score": sig, "position": pos, "price": entry_px, "pnl": pnl, "cum_pnl": pnl.cumsum(), "buy_hold": bh.cumsum()}
    ).iloc[:-1]

    active = df[df["position"] != 0]
    weekly_sd = df["pnl"].std()
    dd = df["cum_pnl"] - df["cum_pnl"].cummax()
    stats = {
        "weeks": len(df),
        "start": df.index[0],
        "end": df.index[-1],
        "total_pnl": float(df["pnl"].sum()),
        "buy_hold_pnl": float(bh.sum()),
        "pct_time_in_market": float((df["position"] != 0).mean() * 100),
        "hit_rate": float((active["pnl"] > 0).mean() * 100) if len(active) else np.nan,
        "sharpe": float(df["pnl"].mean() / weekly_sd * np.sqrt(52)) if weekly_sd > 0 else np.nan,
        "max_drawdown": float(dd.min()),
        "trades": int((df["position"].diff().fillna(df["position"]) != 0).sum()),
        # Does a high score actually precede rising prices? Spearman rank IC
        # between the score and the next week's price move.
        # (Pearson on ranks == Spearman, without the scipy dependency.)
        "ic": float(df["score"].rank().corr(move.reindex(df.index).rank())),
    }
    return df, stats

"""Futures curve structure: backwardation vs contango.

Backwardation (front > deferred) means prompt barrels are scarce: refiners pay
up for oil now, holding inventory loses money, so stocks get drawn. Contango
is the opposite: the market pays you to store. The curve is *not* a price
forecast - it is the price of time/storage given today's balance.

Generic months (M1, M2, ...) are rebuilt from individual contracts with each
exchange's expiry rule, and a date is kept only if every contract needed is
priced that day (the source drops expired contracts, so older dates can be
incomplete until the stored history accumulates).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pandas.tseries.offsets import BDay, BMonthEnd

TENORS = [1, 2, 3, 6, 12]


def expiry(root: str, delivery: pd.Timestamp) -> pd.Timestamp:
    """Approximate last trading day (weekends only, exchange holidays ignored)."""
    if root == "wti":
        # CL: 3 business days before the 25th of the month before delivery
        # (if the 25th is not a business day, count from the business day before it).
        d25 = (delivery - pd.DateOffset(months=1)).replace(day=25)
        if d25.dayofweek >= 5:
            d25 = d25 - BDay(1)
        return d25 - BDay(3)
    # BZ (Brent Last Day Financial): last business day of the 2nd month before delivery.
    return (delivery - pd.DateOffset(months=2)) + BMonthEnd(0)


def front_delivery(root: str, date: pd.Timestamp) -> pd.Timestamp:
    first = date.to_period("M").to_timestamp()
    for i in range(0, 4):
        d = first + pd.DateOffset(months=i)
        if expiry(root, d) >= date:
            return d
    raise ValueError("no front month found")


def generic_curve(fut: pd.DataFrame, root: str, max_tenor: int = 12) -> pd.DataFrame:
    """Wide frame: index = date, columns = M1..M{max_tenor} prices."""
    if fut.empty:
        return pd.DataFrame()
    fut = fut.copy()
    exp = {d: expiry(root, d) for d in fut["delivery"].unique()}
    fut["expiry"] = fut["delivery"].map(exp)
    fut = fut[fut["date"] <= fut["expiry"]]
    all_deliveries = sorted(exp)
    out = {}
    for date, g in fut.groupby("date"):
        live = [d for d in all_deliveries if exp[d] >= date][:max_tenor]
        px = dict(zip(g["delivery"], g["close"]))
        # The true front month from the expiry rule - if the source no longer
        # has it (expired and dropped), this date's curve would be shifted.
        if len(live) < 2 or live[0] != front_delivery(root, date) or live[0] not in px:
            continue
        out[date] = [px.get(d, np.nan) for d in live] + [np.nan] * (max_tenor - len(live))
    df = pd.DataFrame.from_dict(out, orient="index", columns=[f"M{i}" for i in range(1, max_tenor + 1)])
    df.index.name = "date"
    return df.sort_index()


def latest_complete(curve: pd.DataFrame, min_cols: int = 6) -> pd.Series:
    """The most recent date with a reasonably complete curve (today's partial
    intraday rows from the source are skipped)."""
    ok = curve[curve.notna().sum(axis=1) >= min_cols]
    return ok.iloc[-1] if not ok.empty else pd.Series(dtype=float)


def structure(curve: pd.DataFrame) -> pd.DataFrame:
    """Calendar spreads ($/bbl) and M1-M6 as % of M1."""
    if curve.empty:
        return pd.DataFrame()
    s = pd.DataFrame(index=curve.index)
    for t in (2, 3, 6, 12):
        s[f"m1_m{t}"] = curve["M1"] - curve[f"M{t}"]
    s["m1_m6_pct"] = s["m1_m6"] / curve["M1"] * 100
    return s


def classify(m1_m6_pct: float) -> str:
    """Thresholds on the 5-month roll yield, in % of the front price."""
    if np.isnan(m1_m6_pct):
        return "N/A"
    if m1_m6_pct >= 5:
        return "STEEP BACKWARDATION"
    if m1_m6_pct >= 1:
        return "BACKWARDATION"
    if m1_m6_pct <= -5:
        return "STEEP CONTANGO"
    if m1_m6_pct <= -1:
        return "CONTANGO"
    return "FLAT"


def december_spread(fut: pd.DataFrame, root: str) -> tuple[str, pd.Series]:
    """Dec(Y) - Dec(Y+1): a fixed pair of contracts, so its history is
    continuous over the ~2 years both trade - the classic structure gauge."""
    if fut.empty:
        return "", pd.Series(dtype=float)
    today = fut["date"].max()
    y = today.year if expiry(root, pd.Timestamp(year=today.year, month=12, day=1)) > today else today.year + 1
    d1, d2 = pd.Timestamp(year=y, month=12, day=1), pd.Timestamp(year=y + 1, month=12, day=1)
    w = fut[fut["delivery"].isin([d1, d2])].pivot_table(index="date", columns="delivery", values="close")
    if d1 not in w or d2 not in w:
        return "", pd.Series(dtype=float)
    return f"Dec{y % 100:02d}-Dec{(y + 1) % 100:02d}", (w[d1] - w[d2]).dropna()


def summary(fut: pd.DataFrame, root: str) -> dict:
    curve = generic_curve(fut, root)
    if curve.empty:
        return {}
    last = latest_complete(curve)
    if last.empty:
        return {}
    st = structure(curve.loc[[last.name]]).iloc[0]
    label, dec = december_spread(fut, root)
    contracts = fut[fut["date"] == last.name].sort_values("delivery")
    return {
        "date": last.name,
        "curve": last.dropna(),
        "contracts": contracts[["contract", "delivery", "close"]].reset_index(drop=True),
        "m1_m2": float(st["m1_m2"]),
        "m1_m3": float(st["m1_m3"]),
        "m1_m6": float(st["m1_m6"]),
        "m1_m12": float(st["m1_m12"]) if not np.isnan(st["m1_m12"]) else np.nan,
        "m1_m6_pct": float(st["m1_m6_pct"]),
        "structure": classify(float(st["m1_m6_pct"])),
        "dec_label": label,
        "dec_spread": dec,
        "history": structure(curve).dropna(subset=["m1_m6"]),
    }

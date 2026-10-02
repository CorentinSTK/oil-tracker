"""Seasonal comparisons: "vs the 5-year average for this week of the year".

US stocks have a strong seasonal cycle (gasoline builds in winter, draws in
driving season), so a level or a weekly change only means something against
the same week in prior years. The current year is always excluded from its
own baseline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _year_week(idx: pd.DatetimeIndex) -> tuple[np.ndarray, np.ndarray]:
    # ISO year + ISO week, so 1-3 January dates that belong to the previous
    # year's last week are not mixed into the new year. ISO week 53 only
    # exists in some years; fold it into 52 so it has a baseline.
    iso = idx.isocalendar()
    return iso.year.to_numpy(dtype=int), np.minimum(iso.week.to_numpy(dtype=int), 52)


def seasonal_stats(s: pd.Series, years: int = 5, min_years: int = 3) -> pd.DataFrame:
    """For each weekly observation: the prior-``years`` same-week avg/min/max.

    Returns columns ``value, avg, min, max, dev`` (dev = value - avg), indexed
    like ``s``. Rows with fewer than ``min_years`` comparable years get NaN.
    """
    s = s.dropna()
    if s.empty:
        return pd.DataFrame(columns=["value", "avg", "min", "max", "dev"], dtype=float)
    year, week = _year_week(s.index)
    df = pd.DataFrame({"value": s.to_numpy(), "year": year, "week": week}, index=s.index)
    grid = df.pivot_table(index="year", columns="week", values="value", aggfunc="mean")

    avg, lo, hi = [], [], []
    for y, w in zip(df["year"], df["week"]):
        hist = grid.loc[(grid.index >= y - years) & (grid.index < y), w].dropna() if w in grid else pd.Series()
        if len(hist) >= min_years:
            avg.append(hist.mean()); lo.append(hist.min()); hi.append(hist.max())
        else:
            avg.append(np.nan); lo.append(np.nan); hi.append(np.nan)
    out = pd.DataFrame({"value": df["value"], "avg": avg, "min": lo, "max": hi}, index=s.index)
    out["dev"] = out["value"] - out["avg"]
    return out


def seasonal_curve(s: pd.Series, years: int = 5, as_of_year: int | None = None) -> pd.DataFrame:
    """Week-of-year profile for charting: prior-``years`` avg/min/max band plus
    the current and previous year's path."""
    s = s.dropna()
    year, week = _year_week(s.index)
    as_of_year = as_of_year or int(year.max())
    df = pd.DataFrame({"value": s.to_numpy(), "year": year, "week": week})
    hist = df[(df["year"] >= as_of_year - years) & (df["year"] < as_of_year)]
    band = hist.groupby("week")["value"].agg(["mean", "min", "max"])
    cur = df[df["year"] == as_of_year].groupby("week")["value"].last().rename("current")
    prev = df[df["year"] == as_of_year - 1].groupby("week")["value"].last().rename("previous")
    return band.join([cur, prev], how="left")

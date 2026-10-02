"""US weekly fundamentals and the global/OPEC+ balance (EIA STEO)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from oil_tracker.analytics.seasonal import seasonal_stats

# Commercial stocks that make up the "total" used in the S&D score.
STOCK_KEYS = ["us_crude", "us_gasoline", "us_distillates"]


def inventory_summary(s: pd.Series) -> dict:
    """Latest weekly level and change, each judged against its seasonal norm.

    ``seasonal_chg`` is the average change for this week over the prior five
    years; the gap to it (``surprise``) is what separates a genuinely bullish
    draw from an ordinary seasonal one.
    """
    s = s.dropna()
    if len(s) < 2:
        return {}
    lvl = seasonal_stats(s)
    chg = seasonal_stats(s.diff().dropna())
    cur, prev = float(s.iloc[-1]), float(s.iloc[-2])
    wow = cur - prev
    # Size of a "normal" weekly move, from the last 5 years of changes.
    recent_chg = s.diff().loc[s.index > s.index[-1] - pd.Timedelta(days=5 * 365)]
    sd = float(recent_chg.std())
    surprise = wow - chg["avg"].iloc[-1]
    return {
        "date": s.index[-1],
        "level": cur,
        "wow": wow,
        "wow_pct": wow / prev * 100 if prev else np.nan,
        "avg_5y": float(lvl["avg"].iloc[-1]),
        "min_5y": float(lvl["min"].iloc[-1]),
        "max_5y": float(lvl["max"].iloc[-1]),
        "vs_5y": float(lvl["dev"].iloc[-1]),
        "vs_5y_pct": float(lvl["dev"].iloc[-1] / lvl["avg"].iloc[-1] * 100),
        "yoy": cur - float(s.asof(s.index[-1] - pd.Timedelta(days=364))),
        "seasonal_chg": float(chg["avg"].iloc[-1]),
        "surprise": float(surprise),
        "chg_std": sd,
        "signal": "DRAW" if wow < 0 else "BUILD",
        "magnitude": "LARGE" if sd > 0 and abs(wow) > 1.5 * sd else "NORMAL",
    }


def refinery_summary(util: pd.Series) -> dict:
    util = util.dropna()
    if len(util) < 2:
        return {}
    st = seasonal_stats(util)
    cur = float(util.iloc[-1])
    vs5 = float(st["dev"].iloc[-1])
    sd = float(st["dev"].dropna().iloc[-260:].std())
    return {
        "date": util.index[-1],
        "level": cur,
        "wow": cur - float(util.iloc[-2]),
        "avg_5y": float(st["avg"].iloc[-1]),
        "vs_5y": vs5,
        "z": vs5 / sd if sd > 0 else np.nan,
        # Judge vs the seasonal norm: 92% is weak in July but strong in October.
        "signal": "STRONG" if vs5 >= 1.0 else "WEAK" if vs5 <= -1.0 else "NORMAL",
    }


def production_summary(prod: pd.Series) -> dict:
    prod = prod.dropna()
    if len(prod) < 5:
        return {}
    cur = float(prod.iloc[-1])
    return {
        "date": prod.index[-1],
        "level": cur,
        "wow": cur - float(prod.iloc[-2]),
        "chg_4w_avg": float(prod.iloc[-4:].mean() - prod.iloc[-8:-4].mean()),
        "yoy": cur - float(prod.asof(prod.index[-1] - pd.Timedelta(days=364))),
    }


def total_commercial_stocks(weekly: pd.DataFrame) -> pd.Series:
    return weekly[STOCK_KEYS].dropna().sum(axis=1).rename("total_stocks")


# --------------------------------------------------------------- global / STEO

def is_forecast(idx: pd.DatetimeIndex, today: pd.Timestamp | None = None) -> np.ndarray:
    """STEO months from the current month onwards are EIA forecasts; the two
    months before are usually estimates. We flag the forecast part only."""
    today = today or pd.Timestamp.today()
    return np.asarray(idx >= today.to_period("M").to_timestamp())


def global_balance(steo: pd.DataFrame) -> pd.DataFrame:
    """World supply - demand (mb/d), OECD days of forward demand cover, OPEC+."""
    df = steo.copy()
    df["implied_stock_change"] = df["world_supply"] - df["world_demand"]
    # Days of cover: end-of-month OECD commercial stocks / next month's OECD demand.
    df["oecd_days_cover"] = df["oecd_stocks"] / df["oecd_demand"].shift(-1)
    df["forecast"] = is_forecast(df.index)
    return df


def balance_summary(gb: pd.DataFrame) -> dict:
    hist = gb[~gb["forecast"]].dropna(subset=["implied_stock_change"])
    fcst = gb[gb["forecast"]].dropna(subset=["implied_stock_change"])
    if hist.empty:
        return {}
    last = hist.iloc[-1]
    nxt_q = fcst.iloc[:3]
    spare = gb["opec_spare"].dropna()
    spare_hist = spare[~gb.loc[spare.index, "forecast"]]
    cover = gb["oecd_days_cover"].dropna()
    cover_hist = cover[~gb.loc[cover.index, "forecast"]]
    return {
        "date": hist.index[-1],
        "implied_stock_change": float(last["implied_stock_change"]),
        "next_3m_avg": float(nxt_q["implied_stock_change"].mean()) if not nxt_q.empty else np.nan,
        "opec_spare": float(spare_hist.iloc[-1]) if not spare_hist.empty else np.nan,
        "opec_spare_date": spare_hist.index[-1] if not spare_hist.empty else None,
        "days_cover": float(cover_hist.iloc[-1]) if not cover_hist.empty else np.nan,
        "days_cover_5y": float(cover_hist.iloc[-61:-1].mean()) if len(cover_hist) > 12 else np.nan,
    }


# ----------------------------------------------------------------- OECD stocks

def monthly_seasonal(s: pd.Series, years: int = 5) -> pd.DataFrame:
    """Each month vs the average of the same calendar month in the prior
    ``years`` years (current year excluded)."""
    s = s.dropna()
    df = pd.DataFrame({"value": s, "year": s.index.year, "month": s.index.month})
    grid = df.pivot_table(index="year", columns="month", values="value")
    avg = [grid.loc[(grid.index >= y - years) & (grid.index < y), m].mean() if m in grid else np.nan
           for y, m in zip(df["year"], df["month"])]
    out = pd.DataFrame({"value": s, "avg_5y": avg}, index=s.index)
    out["dev"] = out["value"] - out["avg_5y"]
    return out


def oecd_stocks(gb: pd.DataFrame) -> pd.DataFrame:
    """OECD commercial stocks and days of cover, each vs its 5Y same-month average."""
    st = monthly_seasonal(gb["oecd_stocks"])
    cover = monthly_seasonal(gb["oecd_days_cover"])
    out = pd.DataFrame({
        "stocks": st["value"], "stocks_5y": st["avg_5y"], "stocks_vs_5y": st["dev"],
        "days_cover": cover["value"], "days_cover_5y": cover["avg_5y"], "days_cover_vs_5y": cover["dev"],
    })
    for k in ("us_stocks_steo", "other_oecd_stocks"):
        if k in gb:
            out[k] = gb[k]
    out["forecast"] = is_forecast(out.index)
    return out


def oecd_summary(oecd: pd.DataFrame) -> dict:
    hist = oecd[~oecd["forecast"]].dropna(subset=["stocks", "stocks_5y"])
    if hist.empty:
        return {}
    last = hist.iloc[-1]
    prev = hist["stocks"].asof(hist.index[-1] - pd.DateOffset(months=1))
    return {
        "date": hist.index[-1],
        "stocks": float(last["stocks"]),
        "mom": float(last["stocks"] - prev),
        "stocks_5y": float(last["stocks_5y"]),
        "vs_5y": float(last["stocks_vs_5y"]),
        "vs_5y_pct": float(last["stocks_vs_5y"] / last["stocks_5y"] * 100),
        "days_cover": float(last["days_cover"]),
        "days_cover_5y": float(last["days_cover_5y"]),
        "days_vs_5y": float(last["days_cover_vs_5y"]),
        "signal": "TIGHT" if last["stocks_vs_5y"] < -0.02 * last["stocks_5y"]
        else "LOOSE" if last["stocks_vs_5y"] > 0.02 * last["stocks_5y"] else "NORMAL",
    }

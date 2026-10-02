"""OPEC+ production by country, spare capacity, quotas and supply disruptions
(EIA STEO country series; quotas from data/manual/opec_quotas.csv)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from oil_tracker.analytics.fundamentals import is_forecast
from oil_tracker.sources import DISRUPTION_COUNTRIES, OPEC_MEMBERS, OPECPLUS_NON_OPEC

UAE = "TC"  # STEO code; total liquids only (see sources.py)


def country_production(steo: pd.DataFrame) -> pd.DataFrame:
    """Monthly crude production by country (mb/d). UAE is total liquids
    (crude + condensate + NGLs), so it is not comparable one-for-one."""
    cols = {f"prod_{c}": c for c in {**OPEC_MEMBERS, **OPECPLUS_NON_OPEC} if f"prod_{c}" in steo}
    df = steo[list(cols)].rename(columns=cols)
    if "uae_liquids" in steo:
        df[UAE] = steo["uae_liquids"]
    return df.dropna(how="all")


def country_name(code: str) -> str:
    if code == UAE:
        return "UAE (total liquids)"
    return {**OPEC_MEMBERS, **OPECPLUS_NON_OPEC}.get(code, DISRUPTION_COUNTRIES.get(code, code))


def country_table(steo: pd.DataFrame, quotas: pd.DataFrame) -> tuple[pd.Timestamp, pd.DataFrame]:
    """Latest non-forecast month: production, capacity, spare, m/m and y/y,
    and quota compliance where a quota has been entered."""
    prod = country_production(steo)
    hist = prod[~is_forecast(prod.index)]
    # Latest month most countries report (series end on different months).
    hist = hist[hist.notna().sum(axis=1) >= hist.shape[1] // 2]
    if hist.empty:
        return None, pd.DataFrame()
    month = hist.index[-1]
    rows = []
    for code in hist.columns:
        p = hist[code]
        cur = p.get(month, np.nan)
        cap = steo.get(f"cap_{code}", pd.Series(dtype=float)).get(month, np.nan)
        spare = steo.get(f"spare_{code}", pd.Series(dtype=float)).get(month, np.nan)
        rows.append({
            "code": code,
            "country": country_name(code),
            "group": "OPEC" if code in OPEC_MEMBERS else "UAE (liquids)" if code == UAE else "OPEC+ non-OPEC",
            "production": cur,
            "mom": cur - p.asof(month - pd.DateOffset(months=1)),
            "yoy": cur - p.asof(month - pd.DateOffset(months=12)),
            "capacity": cap,
            "spare": spare,
            "utilisation_pct": cur / cap * 100 if cap and cap > 0 else np.nan,
        })
    tbl = pd.DataFrame(rows)
    if not quotas.empty:
        q = quotas[quotas["effective_from"] <= month].sort_values("effective_from").groupby("country_code").last()
        tbl["quota"] = tbl["code"].map(q["required_mbd"])
        tbl["vs_quota"] = tbl["production"] - tbl["quota"]
        # Compliance with a cut is measured on production vs quota: >100% = over-producing.
        tbl["pct_of_quota"] = tbl["production"] / tbl["quota"] * 100
    return month, tbl.sort_values("production", ascending=False).reset_index(drop=True)


def disruptions(steo: pd.DataFrame) -> pd.DataFrame:
    cols = {f"outage_{c}": c for c in DISRUPTION_COUNTRIES if f"outage_{c}" in steo}
    return steo[list(cols)].rename(columns=cols).dropna(how="all")


def disruption_summary(steo: pd.DataFrame) -> dict:
    d = disruptions(steo)
    hist = d[~is_forecast(d.index)].dropna(how="all")
    tot = steo[["outage_opec", "outage_nonopec"]].dropna(how="all") if "outage_opec" in steo else pd.DataFrame()
    tot = tot[~is_forecast(tot.index)]
    if hist.empty or tot.empty:
        return {}
    month = hist.index[-1]
    latest = hist.loc[month].dropna()
    # Not DataFrame.asof: it skips any row containing a NaN.
    prev = hist.loc[hist.index <= month - pd.DateOffset(months=3)].iloc[-1]
    total = tot.loc[month].sum()
    return {
        "month": month,
        "total": float(total),
        "opec": float(tot.loc[month, "outage_opec"]),
        "non_opec": float(tot.loc[month, "outage_nonopec"]),
        "total_3m_ago": float(tot.loc[tot.index <= month - pd.DateOffset(months=3)].iloc[-1].sum()),
        "total_5y_avg": float(tot.sum(axis=1).loc[tot.index > month - pd.DateOffset(years=5)].mean()),
        "by_country": pd.DataFrame({
            "country": [country_name(c) for c in latest.index],
            "outage": latest.to_numpy(),
            "chg_3m": (latest - prev.reindex(latest.index).fillna(0)).to_numpy(),
        }).query("outage > 0.005").sort_values("outage", ascending=False).reset_index(drop=True),
    }

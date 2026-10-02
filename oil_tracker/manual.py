"""Analyst-maintained data that no free API provides.

Stored as CSV files in ``data/manual/`` and committed to the repo, because
Streamlit Community Cloud's disk is wiped on every restart: an edit made in
the deployed app lasts until the next restart unless the CSV is downloaded
and committed. Locally, edits are saved straight to the files.

- consensus.csv   : analyst-survey expectations for the weekly EIA changes
                    (Reuters/WSJ/Bloomberg polls, published Mon-Tue).
- iea_oecd.csv    : IEA Oil Market Report OECD industry stocks and days of
                    forward demand cover (monthly).
- opec_quotas.csv : OPEC+ required production by country.

Files ship with headers only. The tracker never invents values for them.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from oil_tracker import config

MANUAL_DIR = config.ROOT / "data" / "manual"

SCHEMAS: dict[str, dict] = {
    "consensus": {
        "file": "consensus.csv",
        "columns": {"week_ending": "date", "crude": "float", "gasoline": "float", "distillates": "float",
                    "source": "str"},
        "help": "Expected weekly change in Mbbl for the week ending (Friday) - e.g. -1.5 = expected 1.5 Mbbl draw.",
    },
    "iea_oecd": {
        "file": "iea_oecd.csv",
        "columns": {"month": "date", "stocks_mb": "float", "days_cover": "float", "source": "str"},
        "help": "IEA OMR: OECD industry stocks (Mbbl, end of month) and days of forward demand cover.",
    },
    "opec_quotas": {
        "file": "opec_quotas.csv",
        "columns": {"effective_from": "date", "country_code": "str", "required_mbd": "float", "source": "str"},
        "help": "OPEC+ required production (mb/d) by STEO country code (SA, IZ, KU, RS, ...), from the month it applies.",
    },
}


def path(name: str) -> Path:
    return MANUAL_DIR / SCHEMAS[name]["file"]


def empty(name: str) -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype="datetime64[ns]" if t == "date" else "float64" if t == "float" else "object")
                         for c, t in SCHEMAS[name]["columns"].items()})


def load(name: str) -> pd.DataFrame:
    p = path(name)
    if not p.exists():
        return empty(name)
    df = pd.read_csv(p)
    for c, t in SCHEMAS[name]["columns"].items():
        if c not in df:
            df[c] = pd.NA
        if t == "date":
            df[c] = pd.to_datetime(df[c], errors="coerce")
        elif t == "float":
            df[c] = pd.to_numeric(df[c], errors="coerce")
        else:
            df[c] = df[c].astype("object")
    first = next(iter(SCHEMAS[name]["columns"]))
    return df[list(SCHEMAS[name]["columns"])].dropna(subset=[first]).sort_values(first).reset_index(drop=True)


def to_csv(df: pd.DataFrame, name: str) -> str:
    out = df.copy()
    for c, t in SCHEMAS[name]["columns"].items():
        if t == "date":
            out[c] = pd.to_datetime(out[c], errors="coerce").dt.strftime("%Y-%m-%d")
    return out.to_csv(index=False)


def save(df: pd.DataFrame, name: str) -> Path:
    MANUAL_DIR.mkdir(parents=True, exist_ok=True)
    p = path(name)
    p.write_text(to_csv(df, name))
    return p

"""Runtime configuration.

Secrets are resolved in this order: environment variables (``.env`` loaded at
import), then Streamlit secrets (``.streamlit/secrets.toml`` locally, the
"Secrets" panel on Streamlit Community Cloud). Nothing is ever hard-coded.
"""

from __future__ import annotations

import os
import tomllib
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = Path(os.environ.get("OIL_TRACKER_DATA_DIR", ROOT / "data"))
DB_PATH = Path(os.environ.get("OIL_TRACKER_DB", DATA_DIR / "oil_tracker.db"))
NOTICES_PATH = ROOT / "config" / "notices.toml"

HTTP_TIMEOUT = 30
USER_AGENT = "oil-tracker/0.1 (+https://github.com)"


def get_secret(name: str) -> str | None:
    value = os.environ.get(name)
    if value:
        return value
    try:  # Streamlit is optional (the API and the CLI run without it)
        import streamlit as st

        return st.secrets.get(name)  # type: ignore[no-any-return]
    except Exception:
        return None


def eia_key() -> str | None:
    return get_secret("EIA_API_KEY")


def fred_key() -> str | None:
    return get_secret("FRED_API_KEY")


def oilpriceapi_key() -> str | None:
    return get_secret("OILPRICEAPI_KEY")


@lru_cache(maxsize=1)
def notices() -> list[dict]:
    """Analyst-maintained banners (data-quality caveats, disruptions)."""
    if not NOTICES_PATH.exists():
        return []
    with NOTICES_PATH.open("rb") as fh:
        raw = tomllib.load(fh)
    return [n for n in raw.get("notice", []) if n.get("active", True)]

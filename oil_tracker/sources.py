"""Catalogue of every series the tracker stores.

One place that says what each series is, where it comes from, its unit and how
often it is worth refetching. Analytics refer to series by ``key`` only.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Series:
    key: str            # internal id, used everywhere downstream
    source: str         # "eia" | "eia_steo" | "fred"
    remote_id: str      # id at the provider
    label: str
    unit: str
    frequency: str      # "D" | "W" | "M"
    scale: float = 1.0  # multiply raw provider value by this before storing
    note: str = ""


SERIES: dict[str, Series] = {
    s.key: s
    for s in [
        # --- Prices (daily spot, consistent basis for history and spreads) ---
        Series("wti", "eia", "PET.RWTC.D", "WTI Cushing spot", "$/bbl", "D"),
        Series("brent", "eia", "PET.RBRTE.D", "Brent (Dated) spot", "$/bbl", "D"),
        # Dubai has no free daily history; IMF monthly average via FRED.
        Series("dubai_m", "fred", "POILDUBUSDM", "Dubai Fateh (monthly avg, IMF)", "$/bbl", "M",
               note="Monthly average, published with a ~2-3 month lag."),
        # --- US weekly fundamentals (EIA Weekly Petroleum Status Report) ---
        Series("us_crude", "eia", "PET.WCESTUS1.W", "US commercial crude stocks (ex-SPR)", "Mbbl", "W", 1e-3),
        Series("cushing", "eia", "PET.W_EPC0_SAX_YCUOK_MBBL.W", "Cushing crude stocks", "Mbbl", "W", 1e-3),
        Series("us_gasoline", "eia", "PET.WGTSTUS1.W", "US total gasoline stocks", "Mbbl", "W", 1e-3),
        Series("us_distillates", "eia", "PET.WDISTUS1.W", "US distillate stocks", "Mbbl", "W", 1e-3),
        Series("spr", "eia", "PET.WCSSTUS1.W", "US SPR stocks", "Mbbl", "W", 1e-3),
        Series("refinery_util", "eia", "PET.WPULEUS3.W", "US refinery utilization", "%", "W"),
        Series("us_production", "eia", "PET.WCRFPUS2.W", "US crude field production", "kb/d", "W"),
        # --- Global balance & OPEC+ (EIA Short-Term Energy Outlook, monthly) ---
        Series("world_supply", "eia_steo", "PAPR_WORLD", "World liquids production", "mb/d", "M"),
        Series("world_demand", "eia_steo", "PATC_WORLD", "World liquids consumption", "mb/d", "M"),
        Series("oecd_demand", "eia_steo", "PATC_OECD", "OECD liquids consumption", "mb/d", "M"),
        Series("oecd_stocks", "eia_steo", "PASC_OECD_T3", "OECD commercial stocks", "Mbbl", "M"),
        Series("opec_prod", "eia_steo", "COPR_OPEC", "OPEC crude production", "mb/d", "M"),
        Series("opecplus_prod", "eia_steo", "COPR_OPECPLUS", "OPEC+ crude production", "mb/d", "M"),
        Series("opec_capacity", "eia_steo", "COPC_OPEC", "OPEC crude production capacity", "mb/d", "M"),
        Series("opec_spare", "eia_steo", "COPS_OPEC", "OPEC spare capacity", "mb/d", "M"),
        # --- Macro context ---
        Series("usd_broad", "fred", "DTWEXBGS", "Broad trade-weighted USD index", "index", "D"),
        Series("t10y2y", "fred", "T10Y2Y", "US 10Y-2Y Treasury spread", "pp", "D"),
    ]
}

# How long (hours) a stored series is considered fresh before we refetch.
# Weekly EIA data lands Wednesdays; checking every 6h catches it the same day.
REFRESH_HOURS = {"D": 6, "W": 6, "M": 24}

# Codes requested from OilPriceAPI for the indicative live snapshot.
SNAPSHOT_CODES = {
    "WTI_USD": "wti",
    "BRENT_CRUDE_USD": "brent",
    "DUBAI_CRUDE_USD": "dubai",
    "OPEC_BASKET_USD": "opec_basket",
}

"""Catalogue of every series the tracker stores.

One place that says what each series is, where it comes from, its unit and how
often it is worth refetching. Analytics refer to series by ``key`` only.
"""

from __future__ import annotations

from dataclasses import dataclass

GAL_PER_BBL = 42.0


@dataclass(frozen=True)
class Series:
    key: str            # internal id, used everywhere downstream
    source: str         # "eia" | "eia_steo" | "fred" | "gpr"
    remote_id: str      # id at the provider
    label: str
    unit: str
    frequency: str      # "D" | "W" | "M"
    scale: float = 1.0  # multiply raw provider value by this before storing
    note: str = ""


# STEO country codes. In the current STEO, the OPEC total equals the sum of
# these members exactly (UAE is not in it); UAE is tracked separately through
# its total liquids supply, as there is no crude-only STEO series for it.
OPEC_MEMBERS = {
    "SA": "Saudi Arabia", "IZ": "Iraq", "IR": "Iran", "KU": "Kuwait", "LY": "Libya", "NI": "Nigeria",
    "VE": "Venezuela", "AG": "Algeria", "CF": "Congo", "EK": "Equatorial Guinea", "GB": "Gabon",
}
OPECPLUS_NON_OPEC = {
    "RS": "Russia", "KZ": "Kazakhstan", "MX": "Mexico", "MU": "Oman", "AJ": "Azerbaijan",
    "MY": "Malaysia", "BA": "Bahrain", "BX": "Brunei", "SU": "Sudan", "OD": "South Sudan",
}
# Members for which STEO publishes capacity and spare capacity.
CAPACITY_MEMBERS = ["SA", "IZ", "IR", "KU", "LY", "NI", "VE", "AG", "CF", "EK", "GB"]
DISRUPTION_COUNTRIES = {
    "IR": "Iran", "IZ": "Iraq", "KU": "Kuwait", "LY": "Libya", "NI": "Nigeria", "SA": "Saudi Arabia",
    "VE": "Venezuela", "GB": "Gabon", "RS": "Russia", "SY": "Syria", "YM": "Yemen", "SU": "Sudan",
    "CA": "Canada", "US": "United States", "MX": "Mexico", "BR": "Brazil", "NORTHSEA": "North Sea",
    "NO": "Norway", "UK": "United Kingdom", "CO": "Colombia", "AJ": "Azerbaijan", "CH": "China",
}

_core = [
    # --- Crude prices (daily spot, consistent basis for history and spreads) ---
    Series("wti", "eia", "PET.RWTC.D", "WTI Cushing spot", "$/bbl", "D"),
    Series("brent", "eia", "PET.RBRTE.D", "Brent (Dated) spot", "$/bbl", "D"),
    # Dubai has no free daily history; IMF monthly average via FRED.
    Series("dubai_m", "fred", "POILDUBUSDM", "Dubai Fateh (monthly avg, IMF)", "$/bbl", "M",
           note="Monthly average, published with a ~2-3 month lag."),
    # --- Refined product spot prices (EIA, $/gal -> stored in $/bbl) ---
    Series("gas_nyh", "eia", "PET.EER_EPMRU_PF4_Y35NY_DPG.D", "NY Harbor conventional gasoline", "$/bbl", "D", GAL_PER_BBL),
    Series("gas_usgc", "eia", "PET.EER_EPMRU_PF4_RGC_DPG.D", "US Gulf Coast conventional gasoline", "$/bbl", "D", GAL_PER_BBL),
    Series("ulsd_nyh", "eia", "PET.EER_EPD2DXL0_PF4_Y35NY_DPG.D", "NY Harbor ULSD", "$/bbl", "D", GAL_PER_BBL),
    Series("ulsd_usgc", "eia", "PET.EER_EPD2DXL0_PF4_RGC_DPG.D", "US Gulf Coast ULSD", "$/bbl", "D", GAL_PER_BBL),
    Series("jet_usgc", "eia", "PET.EER_EPJK_PF4_RGC_DPG.D", "US Gulf Coast jet fuel", "$/bbl", "D", GAL_PER_BBL),
    Series("gas_retail", "eia", "PET.EMM_EPMR_PTE_NUS_DPG.W", "US retail gasoline (all formulations)", "$/gal", "W"),
    # --- US weekly fundamentals (EIA Weekly Petroleum Status Report) ---
    Series("us_crude", "eia", "PET.WCESTUS1.W", "US commercial crude stocks (ex-SPR)", "Mbbl", "W", 1e-3),
    Series("cushing", "eia", "PET.W_EPC0_SAX_YCUOK_MBBL.W", "Cushing crude stocks", "Mbbl", "W", 1e-3),
    Series("us_gasoline", "eia", "PET.WGTSTUS1.W", "US total gasoline stocks", "Mbbl", "W", 1e-3),
    Series("us_distillates", "eia", "PET.WDISTUS1.W", "US distillate stocks", "Mbbl", "W", 1e-3),
    Series("spr", "eia", "PET.WCSSTUS1.W", "US SPR stocks", "Mbbl", "W", 1e-3),
    Series("refinery_util", "eia", "PET.WPULEUS3.W", "US refinery utilization", "%", "W"),
    Series("us_production", "eia", "PET.WCRFPUS2.W", "US crude field production", "kb/d", "W"),
    Series("crude_imports", "eia", "PET.WCRIMUS2.W", "US crude imports", "kb/d", "W"),
    Series("crude_exports", "eia", "PET.WCREXUS2.W", "US crude exports", "kb/d", "W"),
    # Product supplied = the EIA's proxy for US demand ("implied demand").
    Series("ps_total", "eia", "PET.WRPUPUS2.W", "US total products supplied", "kb/d", "W"),
    Series("ps_gasoline", "eia", "PET.WGFUPUS2.W", "US gasoline supplied", "kb/d", "W"),
    Series("ps_distillate", "eia", "PET.WDIUPUS2.W", "US distillate supplied", "kb/d", "W"),
    Series("ps_jet", "eia", "PET.WKJUPUS2.W", "US jet fuel supplied", "kb/d", "W"),
    # --- Global balance, OECD stocks & OPEC+ (EIA Short-Term Energy Outlook) ---
    Series("world_supply", "eia_steo", "PAPR_WORLD", "World liquids production", "mb/d", "M"),
    Series("world_demand", "eia_steo", "PATC_WORLD", "World liquids consumption", "mb/d", "M"),
    Series("world_stock_draw", "eia_steo", "T3_STCHANGE_WORLD", "World net inventory withdrawals", "mb/d", "M"),
    Series("oecd_demand", "eia_steo", "PATC_OECD", "OECD liquids consumption", "mb/d", "M"),
    Series("china_demand", "eia_steo", "PATC_CH", "China liquids consumption", "mb/d", "M"),
    Series("india_demand", "eia_steo", "PATC_IN", "India liquids consumption", "mb/d", "M"),
    Series("oecd_stocks", "eia_steo", "PASC_OECD_T3", "OECD commercial stocks", "Mbbl", "M"),
    Series("us_stocks_steo", "eia_steo", "PASC_US", "US commercial stocks (STEO)", "Mbbl", "M"),
    Series("other_oecd_stocks", "eia_steo", "PASC_OOECD_T3", "Other OECD commercial stocks", "Mbbl", "M"),
    Series("opec_prod", "eia_steo", "COPR_OPEC", "OPEC crude production", "mb/d", "M"),
    Series("opecplus_prod", "eia_steo", "COPR_OPECPLUS", "OPEC+ crude production", "mb/d", "M"),
    Series("opec_capacity", "eia_steo", "COPC_OPEC", "OPEC crude production capacity", "mb/d", "M"),
    Series("opec_spare", "eia_steo", "COPS_OPEC", "OPEC spare capacity", "mb/d", "M"),
    Series("uae_liquids", "eia_steo", "PAPR_TC", "UAE total liquids supply", "mb/d", "M"),
    Series("outage_opec", "eia_steo", "PADI_OPEC", "OPEC unplanned outages", "mb/d", "M"),
    Series("outage_nonopec", "eia_steo", "PADI_NONOPEC", "Non-OPEC unplanned outages", "mb/d", "M"),
    # --- Macro & risk context ---
    Series("usd_broad", "fred", "DTWEXBGS", "Broad trade-weighted USD index", "index", "D"),
    Series("t10y2y", "fred", "T10Y2Y", "US 10Y-2Y Treasury spread", "pp", "D"),
    Series("ust10y", "fred", "DGS10", "US 10Y Treasury yield", "%", "D"),
    Series("sp500", "fred", "SP500", "S&P 500", "index", "D"),
    Series("ovx", "fred", "OVXCLS", "CBOE crude oil volatility (OVX)", "index", "D"),
    Series("vix", "fred", "VIXCLS", "CBOE equity volatility (VIX)", "index", "D"),
    Series("gepu", "fred", "GEPUCURRENT", "Global economic policy uncertainty", "index", "M"),
    Series("gpr_daily", "gpr", "GPRD", "Geopolitical Risk index (daily)", "index", "D",
           note="Caldara & Iacoviello, share of newspaper articles on geopolitical tensions; 1985-2019 avg = 100."),
    Series("gpr_m", "gpr", "GPR", "Geopolitical Risk index (monthly)", "index", "M"),
]

_countries = (
    [Series(f"prod_{c}", "eia_steo", f"COPR_{c}", f"{n} crude production", "mb/d", "M")
     for c, n in {**OPEC_MEMBERS, **OPECPLUS_NON_OPEC}.items()]
    + [Series(f"cap_{c}", "eia_steo", f"COPC_{c}", f"{OPEC_MEMBERS[c]} crude capacity", "mb/d", "M")
       for c in CAPACITY_MEMBERS]
    + [Series(f"spare_{c}", "eia_steo", f"COPS_{c}", f"{OPEC_MEMBERS[c]} spare capacity", "mb/d", "M")
       for c in CAPACITY_MEMBERS]
    + [Series(f"outage_{c}", "eia_steo", f"PADI_{c}", f"{n} unplanned outages", "mb/d", "M")
       for c, n in DISRUPTION_COUNTRIES.items()]
)

SERIES: dict[str, Series] = {s.key: s for s in _core + _countries}

# How long (hours) a stored series is considered fresh before we refetch.
# Weekly EIA series are additionally refetched as soon as a new WPSR is out
# (see data/pipeline.py), so the 6h is only a fallback.
REFRESH_HOURS = {"D": 6, "W": 6, "M": 24}

# Codes requested from OilPriceAPI for the indicative live snapshot.
SNAPSHOT_CODES = {
    "WTI_USD": "wti",
    "BRENT_CRUDE_USD": "brent",
    "DUBAI_CRUDE_USD": "dubai",
    "OPEC_BASKET_USD": "opec_basket",
}

# Futures roots on Yahoo Finance (NYMEX listings). BZ = NYMEX Brent Last Day
# Financial, which settles on ICE Brent - the free proxy for the ICE curve.
FUTURES_ROOTS = {"wti": "CL", "brent": "BZ"}
FUTURES_MONTHS_AHEAD = 24

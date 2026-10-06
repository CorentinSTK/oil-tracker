"""Data sources, freshness and transparency.

Complete inventory of every series in the Oil Market Tracker, including:
- Source (EIA, FRED, OECD, OilPriceAPI, etc.)
- Frequency (daily, weekly, monthly)
- Lag (when data becomes available)
- Why this source was chosen
"""

import streamlit as st
import pandas as pd

from oil_tracker import ui
from oil_tracker.sources import SERIES

ctx = ui.get_ctx()
ui.page_header(
    "Data Sources & Freshness",
    ctx,
    "Complete transparency on where every number comes from, how fresh it is, and why these sources were chosen.",
)

# Data source definitions with explanations
DATA_SOURCES_INFO = {
    "eia": {
        "label": "U.S. Energy Information Administration (EIA)",
        "url": "https://www.eia.gov",
        "description": "Official US energy data: spot prices, weekly inventories, production, demand (product supplied), refining data.",
        "update_freq": "Daily (prices), Weekly (fundamentals on Wednesdays)",
        "why_chosen": "Official government source, free API, longest history, most trusted by market participants.",
    },
    "eia_steo": {
        "label": "EIA Short-Term Energy Outlook (STEO)",
        "url": "https://www.eia.gov/outlooks/steo/",
        "description": "Monthly global balance sheet: world supply/demand, OPEC+ production, OECD stocks, forecasts.",
        "update_freq": "Monthly (10th of each month)",
        "why_chosen": "Only free global balance sheet reconciling OPEC+, OECD and non-OPEC data. Updated monthly.",
    },
    "fred": {
        "label": "Federal Reserve Economic Data (FRED)",
        "url": "https://fred.stlouisfed.org",
        "description": "Dubai monthly spot (IMF), broad USD index, Treasury yields, equity indices, volatility indices (VIX, OVX).",
        "update_freq": "Daily (markets/indices), Monthly (Dubai pricing)",
        "why_chosen": "Free, high-quality macro data. Dubai is sourced via IMF monthly average (only free long-term history).",
    },
    "gpr": {
        "label": "Caldara & Iacoviello - Geopolitical Risk Index",
        "url": "https://www.matteoiacoviello.com/gpr.htm",
        "description": "Daily and monthly geopolitical risk scores based on news media analysis.",
        "update_freq": "Daily (with lag), Monthly",
        "why_chosen": "Best free measure of geopolitical event intensity. Used to contextualise supply disruptions.",
    },
    "oilprice": {
        "label": "OilPriceAPI",
        "url": "https://oilpriceapi.com",
        "description": "Live indicative spot quotes for WTI, Brent, Dubai, OPEC basket (snapshot only, not stored).",
        "update_freq": "Real-time during market hours",
        "why_chosen": "Provides same-source snapshot for spread calculations; live mid-market indications.",
    },
    "yahoo": {
        "label": "Yahoo Finance",
        "url": "https://finance.yahoo.com",
        "description": "Futures curves: WTI (NYMEX CL), Brent (NYMEX BZ from ICE Brent Dated final)",
        "update_freq": "Daily after US market close",
        "why_chosen": "Free, high-quality futures data; NYMEX CL and ICE BZ are market-standard contracts.",
    },
}

# Detailed series by category
SERIES_BY_CATEGORY = {
    "Crude Spot Prices": [
        ("wti", "WTI Cushing (daily spot)", "EIA", "Daily", "Same day"),
        ("brent", "Brent Dated (daily spot)", "EIA", "Daily", "Same day"),
        ("dubai_m", "Dubai Fateh (monthly avg)", "FRED/IMF", "Monthly", "2-3 months lag"),
    ],
    "Refined Products (US)": [
        ("gas_nyh", "NY Harbor gasoline", "EIA", "Daily", "Same day"),
        ("gas_usgc", "US Gulf Coast gasoline", "EIA", "Daily", "Same day"),
        ("ulsd_nyh", "NY Harbor ULSD", "EIA", "Daily", "Same day"),
        ("ulsd_usgc", "US Gulf Coast ULSD", "EIA", "Daily", "Same day"),
        ("jet_usgc", "US Gulf Coast jet fuel", "EIA", "Daily", "Same day"),
        ("gas_retail", "US retail gasoline (all)", "EIA", "Weekly", "Wednesday release (Tue data)"),
    ],
    "US Fundamentals (Weekly)": [
        ("us_crude", "US commercial crude stocks", "EIA WPSR", "Weekly", "Wednesday (Fri data)"),
        ("cushing", "Cushing crude stocks", "EIA WPSR", "Weekly", "Wednesday (Fri data)"),
        ("us_gasoline", "US total gasoline stocks", "EIA WPSR", "Weekly", "Wednesday (Fri data)"),
        ("us_distillates", "US distillate stocks", "EIA WPSR", "Weekly", "Wednesday (Fri data)"),
        ("spr", "US Strategic Petroleum Reserve", "EIA WPSR", "Weekly", "Wednesday (Fri data)"),
        ("refinery_util", "US refinery utilization", "EIA WPSR", "Weekly", "Wednesday (Fri data)"),
        ("us_production", "US crude field production", "EIA WPSR", "Weekly", "Wednesday (Fri data)"),
        ("crude_imports", "US crude imports", "EIA WPSR", "Weekly", "Wednesday (Fri data)"),
        ("crude_exports", "US crude exports", "EIA WPSR", "Weekly", "Wednesday (Fri data)"),
        ("ps_total", "US total products supplied", "EIA WPSR", "Weekly", "Wednesday (Fri data)"),
        ("ps_gasoline", "US gasoline supplied", "EIA WPSR", "Weekly", "Wednesday (Fri data)"),
        ("ps_distillate", "US distillate supplied", "EIA WPSR", "Weekly", "Wednesday (Fri data)"),
        ("ps_jet", "US jet fuel supplied", "EIA WPSR", "Weekly", "Wednesday (Fri data)"),
    ],
    "Global Balance & OPEC+ (Monthly)": [
        ("world_supply", "World liquids production", "EIA STEO", "Monthly", "10th of month"),
        ("world_demand", "World liquids consumption", "EIA STEO", "Monthly", "10th of month"),
        ("world_stock_draw", "World net inventory change", "EIA STEO", "Monthly", "10th of month"),
        ("oecd_demand", "OECD liquids consumption", "EIA STEO", "Monthly", "10th of month"),
        ("china_demand", "China liquids consumption", "EIA STEO", "Monthly", "10th of month"),
        ("india_demand", "India liquids consumption", "EIA STEO", "Monthly", "10th of month"),
        ("oecd_stocks", "OECD commercial stocks", "EIA STEO", "Monthly", "10th of month"),
        ("opec_prod", "OPEC crude production", "EIA STEO", "Monthly", "10th of month"),
        ("opecplus_prod", "OPEC+ crude production", "EIA STEO", "Monthly", "10th of month"),
        ("opec_capacity", "OPEC crude capacity", "EIA STEO", "Monthly", "10th of month"),
        ("opec_spare", "OPEC spare capacity", "EIA STEO", "Monthly", "10th of month"),
    ],
    "Macro & Risk Context": [
        ("usd_broad", "Broad USD trade-weighted index", "FRED", "Daily", "Same day"),
        ("t10y2y", "US 10Y-2Y Treasury spread", "FRED", "Daily", "Same day"),
        ("ust10y", "US 10Y Treasury yield", "FRED", "Daily", "Same day"),
        ("sp500", "S&P 500", "FRED", "Daily", "Same day"),
        ("ovx", "CBOE crude oil volatility (OVX)", "FRED", "Daily", "Same day"),
        ("vix", "CBOE equity volatility (VIX)", "FRED", "Daily", "Same day"),
        ("gepu", "Global economic policy uncertainty", "FRED", "Monthly", "Monthly"),
        ("gpr_daily", "Geopolitical risk index (daily)", "Caldara & Iacoviello", "Daily", "~1-2 weeks lag"),
        ("gpr_m", "Geopolitical risk index (monthly)", "Caldara & Iacoviello", "Monthly", "Monthly"),
    ],
}

# Display source overview
st.markdown("## Data Sources Overview")
for source_key, info in DATA_SOURCES_INFO.items():
    with st.expander(f"**{info['label']}**", expanded=(source_key == "eia")):
        st.markdown(f"**URL:** [{info['url']}]({info['url']})")
        st.markdown(f"**Description:** {info['description']}")
        st.markdown(f"**Update frequency:** {info['update_freq']}")
        st.markdown(f"**Why chosen:** {info['why_chosen']}")

# Display detailed series table
st.markdown("## Complete Series Inventory")
for category, series_list in SERIES_BY_CATEGORY.items():
    st.markdown(f"### {category}")
    df_data = []
    for key, label, source, freq, lag in series_list:
        series_obj = SERIES.get(key)
        if series_obj:
            df_data.append({
                "Series": label,
                "Key": key,
                "Source": source,
                "Frequency": freq,
                "Data Lag": lag,
                "Unit": series_obj.unit,
            })
    if df_data:
        df = pd.DataFrame(df_data)
        st.dataframe(df, hide_index=True, width="stretch")

# Data freshness status
st.markdown("## Current Data Freshness Status")
staleness = ctx["staleness"]
if staleness:
    cols = st.columns(len(staleness))
    for col, (key, status) in zip(cols, staleness.items()):
        with col:
            label = status["label"]
            age = status["age_days"]
            is_stale = status["stale"]

            badge = "🟢 Fresh" if not is_stale else "🟡 Stale"
            st.metric(
                label,
                badge,
                f"Last: {status['last'].strftime('%Y-%m-%d') if status['last'] else 'N/A'} ({age} days ago if available)"
                if status['last'] else "No data",
                border=True
            )

# Known data limitations
st.markdown("## Known Data Limitations & Gaps")
st.info(
    """
**Asia-Pacific market coverage:**
- No Singapore or Rotterdam product price data available from free sources.
- NYH (New York Harbor) crack is used as Atlantic basin proxy, but does not represent Asian refining margins.
- **Why not estimated?** Singapore margins would require daily Singapore product quotes (Platts/MOPS), which require paid subscriptions.
  Rather than guess, the app documents the gap transparently.

**Dubai pricing:**
- Monthly average only (IMF via FRED), with 2-3 month publication lag.
- No daily Dubai history available free; the Platts 5TC assessment requires subscription.
- Monthly averages smooth out daily volatility but are suitable for spread analysis and global balance.

**OPEC+ production data:**
- STEO forecasts update monthly but are not real-time; reflects IEA/OPEC assessments published mid-month.
- Actual production lags official announcements by weeks. Monthly STEO is the best free consensus view.

**Geopolitical risk:**
- The GPR index is news-based and reflects *reported* tensions, not necessarily market impact.
  Use alongside actual supply data (STEO outage fields) for context.
""",
    icon="⚠️"
)

# API keys and refresh
st.markdown("## Data Pipeline")
st.caption(
    """
- **Price refresh (daily):** Every 6 hours if not already fetched today.
- **Weekly EIA:** Refetched automatically when a new WPSR is announced (typically Wed).
- **Monthly STEO/FRED:** Every 24 hours.
- **Snapshots (OilPriceAPI):** Real-time during market hours; not stored, used for live spread indications only.
"""
)

st.divider()
st.markdown(
    """
**Questions or data requests?**
This tracker prioritises free, widely-available data to remain transparent and reproducible.
If you'd like to add new data sources (e.g. premium databases, proprietary indices),
please open an issue on [GitHub](https://github.com/CorentinSTK/oil-tracker).
"""
)

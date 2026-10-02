"""Oil Market Tracker - Streamlit entry point.

Run locally:   streamlit run streamlit_app.py
"""

import streamlit as st

st.set_page_config(page_title="Oil Market Tracker", page_icon="🛢️", layout="wide")

from oil_tracker import ui  # noqa: E402  (after set_page_config)

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.6rem; max-width: 1500px;}
      [data-testid="stMetricValue"] {font-variant-numeric: tabular-nums;}
      h3 {margin-bottom: 0.1rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

pages = {
    "Overview": [
        st.Page("views/dashboard.py", title="Dashboard", icon="📊", default=True),
        st.Page("views/brief.py", title="Daily brief & alerts", icon="📝"),
    ],
    "Prices & structure": [
        st.Page("views/prices.py", title="Price charts", icon="📈"),
        st.Page("views/curve.py", title="Futures curve", icon="〰️"),
        st.Page("views/spreads.py", title="Spreads analysis", icon="↔️"),
    ],
    "US fundamentals": [
        st.Page("views/fundamentals.py", title="Inventories & runs", icon="🛢️"),
        st.Page("views/surprises.py", title="Inventory surprises", icon="🎯"),
        st.Page("views/refining.py", title="Refining & demand", icon="🏭"),
    ],
    "Global": [
        st.Page("views/oecd.py", title="OECD stocks", icon="🌐"),
        st.Page("views/opec.py", title="Global balance", icon="🌍"),
        st.Page("views/opec_countries.py", title="OPEC+ by country", icon="🛢"),
    ],
    "Risk & research": [
        st.Page("views/risk.py", title="Geopolitical risk", icon="⚠️"),
        st.Page("views/correlations.py", title="Correlations", icon="🔗"),
        st.Page("views/backtest.py", title="Signal backtest", icon="🧪"),
    ],
    "Reference": [
        st.Page("views/reports.py", title="Reports & data status", icon="🗓️"),
    ],
}
nav = st.navigation(pages, expanded=True)
ui.sidebar(ui.get_ctx())
nav.run()
"""
Oil Market Tracker - Main Streamlit App
"""
import sys
from pathlib import Path

# Add package to path
sys.path.insert(0, str(Path(__file__).parent))

from oil_tracker.app import run

if __name__ == "__main__":
    run()

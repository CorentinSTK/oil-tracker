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

pages = [
    st.Page("views/dashboard.py", title="Dashboard", icon="📊", default=True),
    st.Page("views/prices.py", title="Price charts", icon="📈"),
    st.Page("views/fundamentals.py", title="Fundamentals", icon="🛢️"),
    st.Page("views/spreads.py", title="Spreads analysis", icon="↔️"),
    st.Page("views/opec.py", title="OPEC+ & global balance", icon="🌍"),
    st.Page("views/brief.py", title="Daily brief & alerts", icon="📝"),
    st.Page("views/backtest.py", title="Signal backtest", icon="🧪"),
    st.Page("views/reports.py", title="Reports & data status", icon="🗓️"),
]
nav = st.navigation(pages)
ui.sidebar(ui.get_ctx())
nav.run()

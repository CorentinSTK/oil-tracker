"""Catalyst calendar, agency report links and data status."""

import pandas as pd
import streamlit as st

from oil_tracker import ui
from oil_tracker.catalysts import upcoming
from oil_tracker.data import database as db
from oil_tracker.sources import SERIES

ctx = ui.get_ctx()
ui.page_header("Reports & data status", ctx)

st.markdown("#### Catalyst calendar · next 5 weeks")
ev = upcoming(days=35)
st.dataframe(
    pd.DataFrame([{"When (ET)": e.when.strftime("%a %d %b %Y %H:%M"), "Release": e.name, "Source": e.source,
                   "Timing": "estimated" if e.estimated else "scheduled", "Note": e.note, "Link": e.url} for e in ev]),
    hide_index=True, width="stretch",
    column_config={"Link": st.column_config.LinkColumn(display_text="calendar")},
)
st.caption("EIA weekly, Baker Hughes and CFTC follow fixed weekday rules with US-holiday shifts. Monthly agency "
           "dates are estimated from their usual pattern - confirm on the publisher's calendar.")

st.markdown("#### Agency reports")
c1, c2, c3 = st.columns(3)
c1.markdown("**IEA Oil Market Report**  \n[Latest report](https://www.iea.org/topics/oil-market-report) · "
            "monthly; demand growth, OECD stocks, supply by country. Executive summary is free.")
c2.markdown("**OPEC Monthly Oil Market Report**  \n[MOMR](https://www.opec.org/opec_web/en/publications/338.htm) · "
            "monthly; *secondary sources* production table = the reference for OPEC+ quota compliance.")
c3.markdown("**EIA**  \n[Weekly Petroleum Status Report](https://www.eia.gov/petroleum/supply/weekly/) · "
            "[Short-Term Energy Outlook](https://www.eia.gov/outlooks/steo/) · "
            "[This Week in Petroleum](https://www.eia.gov/petroleum/weekly/)")

st.markdown("#### Data status")
log = db.read_fetch_log()
meta = pd.DataFrame([{"series_key": k, "Series": s.label, "Source": f"{s.source.upper()} {s.remote_id}",
                      "Freq": s.frequency, "Unit": s.unit} for k, s in SERIES.items()]
                    + [{"series_key": "snapshot", "Series": "Live snapshot", "Source": "OilPriceAPI", "Freq": "intraday",
                        "Unit": "$/bbl"}])
tbl = meta.merge(log, on="series_key", how="left")
tbl["Last fetch"] = tbl["last_success"].map(ui.age)
tbl["Status"] = tbl["last_error"].map(lambda e: f"ERROR: {e}" if isinstance(e, str) and e else "ok")
st.dataframe(tbl[["Series", "Source", "Freq", "Unit", "last_obs", "n_obs", "Last fetch", "Status"]].rename(
    columns={"last_obs": "Latest obs", "n_obs": "Rows"}), hide_index=True, width="stretch")
st.caption("STEO 'latest obs' includes EIA forecast months. Refresh cadence: daily/weekly series every 6h, "
           "monthly every 24h, snapshot every hour - or use *Force refresh* in the sidebar.")

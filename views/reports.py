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
                        "Unit": "$/bbl"}]
                    + [{"series_key": f"futures_{n}", "Series": f"{n.upper()} futures by contract",
                        "Source": "Yahoo Finance", "Freq": "D", "Unit": "$/bbl"} for n in ("wti", "brent")])
tbl = meta.merge(log, on="series_key", how="left")
tbl["Last fetch"] = tbl["last_success"].map(ui.age)
tbl["Status"] = tbl["last_error"].map(lambda e: f"ERROR: {e}" if isinstance(e, str) and e else "ok")
show = ["Series", "Source", "Freq", "Unit", "last_obs", "n_obs", "Last fetch", "Status"]
names = {"last_obs": "Latest obs", "n_obs": "Rows"}
country = tbl["series_key"].str.match(r"^(prod|cap|spare|outage)_(?!opec|nonopec)")
errors = tbl[tbl["Status"] != "ok"]
if not errors.empty:
    st.error(f"{len(errors)} series failed on their last fetch: " + ", ".join(errors["Series"].head(8)))
st.dataframe(tbl.loc[~country, show].rename(columns=names), hide_index=True, width="stretch")
with st.expander(f"STEO country series ({int(country.sum())})"):
    st.dataframe(tbl.loc[country, show].rename(columns=names), hide_index=True, width="stretch")
st.caption("STEO 'latest obs' includes EIA forecast months. Refresh cadence, checked on each visit: EIA weekly "
           "series as soon as a new Weekly Petroleum Status Report is out (fallback every 6h), daily series and futures "
           "every 6h, GPR every 12h, monthly every 24h, snapshot every hour. *Force refresh* in the sidebar refetches all.")

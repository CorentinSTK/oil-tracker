"""Auto-generated daily brief and the alert log."""

import pandas as pd
import streamlit as st

from oil_tracker import ui
from oil_tracker.analytics.brief import brief_markdown, build_brief
from oil_tracker.data import database as db

ctx = ui.get_ctx()
ui.page_header("Daily brief & alerts", ctx, "Generated from rules over the numbers on this dashboard - every line is "
               "traceable to a metric. Not investment advice.")

b = build_brief(ctx)
text = brief_markdown(b)
c1, c2 = st.columns([2, 1], gap="large")
with c1:
    st.markdown(f"#### {b['headline']}")
    st.markdown(ui.badge({"BULLISH": "bullish", "BEARISH": "bearish"}.get(b["outlook"], "neutral"),
                         f"Outlook {b['outlook']}"), unsafe_allow_html=True)
    st.markdown(b["takeaway"])
    for title, items in (("Bullish signals", b["bullish"]), ("Bearish signals", b["bearish"]),
                         ("What to watch", b["watch"]), ("Trade considerations", b["ideas"])):
        if items:
            st.markdown(f"**{title}**\n" + "\n".join(f"- {i}" for i in items))
with c2:
    st.markdown("**Copy-paste version**")
    st.code(text, language=None)
    st.download_button("Download .txt", text, file_name=f"oil_brief_{b['date']:%Y%m%d}.txt", width="stretch")

st.divider()
st.markdown("#### Alert log")
log = db.read_alerts()
if log.empty:
    st.caption("No alerts recorded yet.")
else:
    sev = st.multiselect("Severity", ["HIGH", "MEDIUM", "LOW"], default=["HIGH", "MEDIUM", "LOW"])
    log = log[log["severity"].isin(sev)]
    st.dataframe(log[["as_of", "severity", "alert_type", "message", "created_at"]].rename(
        columns={"as_of": "Data date", "severity": "Severity", "alert_type": "Rule", "message": "Message",
                 "created_at": "Recorded (UTC)"}), hide_index=True, width="stretch")
st.caption("Alerts are deduplicated per rule and data date, and kept for one year.")

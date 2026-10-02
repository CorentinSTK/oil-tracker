"""Futures curve structure: backwardation vs contango."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from oil_tracker import ui

ctx = ui.get_ctx()
ui.page_header("Futures curve", ctx, "NYMEX WTI (CL) and NYMEX Brent Last Day Financial (BZ, settles on ICE Brent) "
               "by contract, from Yahoo Finance (unofficial, delayed).")

curves = ctx["curves"]
if not any(curves.values()):
    st.info("No futures data stored yet - check Reports & data status.")
    st.stop()

cols = st.columns(2)
for col, (name, cv) in zip(cols, curves.items()):
    if not cv:
        continue
    with col:
        st.metric(f"{name.upper()} structure · {cv['date']:%d %b}", cv["structure"].title(),
                  f"M1-M6 {cv['m1_m6']:+.2f} $/bbl ({cv['m1_m6_pct']:+.1f}%)", delta_color="off", delta_arrow="off", border=True)
        st.caption(f"M1-M2 {cv['m1_m2']:+.2f} · M1-M3 {cv['m1_m3']:+.2f} · M1-M12 {ui.fmt(cv['m1_m12'], sign=True)} · "
                   f"{cv['dec_label']} {cv['dec_spread'].iloc[-1]:+.2f}" if len(cv["dec_spread"]) else "")

st.markdown("#### Curve today")
fig = go.Figure()
for name, cv in curves.items():
    if not cv:
        continue
    c = cv["contracts"]
    fig.add_scatter(x=c["delivery"], y=c["close"], mode="lines+markers", name=name.upper(),
                    line=dict(color=ui.COLORS[name], width=2), marker=dict(size=8),
                    customdata=c["contract"], hovertemplate=f"{name.upper()} %{{customdata}}: %{{y:.2f}}<extra></extra>")
fig.update_layout(height=380, yaxis_title="$/bbl", xaxis_title="Delivery month",
                  title=dict(text="Settlement by delivery month", font_size=13))
st.plotly_chart(fig, width="stretch")

st.markdown("#### Structure history")
a, b = st.columns(2, gap="large")
with a:
    fig = go.Figure()
    for name, cv in curves.items():
        if cv and len(cv["dec_spread"]):
            s = cv["dec_spread"]
            fig.add_scatter(x=s.index, y=s, name=f"{name.upper()} {cv['dec_label']}",
                            line=dict(color=ui.COLORS[name], width=2), hovertemplate="%{y:+.2f}<extra></extra>")
    fig.add_hline(y=0, line=dict(color=ui.INK["muted"], width=1))
    fig.update_layout(height=340, yaxis_title="$/bbl",
                      title=dict(text="December-December spread (> 0 = backwardation)", font_size=13))
    st.plotly_chart(fig, width="stretch")
    st.caption("A fixed pair of contracts, so the history is continuous for as long as both have traded (~2 years).")
with b:
    fig = go.Figure()
    for name, cv in curves.items():
        if cv and not cv["history"].empty:
            h = cv["history"]
            fig.add_scatter(x=h.index, y=h["m1_m6"], name=f"{name.upper()} M1-M6", mode="lines+markers",
                            line=dict(color=ui.COLORS[name], width=2), marker=dict(size=8),
                            hovertemplate="%{y:+.2f}<extra></extra>")
    fig.add_hline(y=0, line=dict(color=ui.INK["muted"], width=1))
    fig.update_layout(height=340, yaxis_title="$/bbl", title=dict(text="Generic M1-M6 spread", font_size=13))
    st.plotly_chart(fig, width="stretch")
    st.caption("Generic months need the expired front contract, which the source drops; this history builds up "
               "as the tracker stores daily settlements.")

st.markdown("#### Front-month futures vs physical spot")
px = ctx["frames"]["prices"]
rows = []
for name, cv in curves.items():
    if cv and name in px:
        spot = px[name].dropna()
        rows.append({"Benchmark": name.upper(), "Front future (M1)": cv["curve"]["M1"], "Futures date": cv["date"].date(),
                     "EIA spot": spot.iloc[-1], "Spot date": spot.index[-1].date(),
                     "Spot - M1": spot.iloc[-1] - cv["curve"]["M1"]})
if rows:
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                 column_config={c: st.column_config.NumberColumn(format="%.2f")
                                for c in ["Front future (M1)", "EIA spot", "Spot - M1"]})
    st.caption("Dated Brent is a physical cargo assessment loading 10 days to a month ahead, so in a tight market it "
               "trades well above the futures front month. Dates can differ by a few days.")

with st.expander("How to read the curve", expanded=False):
    st.markdown(
        """
- **Backwardation** (front > deferred): prompt barrels are scarce, so holding stock costs money and inventories
  get drawn. It typically comes with falling stocks and high spare-capacity usage.
- **Contango** (front < deferred): oversupply; the market pays for storage. Deep contango (beyond the cost of
  storage) fills tanks and floating storage.
- The curve is **not a price forecast**: a backwardated curve does not mean the market "expects" prices to fall,
  it prices the scarcity of prompt barrels relative to later ones.
- Thresholds used here: M1-M6 above +1% of the front price = backwardation, above +5% = steep (and the reverse for
  contango).
"""
    )

"""OPEC+ monitor and the global supply-demand balance (EIA STEO)."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from oil_tracker import ui

ctx = ui.get_ctx()
ui.page_header("Global balance", ctx, "EIA Short-Term Energy Outlook (monthly). Shaded area = EIA forecast. "
               "IEA and OPEC monthly reports are not machine-readable for free - see Reports for links.")

gb, g = ctx["global_balance"], ctx["global"]
if gb.empty:
    st.info("No STEO data stored yet.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Implied stock change · {g['date']:%b %Y}", f"{g['implied_stock_change']:+.2f} mb/d",
          help="World liquids production minus consumption. Negative = stocks drawing (deficit).", border=True)
c2.metric("Next 3 months (EIA fcst)", f"{g['next_3m_avg']:+.2f} mb/d", border=True)
c3.metric("OPEC spare capacity", f"{g['opec_spare']:.2f} mb/d",
          help="EIA estimate of crude capacity that can be brought online within 30 days and sustained 90 days.",
          border=True)
c4.metric("OECD days of forward cover", f"{g['days_cover']:.1f} days", f"{g['days_cover'] - g['days_cover_5y']:+.1f} vs 5Y avg",
          delta_color="inverse", border=True)
st.caption(f"Spare capacity as of {g['opec_spare_date']:%b %Y}. Days of cover = OECD commercial stocks / next month's "
           "OECD demand.")

window = st.segmented_control("Window", ["3Y", "5Y", "All"], default="5Y") or "5Y"
start = gb.index.min() if window == "All" else pd.Timestamp.today() - pd.DateOffset(years=int(window[:-1]))
v = gb.loc[gb.index >= start]
fc_start = v.index[v["forecast"]].min() if v["forecast"].any() else None


def shade(fig: go.Figure) -> go.Figure:
    if fc_start is not None:
        fig.add_vrect(x0=fc_start, x1=v.index.max() + pd.Timedelta(days=20), fillcolor=ui.BAND, line_width=0,
                      annotation_text="EIA forecast", annotation_position="top left", annotation_font_size=10,
                      annotation_font_color=ui.INK["secondary"])
    return fig


fig = go.Figure(go.Bar(
    x=v.index, y=v["implied_stock_change"],
    marker_color=[ui.STATUS["critical"] if x > 0 else ui.STATUS["good"] for x in v["implied_stock_change"]],
    hovertemplate="%{x|%b %Y}: %{y:+.2f} mb/d<extra></extra>",
))
fig.update_layout(height=340, hovermode="closest", yaxis_title="mb/d",
                  title=dict(text="World implied stock change (supply - demand) · green = deficit/draw, red = surplus/build",
                             font_size=13))
st.plotly_chart(shade(fig), width="stretch")

a, b = st.columns(2, gap="large")
with a:
    fig = go.Figure()
    fig.add_scatter(x=v.index, y=v["opec_capacity"], name="OPEC capacity", line=dict(color=ui.INK["muted"], width=2, dash="dash"))
    fig.add_scatter(x=v.index, y=v["opec_prod"], name="OPEC production", line=dict(color=ui.COLORS["wti"], width=2))
    fig.update_layout(height=340, yaxis_title="mb/d", title=dict(text="OPEC crude: production vs capacity", font_size=13))
    st.plotly_chart(shade(fig), width="stretch")
with b:
    fig = go.Figure(go.Scatter(x=v.index, y=v["opec_spare"], line=dict(color=ui.COLORS["brent"], width=2),
                               fill="tozeroy", fillcolor="rgba(217,89,38,0.12)",
                               hovertemplate="%{x|%b %Y}: %{y:.2f} mb/d<extra></extra>"))
    fig.update_layout(height=340, yaxis_title="mb/d", showlegend=False,
                      title=dict(text="OPEC spare capacity (the market's shock absorber)", font_size=13))
    st.plotly_chart(shade(fig), width="stretch")

a, b = st.columns(2, gap="large")
with a:
    fig = go.Figure()
    fig.add_scatter(x=v.index, y=v["world_supply"], name="Supply", line=dict(color=ui.COLORS["wti"], width=2))
    fig.add_scatter(x=v.index, y=v["world_demand"], name="Demand", line=dict(color=ui.COLORS["brent"], width=2))
    fig.update_layout(height=320, yaxis_title="mb/d", title=dict(text="World liquids supply vs demand", font_size=13))
    st.plotly_chart(shade(fig), width="stretch")
with b:
    dc = v["oecd_days_cover"].dropna()
    fig = go.Figure(go.Scatter(x=dc.index, y=dc, line=dict(color=ui.COLORS["dubai"], width=2),
                               hovertemplate="%{x|%b %Y}: %{y:.1f} days<extra></extra>"))
    fig.update_layout(height=320, yaxis_title="days", showlegend=False,
                      title=dict(text="OECD commercial stocks · days of forward demand cover", font_size=13))
    st.plotly_chart(shade(fig), width="stretch")

if "opecplus_prod" in v:
    st.caption(f"OPEC+ crude production (EIA): {v.loc[~v['forecast'], 'opecplus_prod'].dropna().iloc[-1]:.2f} mb/d "
               "latest estimate. Country detail, quotas and outages are on the *OPEC+ by country* page.")

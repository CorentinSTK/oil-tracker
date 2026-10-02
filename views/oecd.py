"""OECD commercial stocks and days of forward demand cover."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from oil_tracker import ui

ctx = ui.get_ctx()
ui.page_header("OECD stocks", ctx, "EIA STEO OECD commercial crude and liquids inventories (monthly, end of period). "
               "5Y average = same calendar month in the five prior years. Shaded = EIA forecast.")

oe, o = ctx["oecd_summary"], ctx["oecd"]
if not oe:
    st.info("No STEO data stored yet.")
    st.stop()

c = st.columns(4)
c[0].metric(f"OECD commercial stocks · {oe['date']:%b %Y}", f"{oe['stocks']:,.0f} Mbbl", f"{oe['mom']:+,.0f} m/m",
            delta_color="off", border=True)
c[1].metric("vs 5Y same-month avg", f"{oe['vs_5y']:+,.0f} Mbbl", f"{oe['vs_5y_pct']:+.1f}%", delta_color="off", border=True)
c[2].metric("Days of forward demand cover", f"{oe['days_cover']:.1f} d", f"{oe['days_vs_5y']:+.1f} d vs 5Y",
            delta_color="off", border=True)
with c[3]:
    st.metric("Read", oe["signal"], border=True)
    st.caption("TIGHT / LOOSE when stocks are more than 2% below / above the 5Y norm. Low stocks = bullish.")

window = st.segmented_control("Window", ["3Y", "5Y", "10Y", "All"], default="5Y") or "5Y"
start = o.index.min() if window == "All" else pd.Timestamp.today() - pd.DateOffset(years=int(window[:-1]))
v = o.loc[o.index >= start]
fc = v.index[v["forecast"]].min() if v["forecast"].any() else None
iea = ctx["iea_oecd"]


def shade(fig):
    if fc is not None:
        fig.add_vrect(x0=fc, x1=v.index.max() + pd.Timedelta(days=20), fillcolor=ui.BAND, line_width=0,
                      annotation_text="EIA forecast", annotation_position="top left", annotation_font_size=10,
                      annotation_font_color=ui.INK["secondary"])
    return fig


a, b = st.columns(2, gap="large")
with a:
    fig = go.Figure()
    fig.add_scatter(x=v.index, y=v["stocks_5y"], name="5Y same-month avg",
                    line=dict(color=ui.INK["muted"], width=2, dash="dash"), hovertemplate="5Y avg %{y:,.0f}<extra></extra>")
    fig.add_scatter(x=v.index, y=v["stocks"], name="OECD stocks (EIA)", line=dict(color=ui.COLORS["wti"], width=2),
                    hovertemplate="%{y:,.0f} Mbbl<extra></extra>")
    if not iea.empty:
        fig.add_scatter(x=iea["month"], y=iea["stocks_mb"], name="IEA OMR (manual)", mode="markers",
                        marker=dict(size=9, color=ui.COLORS["brent"]), hovertemplate="IEA %{y:,.0f}<extra></extra>")
    fig.update_layout(height=360, yaxis_title="Mbbl", title=dict(text="OECD commercial stocks", font_size=13))
    st.plotly_chart(shade(fig), width="stretch")
with b:
    fig = go.Figure()
    fig.add_scatter(x=v.index, y=v["days_cover_5y"], name="5Y same-month avg",
                    line=dict(color=ui.INK["muted"], width=2, dash="dash"), hovertemplate="5Y avg %{y:.1f}<extra></extra>")
    fig.add_scatter(x=v.index, y=v["days_cover"], name="Days of cover (EIA)", line=dict(color=ui.COLORS["dubai"], width=2),
                    hovertemplate="%{y:.1f} days<extra></extra>")
    if not iea.empty and iea["days_cover"].notna().any():
        fig.add_scatter(x=iea["month"], y=iea["days_cover"], name="IEA OMR (manual)", mode="markers",
                        marker=dict(size=9, color=ui.COLORS["brent"]), hovertemplate="IEA %{y:.1f}<extra></extra>")
    fig.update_layout(height=360, yaxis_title="days", title=dict(text="Days of forward demand cover", font_size=13))
    st.plotly_chart(shade(fig), width="stretch")

fig = go.Figure(go.Bar(
    x=v.index, y=v["stocks_vs_5y"],
    marker_color=[ui.STATUS["good"] if x < 0 else ui.STATUS["critical"] for x in v["stocks_vs_5y"]],
    hovertemplate="%{x|%b %Y}: %{y:+,.0f} Mbbl<extra></extra>",
))
fig.update_layout(height=280, hovermode="closest", yaxis_title="Mbbl",
                  title=dict(text="OECD stocks vs 5Y same-month average (green = deficit, red = surplus)", font_size=13))
st.plotly_chart(shade(fig), width="stretch")

if {"us_stocks_steo", "other_oecd_stocks"} <= set(v.columns):
    fig = go.Figure()
    fig.add_scatter(x=v.index, y=v["us_stocks_steo"], name="United States", line=dict(color=ui.COLORS["wti"], width=2))
    fig.add_scatter(x=v.index, y=v["other_oecd_stocks"], name="Other OECD", line=dict(color=ui.COLORS["brent"], width=2))
    fig.update_layout(height=300, yaxis_title="Mbbl", title=dict(text="Where the stocks sit: US vs rest of OECD", font_size=13))
    st.plotly_chart(shade(fig), width="stretch")

st.caption("Days of cover = end-of-month OECD commercial stocks / next month's OECD consumption. The IEA's own "
           "figures (OMR) use a slightly different stock definition, so expect a level gap of tens of Mbbl.")
ui.manual_editor("iea_oecd", "Add IEA Oil Market Report figures (optional overlay)")

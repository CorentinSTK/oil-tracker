"""US weekly fundamentals: seasonal charts, weekly changes, refinery runs, production."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from oil_tracker import ui
from oil_tracker.analytics.seasonal import seasonal_curve
from oil_tracker.sources import SERIES

ctx = ui.get_ctx()
ui.page_header("US fundamentals", ctx, "EIA Weekly Petroleum Status Report. Seasonal band = min/max of the prior 5 years "
               "for the same week; dashed line = their average.")

w = ctx["frames"]["weekly"].copy()
w["total"] = w[["us_crude", "us_gasoline", "us_distillates"]].sum(axis=1, min_count=3)

OPTIONS = {
    "us_crude": "Commercial crude (ex-SPR)",
    "cushing": "Cushing crude",
    "us_gasoline": "Total gasoline",
    "us_distillates": "Distillates",
    "total": "Crude + gasoline + distillates",
    "refinery_util": "Refinery utilization (%)",
    "us_production": "Crude production (kb/d)",
    "spr": "Strategic Petroleum Reserve",
}
key = st.selectbox("Series", list(OPTIONS), format_func=OPTIONS.get)
unit = SERIES[key].unit if key in SERIES else "Mbbl"
s = w[key].dropna()

curve = seasonal_curve(s)
yr = int(s.index.max().year)
fig = go.Figure()
fig.add_scatter(x=curve.index, y=curve["max"], line=dict(width=0), showlegend=False, hoverinfo="skip")
fig.add_scatter(x=curve.index, y=curve["min"], fill="tonexty", fillcolor=ui.BAND, line=dict(width=0),
                name=f"5Y range ({yr-5}–{yr-1})", hovertemplate="5Y range low %{y:.1f}<extra></extra>")
fig.add_scatter(x=curve.index, y=curve["mean"], name="5Y average", line=dict(color=ui.INK["muted"], width=2, dash="dash"),
                hovertemplate="5Y avg %{y:.1f}<extra></extra>")
fig.add_scatter(x=curve.index, y=curve["previous"], name=str(yr - 1), line=dict(color=ui.COLORS["brent"], width=2),
                hovertemplate=f"{yr-1} %{{y:.1f}}<extra></extra>")
fig.add_scatter(x=curve.index, y=curve["current"], name=str(yr), line=dict(color=ui.COLORS["wti"], width=2),
                hovertemplate=f"{yr} %{{y:.1f}}<extra></extra>")
fig.update_layout(height=440, xaxis_title="Week of year", yaxis_title=unit,
                  title=dict(text=f"{OPTIONS[key]} · seasonal view", font_size=14))
st.plotly_chart(fig, width="stretch")

c1, c2 = st.columns(2, gap="large")
with c1:
    chg = s.diff().dropna().iloc[-52:]
    fig = go.Figure(go.Bar(
        x=chg.index, y=chg,
        marker_color=[ui.STATUS["good"] if v < 0 else ui.STATUS["critical"] for v in chg]
        if key not in ("refinery_util", "us_production") else ui.COLORS["wti"],
        hovertemplate="%{x|%d %b %Y}: %{y:+.2f}<extra></extra>",
    ))
    title = "Weekly change · last 52 weeks"
    if key not in ("refinery_util", "us_production"):
        title += " (green = draw, red = build)"
    fig.update_layout(height=300, title=dict(text=title, font_size=13), hovermode="closest", yaxis_title=unit)
    st.plotly_chart(fig, width="stretch")
with c2:
    hist = s.loc[s.index > s.index.max() - pd.Timedelta(days=5 * 365)]
    fig = go.Figure(go.Scatter(x=hist.index, y=hist, line=dict(color=ui.COLORS["wti"], width=2),
                               hovertemplate="%{x|%d %b %Y}: %{y:.1f}<extra></extra>"))
    fig.update_layout(height=300, title=dict(text="Level · last 5 years", font_size=13), showlegend=False, yaxis_title=unit)
    st.plotly_chart(fig, width="stretch")

st.markdown("#### Latest week")
rows = []
for k, d in ctx["inventory"].items():
    if d:
        rows.append({"Series": OPTIONS.get(k, k), "Week ending": d["date"].strftime("%d %b %Y"), "Level": d["level"],
                     "w/w": d["wow"], "Seasonal w/w (5Y)": d["seasonal_chg"], "Surprise vs seasonal": d["surprise"],
                     "vs 5Y avg": d["vs_5y"], "vs 5Y %": d["vs_5y_pct"], "y/y": d["yoy"],
                     "Signal": d["signal"] + (" (large)" if d["magnitude"] == "LARGE" else "")})
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
             column_config={c: st.column_config.NumberColumn(format="%+.2f") for c in
                            ["w/w", "Seasonal w/w (5Y)", "Surprise vs seasonal", "vs 5Y avg", "y/y"]}
             | {"Level": st.column_config.NumberColumn(format="%.1f"),
                "vs 5Y %": st.column_config.NumberColumn(format="%+.1f")})
ref, prod = ctx["refinery"], ctx["production"]
a, b = st.columns(2)
if ref:
    a.metric("Refinery utilization", f"{ref['level']:.1f}%", f"{ref['wow']:+.1f} pp w/w", border=True)
    a.caption(f"{ref['vs_5y']:+.1f} pp vs 5Y same-week average ({ref['avg_5y']:.1f}%) → **{ref['signal']}**")
if prod:
    b.metric("US crude production", f"{prod['level']:,.0f} kb/d", f"{prod['wow']:+,.0f} kb/d w/w", border=True)
    b.caption(f"4-week avg change {prod['chg_4w_avg']:+,.0f} kb/d · y/y {prod['yoy']:+,.0f} kb/d. "
              "Weekly production is a model estimate, rounded by EIA.")
st.caption("'Seasonal w/w' is the 5-year average change for the same week. No free analyst consensus exists, "
           "so the seasonal norm stands in as the 'expected' change.")

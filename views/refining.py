"""Refinery margins, refined product prices and US implied demand."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from oil_tracker import ui
from oil_tracker.analytics.demand import CRACKS, DEMAND
from oil_tracker.analytics.seasonal import seasonal_curve

ctx = ui.get_ctx()
ui.page_header("Refining & demand", ctx, "Product cracks (EIA spot, $/gal × 42) and EIA 'product supplied' - "
               "the downstream pull on crude.")

ds = ctx["demand_score"]
cs = ctx["crack_summary"]
c = st.columns(4)
if ds:
    c[0].metric(
        "Demand strength (0-100)",
        f"{ds['score']:.0f}",
        ds["label"],
        delta_color="off",
        delta_arrow="off",
        border=True,
        help="Composite of three components (each normalized to seasonal norm): implied demand (product supplied), "
             "USGC 3-2-1 crack, and refinery utilization. Score 50 = seasonal normal. Values >50 indicate stronger-than-seasonal demand "
             "and profitability; <50 indicate seasonal weakness."
    )
    c[0].caption(" · ".join(f"{k} {v:+.2f}" for k, v in ds["components"].items()))
for col, k in zip(c[1:], ("usgc_321", "nyh_321", "ulsd_crack")):
    d = cs.get(k)
    if d:
        col.metric(d["label"], f"{d['current']:.2f} $/bbl", f"{d['vs_seasonal']:+.1f} vs seasonal", border=True)
st.caption("Demand strength = 50 + 50 × mean of tanh(z/2) for US implied demand, the USGC 3-2-1 crack and refinery "
           "runs, each against its own seasonal norm. 50 = normal for the time of year.")

st.warning(
    "**No European or Asian margins.** Rotterdam and Singapore 3-2-1 crack spreads require daily product price quotes "
    "(Platts MOPS for Singapore, Argus for Rotterdam) that are only available via paid subscriptions. Rather than estimate, "
    "this tracker shows the NYH-vs-Brent crack as an Atlantic-basin proxy. See **Data Sources & Freshness** for details.",
    icon="ℹ️"
)

# ---------------------------------------------------------------- cracks
st.markdown("#### Crack spreads")
cr = ctx["cracks"]
pick = st.multiselect("Cracks", list(CRACKS), default=["usgc_321", "nyh_321"], format_func=CRACKS.get)
horizon = st.segmented_control("Window", ["1Y", "3Y", "5Y", "10Y"], default="3Y") or "3Y"
view = cr.loc[cr.index > cr.index.max() - pd.DateOffset(years=int(horizon[:-1]))]
palette = [ui.COLORS["wti"], ui.COLORS["brent"], ui.COLORS["dubai"], "#c98500", "#d55181"]
fig = go.Figure()
for i, k in enumerate(pick):
    s = view[k].dropna()
    fig.add_scatter(x=s.index, y=s, name=CRACKS[k], line=dict(color=palette[list(CRACKS).index(k)], width=2),
                    hovertemplate=f"{CRACKS[k]} %{{y:.2f}}<extra></extra>")
fig.update_layout(height=380, yaxis_title="$/bbl", title=dict(text="Daily crack spreads", font_size=13))
st.plotly_chart(fig, width="stretch")

rows = [{"Crack": d["label"], "Latest": d["current"], "As of": d["date"].date(), "4-week chg": d["chg_4w"],
         "Week avg": d["week_avg"], "Seasonal norm (5Y)": d["seasonal_avg"], "vs norm": d["vs_seasonal"],
         "z": d["z"], "Signal": d["signal"]} for d in cs.values()]
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
             column_config={c: st.column_config.NumberColumn(format="%.2f")
                            for c in ["Latest", "Week avg", "Seasonal norm (5Y)"]}
             | {c: st.column_config.NumberColumn(format="%+.2f") for c in ["4-week chg", "vs norm"]}
             | {"z": st.column_config.NumberColumn(format="%+.1f")})
st.caption("3-2-1 = (2 × gasoline + 1 × ULSD) / 3 − crude: the margin of a typical US refinery. Wide margins pull "
           "crude into refineries (bullish crude) until runs max out; collapsing margins lead to run cuts.")

# ---------------------------------------------------------------- product prices
st.markdown("#### Refined product prices")
prod = ctx["frames"]["products"]
pv = prod.loc[prod.index > prod.index.max() - pd.DateOffset(years=int(horizon[:-1]))]
labels = {"gas_nyh": "NYH gasoline", "gas_usgc": "USGC gasoline", "ulsd_nyh": "NYH ULSD", "ulsd_usgc": "USGC ULSD",
          "jet_usgc": "USGC jet"}
fig = go.Figure()
for i, (k, lbl) in enumerate(labels.items()):
    s = pv[k].dropna()
    fig.add_scatter(x=s.index, y=s, name=lbl, line=dict(color=palette[i], width=2),
                    hovertemplate=f"{lbl} %{{y:.2f}}<extra></extra>")
fig.update_layout(height=360, yaxis_title="$/bbl", title=dict(text="Product spot prices ($/bbl)", font_size=13))
st.plotly_chart(fig, width="stretch")
retail = ctx["frames"]["risk"]["gas_retail"].dropna()
if len(retail):
    st.caption(f"US retail gasoline: **${retail.iloc[-1]:.3f}/gal** (week of {retail.index[-1]:%d %b}), "
               f"{retail.iloc[-1] - retail.asof(retail.index[-1] - pd.Timedelta(days=364)):+.3f} y/y.")

# ---------------------------------------------------------------- implied demand
st.markdown("#### US implied demand (product supplied)")
dm = ctx["demand"]
c = st.columns(len(dm))
for col, (k, d) in zip(c, dm.items()):
    col.metric(f"{d['label']} · 4wk avg", f"{d['avg_4w']:,.0f} kb/d",
               f"{d['vs_seasonal_pct']:+.1f}% vs seasonal", border=True)
key = st.selectbox("Seasonal view", list(DEMAND), format_func=DEMAND.get)
s = ctx["frames"]["weekly"][key].dropna().rolling(4).mean().dropna()
curve = seasonal_curve(s)
yr = int(s.index.max().year)
fig = go.Figure()
fig.add_scatter(x=curve.index, y=curve["max"], line=dict(width=0), showlegend=False, hoverinfo="skip")
fig.add_scatter(x=curve.index, y=curve["min"], fill="tonexty", fillcolor=ui.BAND, line=dict(width=0),
                name=f"5Y range ({yr-5}–{yr-1})", hoverinfo="skip")
fig.add_scatter(x=curve.index, y=curve["mean"], name="5Y average", line=dict(color=ui.INK["muted"], width=2, dash="dash"),
                hovertemplate="5Y avg %{y:,.0f}<extra></extra>")
fig.add_scatter(x=curve.index, y=curve["previous"], name=str(yr - 1), line=dict(color=ui.COLORS["brent"], width=2),
                hovertemplate=f"{yr-1} %{{y:,.0f}}<extra></extra>")
fig.add_scatter(x=curve.index, y=curve["current"], name=str(yr), line=dict(color=ui.COLORS["wti"], width=2),
                hovertemplate=f"{yr} %{{y:,.0f}}<extra></extra>")
fig.update_layout(height=380, xaxis_title="Week of year", yaxis_title="kb/d",
                  title=dict(text=f"{DEMAND[key]} supplied · 4-week average, seasonal view", font_size=13))
st.plotly_chart(fig, width="stretch")
st.caption("Product supplied measures disappearance from primary inventories (refinery output + imports − exports "
           "− stock change); it includes exports' mis-measurement and is revised in the monthly data.")

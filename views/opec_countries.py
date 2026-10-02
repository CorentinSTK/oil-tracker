"""OPEC+ production by country, quotas, spare capacity and supply disruptions."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from oil_tracker import ui
from oil_tracker.analytics.fundamentals import is_forecast
from oil_tracker.analytics.opec import country_name, country_production, disruptions

ctx = ui.get_ctx()
ui.page_header("OPEC+ by country", ctx, "EIA STEO country estimates (monthly) - the free, machine-readable "
               "alternative to the OPEC MOMR secondary-sources table.")

month, tbl = ctx["opec_month"], ctx["opec_table"]
if tbl.empty:
    st.info("No STEO country data stored yet.")
    st.stop()

st.markdown(f"#### Production · {month:%B %Y}")
show = tbl.rename(columns={"country": "Country", "group": "Group", "production": "Production", "mom": "m/m",
                           "yoy": "y/y", "capacity": "Capacity", "spare": "Spare", "utilisation_pct": "Capacity used %",
                           "quota": "Quota", "vs_quota": "vs quota", "pct_of_quota": "% of quota"})
cols = [c for c in ["Country", "Group", "Production", "m/m", "y/y", "Capacity", "Spare", "Capacity used %",
                    "Quota", "vs quota", "% of quota"] if c in show]
fmt = {c: "{:.2f}" for c in ["Production", "Capacity", "Spare", "Quota"]} | \
      {c: "{:+.2f}" for c in ["m/m", "y/y", "vs quota"]} | {c: "{:.0f}" for c in ["Capacity used %", "% of quota"]}
st.dataframe(show[cols].style.format({k: v for k, v in fmt.items() if k in cols}, na_rep="—"),
             hide_index=True, width="stretch")
st.caption("mb/d. Capacity and spare capacity are published for OPEC members only. UAE appears as total liquids "
           "(crude + condensate + NGLs): the STEO has no crude-only UAE series and its OPEC total excludes UAE.")
if ctx["quotas"].empty:
    st.info("No OPEC+ quotas entered, so compliance is not shown. Add the required production levels from the latest "
            "OPEC+ decision below - the tracker does not guess them.")
ui.manual_editor("opec_quotas", "Enter OPEC+ required production by country")

opec_only = tbl[tbl["group"] == "OPEC"].dropna(subset=["capacity"])
if not opec_only.empty:
    fig = go.Figure()
    fig.add_bar(x=opec_only["country"], y=opec_only["production"], name="Production",
                marker_color=ui.COLORS["wti"], hovertemplate="%{x}: %{y:.2f} mb/d<extra></extra>")
    fig.add_bar(x=opec_only["country"], y=opec_only["spare"], name="Spare capacity",
                marker_color=ui.COLORS["brent"], hovertemplate="%{x} spare: %{y:.2f} mb/d<extra></extra>")
    if "quota" in opec_only and opec_only["quota"].notna().any():
        fig.add_scatter(x=opec_only["country"], y=opec_only["quota"], name="Quota", mode="markers",
                        marker=dict(symbol="line-ew-open", size=26, line=dict(width=3, color=ui.INK["primary"])))
    fig.update_layout(barmode="stack", bargap=0.35, height=360, hovermode="closest", yaxis_title="mb/d",
                      title=dict(text="OPEC members: production + spare = capacity", font_size=13))
    st.plotly_chart(fig, width="stretch")

st.markdown("#### Production history")
prod = country_production(ctx["frames"]["steo"])
default = [c for c in ("SA", "IZ", "IR", "RS") if c in prod]
pick = st.multiselect("Countries", list(prod.columns), default=default, format_func=country_name, max_selections=4)
years = st.segmented_control("Window", ["3Y", "5Y", "10Y"], default="5Y") or "5Y"
v = prod.loc[prod.index >= pd.Timestamp.today() - pd.DateOffset(years=int(years[:-1]))]
fc = v.index[is_forecast(v.index)].min() if is_forecast(v.index).any() else None
palette = [ui.COLORS["wti"], ui.COLORS["brent"], ui.COLORS["dubai"], "#c98500"]
fig = go.Figure()
for i, c in enumerate(pick):
    fig.add_scatter(x=v.index, y=v[c], name=country_name(c), line=dict(color=palette[i], width=2),
                    hovertemplate=f"{country_name(c)} %{{y:.2f}}<extra></extra>")
if fc is not None:
    fig.add_vrect(x0=fc, x1=v.index.max(), fillcolor=ui.BAND, line_width=0, annotation_text="EIA forecast",
                  annotation_position="top left", annotation_font_size=10, annotation_font_color=ui.INK["secondary"])
fig.update_layout(height=360, yaxis_title="mb/d", title=dict(text="Crude production by country", font_size=13))
st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------- disruptions
st.markdown("#### Supply disruption tracker")
dis = ctx["disruptions"]
if dis:
    c = st.columns(3)
    c[0].metric(f"Unplanned outages · {dis['month']:%b %Y}", f"{dis['total']:.2f} mb/d",
                f"{dis['total'] - dis['total_3m_ago']:+.2f} vs 3 months ago", delta_color="inverse", border=True)
    c[1].metric("of which OPEC", f"{dis['opec']:.2f} mb/d", border=True)
    c[2].metric("5-year average", f"{dis['total_5y_avg']:.2f} mb/d", border=True)
    d = disruptions(ctx["frames"]["steo"])
    d = d[~is_forecast(d.index)]
    d = d.loc[d.index >= pd.Timestamp.today() - pd.DateOffset(years=int(years[:-1]))]
    top = d.iloc[-1].sort_values(ascending=False).index[:6]
    pal6 = palette + ["#d55181", "#008300"]
    fig = go.Figure()
    for i, cc in enumerate(top):
        fig.add_bar(x=d.index, y=d[cc], name=country_name(cc), marker_color=pal6[i],
                    hovertemplate=f"{country_name(cc)} %{{y:.2f}}<extra></extra>")
    rest = d.drop(columns=top).sum(axis=1)
    fig.add_bar(x=d.index, y=rest, name="Other", marker_color=ui.INK["muted"], hovertemplate="Other %{y:.2f}<extra></extra>")
    fig.update_layout(barmode="stack", bargap=0.15, height=380, yaxis_title="mb/d",
                      title=dict(text="Unplanned production outages by country (EIA estimate)", font_size=13))
    st.plotly_chart(fig, width="stretch")
    st.dataframe(dis["by_country"].rename(columns={"country": "Country", "outage": "Outage (mb/d)",
                                                    "chg_3m": "Change vs 3 months ago"}),
                 hide_index=True, width="stretch",
                 column_config={"Outage (mb/d)": st.column_config.NumberColumn(format="%.2f"),
                                "Change vs 3 months ago": st.column_config.NumberColumn(format="%+.2f")})
    st.caption("EIA's estimate of production lost to unplanned events (conflict, sanctions-related shut-ins, "
               "infrastructure damage, strikes) - not OPEC+ policy cuts.")

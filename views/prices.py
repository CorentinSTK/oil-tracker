"""Multi-timeframe price charts, momentum table and technical levels."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from oil_tracker import ui
from oil_tracker.data import database as db

ctx = ui.get_ctx()
ui.page_header("Price charts", ctx, "WTI Cushing and Dated Brent daily spot (EIA); Dubai monthly average (IMF via FRED).")

px = ctx["frames"]["prices"]
horizon = st.segmented_control("Window", ["1M", "3M", "6M", "1Y", "2Y", "5Y", "Max"], default="1Y")
days = {"1M": 31, "3M": 92, "6M": 183, "1Y": 365, "2Y": 730, "5Y": 1826}.get(horizon or "1Y")
view = px if days is None else px.loc[px.index > px.index.max() - pd.Timedelta(days=days)]
show_avg = st.toggle("Show 30-day moving averages", value=False)

fig = go.Figure()
for k, name in (("wti", "WTI"), ("brent", "Brent")):
    s = view[k].dropna()
    fig.add_scatter(x=s.index, y=s, name=name, line=dict(color=ui.COLORS[k], width=2),
                    hovertemplate=f"{name} %{{y:.2f}}<extra></extra>")
    if show_avg:
        ma = px[k].rolling(21, min_periods=15).mean().reindex(s.index)
        fig.add_scatter(x=ma.index, y=ma, name=f"{name} 30D avg", line=dict(color=ui.COLORS[k], width=1, dash="dot"),
                        hovertemplate=f"{name} 30D %{{y:.2f}}<extra></extra>")
dub = ctx["frames"]["dubai_m"]
dub = dub.loc[dub.index >= view.index.min() - pd.Timedelta(days=31)]
if not dub.empty:
    fig.add_scatter(x=dub.index + pd.Timedelta(days=14), y=dub, name="Dubai (monthly avg)", mode="lines+markers",
                    line=dict(color=ui.COLORS["dubai"], width=2, dash="dot"), marker=dict(size=8),
                    hovertemplate="Dubai %{y:.2f}<extra></extra>")
lv = ctx["levels"]
for k in ("wti", "brent"):
    if k in lv and horizon in ("1M", "3M", "6M", "1Y"):
        for kind in ("support", "resistance"):
            fig.add_hline(y=lv[k][kind], line=dict(color=ui.COLORS[k], width=1, dash="dash"), opacity=0.6,
                          annotation_text=f"{k.upper()} {kind} {lv[k][kind]:.2f}", annotation_font_size=10,
                          annotation_font_color=ui.INK["secondary"], annotation_position="right")
fig.update_layout(height=520, yaxis_title="$/bbl")
st.plotly_chart(fig, width="stretch")

st.markdown("#### Momentum & context")
rows = []
for k, label in (("wti", "WTI"), ("brent", "Brent"), ("dubai", "Dubai (monthly)")):
    m = ctx["momentum"].get(k)
    if not m:
        continue
    rows.append({
        "Benchmark": label, "As of": m["date"].strftime("%d %b %Y"), "Last": m["last"],
        "Chg (last obs) %": m["chg_1d_pct"], "vs 30D avg %": m["vs_30d_avg_pct"] if k != "dubai" else None,
        "1M %": m["chg_30d_pct"] if k != "dubai" else None, "1Y avg": m["avg_1y"], "5Y avg": m["avg_5y"],
        "52w high": m["high_52w"], "52w low": m["low_52w"], "vs 52w high %": m["vs_52w_high_pct"],
        "Vol 30D %": m["vol_30d"] if k != "dubai" else None,
        "Support": lv.get(k, {}).get("support"), "Resistance": lv.get(k, {}).get("resistance"),
    })
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
             column_config={c: st.column_config.NumberColumn(format="%.2f") for c in
                            ["Last", "1Y avg", "5Y avg", "52w high", "52w low", "Support", "Resistance"]}
             | {c: st.column_config.NumberColumn(format="%+.1f") for c in
                ["Chg (last obs) %", "vs 30D avg %", "1M %", "vs 52w high %"]}
             | {"Vol 30D %": st.column_config.NumberColumn(format="%.0f")})
st.caption("Support/resistance: clustered swing highs/lows (±5 sessions) over the last 6 months; "
           "nearest level below/above the last close.")

st.markdown("#### Live snapshot history (OilPriceAPI)")
snap_rows = []
for code, name in (("wti", "WTI fut."), ("brent", "Brent fut."), ("dubai", "Dubai"), ("opec_basket", "OPEC basket")):
    h = db.snapshot_history(code)
    if not h.empty:
        h["benchmark"] = name
        snap_rows.append(h)
if snap_rows:
    sh = pd.concat(snap_rows)
    sh["quoted_at"] = pd.to_datetime(sh["quoted_at"], utc=True, format="ISO8601")
    st.caption(f"{len(sh)} snapshots stored since {sh['quoted_at'].min():%d %b %Y}. The tracker builds its own "
               "daily Dubai history from these over time.")
    st.dataframe(sh.pivot_table(index="quoted_at", columns="benchmark", values="price").sort_index(ascending=False).head(30),
                 width="stretch")
else:
    st.caption("No snapshots yet.")

"""Spread analysis: history, dislocation ranking and what drives each spread."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from oil_tracker import ui
from oil_tracker.analytics.spreads import SPREAD_DRIVERS, SPREAD_LABELS

ctx = ui.get_ctx()
ui.page_header("Spreads analysis", ctx, "Each spread compares two prices of the same type: Brent-WTI on daily spot, "
               "Dubai spreads on monthly averages (no free daily Dubai history).")

st.markdown("#### Which spread is most dislocated?")
rk = ctx["ranking"]
if not rk.empty:
    cols = st.columns(len(rk))
    for col, (_, r) in zip(cols, rk.iterrows()):
        with col:
            st.metric(f"#{_ + 1} {r['spread']}", f"{r['current']:+.2f} $/bbl", f"z {r['z_5y']:+.1f} vs 5Y",
                      delta_color="off", border=True)
            st.markdown(ui.badge(r["status"]) + f" <span style='color:{ui.INK['muted']};font-size:0.8rem'>"
                        f"{r['pctile_5y']:.0f}th pctile · 5Y avg {r['avg_5y']:+.2f}</span>", unsafe_allow_html=True)
    st.caption("Ranked by |z-score| against each spread's own 5-year history.")


def spread_chart(s: pd.Series, title: str, freq: str) -> go.Figure:
    y5 = s.loc[s.index > s.index.max() - pd.Timedelta(days=5 * 365)]
    mu, sd = y5.mean(), y5.std()
    fig = go.Figure()
    fig.add_hrect(y0=mu - sd, y1=mu + sd, fillcolor=ui.BAND, line_width=0)
    fig.add_hline(y=mu, line=dict(color=ui.INK["muted"], dash="dash", width=1),
                  annotation_text=f"5Y avg {mu:+.2f} · band ±1σ · dotted ±2σ", annotation_position="top left", annotation_font_size=10,
                  annotation_font_color=ui.INK["secondary"])
    for k in (2, -2):
        fig.add_hline(y=mu + k * sd, line=dict(color=ui.STATUS["critical"], dash="dot", width=1), opacity=0.6)
    fig.add_scatter(x=s.index, y=s, mode="lines+markers" if freq == "M" else "lines",
                    line=dict(color=ui.COLORS["wti"], width=2), marker=dict(size=8),
                    hovertemplate="%{x|%d %b %Y}: %{y:+.2f}<extra></extra>", showlegend=False)
    fig.add_hline(y=0, line=dict(color=ui.AXIS, width=1))
    fig.update_layout(height=360, title=dict(text=title, font_size=14), yaxis_title="$/bbl")
    return fig


yrs = st.segmented_control("History", ["1Y", "3Y", "5Y", "Max"], default="5Y") or "5Y"
cut = pd.Timestamp.min if yrs == "Max" else pd.Timestamp.today() - pd.DateOffset(years=int(yrs[:-1]))

d = ctx["daily_spreads"]["brent_wti"]
st.plotly_chart(spread_chart(d[d.index > cut], "Brent - WTI · daily spot", "D"), width="stretch")
with st.expander("What drives Brent - WTI", expanded=True):
    st.markdown(SPREAD_DRIVERS["brent_wti"])

m = ctx["monthly_spreads"]
c1, c2 = st.columns(2, gap="large")
for col, key in ((c1, "brent_dubai"), (c2, "wti_dubai")):
    with col:
        if key in m:
            st.plotly_chart(spread_chart(m[key][m.index > cut], f"{SPREAD_LABELS[key]} · monthly avg", "M"),
                            width="stretch")
        st.markdown(SPREAD_DRIVERS[key])

st.markdown("#### Live indicative spreads")
ss = ctx["snapshot_spreads"]
if ss:
    cols = st.columns(len(ss))
    for col, (k, v) in zip(cols, ss.items()):
        col.metric(SPREAD_LABELS[k], f"{v:+.2f}", border=True)
    st.caption("From OilPriceAPI's latest quotes: WTI and Brent are front-month futures, Dubai is a physical "
               "assessment, so these mix bases and timing. Use them for direction, not for the level; the "
               "historical stats above use consistent bases.")

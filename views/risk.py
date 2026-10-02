"""Geopolitical risk and volatility gauges."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from oil_tracker import ui
from oil_tracker.analytics.risk import GAUGES

ctx = ui.get_ctx()
ui.page_header("Geopolitical risk", ctx, "Geopolitical Risk index (Caldara & Iacoviello), oil and equity implied "
               "volatility (CBOE via FRED), global policy uncertainty.")

g = ctx["gauges"]
cols = st.columns(len(g))
for col, (k, d) in zip(cols, g.items()):
    if not d:
        continue
    with col:
        st.metric(f"{GAUGES[k][0]} · {d['date']:%d %b}", f"{d['current']:.1f}", f"{d['chg_1m']:+.1f} vs 1M ago",
                  delta_color="off", delta_arrow="off", border=True)
        st.markdown(ui.badge({"EXTREME": "ANOMALY", "ELEVATED": "WIDE", "LOW": "NORMAL"}.get(d["status"], "NORMAL"),
                             d["status"]) + f" <span style='color:{ui.INK['muted']};font-size:0.8rem'>"
                    f"{d['pctile_5y']:.0f}th pctile 5Y</span>", unsafe_allow_html=True)

window = st.segmented_control("Window", ["1Y", "3Y", "5Y", "10Y"], default="3Y") or "3Y"
cut = pd.Timestamp.today() - pd.DateOffset(years=int(window[:-1]))
rk = ctx["frames"]["risk"]
mk = ctx["frames"]["markets"]
px = ctx["frames"]["prices"]


def line(s: pd.Series, title: str, color: str, ytitle: str, ma: int | None = None, events: bool = False) -> go.Figure:
    s = s.dropna()
    s = s[s.index >= cut]
    fig = go.Figure()
    if ma:
        fig.add_scatter(x=s.index, y=s, name="daily", line=dict(color=ui.INK["muted"], width=1), opacity=0.5,
                        hovertemplate="daily %{y:.0f}<extra></extra>")
        sm = s.rolling(ma).mean()
        fig.add_scatter(x=sm.index, y=sm, name=f"{ma}-day avg", line=dict(color=color, width=2),
                        hovertemplate=f"{ma}d avg %{{y:.0f}}<extra></extra>")
    else:
        fig.add_scatter(x=s.index, y=s, line=dict(color=color, width=2), showlegend=False,
                        hovertemplate="%{y:.1f}<extra></extra>")
    fig.update_layout(height=300, yaxis_title=ytitle, title=dict(text=title, font_size=13))
    return fig


a, b = st.columns(2, gap="large")
with a:
    st.plotly_chart(line(rk["gpr_daily"], "Geopolitical Risk index (daily, 1985-2019 avg = 100)", ui.COLORS["brent"],
                         "index", ma=30), width="stretch")
with b:
    st.plotly_chart(line(mk["ovx"], "OVX - 30-day implied volatility of oil (USO options)", ui.COLORS["wti"], "%"),
                    width="stretch")
a, b = st.columns(2, gap="large")
with a:
    st.plotly_chart(line(mk["vix"], "VIX - S&P 500 implied volatility", ui.COLORS["dubai"], "%"), width="stretch")
with b:
    st.plotly_chart(line(px["brent"], "Brent (Dated) spot, same window", ui.COLORS["brent"], "$/bbl"), width="stretch")

st.markdown("#### Oil-specific risk premium proxy")
both = mk[["ovx", "vix"]].dropna()
both = both[both.index >= cut]
ratio = both["ovx"] / both["vix"]
fig = go.Figure(go.Scatter(x=ratio.index, y=ratio, line=dict(color=ui.COLORS["wti"], width=2), showlegend=False,
                           hovertemplate="OVX/VIX %{y:.2f}<extra></extra>"))
fig.add_hline(y=float(ratio.mean()), line=dict(color=ui.INK["muted"], dash="dash", width=1),
              annotation_text=f"window avg {ratio.mean():.2f}", annotation_position="top left",
              annotation_font_size=10, annotation_font_color=ui.INK["secondary"])
fig.update_layout(height=280, yaxis_title="ratio", title=dict(text="OVX / VIX - oil vol relative to equity vol", font_size=13))
st.plotly_chart(fig, width="stretch")
st.caption("When oil volatility rises while equity volatility does not, the risk is oil-specific (supply, "
           "geopolitics) rather than macro. Separate charts by design: no dual axes.")

with st.expander("How to read these", expanded=False):
    st.markdown(
        """
- **GPR** counts newspaper articles about geopolitical tensions (wars, terrorism, military build-ups); the
  *acts* and *threats* sub-indices are in the source file. Spikes tend to lift the risk premium in Brent more than
  in WTI.
- **OVX** is the market price of oil uncertainty. Above ~50 the market is pricing large daily moves; options
  hedging flows can then amplify price swings.
- **VIX** gives the macro backdrop: oil rallies with a low VIX are supply stories; oil sell-offs with a high VIX
  are demand/risk-off stories.
- Percentiles are against the last 5 years. *Elevated* ≥ 80th, *extreme* ≥ 95th.
"""
    )

"""Cross-asset correlations of daily returns."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from oil_tracker import ui
from oil_tracker.analytics.risk import CORR_ASSETS, correlation_matrix, rolling_corr

ctx = ui.get_ctx()
ui.page_header("Correlations", ctx, "Daily returns (log changes; yield changes in pp). Correlating price levels "
               "would show ~1 for any two trending series, so it is never done here.")

frame = ctx["frames"]["prices"].join(ctx["frames"]["markets"], how="outer")[list(CORR_ASSETS)]
window = st.segmented_control("Window", ["3M", "6M", "1Y", "3Y"], default="1Y") or "1Y"
days = {"3M": 92, "6M": 183, "1Y": 365, "3Y": 1096}[window]
cm = correlation_matrix(frame, days)
labels = [CORR_ASSETS[c] for c in cm.columns]

# Diverging blue <-> red with a neutral gray midpoint (dark-theme steps).
scale = [[0.0, "#1c5cab"], [0.25, "#5598e7"], [0.5, "#383835"], [0.75, "#e66767"], [1.0, "#d03b3b"]]
z = cm.to_numpy().copy()
np.fill_diagonal(z, np.nan)  # the diagonal is 1 by definition; hide it so it doesn't dominate the scale
fig = go.Figure(go.Heatmap(
    z=z, x=labels, y=labels, zmin=-1, zmax=1, zmid=0, colorscale=scale, xgap=2, ygap=2,
    text=np.where(np.isnan(z), "", np.round(cm.to_numpy(), 2).astype(str)), texttemplate="%{text}",
    textfont=dict(color=ui.INK["primary"], size=13),
    hovertemplate="%{y} × %{x}: %{z:.2f}<extra></extra>", colorbar=dict(title="ρ", thickness=12),
))
fig.update_layout(height=460, hovermode="closest", yaxis=dict(autorange="reversed"), xaxis=dict(showspikes=False),
                  title=dict(text=f"Correlation of daily returns · last {window}", font_size=13))
st.plotly_chart(fig, width="stretch")
st.caption("Dubai is excluded: it is only available as a monthly average.")

st.markdown("#### Rolling 3-month correlation")
pairs = {"Brent × S&P 500 (risk-on/off coupling)": ("brent", "sp500"),
         "Brent × USD (dollar effect)": ("brent", "usd_broad"),
         "Brent × WTI (benchmark integration)": ("brent", "wti")}
palette = [ui.COLORS["wti"], ui.COLORS["brent"], ui.COLORS["dubai"]]
fig = go.Figure()
for i, (name, (a, b)) in enumerate(pairs.items()):
    rc = rolling_corr(frame, a, b)
    rc = rc[rc.index >= rc.index.max() - pd.DateOffset(years=5)]
    fig.add_scatter(x=rc.index, y=rc, name=name, line=dict(color=palette[i], width=2),
                    hovertemplate=f"{name.split(' (')[0]} %{{y:.2f}}<extra></extra>")
fig.add_hline(y=0, line=dict(color=ui.INK["muted"], width=1))
fig.update_layout(height=380, yaxis=dict(range=[-1, 1], title="ρ (63 trading days)"),
                  title=dict(text="Rolling correlations · last 5 years", font_size=13))
st.plotly_chart(fig, width="stretch")

with st.expander("How to read these", expanded=False):
    st.markdown(
        """
- **Oil × equities** positive: oil trades as a growth/demand asset (risk-on). Near zero or negative: supply shocks
  dominate (a supply-driven rally hurts equities).
- **Oil × USD** usually negative (oil priced in dollars; a strong dollar weighs on non-US demand), but the link
  breaks during supply shocks and for the US as a net exporter.
- **Brent × WTI** daily correlation well below ~0.9 signals the two benchmarks are being driven by different
  forces (US logistics vs seaborne supply) - check the Brent-WTI spread.
- Correlations are unstable: compare windows before drawing conclusions.
"""
    )

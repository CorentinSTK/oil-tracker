"""Historical test of the S&D score as a weekly directional signal."""

import plotly.graph_objects as go
import streamlit as st

from oil_tracker import ui
from oil_tracker.analytics.backtest import run_backtest
from oil_tracker.analytics.balance import WEIGHTS

ctx = ui.get_ctx()
ui.page_header("Signal backtest", ctx, "If I had traded the S&D balance score at every EIA release, what would the P&L "
               "have been?")

hist = ctx["score_history"]
if hist.empty:
    st.info("Not enough history to compute the score.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
bench = c1.selectbox("Instrument", ["wti", "brent"], format_func=str.upper)
long_at = c2.number_input("Long if score ≥", 50.0, 90.0, 55.0, 1.0)
short_at = c3.number_input("Short if score ≤", 10.0, 50.0, 45.0, 1.0)
cost = c4.number_input("Cost per trade ($/bbl)", 0.0, 1.0, 0.05, 0.01)

res, stats = run_backtest(hist["score"], ctx["frames"]["prices"][bench], long_at, short_at, cost)
if res.empty:
    st.info("Not enough overlapping data.")
    st.stop()

m = st.columns(6)
m[0].metric("Total P&L", f"{stats['total_pnl']:+.1f} $/bbl", border=True)
m[1].metric("Buy & hold", f"{stats['buy_hold_pnl']:+.1f} $/bbl", border=True)
m[2].metric("Sharpe (ann.)", f"{stats['sharpe']:.2f}", border=True)
m[3].metric("Hit rate", f"{stats['hit_rate']:.0f}%", border=True)
m[4].metric("Max drawdown", f"{stats['max_drawdown']:.1f} $/bbl", border=True)
m[5].metric("Rank IC", f"{stats['ic']:+.3f}", help="Spearman correlation of the score with the next week's price move.",
            border=True)
st.caption(f"{stats['weeks']} weekly releases from {stats['start']:%d %b %Y} to {stats['end']:%d %b %Y} · "
           f"{stats['trades']} position changes · in market {stats['pct_time_in_market']:.0f}% of weeks.")

fig = go.Figure()
fig.add_scatter(x=res.index, y=res["cum_pnl"], name="S&D strategy", line=dict(color=ui.COLORS["wti"], width=2))
fig.add_scatter(x=res.index, y=res["buy_hold"], name="Buy & hold 1 bbl", line=dict(color=ui.INK["muted"], width=2, dash="dash"))
fig.update_layout(height=380, yaxis_title="cumulative $/bbl", title=dict(text="Cumulative P&L (1 barrel)", font_size=13))
st.plotly_chart(fig, width="stretch")

fig = go.Figure()
fig.add_hrect(y0=short_at, y1=long_at, fillcolor=ui.BAND, line_width=0)
fig.add_scatter(x=hist.index, y=hist["score"], line=dict(color=ui.COLORS["brent"], width=2), showlegend=False,
                hovertemplate="%{x|%d %b %Y}: %{y:.0f}<extra></extra>")
fig.update_layout(height=260, yaxis=dict(range=[0, 100], title="score"),
                  title=dict(text="S&D balance score history (band = flat zone)", font_size=13))
st.plotly_chart(fig, width="stretch")

with st.expander("Method & caveats", expanded=False):
    st.markdown(
        f"""
- **Signal**: score = 50 + 50 × Σ wᵢ·sᵢ with weights {', '.join(f'{k} {v:.0%}' for k, v in WEIGHTS.items())};
  each sᵢ = tanh(z/2) of the component's z-score (see `oil_tracker/analytics/balance.py`).
- **Timing**: the week-ending Friday data is dated at the following Wednesday release; positions are taken at
  that day's close and held to the next release. No look-ahead in prices.
- **P&L in $/bbl** on the *spot* price - spot is not directly tradable (no roll yield, no carry), so treat
  this as a test of the signal's information, not of a strategy's returns.
- EIA weekly data are used as currently published (small revisions are not point-in-time).
- The weights are the a-priori ones from the design brief, not fitted - but they were also not validated
  out-of-sample, and changing the thresholds above on this same history is in-sample tuning.
"""
    )

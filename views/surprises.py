"""Weekly EIA inventory surprises vs seasonal norm and vs analyst consensus."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from oil_tracker import ui
from oil_tracker.analytics.surprises import ITEMS, price_reaction, streak

ctx = ui.get_ctx()
ui.page_header("Inventory surprises", ctx, "Markets trade the gap between the EIA print and what was expected. "
               "Positive surprise = more barrels than expected = bearish.")

surp = ctx["surprises"]
if not surp:
    st.info("Not enough weekly history yet.")
    st.stop()

item = st.segmented_control("Series", list(surp), format_func=ITEMS.get, default="us_crude") or "us_crude"
s = surp[item]
last = s.iloc[-1]
stk = streak(s["surprise"])
c = st.columns(4)
c[0].metric(f"Actual change · week {s.index[-1]:%d %b}", f"{last['actual']:+.2f} Mbbl", border=True)
c[1].metric("Seasonal norm (5Y same week)", f"{last['expected']:+.2f} Mbbl", border=True)
c[2].metric("Surprise vs norm", f"{last['surprise']:+.2f} Mbbl", f"z {last['z']:+.1f}",
            delta_color="inverse" if abs(last["z"]) >= 0.5 else "off",
            delta_arrow="auto" if abs(last["z"]) >= 0.5 else "off", border=True)
c[3].metric("Current run", f"{stk['length']} wk", stk["direction"], delta_color="off", delta_arrow="off", border=True)

recent = s.iloc[-26:]
fig = go.Figure(go.Bar(
    x=recent.index, y=recent["surprise"],
    marker_color=[ui.STATUS["critical"] if v > 0 else ui.STATUS["good"] for v in recent["surprise"]],
    customdata=recent[["actual", "expected"]].to_numpy(),
    hovertemplate="Week %{x|%d %b}: surprise %{y:+.2f}<br>actual %{customdata[0]:+.2f} · norm %{customdata[1]:+.2f}"
                  "<extra></extra>",
))
fig.add_hline(y=0, line=dict(color=ui.INK["muted"], width=1))
fig.update_layout(height=320, hovermode="closest", yaxis_title="Mbbl",
                  title=dict(text=f"{ITEMS[item]} · surprise vs seasonal norm, last 26 weeks "
                                  "(red = bearish build, green = bullish draw)", font_size=13))
st.plotly_chart(fig, width="stretch")
st.caption("Runs of 3+ same-sign surprises are flagged as alerts: a persistent run says more about the balance "
           "than any single week.")

# ----------------------------------------------------------- price reaction
st.markdown("#### Does the market react?")
bench = st.radio("Price", ["wti", "brent"], horizontal=True, format_func=str.upper)
rel, stats = price_reaction(s, ctx["frames"]["prices"][bench])
if stats:
    m = st.columns(4)
    m[0].metric("Releases (10y)", stats["n"], border=True)
    m[1].metric("Correlation surprise vs release-day move", f"{stats['corr']:+.2f}", border=True)
    m[2].metric("Move per +10 Mbbl surprise", f"{stats['slope_pct_per_10mb']:+.2f}%", border=True)
    m[3].metric("Big surprises (|z|≥1.5) moving price the 'right' way", f"{stats['hit_rate_big']:.0f}%",
                f"n = {stats['n_big']}", delta_color="off", delta_arrow="off", border=True)
    fig = go.Figure(go.Scatter(
        x=rel["surprise"], y=rel["px_chg_pct"], mode="markers",
        marker=dict(size=8, color=ui.COLORS[bench], opacity=0.55, line=dict(width=1, color=ui.SURFACE)),
        customdata=rel.index.strftime("%d %b %Y"),
        hovertemplate="Week %{customdata}<br>surprise %{x:+.2f} Mbbl<br>price %{y:+.2f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line=dict(color=ui.INK["muted"], width=1))
    fig.add_vline(x=0, line=dict(color=ui.INK["muted"], width=1))
    fig.update_layout(height=360, hovermode="closest", xaxis_title="Surprise vs seasonal norm (Mbbl)",
                      yaxis_title=f"{bench.upper()} spot change on release day (%)",
                      title=dict(text="Release-day price change vs surprise", font_size=13))
    st.plotly_chart(fig, width="stretch")
    st.caption("Spot closes on release day include all other news that day, and the seasonal norm is a much weaker "
               "'expectation' than the analyst consensus the market actually trades against - so expect a weak "
               "relationship here. Enter consensus figures below for the real thing.")

# ----------------------------------------------------------- consensus
st.markdown("#### Surprises vs analyst consensus")
cs = ctx["consensus_surprises"]
if cs.empty:
    st.info("No consensus entered yet. The EIA does not publish a forecast and the analyst surveys "
            "(Reuters, WSJ, Bloomberg) are not available through a free API: add them below each Tuesday.")
else:
    piv = cs.pivot_table(index="week_ending", columns="item", values="surprise").sort_index(ascending=False)
    ui.table(cs.sort_values("week_ending", ascending=False).assign(week_ending=lambda d: d["week_ending"].dt.date),
             {c: "{:+.2f}" for c in ["expected", "actual", "surprise"]})
    crude = piv.get("Crude")
    if crude is not None:
        st.caption(f"Crude: {streak(crude.sort_index())['length']}-week current run of "
                   f"{streak(crude.sort_index())['direction'].replace('norm', 'consensus')}.")
ui.manual_editor("consensus", "Enter analyst consensus (Mbbl, expected weekly change)")

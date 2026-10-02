"""Main overview: prices, spreads, US fundamentals, balance score, catalysts."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from oil_tracker import ui
from oil_tracker.analytics.balance import WEIGHTS
from oil_tracker.analytics.brief import build_brief
from oil_tracker.analytics.spreads import SPREAD_LABELS
from oil_tracker.catalysts import upcoming

ctx = ui.get_ctx()
ui.page_header("Oil Market Tracker", ctx)
st.markdown(ui.freshness_line(ctx))

mom, snap = ctx["momentum"], ctx["snapshot"]
snap_px = dict(zip(snap["code"], snap["price"])) if not snap.empty else {}

# ---------------------------------------------------------------- prices
st.markdown("#### Benchmark prices")
cols = st.columns(3)
for col, key, label in zip(cols, ("wti", "brent", "dubai"), ("WTI Cushing", "Brent (Dated)", "Dubai")):
    m = mom.get(key, {})
    with col:
        if not m:
            st.metric(label, "—", border=True)
            continue
        if key == "dubai":
            st.metric(f"{label} · monthly avg {m['date']:%b %Y}", ui.fmt(m["last"]),
                      f"{m['chg_1d_pct']:+.1f}% m/m", border=True)
        else:
            st.metric(f"{label} · spot {m['date']:%d %b}", ui.fmt(m["last"]),
                      f"{m['chg_1d']:+.2f} ({m['chg_1d_pct']:+.1f}%)", border=True)
            st.caption(f"30D avg {ui.fmt(m['avg_30d'])} ({m['vs_30d_avg_pct']:+.1f}%) · "
                       f"52w {ui.fmt(m['low_52w'])}–{ui.fmt(m['high_52w'])} · vol 30D {m['vol_30d']:.0f}%")
        if key in snap_px:
            st.caption(f"Live indicative (OilPriceAPI{', front-month futures' if key != 'dubai' else ''}): "
                       f"**{snap_px[key]:.2f}**")

# ---------------------------------------------------------------- spreads + fundamentals
left, right = st.columns([1, 1], gap="large")

with left:
    st.markdown("#### Spreads · market structure")
    rows = []
    for key, s in ctx["spread_stats"].items():
        if not s:
            continue
        basis = f"daily spot, {s['date']:%d %b}" if s["freq"] == "D" else f"monthly avg, {s['date']:%b %Y}"
        rows.append(
            f"<tr><td><b>{SPREAD_LABELS[key]}</b><br><span style='color:{ui.INK['muted']};font-size:0.75rem'>{basis}</span></td>"
            f"<td style='text-align:right'>{s['current']:+.2f}</td>"
            f"<td style='text-align:right'>{s['avg_5y']:+.2f}</td>"
            f"<td style='text-align:right'>{s['z_5y']:+.1f}</td>"
            f"<td>{ui.badge(s['status'])}</td></tr>"
        )
    st.markdown(
        "<table style='width:100%;font-variant-numeric:tabular-nums'>"
        "<tr><th>Spread ($/bbl)</th><th style='text-align:right'>Now</th><th style='text-align:right'>5Y avg</th>"
        "<th style='text-align:right'>z</th><th>Status</th></tr>" + "".join(rows) + "</table>",
        unsafe_allow_html=True,
    )
    ss = ctx["snapshot_spreads"]
    if ss:
        st.caption("Live indicative (OilPriceAPI, mixed futures/physical bases): "
                   + " · ".join(f"{SPREAD_LABELS[k]} {v:+.2f}" for k, v in ss.items()))

with right:
    st.markdown("#### US fundamentals · EIA weekly")
    inv, ref = ctx["inventory"], ctx["refinery"]
    lines = []
    for key, label in (("us_crude", "Crude (ex-SPR)"), ("cushing", "Cushing"),
                       ("us_gasoline", "Gasoline"), ("us_distillates", "Distillates")):
        d = inv.get(key)
        if not d:
            continue
        st_ = "bullish" if d["wow"] < 0 else "bearish"
        lines.append(
            f"<tr><td><b>{label}</b></td><td style='text-align:right'>{d['level']:.1f}</td>"
            f"<td style='text-align:right'>{d['wow']:+.2f}</td>"
            f"<td style='text-align:right'>{d['seasonal_chg']:+.2f}</td>"
            f"<td style='text-align:right'>{d['vs_5y']:+.1f}</td>"
            f"<td>{ui.badge(st_, d['signal'] + (' · large' if d['magnitude'] == 'LARGE' else ''))}</td></tr>"
        )
    if ref:
        sig = {"STRONG": "bullish", "WEAK": "bearish"}.get(ref["signal"], "neutral")
        lines.append(
            f"<tr><td><b>Refinery util.</b></td><td style='text-align:right'>{ref['level']:.1f}%</td>"
            f"<td style='text-align:right'>{ref['wow']:+.1f}pp</td><td style='text-align:right'>—</td>"
            f"<td style='text-align:right'>{ref['vs_5y']:+.1f}pp</td><td>{ui.badge(sig, ref['signal'])}</td></tr>"
        )
    st.markdown(
        "<table style='width:100%;font-variant-numeric:tabular-nums'><tr><th>Mbbl</th>"
        "<th style='text-align:right'>Level</th><th style='text-align:right'>w/w</th>"
        "<th style='text-align:right'>Seasonal w/w</th><th style='text-align:right'>vs 5Y</th><th>Signal</th></tr>"
        + "".join(lines) + "</table>",
        unsafe_allow_html=True,
    )
    if inv.get("us_crude"):
        st.caption(f"Week ending {inv['us_crude']['date']:%d %b %Y}. 'vs 5Y' = vs the 5-year average for the same week.")

# ---------------------------------------------------------------- implications
st.markdown("#### Market implications")
sc = ctx["score"]
c1, c2, c3 = st.columns([0.9, 1.3, 1.6], gap="large")
with c1:
    if sc:
        delta = sc["score"] - sc["prev_score"]
        st.metric("S&D balance score", f"{sc['score']:.0f} / 100", f"{delta:+.1f} w/w", border=True)
        st.markdown(ui.badge(sc["regime"]), unsafe_allow_html=True)
        st.caption(f"Above 55 = deficit, below 45 = surplus. Green = bullish for prices. As of EIA release {sc['release_date']:%d %b}.")
    else:
        st.info("Not enough history to score yet.")
with c2:
    if sc:
        contrib = sc["contributions"]
        names = list(WEIGHTS)
        fig = go.Figure(go.Bar(
            x=[contrib[k] for k in names], y=[f"{k} ({WEIGHTS[k]:.0%})" for k in names], orientation="h",
            marker_color=[ui.STATUS["good"] if contrib[k] >= 0 else ui.STATUS["critical"] for k in names],
            text=[f"{contrib[k]:+.1f}" for k in names], textposition="outside", cliponaxis=False,
            hovertemplate="%{y}: %{x:+.1f} pts<extra></extra>",
        ))
        fig.update_layout(height=200, title=dict(text="Contribution to score (pts vs 50)", font_size=13),
                          hovermode="closest", xaxis=dict(zeroline=True, zerolinecolor=ui.INK["muted"], range=[-22, 22]),
                          yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
with c3:
    b = build_brief(ctx)
    st.markdown(f"**{b['headline']}**")
    st.markdown(b["takeaway"])
    if b["bullish"]:
        st.markdown("**Bullish**\n" + "\n".join(f"- {x}" for x in b["bullish"][:4]))
    if b["bearish"]:
        st.markdown("**Bearish**\n" + "\n".join(f"- {x}" for x in b["bearish"][:4]))
    if b["watch"]:
        st.markdown("**Watch**\n" + "\n".join(f"- {x}" for x in b["watch"][:4]))

# ---------------------------------------------------------------- charts
st.markdown("#### Prices & US stocks · last 12 months")
px = ctx["frames"]["prices"]
px1 = px.loc[px.index > px.index.max() - pd.Timedelta(days=365)]
g1, g2 = st.columns(2, gap="large")
with g1:
    fig = go.Figure()
    for k, name in (("wti", "WTI"), ("brent", "Brent")):
        s = px1[k].dropna()
        fig.add_scatter(x=s.index, y=s, name=name, line=dict(color=ui.COLORS[k], width=2),
                        hovertemplate=f"{name} %{{y:.2f}}<extra></extra>")
    dub = ctx["frames"]["dubai_m"]
    dub = dub.loc[dub.index > px1.index.min() - pd.Timedelta(days=31)]
    fig.add_scatter(x=dub.index + pd.Timedelta(days=14), y=dub, name="Dubai (monthly avg)", mode="lines+markers",
                    line=dict(color=ui.COLORS["dubai"], width=2, dash="dot"), marker=dict(size=8),
                    hovertemplate="Dubai %{y:.2f}<extra></extra>")
    fig.update_layout(height=320, title=dict(text="Spot prices ($/bbl)", font_size=13))
    st.plotly_chart(fig, width="stretch")
with g2:
    w = ctx["frames"]["weekly"]
    crude = w["us_crude"].dropna()
    crude = crude.loc[crude.index > crude.index.max() - pd.Timedelta(days=365)]
    fig = go.Figure(go.Scatter(x=crude.index, y=crude, name="US crude stocks", line=dict(color=ui.COLORS["wti"], width=2),
                               hovertemplate="%{y:.1f} Mbbl<extra></extra>"))
    fig.update_layout(height=320, title=dict(text="US commercial crude stocks (Mbbl) · seasonal view on Fundamentals",
                                             font_size=13), showlegend=False)
    st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------- alerts + catalysts
a, c = st.columns(2, gap="large")
with a:
    st.markdown("#### Active alerts")
    alerts = sorted(ctx["alerts"], key=lambda x: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[x["severity"]])
    if not alerts:
        st.caption("No rule triggered on the latest data.")
    for al in alerts:
        st.markdown(f"{ui.badge(al['severity'])} {al['message']}<br>"
                    f"<span style='color:{ui.INK['muted']};font-size:0.8rem'>{al['action']} · data {al['as_of']}</span>",
                    unsafe_allow_html=True)
with c:
    st.markdown("#### Upcoming catalysts")
    ev = upcoming(days=21)
    st.dataframe(
        pd.DataFrame([{"When (ET)": e.when.strftime("%a %d %b %H:%M"), "Release": e.name,
                       "Note": ("est. · " if e.estimated else "") + e.note} for e in ev[:10]]),
        hide_index=True, width="stretch",
    )

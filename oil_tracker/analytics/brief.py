"""Daily market brief, generated from rules over the computed context.

Deterministic on purpose: every sentence traces back to a number on the
dashboard, so the brief can be checked line by line. "Trade considerations"
are conditional observations, not recommendations.
"""

from __future__ import annotations

import pandas as pd

from oil_tracker.analytics.spreads import SPREAD_LABELS
from oil_tracker.catalysts import upcoming


def _fmt_d(ts) -> str:
    return pd.Timestamp(ts).strftime("%a %d %b")


def build_brief(ctx: dict) -> dict:
    mom, inv, sc = ctx["momentum"], ctx["inventory"], ctx["score"]
    crude, total = inv.get("us_crude", {}), inv.get("total", {})
    ref, bw = ctx["refinery"], ctx["spread_stats"].get("brent_wti", {})
    bull, bear, watch = [], [], []

    # --- signals -------------------------------------------------------------
    if total:
        line = (f"US commercial stocks (crude+gasoline+distillates) {total['wow']:+.1f} Mbbl vs a "
                f"seasonal norm of {total['seasonal_chg']:+.1f} Mbbl")
        (bull if total["surprise"] < 0 else bear).append(line)
        lvl = f"Total stocks {total['vs_5y']:+.1f} Mbbl ({total['vs_5y_pct']:+.1f}%) vs 5Y same-week average"
        (bull if total["vs_5y"] < 0 else bear).append(lvl)
    if crude:
        line = f"Crude {crude['signal'].lower()} of {abs(crude['wow']):.1f} Mbbl ({crude['magnitude'].lower()})"
        (bull if crude["wow"] < 0 else bear).append(line)
    if ref:
        line = f"Refinery runs {ref['level']:.1f}% ({ref['vs_5y']:+.1f} pp vs 5Y seasonal)"
        if ref["signal"] == "STRONG":
            bull.append(line)
        elif ref["signal"] == "WEAK":
            bear.append(line)
    for k in ("wti", "brent"):
        m = mom.get(k)
        if m and abs(m["vs_30d_avg_pct"]) >= 2:
            line = f"{k.upper()} {m['vs_30d_avg_pct']:+.1f}% vs its 30-day average"
            (bull if m["vs_30d_avg_pct"] > 0 else bear).append(line)

    ranking = ctx["ranking"]
    if not ranking.empty and ranking.iloc[0]["abs_z"] >= 1:
        r = ranking.iloc[0]
        watch.append(f"{r['spread']} is the most dislocated spread: {r['current']:+.2f} $/bbl "
                     f"(5Y avg {r['avg_5y']:+.2f}, z {r['z_5y']:+.1f})")
    gl = ctx["global"]
    if gl and gl.get("opec_spare") == gl.get("opec_spare"):
        watch.append(f"OPEC spare capacity {gl['opec_spare']:.2f} mb/d (EIA STEO)")
    if gl and gl.get("next_3m_avg") == gl.get("next_3m_avg"):
        bal = gl["next_3m_avg"]
        watch.append(f"EIA sees the world market {'in surplus' if bal > 0 else 'in deficit'} by "
                     f"{abs(bal):.2f} mb/d over the next 3 months")
    # Market structure and downstream demand
    for name, cv in ctx.get("curves", {}).items():
        if cv and "BACKWARDATION" in cv["structure"]:
            bull.append(f"{name.upper()} curve in {cv['structure'].lower()} (M1-M6 {cv['m1_m6']:+.2f} $/bbl)")
        elif cv and "CONTANGO" in cv["structure"]:
            bear.append(f"{name.upper()} curve in {cv['structure'].lower()} (M1-M6 {cv['m1_m6']:+.2f} $/bbl)")
    c321 = ctx.get("crack_summary", {}).get("usgc_321")
    if c321 and c321["signal"] in ("STRONG", "WEAK"):
        line = (f"USGC 3-2-1 crack {c321['current']:.1f} $/bbl ({c321['vs_seasonal']:+.1f} vs seasonal) - "
                f"{'refiners incentivised to run hard' if c321['signal'] == 'STRONG' else 'margins discourage runs'}")
        (bull if c321["signal"] == "STRONG" else bear).append(line)
    dem = ctx.get("demand", {}).get("ps_total")
    if dem and not pd.isna(dem["z"]) and abs(dem["z"]) >= 0.5:
        line = f"US implied demand (4wk) {dem['vs_seasonal_pct']:+.1f}% vs seasonal norm"
        (bull if dem["z"] > 0 else bear).append(line)
    oe = ctx.get("oecd_summary", {})
    if oe and oe["signal"] != "NORMAL":
        line = (f"OECD stocks {oe['vs_5y']:+.0f} Mbbl vs 5Y ({oe['days_cover']:.1f} days of cover, "
                f"{oe['days_vs_5y']:+.1f} vs norm)")
        (bull if oe["signal"] == "TIGHT" else bear).append(line)
    dis = ctx.get("disruptions", {})
    if dis and dis["total"] >= 2 * dis["total_5y_avg"]:
        watch.append(f"Unplanned outages {dis['total']:.1f} mb/d vs a 5Y average of {dis['total_5y_avg']:.1f} "
                     f"({dis['month']:%b %Y}, EIA STEO)")
    ovx = ctx.get("gauges", {}).get("ovx")
    if ovx and ovx["status"] in ("ELEVATED", "EXTREME"):
        watch.append(f"OVX {ovx['current']:.0f} ({ovx['pctile_5y']:.0f}th pctile 5Y): headline risk priced in")

    nxt = next((e for e in upcoming(days=10) if e.source == "EIA" and "Weekly" in e.name), None)
    if nxt:
        watch.append(f"Next EIA weekly report: {_fmt_d(nxt.when)} {nxt.when:%H:%M} ET")

    # --- headline & outlook --------------------------------------------------
    regime = sc.get("regime", "N/A")
    outlook = {"DEFICIT": "BULLISH", "SURPLUS": "BEARISH"}.get(regime, "NEUTRAL")
    if sc and not pd.isna(sc.get("prev_score")):
        delta = sc["score"] - sc["prev_score"]
        trend = "tightening" if delta > 2 else "loosening" if delta < -2 else "stable"
    else:
        delta, trend = 0.0, "stable"

    if total and abs(total["surprise"]) > total.get("chg_std", 0):
        headline = (f"{'Counter-seasonal draw' if total['surprise'] < 0 else 'Counter-seasonal build'} "
                    f"in US stocks; balance score {sc.get('score', float('nan')):.0f}/100 ({trend})")
    elif not ranking.empty and ranking.iloc[0]["abs_z"] >= 2:
        headline = f"{ranking.iloc[0]['spread']} dislocated; fundamentals {regime.lower()}"
    else:
        headline = f"Fundamentals {regime.lower()}; balance score {sc.get('score', float('nan')):.0f}/100 ({trend})"

    # --- one-sentence takeaway ----------------------------------------------
    parts = []
    if total:
        parts.append(f"US stocks {'drew' if total['wow'] < 0 else 'built'} "
                     f"{abs(total['wow']):.1f} Mbbl against a seasonal {total['seasonal_chg']:+.1f}")
    if ref:
        parts.append(f"refiners ran at {ref['level']:.1f}% ({ref['signal'].lower()} for the season)")
    takeaway = (("; ".join(parts) + ". ") if parts else "") + (
        f"Net, the composite reads {regime.lower()} at {sc['score']:.0f}/100"
        f"{f' ({delta:+.0f} w/w)' if sc else ''}." if sc else "Not enough data to score the balance yet."
    )

    # --- trade considerations (conditional, never advice) --------------------
    ideas = []
    if bw and bw["status"] in ("WIDE", "ANOMALY") and bw["z_5y"] > 0:
        ideas.append(f"Brent-WTI wide at {bw['current']:+.2f} (5Y avg {bw['avg_5y']:+.2f}): mean reversion "
                     "needs US exports to rise or seaborne tightness to ease - check Gulf Coast export capacity and freight.")
    elif bw and bw["status"] in ("NARROW", "ANOMALY") and bw["z_5y"] < 0:
        ideas.append(f"Brent-WTI narrow at {bw['current']:+.2f}: US export arb is closing - "
                     "watch for falling US exports and rising Cushing stocks.")
    bd = ctx["spread_stats"].get("brent_dubai", {})
    if bd and abs(bd["z_5y"]) >= 1:
        ideas.append(f"Brent-Dubai {bd['current']:+.2f} (monthly, z {bd['z_5y']:+.1f}): "
                     + ("sour crude relatively abundant - Middle East barrels flow West."
                        if bd["z_5y"] > 0 else "sour crude tight - Atlantic basin barrels pulled East."))
    if regime == "DEFICIT":
        ideas.append("Composite in deficit: dips are more likely to be bought while the stock draws persist; "
                     "invalidated by a counter-seasonal build next week.")
    elif regime == "SURPLUS":
        ideas.append("Composite in surplus: rallies face weak physical confirmation unless stocks start "
                     "drawing faster than seasonal.")

    lv = ctx["levels"]
    levels = {k: lv[k] for k in lv}

    moves = {k: mom[k] for k in ("wti", "brent", "dubai") if mom.get(k)}
    return {
        "date": pd.Timestamp.today().normalize(),
        "headline": headline,
        "outlook": outlook,
        "takeaway": takeaway,
        "moves": moves,
        "bullish": bull,
        "bearish": bear,
        "watch": watch,
        "levels": levels,
        "ideas": ideas,
    }


def brief_markdown(b: dict) -> str:
    """Plain-text brief ready to paste into a morning note."""
    lines = [f"DAILY OIL BRIEF - {b['date']:%d %b %Y}", "",
             f"HEADLINE: {b['headline']}", f"OUTLOOK: {b['outlook']}", "", b["takeaway"], ""]
    if b["moves"]:
        lines.append("PRICES (last close, spot):")
        for k, m in b["moves"].items():
            if k == "dubai":  # monthly IMF average: the change is month-on-month
                lines.append(f"  {'DUBAI (monthly avg)':<20}{m['last']:>8.2f}  {m['chg_1d_pct']:+.1f}% m/m"
                             f"{'':>23}(month of {m['date']:%b %Y})")
                continue
            lines.append(f"  {k.upper():<20}{m['last']:>8.2f}  {m['chg_1d_pct']:+.1f}% d/d  "
                         f"{m['vs_30d_avg_pct']:+.1f}% vs 30D avg   (as of {m['date']:%d %b})")
        lines.append("")
    for title, items in (("BULLISH", b["bullish"]), ("BEARISH", b["bearish"]), ("WATCH", b["watch"])):
        if items:
            lines.append(f"{title}:")
            lines += [f"  - {i}" for i in items]
            lines.append("")
    if b["levels"]:
        lines.append("TECHNICAL LEVELS (swing pivots, 6M):")
        for k, lv in b["levels"].items():
            lines.append(f"  {k.upper():<6} support {lv['support']:.2f} | resistance {lv['resistance']:.2f}")
        lines.append("")
    if b["ideas"]:
        lines.append("TRADE CONSIDERATIONS (not advice):")
        lines += [f"  - {i}" for i in b["ideas"]]
    return "\n".join(lines).rstrip() + "\n"

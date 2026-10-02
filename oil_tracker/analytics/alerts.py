"""Rule-based alerts. Each rule is explicit, dated to the data it reads, and
deduplicated in the database on (as_of, type)."""

from __future__ import annotations

import pandas as pd

from oil_tracker.analytics.spreads import SPREAD_LABELS


def _d(ts) -> str:
    return pd.Timestamp(ts).strftime("%Y-%m-%d")


def generate_alerts(ctx: dict) -> list[dict]:
    """``ctx`` is the dict produced by :func:`oil_tracker.service.build_context`."""
    alerts: list[dict] = []

    def add(as_of, kind, severity, message, action):
        alerts.append({"as_of": _d(as_of), "type": kind, "severity": severity, "message": message, "action": action})

    crude = ctx["inventory"].get("us_crude", {})
    if crude:
        if crude["magnitude"] == "LARGE":
            word = "build" if crude["wow"] > 0 else "draw"
            add(crude["date"], f"crude_large_{word}", "HIGH",
                f"Large US crude {word}: {crude['wow']:+.1f} Mbbl (normal weekly move ~{crude['chg_std']:.1f}).",
                "Check imports/exports and refinery runs in the WPSR; one-off export swings often reverse.")
        if abs(crude["surprise"]) > 1.5 * crude["chg_std"]:
            add(crude["date"], "crude_vs_seasonal", "MEDIUM",
                f"Crude change {crude['wow']:+.1f} Mbbl vs seasonal norm {crude['seasonal_chg']:+.1f} Mbbl.",
                "No free analyst consensus exists here; the 5Y seasonal change is used as the expectation.")

    cushing = ctx["inventory"].get("cushing", {})
    if cushing and cushing["level"] < 25:
        add(cushing["date"], "cushing_low", "MEDIUM",
            f"Cushing stocks at {cushing['level']:.1f} Mbbl, near operational lows (~20 Mbbl).",
            "Low hub stocks support WTI time-spreads (backwardation) and can squeeze the front month.")

    ref = ctx.get("refinery", {})
    if ref and ref["wow"] <= -2:
        add(ref["date"], "refinery_drop", "HIGH",
            f"Refinery utilisation fell {ref['wow']:.1f} pp to {ref['level']:.1f}%.",
            "Check for outages, hurricanes or maintenance before reading it as a demand shock.")

    for key, st in ctx["spread_stats"].items():
        if st and st["status"] == "ANOMALY":
            add(st["date"], f"spread_{key}", "MEDIUM",
                f"{SPREAD_LABELS[key]} at {st['current']:+.2f} $/bbl, z = {st['z_5y']:+.1f} vs 5Y.",
                "Look at the drivers: pipeline/export capacity, freight, crude quality, OPEC+ supply.")
    bw = ctx["spread_stats"].get("brent_wti", {})
    if bw and not (-2 <= bw["current"] <= 12):
        add(bw["date"], "brent_wti_range", "MEDIUM",
            f"Brent-WTI outside its usual -2..12 $/bbl corridor ({bw['current']:+.2f}).",
            "Market structure distortion: check Gulf Coast export capacity and freight.")

    for k in ("wti", "brent"):
        m = ctx["momentum"].get(k, {})
        if m and abs(m["chg_1d_pct"]) >= 5:
            add(m["date"], f"{k}_big_move", "MEDIUM",
                f"{k.upper()} moved {m['chg_1d_pct']:+.1f}% in one session.",
                "Identify the headline (OPEC+, geopolitics, macro) before trading the follow-through.")

    gb = ctx.get("global", {})
    if gb and gb.get("opec_spare", 99) < 2.0:
        add(gb["opec_spare_date"], "opec_spare_low", "MEDIUM",
            f"OPEC spare capacity estimated at {gb['opec_spare']:.2f} mb/d (EIA STEO).",
            "Thin spare capacity raises the price impact of any supply outage.")

    for name, cv in ctx.get("curves", {}).items():
        if cv and cv["structure"].startswith("STEEP"):
            add(cv["date"], f"curve_{name}", "MEDIUM",
                f"{name.upper()} curve in {cv['structure'].lower()}: M1-M6 {cv['m1_m6']:+.2f} $/bbl ({cv['m1_m6_pct']:+.1f}%).",
                "Extreme structure: prompt scarcity (backwardation) or a storage glut (contango). Watch time-spreads "
                "for the first sign of a turn.")

    streak = ctx.get("surprise_streak", {})
    if streak.get("length", 0) >= 3:
        add(ctx["inventory"]["total"]["date"], "surprise_streak", "MEDIUM",
            f"{streak['length']} consecutive weeks of US stock {streak['direction']} (crude+products vs seasonal).",
            "A persistent run is more informative than any single week: a trend in the balance.")

    for key, g in ctx.get("gauges", {}).items():
        if g and g["status"] == "EXTREME" and key in ("ovx", "gpr_daily"):
            add(g["date"], f"{key}_extreme", "MEDIUM",
                f"{'OVX' if key == 'ovx' else 'Geopolitical Risk index'} at {g['current']:.0f}, "
                f"{g['pctile_5y']:.0f}th percentile of 5 years.",
                "Risk premium likely embedded in prices; expect gap risk on headlines in both directions.")

    for key, c in ctx.get("crack_summary", {}).items():
        if c and not pd.isna(c["z"]) and abs(c["z"]) >= 2.5:
            add(c["date"], f"crack_{key}", "MEDIUM",
                f"{c['label']} at {c['current']:.1f} $/bbl, {c['vs_seasonal']:+.1f} vs seasonal norm (z {c['z']:+.1f}).",
                "Extreme margins pull crude into refineries (bullish crude) until runs max out or demand cracks.")

    dis = ctx.get("disruptions", {})
    if dis and dis["total"] - dis["total_3m_ago"] >= 1.0:
        add(dis["month"], "outages_rising", "HIGH",
            f"Unplanned supply outages up {dis['total'] - dis['total_3m_ago']:+.1f} mb/d in 3 months "
            f"to {dis['total']:.1f} mb/d (EIA STEO).", "Check which countries drive it on the OPEC+ page.")

    oe = ctx.get("oecd_summary", {})
    if oe and abs(oe["vs_5y_pct"]) >= 5:
        add(oe["date"], "oecd_stocks", "MEDIUM",
            f"OECD commercial stocks {oe['vs_5y']:+.0f} Mbbl ({oe['vs_5y_pct']:+.1f}%) vs 5Y same-month average.",
            "A >5% gap to the 5Y norm is where stocks start to drive time-spreads and flat price.")

    for key, info in ctx.get("staleness", {}).items():
        if info["stale"]:
            add(pd.Timestamp.today(), f"stale_{key}", "LOW",
                f"{info['label']} data is {info['age_days']} days old.",
                "Run a refresh or check the Data status page for fetch errors.")
    return alerts

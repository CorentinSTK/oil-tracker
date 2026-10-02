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

    for key, info in ctx.get("staleness", {}).items():
        if info["stale"]:
            add(pd.Timestamp.today(), f"stale_{key}", "LOW",
                f"{info['label']} data is {info['age_days']} days old.",
                "Run a refresh or check the Data status page for fetch errors.")
    return alerts

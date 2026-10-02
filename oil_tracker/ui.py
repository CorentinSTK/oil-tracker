"""Streamlit-only helpers: cached data access, sidebar, formatting, chart theme."""

from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from oil_tracker import config
from oil_tracker.data import database as db
from oil_tracker.data.pipeline import refresh
from oil_tracker.service import build_context

# ------------------------------------------------------------------ palette
# Categorical slots 1-3 of the validated dark palette, fixed per benchmark.
COLORS = {"wti": "#3987e5", "brent": "#d95926", "dubai": "#199e70"}
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}
INK = {"primary": "#ffffff", "secondary": "#c3c2b7", "muted": "#898781"}
GRID, AXIS, SURFACE = "#2c2c2a", "#383835", "#1a1a19"
BAND = "rgba(195,194,183,0.14)"

pio.templates["oil"] = go.layout.Template(
    layout=dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", color=INK["secondary"], size=12),
        xaxis=dict(gridcolor=GRID, linecolor=AXIS, zeroline=False, showspikes=True, spikemode="across",
                   spikethickness=1, spikecolor=INK["muted"], spikedash="solid"),
        yaxis=dict(gridcolor=GRID, linecolor=AXIS, zerolinecolor=AXIS),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=SURFACE, bordercolor=AXIS, font=dict(color=INK["primary"])),
        legend=dict(orientation="h", y=1.0, yanchor="bottom", x=0, bgcolor="rgba(0,0,0,0)"),
        title=dict(y=0.98, yanchor="top"),
        margin=dict(l=8, r=8, t=64, b=8),
        colorway=list(COLORS.values()),
    )
)
pio.templates.default = "plotly_dark+oil"

# Status of a signal -> (palette role, icon, label). Colour never travels alone.
SIGNAL_STYLE = {
    "bullish": ("good", "●"),
    "bearish": ("critical", "●"),
    "neutral": ("warning", "●"),
    "NORMAL": ("good", "✓"),
    "WIDE": ("warning", "▲"),
    "NARROW": ("warning", "▼"),
    "ANOMALY": ("critical", "!"),
    "DEFICIT": ("good", "▲"),
    "BALANCED": ("warning", "●"),
    "SURPLUS": ("critical", "▼"),
    "HIGH": ("critical", "!"),
    "MEDIUM": ("warning", "●"),
    "LOW": ("serious", "·"),
}


def badge(status: str, text: str | None = None) -> str:
    role, icon = SIGNAL_STYLE.get(status, ("warning", "●"))
    c = STATUS[role]
    return (f"<span style='display:inline-block;padding:1px 8px;border-radius:10px;border:1px solid {c};"
            f"color:{c};font-size:0.78rem;font-weight:600;white-space:nowrap'>{icon} {text or status}</span>")


# ------------------------------------------------------------------ data access

@st.cache_data(ttl=1800, show_spinner="Refreshing data from EIA / FRED / OilPriceAPI…")
def _auto_refresh() -> dict:
    rep = refresh()
    return {"updated": rep.updated, "errors": rep.errors, "at": pd.Timestamp.now(tz="UTC")}


@st.cache_data(ttl=900, show_spinner="Computing analytics…")
def _context(_stamp: str) -> dict:
    ctx = build_context()
    db.save_alerts(ctx["alerts"])
    return ctx


def get_ctx() -> dict:
    rep = _auto_refresh()
    return _context(str(rep["at"]))


def force_refresh() -> None:
    refresh(force=True)
    _auto_refresh.clear()
    _context.clear()


def keys_configured() -> bool:
    return bool(config.eia_key() and config.fred_key())


# ------------------------------------------------------------------ formatting

def fmt(x, nd: int = 2, sign: bool = False, unit: str = "") -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    s = f"{x:+,.{nd}f}" if sign else f"{x:,.{nd}f}"
    return f"{s}{unit}"


def age(ts) -> str:
    if ts is None or pd.isna(ts):
        return "never"
    ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    secs = (pd.Timestamp.now(tz="UTC") - ts).total_seconds()
    if secs < 3600:
        return f"{int(secs // 60)} min ago"
    if secs < 86400 * 2:
        return f"{int(secs // 3600)} h ago"
    return f"{int(secs // 86400)} days ago"


# ------------------------------------------------------------------ page chrome

def page_header(title: str, ctx: dict, subtitle: str | None = None) -> None:
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)
    for n in config.notices():
        getattr(st, n.get("level", "warning"), st.warning)(n["text"], icon="⚠️")
    if not keys_configured():
        st.error("EIA_API_KEY / FRED_API_KEY are not configured - see README → Configuration. "
                 "Showing whatever is already stored.", icon="🔑")


def freshness_line(ctx: dict) -> str:
    st_ = ctx["staleness"]
    p, w = st_.get("prices", {}), st_.get("weekly", {})
    from oil_tracker.catalysts import next_wpsr

    parts = []
    if p.get("last") is not None:
        parts.append(f"Spot prices to **{p['last']:%a %d %b}**")
    if w.get("last") is not None:
        parts.append(f"EIA weekly: week ending **{w['last']:%d %b}**")
    parts.append(f"Next EIA release **{next_wpsr():%a %d %b %H:%M} ET**")
    return " · ".join(parts)


def sidebar(ctx: dict) -> None:
    with st.sidebar:
        st.markdown("**Data freshness**")
        rep = _auto_refresh()
        st.caption(f"Last refresh check: {age(rep['at'])}")
        for info in ctx["staleness"].values():
            label = info["label"]
            if info["last"] is None:
                st.markdown(f"{badge('ANOMALY', 'missing')} {label}", unsafe_allow_html=True)
            else:
                b = badge("ANOMALY", "stale") if info["stale"] else badge("NORMAL", "fresh")
                st.markdown(f"{b} {label}<br><span style='color:{INK['muted']};font-size:0.8rem'>"
                            f"latest obs {info['last']:%d %b %Y}</span>", unsafe_allow_html=True)
        snap = ctx["snapshot"]
        if not snap.empty:
            st.markdown(f"{badge('NORMAL', 'live')} OilPriceAPI snapshot<br>"
                        f"<span style='color:{INK['muted']};font-size:0.8rem'>quoted {age(snap['quoted_at'].max())}"
                        f"</span>", unsafe_allow_html=True)
        if rep["errors"]:
            st.warning(f"{len(rep['errors'])} source(s) failed - see *Data status*.")
        if st.button("Force refresh", width="stretch"):
            with st.spinner("Refetching all series…"):
                force_refresh()
            st.rerun()
        st.divider()
        st.caption(
            "Free public data (EIA, FRED, OilPriceAPI). For production trading, cross-check with "
            "Bloomberg, LSEG or your broker. **Not investment advice.**"
        )


# ------------------------------------------------------------------ manual data

def manual_editor(name: str, title: str) -> None:
    """Edit one of the analyst-maintained CSVs (see oil_tracker/manual.py)."""
    from oil_tracker import manual

    schema = manual.SCHEMAS[name]
    with st.expander(f"✏️ {title}", expanded=False):
        st.caption(schema["help"])
        df = manual.load(name)
        cfg = {c: st.column_config.DateColumn(format="YYYY-MM-DD") for c, t in schema["columns"].items() if t == "date"}
        edited = st.data_editor(df, num_rows="dynamic", hide_index=True, width="stretch", column_config=cfg,
                                key=f"editor_{name}")
        a, b = st.columns(2)
        if a.button("Save", key=f"save_{name}", width="stretch"):
            path = manual.save(edited, name)
            _context.clear()
            st.success(f"Saved to {path.relative_to(config.ROOT)}. On Streamlit Cloud this lasts until the app "
                       "restarts - download the CSV and commit it to keep it.")
        b.download_button("Download CSV", manual.to_csv(edited, name), file_name=schema["file"],
                          key=f"dl_{name}", width="stretch")

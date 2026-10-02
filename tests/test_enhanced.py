"""Tests for the curve, refining, surprises, OECD, risk and manual-data modules."""

import numpy as np
import pandas as pd
import pytest

from oil_tracker import manual
from oil_tracker.analytics import curve, demand, risk, surprises
from oil_tracker.analytics.fundamentals import monthly_seasonal


# ------------------------------------------------------------------ curve

def test_expiry_rules_match_exchange_calendars():
    # CL Nov-26: 25 Oct 2026 is a Sunday -> Fri 23 Oct -> 3 business days before = Tue 20 Oct.
    assert curve.expiry("wti", pd.Timestamp("2026-11-01")) == pd.Timestamp("2026-10-20")
    # CL Dec-26: 25 Nov 2026 is a Wednesday -> 3 business days before = Fri 20 Nov.
    assert curve.expiry("wti", pd.Timestamp("2026-12-01")) == pd.Timestamp("2026-11-20")
    # BZ Dec-26: last business day of October 2026 = Fri 30 Oct.
    assert curve.expiry("brent", pd.Timestamp("2026-12-01")) == pd.Timestamp("2026-10-30")


def test_front_delivery_rolls_after_expiry():
    assert curve.front_delivery("wti", pd.Timestamp("2026-10-20")) == pd.Timestamp("2026-11-01")
    assert curve.front_delivery("wti", pd.Timestamp("2026-10-21")) == pd.Timestamp("2026-12-01")


def _futures(dates, deliveries, price_fn):
    rows = [{"contract": f"C{d:%y%m}", "delivery": d, "date": t, "close": price_fn(t, i)}
            for t in dates for i, d in enumerate(deliveries)]
    return pd.DataFrame(rows)


def test_generic_curve_and_backwardation():
    dates = pd.bdate_range("2026-09-23", "2026-10-02")
    deliveries = [pd.Timestamp(2026, 11, 1) + pd.DateOffset(months=i) for i in range(13)]
    fut = _futures(dates, deliveries, lambda t, i: 90.0 - i)  # $1 backwardation per month
    gc = curve.generic_curve(fut, "wti")
    assert list(gc.columns[:3]) == ["M1", "M2", "M3"]
    assert (gc["M1"] - gc["M6"] == 5).all()
    s = curve.summary(fut, "wti")
    assert s["structure"] == "STEEP BACKWARDATION" and s["m1_m2"] == pytest.approx(1.0)


def test_generic_curve_drops_dates_missing_the_true_front():
    # On 15 Oct the true front is Nov-26; if only Dec-26 onwards is in the data,
    # the date must be skipped instead of mislabelling Dec as M1.
    dates = [pd.Timestamp("2026-10-15")]
    deliveries = [pd.Timestamp(2026, 12, 1) + pd.DateOffset(months=i) for i in range(6)]
    fut = _futures(dates, deliveries, lambda t, i: 80.0)
    assert curve.generic_curve(fut, "wti").empty


def test_structure_classification():
    assert curve.classify(6) == "STEEP BACKWARDATION"
    assert curve.classify(2) == "BACKWARDATION"
    assert curve.classify(0.5) == "FLAT"
    assert curve.classify(-3) == "CONTANGO"
    assert curve.classify(-7) == "STEEP CONTANGO"


# ------------------------------------------------------------------ refining

def test_crack_spread_formulas():
    idx = pd.bdate_range("2025-01-01", periods=3)
    p = pd.DataFrame({"wti": 70.0, "brent": 74.0, "gas_usgc": 90.0, "gas_nyh": 92.0, "ulsd_usgc": 99.0,
                      "ulsd_nyh": 101.0, "jet_usgc": 95.0}, index=idx)
    c = demand.crack_spreads(p)
    assert c["usgc_321"].iloc[0] == pytest.approx((2 * 90 + 99) / 3 - 70)
    assert c["nyh_321"].iloc[0] == pytest.approx((2 * 92 + 101) / 3 - 74)
    assert c["jet_crack"].iloc[0] == pytest.approx(25.0)


def test_demand_composite_is_neutral_at_seasonal_norm():
    out = demand.demand_composite({"usgc_321": {"z": 0.0}}, {"ps_total": {"z": 0.0}}, {"z": 0.0})
    assert out["score"] == pytest.approx(50) and out["label"] == "NORMAL"


# ------------------------------------------------------------------ surprises

def test_streak_counts_current_run():
    s = pd.Series([1.0, -2.0, 0.5, 1.2, 3.0])
    assert surprises.streak(s) == {"length": 3, "direction": "builds above norm"}
    assert surprises.streak(pd.Series([2.0, -1.0]))["direction"] == "draws below norm"


def test_consensus_surprise_is_actual_minus_expected_in_mbbl():
    idx = pd.date_range("2026-09-04", periods=4, freq="W-FRI")
    weekly = pd.DataFrame({"us_crude": [400, 402, 399, 397.5], "us_gasoline": 200.0, "us_distillates": 110.0}, index=idx)
    cons = pd.DataFrame({"week_ending": [idx[2]], "crude": [-1.0], "gasoline": [np.nan], "distillates": [np.nan],
                         "source": ["test"]})
    cs = surprises.consensus_surprises(weekly, cons)
    row = cs[cs["item"] == "Crude"].iloc[0]
    assert row["actual"] == pytest.approx(-3.0) and row["surprise"] == pytest.approx(-2.0)


# ------------------------------------------------------------------ OECD / risk

def test_monthly_seasonal_uses_same_month_prior_years():
    idx = pd.date_range("2018-01-01", "2026-09-01", freq="MS")
    s = pd.Series(idx.year.astype(float) * 10 + idx.month, index=idx)
    out = monthly_seasonal(s)
    # Sep 2026: mean of Sep 2021..2025 = (2021..2025 mean)*10 + 9 = 20239
    assert out["avg_5y"].iloc[-1] == pytest.approx(20239)


def test_correlations_use_returns_not_levels():
    idx = pd.bdate_range("2024-01-01", periods=400)
    rng = np.random.default_rng(3)
    a = pd.Series(np.linspace(50, 100, 400) * np.exp(rng.normal(0, 0.01, 400)), index=idx)
    b = pd.Series(np.linspace(10, 30, 400) * np.exp(rng.normal(0, 0.01, 400)), index=idx)
    frame = pd.DataFrame({"wti": a, "sp500": b})
    assert frame.corr().iloc[0, 1] > 0.9                    # levels: spurious
    assert abs(risk.correlation_matrix(frame, 3650).iloc[0, 1]) < 0.2  # returns: independent


def test_gauge_percentile():
    s = pd.Series(np.arange(1, 1001, dtype=float), index=pd.bdate_range("2022-01-01", periods=1000))
    g = risk.gauge_summary(s)
    assert g["status"] == "EXTREME" and g["pctile_5y"] > 99


# ------------------------------------------------------------------ manual data

def test_manual_csv_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(manual, "MANUAL_DIR", tmp_path)
    assert manual.load("consensus").empty
    df = pd.DataFrame({"week_ending": [pd.Timestamp("2026-09-25")], "crude": [-1.5], "gasoline": [0.4],
                       "distillates": [-0.8], "source": ["Reuters poll"]})
    manual.save(df, "consensus")
    back = manual.load("consensus")
    assert back.loc[0, "crude"] == -1.5 and back.loc[0, "week_ending"] == pd.Timestamp("2026-09-25")

"""Analytics tests on synthetic data with known answers (no network)."""

import numpy as np
import pandas as pd
import pytest

from oil_tracker.analytics import balance, fundamentals, prices, spreads
from oil_tracker.analytics.backtest import run_backtest
from oil_tracker.analytics.seasonal import seasonal_stats
from oil_tracker.catalysts import eia_wpsr_dates


def weekly_index(years=8, end="2026-09-25"):
    return pd.date_range(end=end, periods=52 * years, freq="W-FRI")


def test_seasonal_avg_uses_only_prior_years():
    idx = weekly_index()
    # Level = year number: the 5Y same-week average for year Y is mean(Y-5..Y-1) = Y-3.
    s = pd.Series(idx.year.astype(float), index=idx)
    out = seasonal_stats(s)
    last = out.iloc[-1]
    assert last["avg"] == pytest.approx(idx[-1].year - 3)
    assert last["min"] == idx[-1].year - 5 and last["max"] == idx[-1].year - 1


def test_seasonal_needs_three_years():
    idx = weekly_index(years=2)
    out = seasonal_stats(pd.Series(1.0, index=idx))
    assert out["avg"].isna().all()


def test_inventory_summary_signals_and_surprise():
    idx = weekly_index()
    # Flat seasonal pattern (+1 per week-of-year cycle reset), then a big draw in the last week.
    rng = np.random.default_rng(0)
    vals = 400 + rng.normal(0, 1, len(idx)).cumsum() * 0.1
    vals[-1] = vals[-2] - 10
    d = fundamentals.inventory_summary(pd.Series(vals, index=idx))
    assert d["signal"] == "DRAW"
    assert d["wow"] == pytest.approx(-10)
    assert d["magnitude"] == "LARGE"
    assert d["surprise"] < -9


def test_spread_stats_and_classification():
    idx = pd.bdate_range("2020-01-01", "2026-09-30")
    s = pd.Series(np.sin(np.arange(len(idx)) / 20), index=idx)
    s.iloc[-1] = 5.0
    st = spreads.spread_stats(s)
    assert st["status"] == "ANOMALY" and st["z_5y"] > 2
    assert spreads.classify(1.2) == "WIDE" and spreads.classify(-1.5) == "NARROW" and spreads.classify(0.3) == "NORMAL"


def test_monthly_spreads_align_on_month_start():
    idx = pd.bdate_range("2025-01-01", "2025-03-31")
    px = pd.DataFrame({"wti": 70.0, "brent": 75.0}, index=idx)
    dubai = pd.Series([72.0, 73.0, 74.0], index=pd.to_datetime(["2025-01-01", "2025-02-01", "2025-03-01"]))
    m = spreads.monthly_spreads(px, dubai)
    assert list(m["brent_dubai"]) == [3.0, 2.0, 1.0]
    assert list(m["wti_dubai"]) == [-2.0, -3.0, -4.0]


def test_momentum_basic():
    idx = pd.bdate_range("2025-01-01", periods=300)
    px = pd.Series(np.linspace(60, 90, 300), index=idx)
    m = prices.momentum(px)
    assert m["last"] == pytest.approx(90) and m["trend"] == "up"
    assert m["high_52w"] == pytest.approx(90) and m["vs_52w_high_pct"] == pytest.approx(0)


def test_technical_levels_bracket_price():
    idx = pd.bdate_range("2025-01-01", periods=200)
    px = pd.Series(80 + 5 * np.sin(np.arange(200) / 8), index=idx)
    lv = prices.technical_levels(px)
    assert lv["support"] < px.iloc[-1] < lv["resistance"]


def _synthetic_market():
    widx = weekly_index()
    rng = np.random.default_rng(1)
    weekly = pd.DataFrame(
        {
            "us_crude": 420 + rng.normal(0, 3, len(widx)).cumsum() * 0.2,
            "us_gasoline": 220 + rng.normal(0, 2, len(widx)),
            "us_distillates": 120 + rng.normal(0, 2, len(widx)),
            "refinery_util": 90 + rng.normal(0, 1.5, len(widx)),
        },
        index=widx,
    )
    didx = pd.bdate_range(widx[0], widx[-1] + pd.Timedelta(days=10))
    wti = 70 + rng.normal(0, 1, len(didx)).cumsum() * 0.3
    px = pd.DataFrame({"wti": wti, "brent": wti + 4 + rng.normal(0, 0.5, len(didx))}, index=didx)
    return weekly, px


def test_score_history_bounds_and_release_dating():
    weekly, px = _synthetic_market()
    h = balance.score_history(weekly, px)
    assert not h.empty
    assert h["score"].between(0, 100).all()
    assert (h.index.dayofweek == 2).all()  # Wednesday release dates
    assert set(h["regime"]) <= {"DEFICIT", "BALANCED", "SURPLUS"}


def test_backtest_no_lookahead_and_costs():
    idx = pd.date_range("2024-01-03", periods=60, freq="W-WED")
    price = pd.Series(np.arange(60, dtype=float), index=idx)  # +1 $/bbl every week
    score = pd.Series(80.0, index=idx)                        # always long
    res, st = run_backtest(score, price, cost_per_trade=0.0)
    assert st["total_pnl"] == pytest.approx(59.0)              # 60 releases -> 59 completed weeks
    res_c, st_c = run_backtest(score, price, cost_per_trade=0.5)
    assert st_c["total_pnl"] == pytest.approx(59.0 - 0.5)      # one entry, never flips


def test_wpsr_holiday_shift():
    # Labor Day 2026 is Mon 7 Sep -> report moves to Thursday 10 Sep.
    dates = eia_wpsr_dates(pd.Timestamp("2026-09-01").date(), pd.Timestamp("2026-09-20").date())
    days = [(d.date().isoformat(), d.strftime("%H:%M")) for d in dates]
    assert ("2026-09-02", "10:30") in days
    assert ("2026-09-10", "11:00") in days
    assert ("2026-09-16", "10:30") in days

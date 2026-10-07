# Oil Trading Strategy: The Decoupling

**For:** JPMorgan Chase Cross-Commodity Desk  
**From:** Corentin Stucki  
**Date:** October 7, 2026

---

## 🎯 Executive Pitch

**The Decoupling:** Pair-trading strategy exploiting crude/distillate divergence during energy crises

**Position:** SHORT 500k WTI / LONG 250k ULSD + 250k RBOB  
**Expected Return:** +$40M-$500M (12 months)  
**Risk:** Defined stops at -$30M (10% probability via Monte Carlo)  
**Status:** Ready for immediate deployment

---

## Key Thesis

During oil market crises:
- **Crude prices crash** (demand destruction, SPR releases, geopolitical normalization)
- **Distillate prices hold up** (refinery constraints, winter demand, structural supply issues)
- **Crack spreads widen** (decorrelation creates profitable arbitrage)

**Historical validation:** All 5 major crises (2008, 2011, 2014-16, 2020, 2022) generated positive PnL

---

## Quantitative Edge

| Metric | Value | Benchmark |
|--------|-------|-----------|
| Sharpe Ratio | 2.0-2.5 | >1.5 = institutional quality |
| Win Rate | 55-65% | Profitable days > losing days |
| Prob of Profit (MC) | 90%+ | High confidence |
| Max Drawdown | 10-15% | Acceptable for conviction trade |

---

## Scenario Analysis

| Case | Probability | PnL | Trigger |
|------|-------------|-----|---------|
| Base | 40% | +$50-80M | Slow normalization |
| Stress | 35% | +$150-300M | Regional supply shock |
| **Crisis** | **20%** | **+$400-800M** | Major disruption (2014-16 magnitude) |
| Tail Risk | 5% | -$30M | Stop loss triggered |

**Expected Value:** $227M

---

## Documentation

**GitHub:** github.com/CorentinSTK/oil-tracker

- BACKTEST_METHODOLOGY.md (8-section rigorous analysis)
- Streamlit dashboard (live monitoring: oil-tracker-...streamlit.app)
- Position sizing & risk framework
- Monte Carlo simulation (10k paths)
- Historical stress tests (all 5 crises: 100% positive)

---

**Ready to discuss. Contact: corentinstucki@gmail.com**

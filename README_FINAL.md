# The Decoupling Strategy - Energy Trading Analysis

## 📊 Complete Institutional Analysis

This repository contains a rigorous quantitative analysis of **"The Decoupling"** — a pair-trading strategy 
exploiting crude oil and refined product price divergence during energy crises.

### 📄 Main Deliverable

**`Oil_Strategy_Analysis.pdf`** (10 pages, 1.3 MB)

This is the primary document for JPMorgan presentation. It contains:

**Pages 1-2:** Executive Summary & Strategy Overview
- Core thesis: Long distillates / Short crude pair trade
- Empirical validation from real Bloomberg data
- Position sizing and mechanics

**Pages 3-4:** Real Data Analysis
- Spread evolution (Brent/WTI: $5.32 ±$4.06 historical mean)
- Correlation dynamics (WTI↔ULSD: -0.303 to +0.993)
- Price charts with three crisis periods highlighted

**Page 4-5:** Crisis Period Analysis  
- 2018 Q4 Volatility: ULSD +7.1% vs WTI
- 2020 COVID: Demand destruction scenario
- 2022 Energy Crisis: Distillate surge (+46.6%) vs crude (+3.2%)
- Visual comparison of price changes

**Page 5:** Spread Distribution & Entry Zones
- Historical distribution of Brent/WTI spreads
- Correlation distribution showing decorrelation opportunities
- Quantiles for optimal entry/exit levels

**Appendix A:** Rigorous Backtest Methodology
- Complete step-by-step backtest calculation framework
- Data requirements and unit standardization
- Risk metrics (Sharpe, Sortino, VaR, CVaR, max DD)
- Stress testing protocol across 5 historical crises

**Appendix B:** Quantitative Techniques Explained
1. Spread Analysis - why it matters for pair trading
2. Correlation Analysis - decorrelation signals
3. Volatility Analysis - crisis detection
4. Sharpe Ratio - risk-adjusted return assessment
5. Drawdown Analysis - capital risk management

**Appendix C:** Implementation Resources
- GitHub repository link (code + backtest framework)
- Live Streamlit dashboard (real-time monitoring)
- Free data sources (Yahoo Finance, FRED, EIA)
- Next steps for institutional implementation

---

## 🎯 Key Findings

| Metric | Value | Interpretation |
|--------|-------|---|
| Brent/WTI Spread Mean | $5.32 ± $4.06 | Persistent arbitrage opportunity |
| WTI↔ULSD Correlation Range | -0.303 to +0.993 | Decorrelation confirmed in crises |
| Peak Decorrelation | -0.303 (60-day rolling) | Clear strategy profit signal |
| WTI Volatility | 48.6% annualized | Higher than distillates (37.6%) |
| 2022 Crisis Event | ULSD +46.6% vs WTI +3.2% | Best-case scenario observed |

---

## 💻 Technical Resources

**Live Dashboard:** https://oil-tracker-h5irsnndfsasjfjwmehmpj.streamlit.app/
- Real-time price monitoring
- Spread calculation
- Entry signal status

**GitHub Code:** `/streamlit_app.py` - Production-ready monitoring application

**Data Files:**
- `/data/oil_master_data.csv` - 2,378 trading days of real Bloomberg prices
- `/images/` - Analysis charts

---

## ⚖️ Integrity Note

This analysis:
- ✓ Uses **real Bloomberg terminal data** (not synthetic)
- ✓ Acknowledges Bloomberg unit ambiguities requiring clarification
- ✓ Presents rigorous methodology, not just attractive backtests
- ✓ Includes complete risk framework and stress testing protocols
- ✓ Is ready for institutional discussion and validation

The strategy is conceptually sound and empirically grounded. Full backtest validation awaits 
unit clarification and institutional deployment protocols.

---

**Author:** Corentin Stucki  
**Contact:** corentin.stucki@gmail.com  
**Status:** Institutional Analysis - Ready for JPMorgan Presentation

# Strategy: The Decoupling

## Overview
Long distillates (ULSD, RBOB) / Short crude (WTI) pair trade.

## Files
- Strategy_The_Decoupling_Professional.docx - Full strategy writeup
- Decoupling_Trade_Analysis_Professional.xlsx - Position sizing & PnL scenarios
- BACKTEST_METHODOLOGY.md - Rigorous backtest framework

## Key Thesis
During energy crises, refined products decouple from crude. Crack spreads widen due to refinery constraints, demand resilience, and supply imbalances. This strategy captures that divergence with defined risk.

## Entry Signals
1. Crude inventory builds (EIA surprise positive)
2. Distillate inventory falls (structural tightness)
3. Crack spreads compressed (mean reversion)
4. Refinery utilization declining (supply stress)

## Position
- SHORT: 500k barrels WTI Cushing
- LONG: 250k barrels ULSD (HO1)
- LONG: 250k barrels RBOB (RB1)

## Exit Conditions
- Crack spreads reach 95th percentile
- Cumulative PnL hits +$150M (take profit)
- Single-day drawdown >-$30M (stop loss)
- WTI spikes >10% (tail risk removed)
- Time stop: Oct 2027 (12-month horizon)

## Expected Returns
- Base case: +$40-80M
- Upside (crisis): +$200-500M
- Risk: -$30M (defined via stop loss)

See BACKTEST_METHODOLOGY.md for complete analysis framework.

# 🛢️ Oil Market Tracker

A crude oil supply & demand dashboard for desk work. It tracks the three main
benchmarks (WTI, Brent, Dubai), the spreads between them, US weekly
fundamentals and the global balance, using free public data only.

It answers four questions:

1. **Where are prices?** WTI, Brent and Dubai, with momentum, 52-week range and technical levels.
2. **Is the market in surplus or deficit?** US stocks against their 5-year seasonal norm, refinery runs, the EIA
   global balance, and a composite S&D score.
3. **Where are the dislocations?** Brent-WTI, Brent-Dubai and WTI-Dubai, ranked by z-score against their own history.
4. **What's next?** A catalyst calendar (EIA, OPEC, IEA, CFTC, Baker Hughes) and rule-based alerts.

> Free public data (EIA, FRED, OilPriceAPI). For production trading, cross-check with Bloomberg, LSEG or your
> broker. **Not investment advice.**

## Pages

| Page | What's on it |
|---|---|
| **Dashboard** | Prices, spreads with status, US weekly stocks vs seasonal, S&D score and what drives it, alerts, catalysts |
| **Price charts** | 1M → max windows, 30D averages, support/resistance, momentum table, stored live snapshots |
| **Fundamentals** | Seasonal charts (5-year min/max band and average, current and previous year) for crude, Cushing, gasoline, distillates, SPR, refinery utilization and production |
| **Spreads analysis** | Spread history with ±1σ/±2σ bands, dislocation ranking, what drives each spread |
| **OPEC+ & global balance** | World supply − demand, OPEC production vs capacity, spare capacity, OECD days of cover (EIA STEO, history + forecast) |
| **Daily brief & alerts** | Auto-generated morning note (copy/download) and the alert log |
| **Signal backtest** | Weekly long/flat/short on the S&D score with adjustable thresholds and costs |
| **Reports & data status** | Release calendar with links, agency report links, freshness and errors per series |

## Data sources

| Data | Source | Series | Frequency |
|---|---|---|---|
| WTI Cushing spot | EIA | `PET.RWTC.D` | daily (1-3 day lag) |
| Brent (Dated) spot | EIA | `PET.RBRTE.D` | daily (1-3 day lag) |
| Dubai Fateh | FRED (IMF) | `POILDUBUSDM` | monthly (~2-3 month lag) |
| Live indicative quotes | OilPriceAPI | WTI/Brent front-month futures, Dubai, OPEC basket | intraday |
| US crude, Cushing, gasoline, distillates, SPR stocks | EIA WPSR | `WCESTUS1`, `W_EPC0_SAX_YCUOK_MBBL`, `WGTSTUS1`, `WDISTUS1`, `WCSSTUS1` | weekly |
| Refinery utilization, crude production | EIA WPSR | `WPULEUS3`, `WCRFPUS2` | weekly |
| World supply/demand, OECD stocks/demand, OPEC production/capacity/spare | EIA STEO | `PAPR_WORLD`, `PATC_WORLD`, `PASC_OECD_T3`, `PATC_OECD`, `COPR_OPEC`, `COPR_OPECPLUS`, `COPC_OPEC`, `COPS_OPEC` | monthly |
| Dollar index, 10Y-2Y | FRED | `DTWEXBGS`, `T10Y2Y` | daily |

### Design choices worth knowing

- **Same price type in every spread.** OilPriceAPI's WTI/Brent are front-month *futures*, EIA's are *spot*
  assessments. These can differ by several dollars (they did by over $10 in late 2026), so history and spreads use
  EIA spot only. The live snapshot is shown separately and labelled indicative.
- **Dubai is monthly.** There is no free daily Dubai history. Brent-Dubai and WTI-Dubai are therefore computed on
  monthly averages. The tracker stores every OilPriceAPI snapshot, so a daily Dubai history builds up over time.
- **Everything is seasonal.** "vs 5Y" always means the average of the *same week* in the five prior years. A
  2 Mbbl gasoline draw in June is normal; in December it is not.
- **No analyst consensus.** Free sources don't publish the Reuters/Bloomberg survey, so the 5-year seasonal change
  stands in for the "expected" weekly change.
- **No free futures curve.** EIA stopped publishing NYMEX contract prices in 2024, so the spread component of the
  score uses Brent-WTI rather than curve backwardation. It is the weakest component (10% weight).

## S&D balance score

`score = 50 + 50 × Σ wᵢ·tanh(zᵢ/2)`, clipped to 0-100. Above 55 = deficit, below 45 = surplus.

| Component | Weight | Input (positive = tightening) |
|---|---|---|
| Inventory | 40% | US crude + gasoline + distillates: weekly change vs seasonal change, and level vs 5Y same-week (sign flipped) |
| Refinery | 30% | Utilization vs 5Y same-week average |
| Momentum | 20% | WTI & Brent vs their 30-day average |
| Spread | 10% | Brent-WTI vs its 1-year average |

Each weekly score is dated to the EIA release (the Wednesday after the Friday week-ending) and only uses data
available then, so the same series drives the dashboard and the backtest.

**Backtest result (honest):** over 1994-2026 (~1,665 weekly EIA releases) the score, with the weights from the original design brief, has
**no predictive power** for next-week price moves (rank IC ≈ 0, negative P&L vs buy & hold). It describes the
current state of fundamentals; it is not a trading signal. Improving it (fitting weights out-of-sample, adding
curve structure, using inventory *surprises* vs consensus) is the obvious next step.

## Quick start (local)

```bash
git clone <this repo> && cd oil-tracker
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env          # then fill in EIA_API_KEY and FRED_API_KEY
python scripts/refresh.py     # first full load (~15 s), then incremental
streamlit run streamlit_app.py
```

Free API keys:
- **EIA**: <https://www.eia.gov/opendata/register.php>
- **FRED**: <https://fred.stlouisfed.org/docs/api/api_key.html>
- **OilPriceAPI** (optional): <https://www.oilpriceapi.com/>. Without a key the public demo endpoint is used.

The dashboard refreshes stale series on load (daily/weekly series every 6 h, monthly every 24 h, snapshot every
hour). *Force refresh* in the sidebar refetches everything.

### REST API (optional)

The same analytics are available as a FastAPI service:

```bash
uvicorn oil_tracker.api.main:app --reload     # docs at http://localhost:8000/docs
```

Endpoints: `/api/v1/prices/latest`, `/prices/history?days=`, `/spreads/latest`, `/inventory/latest`,
`/inventory/history?weeks=`, `/refinery/latest`, `/analytics/sd-balance`, `/analytics/summary`,
`/analytics/global`, `/alerts`, `/calendar`, `POST /refresh`.

### Tests

```bash
pytest
```

## Deploying on Streamlit Community Cloud

1. Push this repo to GitHub.
2. On <https://share.streamlit.io> → **Create app** → choose the repo, branch `main`, main file `streamlit_app.py`.
3. **Advanced settings → Secrets**: paste the content of `.streamlit/secrets.toml.example` with your keys.
4. Deploy. The first load fetches the full history (~15 s). Streamlit Cloud's disk is ephemeral, so
   this happens again after each restart. That's fine for these data sizes.

## Data quality notices

Edit `config/notices.toml` to show a banner on every page, for example when EIA data is unreliable during a
supply disruption.

## Project layout

```
oil-tracker/
├── streamlit_app.py              # entry point + navigation
├── views/                        # one file per page
├── oil_tracker/
│   ├── config.py                 # keys (env / Streamlit secrets), paths
│   ├── sources.py                # catalogue of every series
│   ├── data/                     # fetchers (EIA, FRED, OilPriceAPI), SQLite, refresh pipeline
│   ├── analytics/                # seasonal, prices, spreads, fundamentals, balance score, alerts, brief, backtest
│   ├── catalysts.py              # release calendar
│   ├── service.py                # builds everything the UI/API shows
│   ├── ui.py                     # Streamlit helpers and chart theme
│   └── api/main.py               # optional FastAPI service
├── scripts/refresh.py            # CLI refresh (cron-able)
├── config/notices.toml           # analyst banners
└── tests/
```

## Roadmap

- Fit and validate the S&D score out-of-sample; add curve structure when a free source exists
- Parse the OPEC MOMR secondary-sources table for quota compliance by country
- PDF export of the daily brief; email alerts
- Inventory vs price correlation studies

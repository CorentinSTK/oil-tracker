# 🛢️ Oil Market Tracker

A crude oil supply & demand dashboard for desk work. It tracks the three main
benchmarks (WTI, Brent, Dubai), the spreads between them, US weekly
fundamentals and the global balance, using free public data only.

It answers five questions:

1. **Where are prices?** WTI, Brent and Dubai, with momentum, 52-week range and technical levels.
2. **Is the market in surplus or deficit?** US stocks against their 5-year seasonal norm, refinery runs, the EIA
   global balance, and a composite S&D score.
3. **Where are the dislocations?** Brent-WTI, Brent-Dubai and WTI-Dubai, ranked by z-score against their own history.
4. **What does the curve and the downstream say?** Futures structure, refinery margins, implied demand.
5. **What's next, and what's the risk?** A catalyst calendar, geopolitical risk and volatility gauges, supply
   disruptions, and rule-based alerts.

> Free public data (EIA, FRED, OilPriceAPI). For production trading, cross-check with Bloomberg, LSEG or your
> broker. **Not investment advice.**

## Pages

| Section | Page | What's on it |
|---|---|---|
| Overview | **Dashboard** | Prices, spreads, US weekly stocks vs seasonal, curve structure, OECD stocks, cracks, demand strength, OVX/GPR, S&D score, alerts, catalysts |
| | **Daily brief & alerts** | Auto-generated morning note (copy/download) and the alert log |
| Prices & structure | **Price charts** | 1M → max windows, 30D averages, support/resistance, momentum, stored live snapshots |
| | **Futures curve** | WTI and Brent curves by contract, backwardation/contango, Dec-Dec spread history, futures vs physical spot |
| | **Spreads analysis** | Brent-WTI, Brent-Dubai, WTI-Dubai with ±1σ/±2σ bands, dislocation ranking, drivers |
| US fundamentals | **Inventories & runs** | Seasonal charts (5-year band) for crude, Cushing, gasoline, distillates, SPR, runs, production |
| | **Inventory surprises** | Weekly surprise vs seasonal norm and vs analyst consensus (manual), runs of surprises, release-day price reaction |
| | **Refining & demand** | 3-2-1 and single-product cracks vs seasonal norm, product prices, US implied demand, demand-strength composite |
| Global | **OECD stocks** | OECD commercial stocks and days of forward cover vs 5Y same-month average, US vs rest of OECD, optional IEA overlay |
| | **Global balance** | World supply − demand, OPEC production vs capacity, spare capacity (EIA STEO, history + forecast) |
| | **OPEC+ by country** | Production, capacity, spare by country; quotas and compliance (manual); unplanned supply disruption tracker |
| Risk & research | **Geopolitical risk** | GPR index (daily), OVX, VIX, OVX/VIX ratio, global policy uncertainty |
| | **Correlations** | Return-correlation heatmap (3M-3Y) and rolling correlations: oil × equities, oil × USD, Brent × WTI |
| | **Signal backtest** | Weekly long/flat/short on the S&D score with adjustable thresholds and costs |
| Reference | **Reports & data status** | Release calendar, agency report links, freshness and errors per series |

## Data sources

| Data | Source | Series | Frequency |
|---|---|---|---|
| WTI Cushing, Brent (Dated) spot | EIA | `PET.RWTC.D`, `PET.RBRTE.D` | daily (1-3 day lag) |
| Dubai Fateh | FRED (IMF) | `POILDUBUSDM` | monthly (~2-3 month lag) |
| Live indicative quotes | OilPriceAPI | WTI/Brent front-month futures, Dubai, OPEC basket | intraday |
| WTI and Brent futures by contract | Yahoo Finance (unofficial) | `CL{M}{YY}.NYM`, `BZ{M}{YY}.NYM` | daily, delayed |
| Gasoline, ULSD, jet spot (NYH, USGC) | EIA | `EER_EPMRU_PF4_*`, `EER_EPD2DXL0_PF4_*`, `EER_EPJK_PF4_RGC` | daily |
| US retail gasoline | EIA | `EMM_EPMR_PTE_NUS_DPG` | weekly |
| US stocks (crude, Cushing, gasoline, distillates, SPR) | EIA WPSR | `WCESTUS1`, `W_EPC0_SAX_YCUOK_MBBL`, `WGTSTUS1`, `WDISTUS1`, `WCSSTUS1` | weekly |
| US runs, production, crude imports/exports | EIA WPSR | `WPULEUS3`, `WCRFPUS2`, `WCRIMUS2`, `WCREXUS2` | weekly |
| US implied demand (product supplied) | EIA WPSR | `WRPUPUS2`, `WGFUPUS2`, `WDIUPUS2`, `WKJUPUS2` | weekly |
| World and OECD balance, OECD stocks, China/India demand | EIA STEO | `PAPR_WORLD`, `PATC_WORLD`, `T3_STCHANGE_WORLD`, `PASC_OECD_T3`, `PASC_US`, `PASC_OOECD_T3`, `PATC_OECD`, `PATC_CH`, `PATC_IN` | monthly |
| OPEC+ production, capacity, spare by country | EIA STEO | `COPR_*`, `COPC_*`, `COPS_*`, `PAPR_TC` (UAE liquids) | monthly |
| Unplanned supply disruptions by country | EIA STEO | `PADI_*` | monthly |
| Geopolitical Risk index | Caldara & Iacoviello ([matteoiacoviello.com](https://www.matteoiacoviello.com/gpr.htm)) | `GPRD` (daily), `GPR` (monthly) | daily |
| OVX, VIX, S&P 500, USD, 10Y, 10Y-2Y, policy uncertainty | FRED | `OVXCLS`, `VIXCLS`, `SP500`, `DTWEXBGS`, `DGS10`, `T10Y2Y`, `GEPUCURRENT` | daily / monthly |

### Design choices worth knowing

- **Same price type in every spread.** OilPriceAPI's WTI/Brent are front-month *futures*, EIA's are *spot*
  assessments. In tight markets these differ a lot (Dated Brent was $11 over the front-month future in late 2026),
  so history and spreads use EIA spot only. The live snapshot is shown separately and labelled indicative.
- **Dubai is monthly.** No free daily Dubai history exists. The Dubai spreads use monthly averages. The tracker
  stores every OilPriceAPI snapshot, so a daily Dubai history builds up over time.
- **Everything is seasonal.** "vs 5Y" means the same week (weekly data) or same calendar month (monthly data) in
  the five prior years.
- **Futures curve.** Generic months (M1, M2…) are rebuilt from individual contracts using each exchange's
  expiry rule. A date is kept only if the true front contract is priced. Yahoo drops expired contracts, so the
  generic history builds up from the first run. The Dec-Dec spread has ~2 years of continuous history straight
  away. The EIA stopped publishing NYMEX contract prices in 2024.
- **Inventory surprises in Mbbl, not %.** The EIA does not publish forecasts, and analyst surveys are not free.
  The seasonal norm is the automatic baseline, and analyst consensus can be entered by hand. Percentages of a
  near-zero forecast are meaningless, so surprises are always in barrels.
- **No European or Asian margins.** Rotterdam and Singapore product prices have no free source. NYH vs Brent is
  shown as the Atlantic-basin proxy, and Asia is left out rather than estimated.
- **OPEC by country from the EIA STEO**, not by parsing the OPEC MOMR PDF. It is machine-readable, monthly and
  includes capacity, spare capacity and unplanned outages. The current STEO OPEC total excludes the UAE, so UAE
  is shown as total liquids (`PAPR_TC`) and is not comparable one-for-one.
- **Correlations on returns**, never on price levels. No dual-axis charts: series with different units get
  separate charts.
- **No background scheduler.** Streamlit Cloud apps sleep when idle, so each visit checks freshness instead. EIA
  weekly series refetch as soon as a new Weekly Petroleum Status Report is out (Wed 10:30 ET, holiday-shifted),
  and every 15 minutes if the release is late. `scripts/refresh.py` can go on cron for an always-on deployment.

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

## Manually maintained data

Three things have no free API. They live as CSV files in `data/manual/` and can be edited from the relevant page:

| File | Page | Content |
|---|---|---|
| `consensus.csv` | Inventory surprises | Analyst-survey expected weekly change (Mbbl) for crude, gasoline, distillates |
| `iea_oecd.csv` | OECD stocks | IEA Oil Market Report OECD stocks and days of cover (overlay on the EIA series) |
| `opec_quotas.csv` | OPEC+ by country | OPEC+ required production by STEO country code (enables compliance) |

They ship with headers only. The tracker never invents values. Locally, *Save* writes the file. On Streamlit
Cloud the disk is wiped on restart, so download the CSV and commit it.

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

Endpoints (under `/api/v1`): `/prices/latest`, `/prices/history?days=`, `/spreads/latest`, `/curve`,
`/inventory/latest`, `/inventory/history?weeks=`, `/surprises?weeks=`, `/refinery/latest`, `/refining`, `/oecd`,
`/opec/countries`, `/disruptions`, `/risk`, `/analytics/sd-balance`, `/analytics/summary`, `/analytics/global`,
`/alerts`, `/calendar`, `POST /refresh`.

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
├── streamlit_app.py              # entry point + sectioned navigation
├── views/                        # one file per page
├── oil_tracker/
│   ├── config.py                 # keys (env / Streamlit secrets), paths
│   ├── sources.py                # catalogue of every series (EIA, STEO, FRED, GPR, futures roots)
│   ├── data/                     # fetchers, SQLite storage, incremental parallel refresh
│   ├── analytics/
│   │   ├── seasonal.py           # same-week 5Y comparisons
│   │   ├── prices.py, spreads.py # momentum, levels, inter-benchmark spreads
│   │   ├── curve.py              # generic futures months, backwardation/contango
│   │   ├── fundamentals.py       # US weekly, global balance, OECD stocks
│   │   ├── surprises.py          # inventory surprises and price reaction
│   │   ├── demand.py             # cracks, implied demand, demand composite
│   │   ├── opec.py               # OPEC+ by country, quotas, disruptions
│   │   ├── risk.py               # GPR/OVX/VIX gauges, return correlations
│   │   ├── balance.py, backtest.py, alerts.py, brief.py
│   ├── manual.py                 # analyst-maintained CSVs
│   ├── catalysts.py              # release calendar
│   ├── service.py                # builds everything the UI/API shows
│   ├── ui.py                     # Streamlit helpers and chart theme
│   └── api/main.py               # optional FastAPI service
├── data/manual/                  # consensus, IEA, OPEC+ quota CSVs
├── scripts/refresh.py            # CLI refresh (cron-able)
├── config/notices.toml           # analyst banners
└── tests/
```

## Roadmap

- Fit and validate the S&D score out-of-sample; add curve structure once enough generic-month history is stored
- Test whether extreme readings (e.g. score > 70, steep backwardation) have any forward information
- PDF export of the daily brief; email alerts
- Persist the database somewhere durable for the Streamlit Cloud deployment (it is rebuilt on every restart)

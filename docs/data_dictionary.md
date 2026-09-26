# Data dictionary

## `data/market_history.csv`

| Variable | Meaning | Unit |
|---|---|---|
| `date` | Public market observation date | ISO date |
| `gasoil_10ppm` | Gasoil 10 ppm FOB Arab Gulf mid indication | USD/bbl |
| `ron92` | RON92 FOB Arab Gulf mid indication | USD/bbl |
| `ron95` | RON95 FOB Arab Gulf mid indication | USD/bbl |
| `usd_bdt` | Bangladesh Bank-attributed USD/BDT midpoint | Tk/USD |

Benchmark observations are sparse by design; no missing benchmark observation is syntheticly filled.

## `data/official_prices.csv`

| Variable | Meaning | Unit |
|---|---|---|
| `effective_date` | Date a retail price becomes effective | ISO date |
| `diesel` | Official diesel retail price | Tk/L |
| `petrol` | Official petrol retail price | Tk/L |
| `octane` | Official octane retail price | Tk/L |
| `kerosene` | Official kerosene retail price | Tk/L |
| `source_url` | Public source documenting the price event | URL |
| `source_name` | Source publisher | text |
| `source_tier` | Source type flag | text |

## Derived variables in `model.json`

- `latest_market_value_tk_l`: latest available benchmark × latest aligned FX ÷ barrel litres.
- `market_signal_tk_l`: prior 30-day market-window mean.
- `domestic_calibration_residual_tk_l`: expanding median residual available before the current cutoff.
- `estimated_retail_tk_l`: market signal + calibration.
- `official_reference_tk_l`: latest official event at or before the model cutoff.
- `gap_tk_l`: model estimate − official reference.
- `eligible_backtest_events`: count of official events with sufficient prior market observations.

## Provenance

The model output includes source URLs, coverage dates and research-status fields. `market_update.json` records the source methods and validation status of the current market snapshot.

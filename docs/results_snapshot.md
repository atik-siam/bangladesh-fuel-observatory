# Results snapshot — bundled public-data build

This file describes what the current bundled data support. It is a **snapshot**, not a claim of final predictive performance.

## Coverage

- Market rows: 138 distinct observation dates.
- Gasoil 10 ppm: 138 observations, 2026-01-26 to 2026-09-24.
- RON92: 136 observations, 2026-01-26 to 2026-09-21.
- RON95: 131 observations, 2026-01-26 to 2026-09-14.
- USD/BDT aligned market observations: 138.
- Official Bangladesh price events: 11, 2026-01-01 to 2026-09-21.

## Current model-implied estimates

The current estimates are nowcasts as of each fuel's latest benchmark date. They are not official prices.

The website is the authoritative presentation layer for the exact current numbers in `data/model.json`.

## Backtest evidence

The primary expanding-calibration estimator currently produces 8 valid out-of-sample level predictions per fuel, while the naive previous-official-price reference has 10 valid predictions. The current bundled sample remains below the project's headline threshold for mature regression/uncertainty claims.

The current snapshot is therefore intended to demonstrate the **workflow and evidence discipline** rather than to establish a winning predictive model.

## Interpretation rule

If the primary estimator has larger error than the naive reference in this snapshot, the correct interpretation is simply that the current specification has not demonstrated incremental predictive value in this limited sample. More historical official events and benchmark overlap are needed before selecting a final forecasting specification.

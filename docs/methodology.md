# Bangladesh Fuel Observatory methodology

## 1. Objective

Bangladesh Fuel Observatory is an independent empirical framework for studying the relationship between international refined-product benchmarks, USD/BDT and Bangladesh retail fuel-price events.

It is **not** an official pricing calculator and does not define a normative “fair price”.

## 2. Data

### International product benchmarks

- Diesel → Gasoil 10 ppm FOB Arab Gulf
- Petrol → RON92 FOB Arab Gulf
- Octane → RON95 FOB Arab Gulf

The source archive states that these are indicative, non-binding historical market levels rather than licensed price assessments or commercial offers.

### FX

Historical modeling uses a Bangladesh Bank-attributed daily USD/BDT midpoint series via Fexant. The direct Bangladesh Bank reference-rate page is retained as the preferred current official reference and a health check when the table can be parsed.

### Official price events

`official_prices.csv` stores effective-date retail price events. Each row includes its source URL and source tier. The current bundled history is a curated 2026 event series; adding a new event should be treated as a version-controlled data operation.

## 3. Market-equivalent transformation

\[
M_{t,f}=B_{t,f}\times FX_t / 158.9873
\]

where:

- `B` = benchmark in USD/barrel;
- `FX` = Tk/USD;
- 158.9873 = litres per barrel.

The result is the international benchmark equivalent in Tk/litre.

## 4. Prior market-window signal

For an official event date `t`, the model uses all available benchmark/FX observations satisfying:

\[
t-30\text{ days} \le d < t
\]

The event-day observation is excluded.

The arithmetic mean of those converted observations is the primary market signal. A minimum of four valid observations is required.

This is a reproducible public-data proxy for the prior-period/moving-average concept described in Bangladesh's automatic pricing framework; it is not claimed to reproduce a proprietary government feed.

## 5. Domestic calibration

For an eligible event:

\[
R_t=P_t-M_t
\]

The historical residual is not interpreted as a literal accounting ledger. It is an empirical remainder that can absorb domestic cost, tax, margin, distribution and policy components not separately observed in the public dataset.

### Primary estimator

The current model uses:

\[
\widehat P_t=M_t+\operatorname{median}(R_{1:(t-1)})
\]

where only residuals from earlier eligible events are used.

For the current estimate, the calibration cutoff is **strictly before the latest market benchmark date**. This prevents a same-day official price from calibrating itself when market and official events share a date.

## 6. Validation

### Primary expanding calibration

At each eligible event, the model predicts using the median residual from earlier eligible events. The resulting predictions are compared with the actual official price.

### Naive baseline

The previous official retail price is used as a deliberately simple reference model.

### Pass-through regression

The exploratory regression uses the prior market-window mean and the prior-window mean USD/BDT as predictors:

\[
P_t=\beta_0+\beta_1M_t+\beta_2FX_t+\epsilon_t
\]

It is considered exploratory below 12 eligible events and is never treated as an out-of-sample forecast-performance metric when fitted in-sample.

### Walk-forward regression

A sequence of OLS fits is trained only on earlier eligible events and evaluated on the next event. At least 6 predictions are required before the diagnostic can be reported as reportable by the dashboard; a larger research threshold is still recommended for formal inference.

## 7. Error metrics

- **MAE:** average absolute error in Tk/L.
- **RMSE:** square-root mean squared error; more sensitive to large misses.
- **MAPE:** mean absolute percentage error.
- **Bias / mean error:** average signed prediction error; positive values indicate systematic overestimation and negative values indicate systematic underestimation.

## 8. Benchmark and window robustness

The model output includes sensitivity checks for 14, 30, 45 and 60 calendar-day windows. Window selection is descriptive in the bundled snapshot; a future forecasting study should select any hyperparameter using only a training period and then lock it before testing.

## 9. Uncertainty

Prediction intervals are intentionally withheld until enough out-of-sample predictions exist. The configured minimum is 12 predictions. A point estimate without enough historical residual information is not presented as if its uncertainty were known.

## 10. Causality

The project measures historical association and price transmission. It does not identify causal effects. Policy changes, inventory, freight, taxes, exchange-rate regimes, geopolitical shocks and other omitted variables can all affect the observed relationship.

## 11. Source limitations

The public benchmark archive is an important data limitation because it is an indicative public proxy rather than the licensed commercial assessment described in government pricing documentation. The final research write-up should therefore describe the project as **public-data market-linked estimation**, not as an exact reconstruction of the government's import-price ledger.

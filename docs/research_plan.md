# Research plan

Bangladesh Fuel Observatory is designed as an empirical study of fuel-price transmission, not as a static price calculator.

## Phase 1 — data foundation

1. Collect the full public archive available for Gasoil 10 ppm, RON92 and RON95.
2. Collect a consistent USD/BDT history and document the exact rate definition used.
3. Curate official Bangladesh retail-price revision events with source links.
4. Define a non-leaking calendar alignment rule.
5. Convert USD/bbl to Tk/L.
6. Construct the prior market-window signal.
7. Estimate the domestic calibration state using only earlier eligible events for historical predictions.
8. Add automated data-quality and source-health checks.

## Phase 2 — benchmark and window robustness

Evaluate multiple transparent window definitions (for example 14/30/45/60 days) and alternative public benchmark series where the comparison is conceptually appropriate. Window choice must be evaluated without leaking future information.

## Phase 3 — statistical pass-through

After sufficient official-event overlap exists, evaluate:

- previous-price naive baseline;
- market-window baseline;
- OLS pass-through;
- lagged pass-through;
- robust/regularized regression;
- price-increase vs price-decrease asymmetry;
- structural breaks around policy-regime changes;
- market-price vs FX contribution decomposition.

## Phase 4 — uncertainty and robustness

Use appropriate time-ordered prediction intervals, bootstrap uncertainty where event counts permit, residual diagnostics, sensitivity analysis and benchmark robustness.

## Guardrails

- Never use future official prices to train a past prediction.
- Never fabricate missing benchmark observations.
- Never promote a model because it has a high in-sample R² alone.
- Never call the model output a government price or a universally “fair” price.
- Record source, date, model version and key parameters for every generated snapshot.

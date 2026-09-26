# Model card — Bangladesh Fuel Observatory

**Version:** 4.0  
**Primary use:** transparent market-linked nowcasting and historical price-transmission analysis for Bangladesh fuel prices.

## Outputs

1. International benchmark equivalent (Tk/L)
2. Model-implied retail estimate (Tk/L)
3. Official retail reference (Tk/L)
4. Historical backtest diagnostics
5. Scenario analysis

## Intended use

- research and reproducible analysis;
- educational demonstrations of time-aware modeling;
- market monitoring;
- transparent scenario exploration;
- portfolio demonstration of data engineering + statistics + web deployment.

## Not intended for

- official government pricing;
- commercial trading execution;
- accounting or internal BPC decision-making;
- legal/compliance advice;
- claims that a predicted value is a universal “fair price”.

## Primary estimator

\[
\widehat P_t=M_t+\operatorname{median}(R_{1:(t-1)})
\]

where `M_t` is the prior 30-calendar-day market-window signal and `R` is the historical residual between official retail price and that signal.

## No-lookahead policy

The event-day benchmark is excluded from event windows. Current calibration uses official events strictly before the market cutoff. Historical predictions use only residuals observed before the event being predicted.

## Validation guardrails

- Minimum 4 market observations in a pricing window.
- Minimum 6 eligible events for exploratory pass-through regression.
- Minimum 12 eligible events before regression can be labeled research-ready.
- Minimum 6 walk-forward predictions before that diagnostic can be labeled reportable.
- Minimum 12 walk-forward predictions before empirical prediction intervals are enabled.

These are **project reporting thresholds**, not universal statistical laws.

## Current snapshot

The bundled market history has 138 Gasoil observations, 136 RON92 observations and 131 RON95 observations. The official event dataset has 11 events. Each fuel currently has 9 eligible event windows, but only 3 walk-forward OLS predictions because the regression requires 6 prior training events.

## Current evidence status

The expanding primary estimator is a developing baseline. In the current limited 2026 event sample, the naive previous-official-price reference is numerically more stable than the primary expanding calibration. The project therefore does **not** claim that the primary estimator is superior.

## Known limitations

- public benchmark proxy rather than licensed commercial assessment;
- limited official-event history;
- discrete policy events rather than daily retail observations;
- incomplete public domestic cost breakdown;
- potential regime changes over time;
- association rather than causality.

# Bangladesh Fuel Observatory — Technical Project Overview

## 1. What the project is

**Bangladesh Fuel Observatory (BFO)** is an end-to-end, reproducible data-science and web application for studying how international refined-fuel market observations and the USD/BDT exchange rate relate to Bangladesh retail fuel-price events.

It deliberately separates three quantities that are often mixed together:

1. **International benchmark equivalent** — the selected international refined-product benchmark converted from USD/barrel to Tk/litre.
2. **Model-implied retail estimate** — the prior-period market signal plus an empirically calibrated domestic component.
3. **Official Bangladesh price** — the published retail-price event used as the observed reference.

BFO does **not** claim to calculate a universal or normative “fair price,” reproduce BPC's private accounting, or provide an official government price forecast.

## 2. Research question

> **How do observable international refined-fuel prices and exchange-rate movements translate into Bangladesh retail fuel-price signals, and how closely do transparent specifications track official pricing events?**

This framing makes the project an empirical price-transmission study rather than a simple calculator.

## 3. Fuel-grade mapping

The model uses a grade-specific international public proxy for each Bangladesh fuel category:

| Bangladesh fuel | International benchmark proxy | Quoted unit | Basis |
|---|---|---|---|
| Diesel | Gasoil 10 ppm | USD/bbl | FOB Arab Gulf |
| Petrol | RON92 | USD/bbl | FOB Arab Gulf |
| Octane | RON95 | USD/bbl | FOB Arab Gulf |

The benchmark source used by the project is an indicative public archive. It is retained for reproducibility, but it is not represented as a licensed Platts/Argus assessment, executable quote, or Bangladesh import-cost ledger.

## 4. Data pipeline

The project has two main data streams.

### 4.1 International market stream

The ingestion script retrieves the Gasoil 10 ppm, RON92 and RON95 historical tables and a consistent historical USD/BDT series. It preserves observed benchmark dates instead of filling missing observations with artificial values.

### 4.2 Official-price event stream

The repository stores discrete Bangladesh retail-price events with an effective date, fuel prices, source name, source URL and source tier. These observations are treated as the ground-truth reference for comparison—not as continuously observed daily prices.

### 4.3 Data-quality controls

Before a refreshed market file replaces the existing snapshot, the pipeline checks schema, date order, duplicate dates, non-positive values, minimum series length and the presence of the required benchmark and FX fields. A direct Bangladesh Bank reference-rate page is also retained as a current-source health check.

The refresh workflow is designed to fail closed: a suspiciously short or structurally broken source should stop the update rather than overwrite a previously valid dataset.

## 5. Unit conversion

International benchmark prices are quoted in USD/barrel while Bangladesh retail prices are quoted in taka/litre. BFO converts them using:

\[
\text{MarketValue}_{t,f}=\frac{\text{Benchmark}_{t,f}\times\text{USD/BDT}_t}{158.9873}
\]

where 158.9873 is the litre volume of one petroleum barrel used by the model.

### Example

If a benchmark is 162.6 USD/bbl and the exchange rate is 123.18 Tk/USD:

\[
\frac{162.6\times123.18}{158.9873}\approx125.97	ext{ Tk/L}
\]

This result is the **international benchmark equivalent**. It is not the final Bangladesh retail price because domestic pricing components have not yet been included.

## 6. Prior market-window signal

For an official pricing event at date `t`, the model uses only market observations strictly before the event and inside the previous 30 calendar days. It converts each valid market observation to Tk/litre and takes the arithmetic mean.

This 30-calendar-day window is a transparent reproducible approximation to the prior-period / moving-average idea described in Bangladesh's published automatic-pricing framework. It is not claimed to reproduce BPC's proprietary market feed or internal accounting.

The strict pre-event rule is important because it prevents future observations from leaking into a historical calculation.

## 7. Domestic calibration

For each eligible historical official event:

\[
R_t=P_t-M_t
\]

where `P_t` is the official Bangladesh retail price and `M_t` is the prior market-window signal.

The primary estimator uses the median of residuals from official events strictly before the current market cutoff:

\[
\hat P_t=M_t+\operatorname{median}(R_1,\ldots,R_{t-1})
\]

The median makes the calibration less sensitive to a single unusual event. The residual is a **model component**, not a claim about the exact internal tax, margin, freight, storage, financing, distribution or BPC cost ledger.

## 8. Three numbers on the website

### International benchmark equivalent

Answers:

> **What does the international refined-product benchmark correspond to in Tk/litre at the selected exchange rate?**

### Model-implied retail estimate

Answers:

> **What retail price does the current transparent model imply under its market-window and calibration assumptions?**

This is an independent calibrated nowcast, not an official government price.

### Official Bangladesh price

Answers:

> **What published retail price is observed for Bangladesh?**

For a point-in-time model comparison, the site uses the latest official event known at or before that fuel's market-data cutoff. A later official event is shown separately for current context and is not inserted into the historical nowcast.

## 9. Nowcast versus Scenario Lab

The **Current View** estimates are calibrated nowcasts based on the information available up to each fuel's latest benchmark observation.

The **Scenario Lab** is different: it is a hypothetical sensitivity experiment. A user changes the benchmark and USD/BDT assumptions and sees the resulting benchmark-equivalent value and model-implied retail estimate.

Therefore, a Scenario Lab output such as Tk 170/L means:

> “Under these hypothetical market inputs, the model produces approximately Tk 170/L.”

It does not mean that the government should charge Tk 170/L, nor that it is an official forecast.

## 10. Historical validation

BFO uses time-ordered validation rather than random shuffling. For walk-forward prediction, each historical event can only use information available before that event.

Two reference specifications are retained:

- **Primary:** expanding domestic calibration using the prior market-window signal.
- **Naive:** previous official retail price.

The naive reference is important because a complex model should not be assumed to add value merely because it uses more variables.

## 11. Performance metrics

### MAE

Mean Absolute Error. It measures average absolute error in Tk/litre.

### RMSE

Root Mean Squared Error. It weights larger errors more heavily than MAE.

### MAPE

Mean Absolute Percentage Error. It expresses error relative to the observed price level.

### Bias

Mean signed prediction error. It indicates systematic over- or under-estimation.

The website reports these only when the corresponding sample is large enough under the project's reporting guardrails.

## 12. Why some diagnostics can say “insufficient data”

The international market dataset is daily-like and relatively large, but Bangladesh retail prices are discrete policy events. Statistical sample size is therefore driven largely by the number of **usable official price events**, not by the number of market observations.

BFO uses explicit thresholds so that a regression with a tiny sample is not presented as established evidence. At the current bundled snapshot there are 11 official events, 9 eligible market windows per fuel, and 3 walk-forward OLS predictions per fuel. These counts are displayed transparently.

## 13. Event eligibility

An official event is eligible for the primary event-level analysis when the preceding 30 calendar days contain at least four valid benchmark/FX-derived observations.

The event-audit table exposes:

- official effective date;
- official price;
- number of market observations in the window;
- market-window dates;
- usable/excluded status;
- reason for exclusion;
- source link.

## 14. No-lookahead design

The project has three different clocks:

1. **Source observation date** — when a benchmark value was observed/published.
2. **Model cutoff date** — the latest market observation allowed into a particular nowcast.
3. **Official effective date** — when the Bangladesh retail price took effect.

A later official price event may exist after the model cutoff. BFO keeps it visible as current context but excludes it from the point-in-time comparison.

This is why, for example, Octane can show an official Tk145 reference at the September 14 market cutoff while separately acknowledging a later Tk165 official event effective September 21.

## 15. Source verification and provenance

The website exposes direct verification links for each international benchmark archive. Event-audit rows expose the public report used to document each official price event.

The website also records snapshot refresh time and model generation time. The downloadable CSV/JSON files let a reader reproduce the calculation from the same versioned inputs.

## 16. Automation

The intended production workflow is:

```text
Scheduled GitHub Action
        ↓
Retrieve public market data
        ↓
Validate source structure and coverage
        ↓
Rebuild the model
        ↓
Run tests
        ↓
Publish model.json + model.js
        ↓
Deploy GitHub Pages
```

The browser uses the bundled `model.js` snapshot so the site can run without a browser-side JSON fetch dependency when the HTML is opened locally. On GitHub Pages, the same generated outputs are served as normal web assets.

## 17. Current evidence status

The current bundled dataset supports a complete reproducible workflow, but the official-event sample remains small. The project's regression headline threshold is 12 eligible events, so the current pass-through regressions remain exploratory. Walk-forward OLS predictions are also withheld as headline evidence until at least 6 reportable predictions are available.

The current primary expanding-calibration estimator does not numerically outperform the naive previous-official-price reference in the bundled snapshot. BFO intentionally displays this result rather than hiding it or selecting a preferred model based on the same test sample.

## 18. Research extensions

Once the historical official-event overlap is sufficiently deep, the same repository can support:

- lagged pass-through models;
- price-level and price-change specifications;
- benchmark sensitivity analysis;
- price-rise versus price-fall asymmetry;
- structural-break/regime analysis;
- market versus FX contribution decomposition;
- bootstrap uncertainty;
- empirical prediction intervals;
- regularized models as secondary benchmarks.

These are extensions, not claims already established by the current snapshot.

## 19. What BFO is—and is not

**It is:** an open, reproducible market-linked data product and research framework.

**It is not:** an official Bangladesh government pricing system, a licensed commercial benchmark provider, a normative “fair price” authority, or proof of causal relationships.

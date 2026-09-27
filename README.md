# Bangladesh Fuel Observatory

**A reproducible, market-linked data product for Bangladesh fuel-price analysis.**

Bangladesh Fuel Observatory studies how observable international refined-product market indications and USD/BDT translate into Bangladesh retail fuel-price signals. It keeps three concepts separate:

1. **International benchmark equivalent** — the selected international refined-product benchmark converted from USD/barrel to Tk/litre.
2. **Model-implied retail estimate** — the prior market-window signal plus an empirically calibrated domestic component.
3. **Official retail price** — the published Bangladesh price event stored in the version-controlled event dataset.

The project does **not** define a universal “fair price” and does not claim to reproduce BPC's private accounting.

> **Need the full technical explanation?** See [`docs/PROJECT_OVERVIEW.md`](docs/PROJECT_OVERVIEW.md).

## Research question

> **How do observable international refined-fuel prices and exchange-rate movements translate into Bangladesh retail fuel-price signals, and how closely do transparent specifications track official pricing events?**

## Why this is a statistics/data-engineering project

Bangladesh Fuel Observatory is a pipeline, not a static calculator. It combines:

- historical market-data ingestion;
- grade-specific benchmark mapping;
- USD/barrel → Tk/litre transformation;
- prior-period market windows;
- expanding domestic calibration;
- a naive previous-price baseline;
- exploratory pass-through regression;
- walk-forward validation;
- MAE, RMSE, MAPE and bias;
- event-level eligibility auditing;
- source/provenance metadata;
- automated quality checks;
- GitHub Actions refresh and GitHub Pages deployment.

## Source verification

The website provides direct **Verify benchmark ** links for each international benchmark source and direct verification links for official price events in the audit table. This is intentional: the Observatory transforms public source observations; it does not replace the source of record.

International benchmark archives are **as-available market-indication sources**, not guaranteed daily feeds. The site therefore keeps three dates separate: the source observation date, the model cutoff date, and the latest official Bangladesh price-event date.

The USD/BDT input is documented separately as a Bangladesh Bank-attributed historical series, with the Bangladesh Bank reference-rate page retained as the current official source check.

## Fuel-grade mapping

| Bangladesh fuel | International public proxy | Unit | Basis |
|---|---|---|---|
| Diesel | Gasoil 10 ppm | USD/bbl | FOB Arab Gulf |
| Petrol | RON92 | USD/bbl | FOB Arab Gulf |
| Octane | RON95 | USD/bbl | FOB Arab Gulf |

The public benchmark archives are indicative, non-binding market information. They are not licensed commercial assessments, executable quotes or a government import-cost series.

## Mathematical framework

### 1. International benchmark equivalent

For fuel grade `f` and market date `t`:

\[
\text{MarketValue}_{t,f}=
\frac{\text{Benchmark}_{t,f}\times\text{USD/BDT}_t}{158.9873}
\]

This is a **market-equivalent value**, not a Bangladesh retail price.

### 2. Prior market-window signal

For an official event at date `t`, only observations strictly before `t` and inside the previous **30 calendar days** are used. The model takes their arithmetic mean after conversion to Tk/litre.

The 30-day window is a transparent approximation to the prior-period/moving-average idea in Bangladesh's published automatic-pricing framework. It is not presented as an exact reconstruction of BPC's proprietary feed or internal accounting.

### 3. Domestic calibration

For each eligible official event:

\[
R_t = P_t - M_t
\]

where `P_t` is the official retail price and `M_t` is the prior market-window signal.

The primary current estimator uses the **median of eligible residuals from official events strictly before the current market cutoff**:

\[
\widehat P_t = M_t + \operatorname{median}(R_1,\ldots,R_{t-1})
\]

This is intentionally robust to a single unusual event.

### 4. Historical validation

The primary estimator is evaluated with an expanding, time-ordered procedure. A naive previous-official-price baseline is shown beside it. Pass-through regression is an exploratory diagnostic until at least 12 eligible official events are available, and walk-forward regression is withheld from headline interpretation until its prediction-count threshold is met.

## Current snapshot status

The bundled snapshot was assembled from the public benchmark archive and the Bangladesh Bank-attributed historical USD/BDT series available at preparation time. The current benchmark coverage is:

- Gasoil 10 ppm: **138 observations**
- RON92: **136 observations**
- RON95: **131 observations**
- USD/BDT aligned observations: **138**
- Official Bangladesh price events in the bundled dataset: **11**

The benchmark archives themselves report 138, 136 and 131 published readings and identify them as indicative archive information. See the source pages in the website and `data/README.md`.

The current official-event sample is still below the configured **12-event headline threshold**, so pass-through results remain exploratory and prediction intervals are withheld. This is deliberate rather than a missing-output bug.

## How to run locally

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
# source .venv/bin/activate
pip install -r requirements.txt
python scripts/update_market_data.py
python scripts/build_model.py
pytest -q
python -m http.server 8000
```

Open `http://localhost:8000`.

On Windows, `START_LOCAL.bat` launches a local HTTP server. The bundled `data/model.js` also lets the dashboard open directly from `index.html` without a browser-side `fetch()` dependency.

## GitHub Pages deployment

1. Create an empty GitHub repository.
2. Copy the contents of this folder into the repository.
3. Push to the `main` branch.
4. Enable **Settings → Pages → Source → GitHub Actions**.

Two workflows are included:

- `Update market data` — scheduled data refresh, validation, model rebuild and tests.
- `Deploy website` — GitHub Pages deployment on successful updates/pushes.

The refresh workflow uses the long historical benchmark pages online. It intentionally fails on structural/source-quality problems rather than publishing a suspiciously short dataset.

## Repository structure

```text
bangladesh-fuel-observatory/
├── index.html
├── assets/
│   ├── app.js
│   └── styles.css
├── data/
│   ├── market_history.csv
│   ├── official_prices.csv
│   ├── market_update.json
│   ├── model.json
│   ├── model.js
│   └── README.md
├── scripts/
│   ├── update_market_data.py
│   └── build_model.py
├── analysis/
│   ├── 01_research_pipeline.ipynb
│   └── README.md
├── docs/
│   ├── methodology.md
│   ├── model_card.md
│   ├── data_dictionary.md
│   ├── interpretation.md
│   ├── audit.md
│   ├── results_snapshot.md
│   └── research_plan.md
├── tests/
│   └── test_model.py
└── .github/workflows/
    ├── update-data.yml
    └── pages.yml
```

## What the website means

**Current estimate:** a calibrated nowcast as of each fuel's latest benchmark observation.

**Scenario Lab:** a hypothetical what-if calculation. It is not a forecast and does not state what the government should charge.

**Walk-forward backtest:** a historical simulation in which each prediction uses only information available before the event being predicted.

**Model diagnostics:** a research-status guardrail that prevents tiny samples from being presented as established statistical evidence.

## Limitations

1. The public benchmark archive is a proxy for the international market component and is not a licensed Platts/Argus assessment.
2. Public data do not reveal every domestic tax, margin, freight, storage, financing or distribution component inside the government pricing process.
3. Official prices are discrete policy events, so the effective statistical sample is much smaller than the daily market-data sample.
4. The current bundled official-event history contains 11 events, below the project's headline threshold for regression/uncertainty promotion.
5. RON95 currently has an earlier latest observation than Gasoil/RON92, so its current nowcast cutoff can precede the latest official event. The site displays that explicitly and prevents look-ahead.
6. The model estimates historical association/price transmission and does not establish causality.

## Research roadmap

The repository is intentionally designed to support, after sufficient historical overlap is available:

- longer official-price history;
- exact reconstruction of publicly documented pricing components where parameters are observable;
- lagged pass-through models;
- robust/regularized regression;
- benchmark sensitivity;
- asymmetric price-rise vs price-fall analysis;
- structural-break/regime analysis;
- market-vs-FX contribution decomposition;
- bootstrap uncertainty and prediction intervals.

## License

MIT

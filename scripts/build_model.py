from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONFIG = json.loads((DATA / "config.json").read_text(encoding="utf-8"))
BARREL = float(CONFIG.get("barrel_litres", 158.9873))
WINDOW_DAYS = int(CONFIG.get("policy_window_days", 30))
MIN_WINDOW_OBS = int(CONFIG.get("minimum_window_observations", 4))
EXPLORATORY_MIN_EVENTS = int(CONFIG.get("minimum_exploratory_events", 6))
MODEL_MIN_EVENTS = int(CONFIG.get("minimum_regression_events", 12))
BOOTSTRAP_MIN_EVENTS = int(CONFIG.get("minimum_bootstrap_events", 12))
WALK_FORWARD_MIN_TRAIN = int(CONFIG.get("walk_forward_min_train", 6))
WALK_FORWARD_MIN_REPORTABLE = int(CONFIG.get("walk_forward_min_reportable", 6))

FUEL_BENCHMARK = {"diesel": "gasoil_10ppm", "petrol": "ron92", "octane": "ron95"}
LABELS = {"diesel": "Diesel", "petrol": "Petrol", "octane": "Octane"}
BENCH_LABEL = {
    "gasoil_10ppm": "Gasoil 10 ppm FOB Arab Gulf",
    "ron92": "RON92 FOB Arab Gulf",
    "ron95": "RON95 FOB Arab Gulf",
}


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    market = pd.read_csv(DATA / "market_history.csv", parse_dates=["date"])
    official = pd.read_csv(DATA / "official_prices.csv", parse_dates=["effective_date"])
    market = market.sort_values("date").drop_duplicates("date").reset_index(drop=True)
    official = official.sort_values("effective_date").drop_duplicates("effective_date").reset_index(drop=True)

    req_market = {"date", *FUEL_BENCHMARK.values(), "usd_bdt"}
    req_official = {"effective_date", *LABELS}
    missing_m = req_market - set(market.columns)
    missing_o = req_official - set(official.columns)
    if missing_m:
        raise ValueError(f"market_history.csv missing columns: {sorted(missing_m)}")
    if missing_o:
        raise ValueError(f"official_prices.csv missing columns: {sorted(missing_o)}")

    for column in [*FUEL_BENCHMARK.values(), "usd_bdt"]:
        market[column] = pd.to_numeric(market[column], errors="coerce")
    for column in LABELS:
        official[column] = pd.to_numeric(official[column], errors="coerce")
    return market, official


def market_value_series(frame: pd.DataFrame, benchmark: str) -> pd.Series:
    return frame[benchmark] * frame["usd_bdt"] / BARREL


def window_for_event(
    market: pd.DataFrame,
    benchmark: str,
    event_date: pd.Timestamp,
    days: int = WINDOW_DAYS,
) -> tuple[float | None, int, str | None, str | None, float | None, float | None]:
    left = event_date - pd.Timedelta(days=days)
    subset = market[(market["date"] < event_date) & (market["date"] >= left)].copy()
    subset["market_value"] = market_value_series(subset, benchmark)
    subset = subset.dropna(subset=["market_value", "usd_bdt"])
    n = len(subset)
    start = subset["date"].min().date().isoformat() if n else None
    end = subset["date"].max().date().isoformat() if n else None
    benchmark_mean = float(subset[benchmark].mean()) if n else None
    fx_mean = float(subset["usd_bdt"].mean()) if n else None
    if n < MIN_WINDOW_OBS:
        return None, n, start, end, benchmark_mean, fx_mean
    return float(subset["market_value"].mean()), n, start, end, benchmark_mean, fx_mean


def eligible_events(market: pd.DataFrame, official: pd.DataFrame, fuel: str, days: int = WINDOW_DAYS) -> pd.DataFrame:
    benchmark = FUEL_BENCHMARK[fuel]
    previous_official = None
    rows = []
    for _, event in official.iterrows():
        signal, n, start, end, benchmark_mean, fx_mean = window_for_event(
            market, benchmark, event["effective_date"], days
        )
        official_price = float(event[fuel]) if pd.notna(event[fuel]) else None
        official_change = None if previous_official is None or official_price is None else official_price - previous_official
        eligible = signal is not None and official_price is not None
        reason = "eligible" if eligible else (
            "insufficient_market_window" if n < MIN_WINDOW_OBS else "missing_required_value"
        )
        rows.append(
            {
                "effective_date": event["effective_date"],
                "official_price": official_price,
                "official_change": official_change,
                "market_signal": signal,
                "benchmark_window_usd_bbl": benchmark_mean,
                "fx_window_usd_bdt": fx_mean,
                "window_observations": n,
                "window_start": start,
                "window_end": end,
                "eligible": eligible,
                "eligibility_reason": reason,
            }
        )
        previous_official = official_price

    out = pd.DataFrame(rows)
    out["residual"] = out["official_price"] - out["market_signal"]
    return out


def expanding_primary(events: pd.DataFrame) -> pd.DataFrame:
    e = events.copy()
    e["primary_pred"] = np.nan
    e["naive_pred"] = np.nan
    e["calibration_median"] = np.nan
    prior_residuals: list[float] = []
    prior_official: float | None = None

    for idx, row in e.iterrows():
        if bool(row["eligible"]):
            if prior_residuals:
                median = float(np.median(prior_residuals))
                e.loc[idx, "calibration_median"] = median
                e.loc[idx, "primary_pred"] = float(row["market_signal"]) + median
        if prior_official is not None:
            e.loc[idx, "naive_pred"] = prior_official
        if bool(row["eligible"]) and pd.notna(row["residual"]):
            prior_residuals.append(float(row["residual"]))
        if pd.notna(row["official_price"]):
            prior_official = float(row["official_price"])
    return e


def metrics(actual: pd.Series | np.ndarray, pred: pd.Series | np.ndarray) -> dict:
    d = pd.DataFrame({"actual": actual, "pred": pred}).dropna()
    if d.empty:
        return {"n": 0, "mae_tk_l": None, "rmse_tk_l": None, "mape_pct": None, "mean_error_tk_l": None}
    err = d["pred"] - d["actual"]
    return {
        "n": int(len(d)),
        "mae_tk_l": round(float(err.abs().mean()), 3),
        "rmse_tk_l": round(float(np.sqrt(np.mean(err**2))), 3),
        "mape_pct": round(float((err.abs() / d["actual"].abs()).mean() * 100), 3),
        "mean_error_tk_l": round(float(err.mean()), 3),
    }


def fit_ols(events: pd.DataFrame) -> dict | None:
    d = events.dropna(subset=["market_signal", "fx_window_usd_bdt", "official_price"])
    if len(d) < 3:
        return None
    x1 = d["market_signal"].to_numpy(float)
    x2 = d["fx_window_usd_bdt"].to_numpy(float)
    y = d["official_price"].to_numpy(float)
    X = np.column_stack([np.ones(len(d)), x1, x2])
    coef = np.linalg.lstsq(X, y, rcond=None)[0]
    pred = X @ coef
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = None if ss_tot == 0 else 1 - ss_res / ss_tot
    return {
        "intercept_tk_l": float(coef[0]),
        "market_signal_slope": float(coef[1]),
        "fx_slope_tk_per_tk_usd": float(coef[2]),
        "r2_in_sample": r2,
    }


def regression_diagnostic(events: pd.DataFrame) -> dict:
    d = events[events["eligible"]].dropna(subset=["market_signal", "fx_window_usd_bdt", "official_price"])
    n = len(d)
    if n < EXPLORATORY_MIN_EVENTS:
        return {
            "status": "insufficient_data",
            "n": int(n),
            "minimum_exploratory_events": EXPLORATORY_MIN_EVENTS,
            "minimum_research_events": MODEL_MIN_EVENTS,
        }
    fit = fit_ols(d)
    if fit is None:
        return {"status": "insufficient_data", "n": int(n)}
    return {
        "status": "research_ready" if n >= MODEL_MIN_EVENTS else "exploratory",
        "n": int(n),
        **{k: None if v is None else round(float(v), 6) for k, v in fit.items()},
        "warning": "In-sample diagnostic only; coefficient estimates are not a forecast-performance result.",
    }


def walk_forward_regression(events: pd.DataFrame, min_train: int = WALK_FORWARD_MIN_TRAIN) -> tuple[dict, pd.DataFrame]:
    d = (
        events[events["eligible"]]
        .dropna(subset=["market_signal", "fx_window_usd_bdt", "official_price"])
        .sort_values("effective_date")
        .reset_index(drop=True)
    )
    rows = []
    for i in range(min_train, len(d)):
        fit = fit_ols(d.iloc[:i])
        if fit is None:
            continue
        pred = (
            fit["intercept_tk_l"]
            + fit["market_signal_slope"] * float(d.loc[i, "market_signal"])
            + fit["fx_slope_tk_per_tk_usd"] * float(d.loc[i, "fx_window_usd_bdt"])
        )
        rows.append(
            {
                "date": d.loc[i, "effective_date"],
                "actual": float(d.loc[i, "official_price"]),
                "pred": float(pred),
                "train_n": int(i),
            }
        )
    pred_df = pd.DataFrame(rows)
    n = len(pred_df)
    result = {
        "status": "research_ready" if n >= WALK_FORWARD_MIN_REPORTABLE else "insufficient_data",
        "n": int(n),
        "min_train": int(min_train),
        "minimum_reportable_predictions": int(WALK_FORWARD_MIN_REPORTABLE),
        "metrics": metrics(pred_df["actual"], pred_df["pred"]) if n else metrics(pd.Series(dtype=float), pd.Series(dtype=float)),
        "warning": "Walk-forward predictions are withheld as headline evidence until the configured prediction count is reached.",
    }
    return result, pred_df


def bootstrap_prediction_interval(walk_forward: pd.DataFrame, latest_market_signal: float | None, reps: int = 4000) -> dict:
    if latest_market_signal is None:
        return {"status": "unavailable", "reason": "no current market signal"}
    if len(walk_forward) < BOOTSTRAP_MIN_EVENTS:
        return {
            "status": "insufficient_data",
            "n": int(len(walk_forward)),
            "minimum_required": BOOTSTRAP_MIN_EVENTS,
            "reason": "Not enough out-of-sample predictions to estimate a stable empirical prediction interval.",
        }
    errors = (walk_forward["pred"] - walk_forward["actual"]).to_numpy(float)
    rng = np.random.default_rng(42)
    boot = rng.choice(errors, size=(reps, len(errors)), replace=True)
    correction = np.median(boot, axis=1)
    draws = latest_market_signal + correction
    q = np.quantile(draws, [0.05, 0.5, 0.95])
    return {
        "status": "available",
        "n": int(len(walk_forward)),
        "lower_tk_l": round(float(q[0]), 2),
        "median_tk_l": round(float(q[1]), 2),
        "upper_tk_l": round(float(q[2]), 2),
        "method": "empirical bootstrap of walk-forward errors",
        "coverage": "90% empirical interval",
    }


def window_sensitivity(market: pd.DataFrame, official: pd.DataFrame, fuel: str, windows=(14, 30, 45, 60)) -> list[dict]:
    out = []
    for days in windows:
        events = eligible_events(market, official, fuel, days)
        bt = expanding_primary(events)
        primary = metrics(bt["official_price"], bt["primary_pred"])
        out.append({"window_days": int(days), **primary})
    return out


def benchmark_coverage(market: pd.DataFrame) -> dict:
    out = {}
    for fuel, benchmark in FUEL_BENCHMARK.items():
        subset = market.dropna(subset=[benchmark])
        out[fuel] = {
            "benchmark": benchmark,
            "observations": int(len(subset)),
            "start": subset["date"].min().date().isoformat() if len(subset) else None,
            "latest": subset["date"].max().date().isoformat() if len(subset) else None,
        }
    fx = market.dropna(subset=["usd_bdt"])
    out["usd_bdt"] = {
        "observations": int(len(fx)),
        "start": fx["date"].min().date().isoformat() if len(fx) else None,
        "latest": fx["date"].max().date().isoformat() if len(fx) else None,
    }
    return out


def current_state(market: pd.DataFrame, official: pd.DataFrame, fuel: str) -> dict:
    benchmark = FUEL_BENCHMARK[fuel]
    valid = market.dropna(subset=[benchmark, "usd_bdt"]).copy().sort_values("date")
    if valid.empty:
        return {"status": "unavailable", "reason": "no valid current benchmark/FX pair"}

    latest = valid.iloc[-1]
    cutoff = pd.Timestamp(latest["date"])
    current_event_date = cutoff + pd.Timedelta(days=1)
    signal, n, start, end, benchmark_mean, fx_mean = window_for_event(
        market, benchmark, current_event_date
    )

    # Critical no-lookahead rule: when the latest market cutoff shares the same date as
    # an official price event, that same-day official price is NOT used to calibrate itself.
    calibration_events = eligible_events(market, official, fuel)
    calibration_events = calibration_events[
        calibration_events["effective_date"] < cutoff
    ].copy()
    residuals = calibration_events[calibration_events["eligible"]]["residual"].dropna().to_numpy(float)
    domestic = float(np.median(residuals)) if len(residuals) else None
    estimate = None if signal is None or domestic is None else signal + domestic

    reference = official[official["effective_date"] <= cutoff]
    official_ref = reference.iloc[-1] if not reference.empty else None
    official_overall = official.iloc[-1] if not official.empty else None
    ref_price = None if official_ref is None else float(official_ref[fuel])
    gap = None if estimate is None or ref_price is None else estimate - ref_price

    eligible_all = eligible_events(market, official, fuel)
    primary_bt = expanding_primary(eligible_all)
    wf_result, wf_df = walk_forward_regression(eligible_all)

    change_count = int(
        eligible_all.loc[eligible_all["eligible"] & eligible_all["official_change"].notna() & (eligible_all["official_change"] != 0)].shape[0]
    )

    return {
        "status": "available" if estimate is not None else "unavailable",
        "label": LABELS[fuel],
        "benchmark": benchmark,
        "benchmark_label": BENCH_LABEL[benchmark],
        "model_cutoff_date": cutoff.date().isoformat(),
        "latest_benchmark_usd_bbl": round(float(latest[benchmark]), 4),
        "latest_benchmark_date": cutoff.date().isoformat(),
        "latest_fx_usd_bdt": round(float(latest["usd_bdt"]), 6),
        "latest_market_value_tk_l": round(float(latest[benchmark] * latest["usd_bdt"] / BARREL), 2),
        "market_signal_tk_l": None if signal is None else round(signal, 2),
        "market_signal_benchmark_mean_usd_bbl": None if benchmark_mean is None else round(benchmark_mean, 4),
        "market_signal_fx_mean_usd_bdt": None if fx_mean is None else round(fx_mean, 6),
        "window_observations": int(n),
        "window_start": start,
        "window_end": end,
        "domestic_calibration_residual_tk_l": None if domestic is None else round(domestic, 2),
        "calibration_events": int(len(residuals)),
        "calibration_cutoff_date": (cutoff - pd.Timedelta(days=1)).date().isoformat(),
        "calibration_excludes_same_day_official_event": True,
        "estimated_retail_tk_l": None if estimate is None else round(float(estimate), 2),
        "official_reference_tk_l": ref_price,
        "official_reference_date": None if official_ref is None else official_ref["effective_date"].date().isoformat(),
        "latest_official_overall_tk_l": None if official_overall is None else float(official_overall[fuel]),
        "latest_official_overall_date": None if official_overall is None else official_overall["effective_date"].date().isoformat(),
        "gap_tk_l": None if gap is None else round(float(gap), 2),
        "eligible_backtest_events": int(eligible_all["eligible"].sum()),
        "official_events_total": int(len(official)),
        "official_nonzero_change_events": change_count,
        "estimate_role": "current calibrated nowcast using information available by the market cutoff; not an out-of-sample forecast",
        "regression": regression_diagnostic(eligible_all),
        "walk_forward_regression": wf_result,
        "prediction_interval": bootstrap_prediction_interval(wf_df, signal),
        "event_audit": [
            {
                "date": r.effective_date.date().isoformat(),
                "official_price": float(r.official_price) if pd.notna(r.official_price) else None,
                "window_observations": int(r.window_observations),
                "window_start": r.window_start,
                "window_end": r.window_end,
                "eligible": bool(r.eligible),
                "reason": r.eligibility_reason,
                "source_name": str(official.loc[official["effective_date"] == r.effective_date, "source_name"].iloc[0]) if "source_name" in official.columns and not official.loc[official["effective_date"] == r.effective_date].empty else "",
                "source_url": str(official.loc[official["effective_date"] == r.effective_date, "source_url"].iloc[0]) if "source_url" in official.columns and not official.loc[official["effective_date"] == r.effective_date].empty else "",
            }
            for _, r in eligible_all.iterrows()
        ],
    }, primary_bt, wf_df


def build() -> dict:
    market, official = load_data()
    coverage = benchmark_coverage(market)
    update_meta = {}
    update_path = DATA / "market_update.json"
    if update_path.exists():
        try:
            update_meta = json.loads(update_path.read_text(encoding="utf-8"))
        except Exception:
            update_meta = {}

    result = {
        "schema_version": "4.0",
        "project": {"name": CONFIG.get("project_name", "Bangladesh Fuel Observatory"), "short_name": CONFIG.get("project_short_name", "BFO")},
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_snapshot": {
            "updated_at_utc": update_meta.get("updated_at_utc"),
            "snapshot_type": update_meta.get("snapshot_type", "live_pipeline_output"),
            "sources": update_meta.get("sources", CONFIG.get("sources", {})),
            "fx_method": update_meta.get("fx_method"),
            "market_method": update_meta.get("market_method"),
            "validation": update_meta.get("validation", {}),
        },
        "method": {
            "primary_estimator": "30-calendar-day prior market window + expanding median domestic calibration",
            "policy_window_days": WINDOW_DAYS,
            "minimum_window_observations": MIN_WINDOW_OBS,
            "minimum_exploratory_events": EXPLORATORY_MIN_EVENTS,
            "minimum_regression_events": MODEL_MIN_EVENTS,
            "minimum_bootstrap_events": BOOTSTRAP_MIN_EVENTS,
            "walk_forward_min_train": WALK_FORWARD_MIN_TRAIN,
            "walk_forward_min_reportable": WALK_FORWARD_MIN_REPORTABLE,
            "barrel_litres": BARREL,
            "strict_no_lookahead": True,
            "market_window_aggregation": "arithmetic_mean of valid benchmark-equivalent observations",
            "calibration_excludes_same_day_official_event": True,
            "benchmark_mapping": FUEL_BENCHMARK,
            "causal_interpretation": False,
            "calibration_rule": "Median residual using official events strictly before the current market cutoff; same-day official price is never used to calibrate itself.",
            "interpretation": {
                "international_benchmark_equivalent": "Benchmark × USD/BDT ÷ 158.9873 = Tk/L; market value only, not retail price.",
                "model_implied_retail": "Prior market-window signal + expanding empirical domestic calibration; independent nowcast, not official price.",
                "official_retail": "Latest official event at or before the model market cutoff; the latest overall official event is retained separately for context.",
                "fair_price_claim": False,
            },
        },
        "data_coverage": {
            "market_rows": int(len(market)),
            "market_start": market["date"].min().date().isoformat() if len(market) else None,
            "market_end": market["date"].max().date().isoformat() if len(market) else None,
            "official_events": int(len(official)),
            "official_start": official["effective_date"].min().date().isoformat() if len(official) else None,
            "official_end": official["effective_date"].max().date().isoformat() if len(official) else None,
            "by_series": coverage,
        },
        "fuels": {},
        "history": [],
        "official_history": [],
        "backtest": {},
        "backtest_history": {},
        "window_sensitivity": {},
    }

    for _, row in market.iterrows():
        item = {
            "date": row.date.date().isoformat(),
            "usd_bdt": None if pd.isna(row.usd_bdt) else round(float(row.usd_bdt), 6),
        }
        for fuel, benchmark in FUEL_BENCHMARK.items():
            item[f"{fuel}_benchmark"] = None if pd.isna(row[benchmark]) else round(float(row[benchmark]), 4)
            item[f"{fuel}_market_value"] = (
                None if pd.isna(row[benchmark]) or pd.isna(row.usd_bdt)
                else round(float(row[benchmark] * row.usd_bdt / BARREL), 4)
            )
        result["history"].append(item)

    for _, row in official.iterrows():
        result["official_history"].append(
            {
                "date": row.effective_date.date().isoformat(),
                "diesel": float(row.diesel),
                "petrol": float(row.petrol),
                "octane": float(row.octane),
                "source_name": str(row.get("source_name", "")),
                "source_url": str(row.get("source_url", "")),
                "source_tier": str(row.get("source_tier", "secondary_reported_official")),
            }
        )

    for fuel in FUEL_BENCHMARK:
        current, primary_bt, wf_df = current_state(market, official, fuel)
        result["fuels"][fuel] = current
        result["backtest"][fuel] = {
            "primary_expanding_calibration": metrics(primary_bt["official_price"], primary_bt["primary_pred"]),
            "naive_previous_official": metrics(primary_bt["official_price"], primary_bt["naive_pred"]),
            "walk_forward_regression": current["walk_forward_regression"]["metrics"],
        }
        result["backtest_history"][fuel] = [
            {
                "date": r.effective_date.date().isoformat(),
                "official": float(r.official_price) if pd.notna(r.official_price) else None,
                "primary": None if pd.isna(r.primary_pred) else round(float(r.primary_pred), 2),
                "naive": None if pd.isna(r.naive_pred) else round(float(r.naive_pred), 2),
                "eligible": bool(r.eligible),
                "window_observations": int(r.window_observations),
                "reason": r.eligibility_reason,
            }
            for _, r in primary_bt.iterrows()
        ]
        result["window_sensitivity"][fuel] = window_sensitivity(market, official, fuel)

    result["research_status"] = {
        "level": "developing",
        "headline_regression_threshold": MODEL_MIN_EVENTS,
        "official_events_total": int(len(official)),
        "eligible_events_by_fuel": {fuel: int(result["fuels"][fuel]["eligible_backtest_events"]) for fuel in FUEL_BENCHMARK},
        "walk_forward_predictions_by_fuel": {fuel: int(result["fuels"][fuel]["walk_forward_regression"]["n"]) for fuel in FUEL_BENCHMARK},
        "primary_vs_naive": {
            fuel: {
                "primary_mae_tk_l": result["backtest"][fuel]["primary_expanding_calibration"]["mae_tk_l"],
                "naive_mae_tk_l": result["backtest"][fuel]["naive_previous_official"]["mae_tk_l"],
                "primary_mae_relation": (
                    "lower" if result["backtest"][fuel]["primary_expanding_calibration"]["mae_tk_l"] < result["backtest"][fuel]["naive_previous_official"]["mae_tk_l"]
                    else "higher" if result["backtest"][fuel]["primary_expanding_calibration"]["mae_tk_l"] > result["backtest"][fuel]["naive_previous_official"]["mae_tk_l"]
                    else "equal"
                ),
            } for fuel in FUEL_BENCHMARK
        },
        "interpretation": "The bundled source snapshot supports a reproducible research workflow but still has fewer official-event observations than the configured headline threshold. Statistics below that threshold are shown as exploratory or withheld. The primary specification is evaluated against a naive previous-official-price reference rather than assumed to be superior.",
    }
    return result


def main() -> None:
    result = build()
    (DATA / "model.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (DATA / "model.js").write_text(
        "window.BANGLADESH_FUEL_OBSERVATORY_MODEL = " + json.dumps(result, separators=(",", ":")) + ";",
        encoding="utf-8",
    )
    print(json.dumps(result["research_status"], indent=2))


if __name__ == "__main__":
    main()

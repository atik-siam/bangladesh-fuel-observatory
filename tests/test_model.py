from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def load_model():
    return json.loads((ROOT / "data" / "model.json").read_text(encoding="utf-8"))


def test_config_and_mapping():
    cfg = json.loads((ROOT / "data" / "config.json").read_text(encoding="utf-8"))
    assert cfg["schema_version"] == "4.0"
    assert cfg["policy_window_days"] == 30
    assert cfg["minimum_window_observations"] >= 4
    assert cfg["minimum_regression_events"] >= 10
    assert cfg["benchmark_mapping"] == {
        "diesel": "gasoil_10ppm",
        "petrol": "ron92",
        "octane": "ron95",
    }


def test_market_snapshot_quality_and_history_depth():
    market = pd.read_csv(ROOT / "data" / "market_history.csv", parse_dates=["date"])
    assert market["date"].is_monotonic_increasing
    assert market["date"].duplicated().sum() == 0
    for column in ["gasoil_10ppm", "ron92", "ron95", "usd_bdt"]:
        values = market[column].dropna()
        assert len(values) >= 60
        assert (values > 0).all()
    assert market["date"].min().date().isoformat() == "2026-01-26"


def test_model_snapshot_schema():
    model = load_model()
    assert model["schema_version"] == "4.0"
    assert model["method"]["strict_no_lookahead"] is True
    assert "backtest_history" in model
    assert "official_history" in model
    assert "research_status" in model
    for fuel in ["diesel", "petrol", "octane"]:
        assert fuel in model["fuels"]
        f = model["fuels"][fuel]
        assert f["benchmark_label"]
        assert f["official_reference_date"] is None or f["official_reference_date"] <= f["model_cutoff_date"]
        assert f["calibration_cutoff_date"] < f["model_cutoff_date"]
        assert f["calibration_excludes_same_day_official_event"] is True
        assert "regression" in f
        assert "walk_forward_regression" in f
        assert "event_audit" in f


def test_current_estimate_arithmetic():
    model = load_model()
    for fuel in ["diesel", "petrol", "octane"]:
        f = model["fuels"][fuel]
        if f["market_signal_tk_l"] is not None and f["domestic_calibration_residual_tk_l"] is not None:
            expected = round(f["market_signal_tk_l"] + f["domestic_calibration_residual_tk_l"], 2)
            assert abs(f["estimated_retail_tk_l"] - expected) <= 0.02


def test_no_lookahead_in_backtest_rows():
    model = load_model()
    for fuel in ["diesel", "petrol", "octane"]:
        rows = model["backtest_history"][fuel]
        eligible_dates = [r["date"] for r in rows if r["eligible"]]
        for i, row in enumerate(rows):
            if row["primary"] is not None:
                assert row["date"] in eligible_dates
                prior = eligible_dates[: eligible_dates.index(row["date"])]
                assert prior, "a primary prediction must have at least one earlier eligible event"


def test_source_metadata():
    update = json.loads((ROOT / "data" / "market_update.json").read_text(encoding="utf-8"))
    assert update["schema_version"] == "5.1"
    assert update["validation"]["status"] == "passed"
    assert "bangladesh_bank_current_check" in update
    assert update.get("fx_retrieval_mode") in {"fexant_live", "validated_snapshot_fallback"}
    for key in ["gasoil_10ppm", "ron92", "ron95"]:
        assert key in update["sources"]

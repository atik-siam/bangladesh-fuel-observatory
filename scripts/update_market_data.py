from __future__ import annotations

import io
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONFIG = json.loads((DATA / "config.json").read_text(encoding="utf-8"))
HEADERS = {
    "User-Agent": "Bangladesh-Fuel-Observatory/5.0 (+https://github.com/)",
    "Cache-Control": "no-cache, no-store, max-age=0",
    "Pragma": "no-cache",
}

URLS = CONFIG["sources"]
SERIES = ("gasoil_10ppm", "ron92", "ron95")
MIN_OBS = int(CONFIG.get("minimum_market_observations_per_series", 60))


def _cache_bust(url: str) -> str:
    """Append a harmless cache-busting query parameter for source retrieval only."""
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["bfo_refresh"] = str(int(time.time()))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def get(url: str) -> str:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = requests.get(_cache_bust(url), timeout=45, headers=HEADERS)
            response.raise_for_status()
            if not response.text.strip():
                raise RuntimeError("Source returned an empty response")
            return response.text
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to retrieve source after 3 attempts: {last_error}") from last_error


def _flat_columns(df: pd.DataFrame) -> list[str]:
    names = []
    for column in df.columns:
        if isinstance(column, tuple):
            parts = [str(x).strip() for x in column if str(x).strip().lower() not in {"nan", "none"}]
            names.append(" ".join(parts).strip().lower())
        else:
            names.append(str(column).strip().lower())
    return names


def parse_alghaf(url: str, column: str) -> pd.DataFrame:
    """Parse the largest Date/Mid table from an Alghaf archive page.

    The source page can expose different table views (for example, a recent
    window plus the full archive). Selecting the largest valid table prevents
    the ingestion job from accidentally freezing at a shorter view.
    """
    tables = pd.read_html(io.StringIO(get(url)))
    candidates: list[pd.DataFrame] = []
    for frame in tables:
        columns = _flat_columns(frame)
        date_col = next((c for c in columns if c == "date" or c.startswith("date ")), None)
        mid_col = next((c for c in columns if c == "mid" or c.startswith("mid ")), None)
        if date_col is None or mid_col is None:
            continue
        frame = frame.copy()
        frame.columns = columns
        frame["date"] = pd.to_datetime(frame[date_col], errors="coerce", dayfirst=False)
        frame[column] = pd.to_numeric(frame[mid_col], errors="coerce")
        out = frame[["date", column]].dropna().drop_duplicates("date").sort_values("date")
        if not out.empty:
            candidates.append(out.reset_index(drop=True))
    if not candidates:
        raise RuntimeError(f"Could not find Date/Mid table at {url}")
    return max(candidates, key=len).reset_index(drop=True)


def parse_bangladesh_bank_fx(url: str) -> pd.DataFrame:
    """Parse the visible Bangladesh Bank 05:00 PM reference table when available.

    This is used as a current-source health check. Historical modeling uses the
    consistent Bangladesh Bank-attributed daily midpoint series from Fexant.
    """
    tables = pd.read_html(io.StringIO(get(url)))
    for frame in tables:
        columns = _flat_columns(frame)
        date_col = next((c for c in columns if c == "date" or c.startswith("date ")), None)
        evening_col = next((c for c in columns if "05:00 pm" in c), None)
        if date_col is None or evening_col is None:
            continue
        frame = frame.copy()
        frame.columns = columns
        frame["date"] = pd.to_datetime(frame[date_col], errors="coerce", dayfirst=False)
        frame["usd_bdt"] = pd.to_numeric(frame[evening_col], errors="coerce")
        out = frame[["date", "usd_bdt"]].dropna().drop_duplicates("date").sort_values("date")
        if not out.empty:
            return out.reset_index(drop=True)
    raise RuntimeError(f"Could not find Bangladesh Bank 05:00 PM USD/BDT table at {url}")


def parse_fexant_fx(url: str) -> pd.DataFrame:
    tables = pd.read_html(io.StringIO(get(url)))
    candidates: list[pd.DataFrame] = []
    for frame in tables:
        columns = _flat_columns(frame)
        date_col = next((c for c in columns if c == "date" or c.startswith("date ")), None)
        mid_col = next((c for c in columns if c in {"mid", "mid rate", "middle"} or c.startswith("mid ")), None)
        buy_col = next((c for c in columns if "buy" in c), None)
        sell_col = next((c for c in columns if "sell" in c), None)
        if date_col is None or (mid_col is None and not (buy_col and sell_col)):
            continue
        frame = frame.copy()
        frame.columns = columns
        frame["date"] = pd.to_datetime(frame[date_col], errors="coerce", dayfirst=False)
        if mid_col:
            frame["usd_bdt"] = pd.to_numeric(frame[mid_col], errors="coerce")
        else:
            frame["usd_bdt"] = (
                pd.to_numeric(frame[buy_col], errors="coerce")
                + pd.to_numeric(frame[sell_col], errors="coerce")
            ) / 2
        out = frame[["date", "usd_bdt"]].dropna().drop_duplicates("date").sort_values("date")
        if not out.empty:
            candidates.append(out)
    if not candidates:
        raise RuntimeError(f"Could not find a historical USD/BDT table at {url}")
    return max(candidates, key=len).reset_index(drop=True)


def validate_market(df: pd.DataFrame) -> dict:
    required = {"date", *SERIES, "usd_bdt"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Market dataset missing columns: {sorted(missing)}")
    if df.empty:
        raise ValueError("Market dataset is empty")
    if df["date"].duplicated().any():
        raise ValueError("Duplicate market dates detected")
    if not df["date"].is_monotonic_increasing:
        raise ValueError("Market dates are not sorted")

    for column in [*SERIES, "usd_bdt"]:
        values = pd.to_numeric(df[column], errors="coerce")
        if (values.dropna() <= 0).any():
            raise ValueError(f"Non-positive value detected in {column}")

    coverage = {}
    for column in SERIES:
        subset = df.dropna(subset=[column])
        count = len(subset)
        if count < MIN_OBS:
            raise ValueError(f"{column} has only {count} observations; minimum required is {MIN_OBS}")
        coverage[column] = {
            "observations": int(count),
            "start": subset["date"].min().date().isoformat(),
            "latest": subset["date"].max().date().isoformat(),
        }

    fx = df.dropna(subset=["usd_bdt"])
    if len(fx) < MIN_OBS:
        raise ValueError(f"usd_bdt has only {len(fx)} observations; minimum required is {MIN_OBS}")
    coverage["usd_bdt"] = {
        "observations": int(len(fx)),
        "start": fx["date"].min().date().isoformat(),
        "latest": fx["date"].max().date().isoformat(),
    }
    return coverage


def atomic_write_csv(df: pd.DataFrame, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False, float_format="%.6f")
    tmp.replace(path)


def validate_refresh_against_previous(new_df: pd.DataFrame, old_path: Path) -> None:
    """Prevent a refresh from publishing an older/truncated benchmark history."""
    if not old_path.exists():
        return
    old = pd.read_csv(old_path, parse_dates=["date"])
    old_latest = {c: old.loc[old[c].notna(), "date"].max() for c in SERIES}
    for column in SERIES:
        new_series = new_df.dropna(subset=[column])
        if new_series.empty:
            raise ValueError(f"Refresh produced no observations for {column}")
        new_latest = new_series["date"].max()
        if pd.notna(old_latest.get(column)) and new_latest < old_latest[column]:
            raise ValueError(
                f"Refresh regression for {column}: latest observation moved backward "
                f"from {old_latest[column].date()} to {new_latest.date()}"
            )


def main() -> None:
    market_frames = [parse_alghaf(URLS[key], key) for key in SERIES]
    fx = parse_fexant_fx(URLS["usd_bdt_history_mirror"])

    merged = market_frames[0]
    for frame in market_frames[1:]:
        merged = merged.merge(frame, on="date", how="outer")
    merged = merged.sort_values("date").reset_index(drop=True)
    fx = fx.sort_values("date").reset_index(drop=True)

    # Model history uses a single, consistent Bangladesh Bank-attributed midpoint source.
    merged = pd.merge_asof(merged, fx, on="date", direction="backward")
    merged = merged.sort_values("date").reset_index(drop=True)

    validate_refresh_against_previous(merged, DATA / "market_history.csv")
    coverage = validate_market(merged)
    now = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
    freshness = {
        key: None if not meta["latest"] else int((now - pd.Timestamp(meta["latest"])).days)
        for key, meta in coverage.items()
    }

    bb_check = {"status": "not_run", "message": "Direct Bangladesh Bank current-table parser was not required for historical modeling."}
    try:
        direct = parse_bangladesh_bank_fx(URLS["usd_bdt_current"])
        latest_direct = direct.iloc[-1]
        latest_hist = fx.iloc[-1]
        bb_check = {
            "status": "available",
            "direct_date": latest_direct["date"].date().isoformat(),
            "direct_05pm_tk_usd": round(float(latest_direct["usd_bdt"]), 4),
            "historical_mid_date": latest_hist["date"].date().isoformat(),
            "historical_mid_tk_usd": round(float(latest_hist["usd_bdt"]), 4),
            "difference_tk_per_usd": round(float(latest_hist["usd_bdt"] - latest_direct["usd_bdt"]), 4)
            if latest_hist["date"].date() == latest_direct["date"].date() else None,
        }
    except Exception as exc:  # health-check failure must not destroy a valid historical refresh
        bb_check = {"status": "unavailable", "message": str(exc)}

    merged["date"] = merged["date"].dt.strftime("%Y-%m-%d")
    meta = {
        "schema_version": "5.0",
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "market_rows": int(len(merged)),
        "coverage": coverage,
        "freshness_days": freshness,
        "sources": URLS,
        "fx_method": "Bangladesh Bank-attributed historical daily midpoint via Fexant; direct Bangladesh Bank 05:00 PM table retained as a current-reference health check.",
        "market_method": "Alghaf Marine public APAG archive mid observations; the ingestion job selects the largest valid Date/Mid table, bypasses intermediary caches, and retains sparse source dates without synthetic benchmark values.",
        "validation": {
            "minimum_observations_per_series": MIN_OBS,
            "status": "passed",
        },
        "bangladesh_bank_current_check": bb_check,
    }

    atomic_write_csv(merged, DATA / "market_history.csv")
    (DATA / "market_update.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()

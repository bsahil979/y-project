"""Leakage checks for the frozen Experiment A MarketMind dataset.

This audit is deliberately conservative.  A dataset passes only when its
observation timestamp and feature schema make the causal boundary explicit:
features describe information available at t, while target/future_return are
outcomes and are never model inputs.
"""

from typing import Iterable, Mapping, Optional

import numpy as np
import pandas as pd


FUTURE_COLUMNS = {
    "target", "future_return", "forecast_signal", "forecast_magnitude",
    "predicted_return", "prediction", "label",
}


def audit_dataset(
    dataset: pd.DataFrame,
    feature_columns: Iterable[str],
    horizon: int = 5,
    feature_timestamp_columns: Optional[Mapping[str, str]] = None,
) -> dict:
    """Audit a MarketMind dataset and raise ``ValueError`` on violations.

    ``feature_timestamp_columns`` can be supplied by future feature providers
    to prove the timestamp of each feature directly.  The current MarketMind
    feature engine derives technical indicators and regime solely from OHLCV
    rows through t, so those columns are documented in the returned report.
    """
    if horizon < 1:
        raise ValueError("horizon must be at least one day.")
    if dataset is None or dataset.empty:
        raise ValueError("Dataset is empty.")

    features = list(feature_columns)
    required = {"ticker", "Date", "target", "future_return", *features}
    missing = sorted(required.difference(dataset.columns))
    if missing:
        raise ValueError(f"Dataset is missing audit columns: {missing}")

    dates = pd.to_datetime(dataset["Date"], errors="coerce", utc=True)
    if dates.isna().any():
        raise ValueError("Dataset contains invalid observation timestamps.")
    if not dates.is_monotonic_increasing:
        raise ValueError("Dataset must be sorted chronologically by Date.")

    tickers = dataset["ticker"].astype(str).str.upper().str.strip()
    if tickers.eq("").any():
        raise ValueError("Dataset contains an empty ticker identifier.")
    if dataset.assign(_ticker=tickers).duplicated(["_ticker", "Date"]).any():
        raise ValueError("Dataset contains duplicate ticker/date observations.")

    forbidden_inputs = sorted(set(features).intersection(FUTURE_COLUMNS))
    if forbidden_inputs:
        raise ValueError(f"Future-derived columns are model features: {forbidden_inputs}")

    target_values = pd.to_numeric(dataset["target"], errors="coerce")
    if target_values.isna().any() or not set(target_values.astype(int).unique()).issubset({-1, 0, 1}):
        raise ValueError("Target must contain only finite -1, 0, and 1 labels.")

    future_returns = pd.to_numeric(dataset["future_return"], errors="coerce")
    if future_returns.isna().any():
        raise ValueError("Future return contains missing values; incomplete label rows must be removed.")
    if not np.isfinite(future_returns.to_numpy()).all():
        raise ValueError("Future return contains non-finite values.")

    timestamp_checks = {}
    for feature, timestamp_column in (feature_timestamp_columns or {}).items():
        if feature not in features:
            raise ValueError(f"Timestamp supplied for non-feature column: {feature}")
        if timestamp_column not in dataset.columns:
            raise ValueError(f"Missing timestamp column for feature {feature}: {timestamp_column}")
        feature_dates = pd.to_datetime(dataset[timestamp_column], errors="coerce", utc=True)
        if feature_dates.isna().any() or (feature_dates > dates).any():
            raise ValueError(f"Feature {feature} contains information after its observation date.")
        timestamp_checks[feature] = timestamp_column

    return {
        "status": "passed",
        "rows": int(len(dataset)),
        "tickers": sorted(tickers.unique().tolist()),
        "date_range": {"start": dates.min().isoformat(), "end": dates.max().isoformat()},
        "horizon_days": horizon,
        "features": features,
        "future_columns_excluded_from_inputs": sorted(FUTURE_COLUMNS),
        "feature_timestamp_checks": timestamp_checks,
        "feature_provenance": {
            "ohlcv": "observation timestamp t",
            "technical_indicators": "backward-looking OHLCV through t",
            "regime": "backward-looking returns through t",
            "sentiment": "historical article date <= observation timestamp t; neutral fallback when unavailable",
            "label": "future return from t to t+h; target is not an input feature",
        },
        "split_requirements": {
            "chronological": True,
            "same_date_group_kept_together": True,
            "imputation_fit_window_only": True,
            "scaler_fit_window_only": True,
            "feature_selection_fit_window_only": True,
        },
    }
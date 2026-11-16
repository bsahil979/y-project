"""Replay TimesFM forecasts at historical cutoffs against a last-close baseline.

This is a chronological inference check. TimesFM's pretraining cutoff is not verified,
so these dates must not be described as an untouched model holdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from services.forecaster import get_price_forecast


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "MSFT": ROOT / "models" / "forecast_v2" / "MSFT" / "prices.csv",
    "RELIANCE.NS": ROOT / "research" / "regime_data_v1" / "prices.csv",
}


def evaluate(ticker: str, path: Path, horizon: int, max_origins: int, stride: int):
    frame = pd.read_csv(path, parse_dates=["Date"]).set_index("Date")
    prices = frame[ticker].dropna().astype(float).sort_index()
    if len(prices) < 512 + horizon + max_origins * stride:
        raise ValueError(f"Not enough prices for {ticker}")
    last_origin = len(prices) - horizon - 1
    origins = list(range(last_origin - (max_origins - 1) * stride, last_origin + 1, stride))
    rows = []
    for origin in origins:
        context = prices.iloc[:origin + 1]
        actual = prices.iloc[origin + 1:origin + 1 + horizon].to_numpy(dtype=float)
        output = get_price_forecast(context, horizon=horizon, return_metadata=True)
        if output["model"] != "TimesFM 2.5":
            raise RuntimeError(f"{ticker} {context.index[-1].date()}: TimesFM unavailable; {output['model']}: {output.get('fallback_reason')}")
        predicted = np.array([item["predicted_price"] for item in output["forecast"]], dtype=float)
        if len(predicted) != horizon or not np.isfinite(predicted).all():
            raise ValueError(f"Invalid forecast for {ticker} at {context.index[-1].date()}")
        spot = float(context.iloc[-1])
        rows.append({
            "ticker": ticker,
            "origin": str(context.index[-1].date()),
            "last_actual": str(prices.index[origin + horizon].date()),
            "spot": spot,
            "actual_terminal": float(actual[-1]),
            "predicted_terminal": float(predicted[-1]),
            "model_mae_pct_of_spot": float(np.mean(np.abs(predicted - actual)) / spot * 100),
            "baseline_mae_pct_of_spot": float(np.mean(np.abs(spot - actual)) / spot * 100),
            "model_terminal_direction_correct": bool(np.sign(predicted[-1] - spot) == np.sign(actual[-1] - spot)),
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon", type=int, default=30)
    parser.add_argument("--max-origins", type=int, default=12)
    parser.add_argument("--stride", type=int, default=21)
    parser.add_argument("--output", type=Path, default=ROOT / "evaluations" / "timesfm_replay_2026-11-04.json")
    args = parser.parse_args()
    if not 1 <= args.horizon <= 60 or args.max_origins < 1 or args.stride < 1:
        parser.error("horizon must be 1–60; origins and stride must be positive")
    rows = []
    sources = {}
    for ticker, path in SOURCES.items():
        sources[ticker] = {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        rows.extend(evaluate(ticker, path, args.horizon, args.max_origins, args.stride))
    summary = {}
    for ticker in [*SOURCES, "ALL"]:
        subset = [row for row in rows if ticker == "ALL" or row["ticker"] == ticker]
        summary[ticker] = {
            "origins": len(subset),
            "model_mean_mae_pct_of_spot": float(np.mean([row["model_mae_pct_of_spot"] for row in subset])),
            "baseline_mean_mae_pct_of_spot": float(np.mean([row["baseline_mae_pct_of_spot"] for row in subset])),
            "model_better_origins": sum(row["model_mae_pct_of_spot"] < row["baseline_mae_pct_of_spot"] for row in subset),
            "terminal_direction_accuracy": float(np.mean([row["model_terminal_direction_correct"] for row in subset])),
        }
    report = {
        "method": "chronological historical replay of serving-time TimesFM versus unchanged last close",
        "limitation": "TimesFM pretraining cutoff is unverified; these dates are not an untouched model holdout. Two chosen symbols and overlapping forecast windows are not enough to establish general predictive skill.",
        "horizon_sessions": args.horizon,
        "stride_sessions": args.stride,
        "sources": sources,
        "summary": summary,
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

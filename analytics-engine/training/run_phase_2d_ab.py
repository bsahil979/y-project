"""Run the frozen Phase 2D MarketMind A/B experiment without rebuilding data."""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from trading_engine.meta_model import FEATURE_COLUMNS, MarketMindMetaModel
from training.marketmind_pytorch import (attach_ticker_metadata, chronological_split,
                                         load_ticker_metadata, train_experiment_b)


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_PATH = os.path.join(PROJECT_ROOT, "models", "meta_model", "meta_dataset.csv")
OUTPUT_DIRECTORY = os.path.join(PROJECT_ROOT, "models", "phase_2d")
TEST_SIZE = 0.2
SEED = 42
B_EPOCHS = 25
B_BATCH_SIZE = 256
B_LEARNING_RATE = 0.001


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    if not os.path.isfile(DATASET_PATH):
        raise FileNotFoundError(f"Frozen Phase 2C.3 dataset not found: {DATASET_PATH}")

    dataset = pd.read_csv(DATASET_PATH)
    required_columns = {"Date", "ticker", "target", *FEATURE_COLUMNS}
    missing_columns = sorted(required_columns.difference(dataset.columns))
    if missing_columns:
        raise ValueError(f"Frozen dataset is missing required columns: {missing_columns}")
    train_frame, holdout_frame = chronological_split(dataset, TEST_SIZE)
    if set(train_frame["ticker"].str.upper()) != set(holdout_frame["ticker"].str.upper()):
        raise ValueError("Frozen chronological split does not retain identical ticker coverage.")

    os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
    experiment_a_directory = os.path.join(OUTPUT_DIRECTORY, "experiment_a")
    experiment_b_directory = os.path.join(OUTPUT_DIRECTORY, "experiment_b")

    experiment_a = MarketMindMetaModel(model_dir=experiment_a_directory)
    experiment_a_result = experiment_a.train(dataset, test_size=TEST_SIZE, random_state=SEED)

    experiment_b_dataset = attach_ticker_metadata(dataset, load_ticker_metadata())
    experiment_b_result = train_experiment_b(
        experiment_b_dataset,
        FEATURE_COLUMNS,
        experiment_b_directory,
        test_size=TEST_SIZE,
        epochs=B_EPOCHS,
        batch_size=B_BATCH_SIZE,
        learning_rate=B_LEARNING_RATE,
        seed=SEED,
    )

    report = {
        "phase": "2D",
        "status": "completed",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_identity": {
            "path": DATASET_PATH,
            "rows": int(len(dataset)),
            "sha256": file_sha256(DATASET_PATH),
            "feature_columns": FEATURE_COLUMNS,
        },
        "split": {
            "method": "chronological_final_block_by_unique_date",
            "test_size": TEST_SIZE,
            "train_rows": int(len(train_frame)),
            "holdout_rows": int(len(holdout_frame)),
            "train_end": str(train_frame["Date"].iloc[-1]),
            "holdout_start": str(holdout_frame["Date"].iloc[0]),
            "train_tickers": int(train_frame["ticker"].nunique()),
            "holdout_tickers": int(holdout_frame["ticker"].nunique()),
        },
        "experiment_a": {
            "implementation": "existing_sklearn_baseline",
            "seed": SEED,
            "output_directory": experiment_a_directory,
            "result": experiment_a_result,
        },
        "experiment_b": {
            "implementation": "existing_pytorch_embedding_model",
            "seed": SEED,
            "epochs": B_EPOCHS,
            "batch_size": B_BATCH_SIZE,
            "learning_rate": B_LEARNING_RATE,
            "output_directory": experiment_b_directory,
            "result": experiment_b_result["config"],
        },
        "not_evaluated_in_frozen_run": {
            "classification": [
                "balanced_accuracy", "per_class_precision", "per_class_recall",
            ],
            "calibration": ["brier_score", "expected_calibration_error"],
            "trading": ["net_return", "sharpe", "maximum_drawdown", "turnover", "transaction_costs"],
            "breakdowns": ["market", "sector", "ticker", "market_regime"],
            "reason": "Neither existing frozen training implementation emits predictions/probabilities or trading backtest outputs for these metrics.",
        },
    }
    report_path = os.path.join(OUTPUT_DIRECTORY, "phase_2d_ab_report.json")
    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    print(json.dumps({
        "report": report_path,
        "dataset_sha256": report["dataset_identity"]["sha256"],
        "experiment_a": experiment_a_result["metrics"],
        "experiment_b": experiment_b_result["metrics"],
    }, indent=2))


if __name__ == "__main__":
    main()
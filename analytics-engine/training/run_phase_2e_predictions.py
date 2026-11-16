
"""Phase 2E.1: preserve aligned predictions from the fixed Phase 2D artifacts."""

import hashlib
import json
import os
import pickle
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from trading_engine.meta_model import FEATURE_COLUMNS
from training.marketmind_pytorch import (INDEX_TO_CLASS, MarketMindDataset, MarketMindMLP,
                                         MarketMindMappings, attach_ticker_metadata,
                                         chronological_split, load_ticker_metadata,
                                         predict_probabilities)


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_PATH = os.path.join(PROJECT_ROOT, "models", "meta_model", "meta_dataset.csv")
PHASE_2D_REPORT_PATH = os.path.join(PROJECT_ROOT, "models", "phase_2d", "phase_2d_ab_report.json")
A_DIRECTORY = os.path.join(PROJECT_ROOT, "models", "phase_2d", "experiment_a")
B_DIRECTORY = os.path.join(PROJECT_ROOT, "models", "phase_2d", "experiment_b")
OUTPUT_DIRECTORY = os.path.join(PROJECT_ROOT, "models", "phase_2e")
PREDICTION_COLUMNS = [
    "ticker", "Date", "actual_target", "A_prediction", "A_prob_-1", "A_prob_0", "A_prob_1",
    "B_prediction", "B_prob_-1", "B_prob_0", "B_prob_1", "market", "sector", "regime_code",
    "future_return",
]
PROBABILITY_COLUMNS = ["A_prob_-1", "A_prob_0", "A_prob_1", "B_prob_-1", "B_prob_0", "B_prob_1"]


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def assert_probability_matrix(probabilities, model_name):
    probabilities = np.asarray(probabilities, dtype=float)
    if probabilities.ndim != 2 or probabilities.shape[1] != 3:
        raise ValueError(f"{model_name} probabilities must have exactly three class columns.")
    if not np.isfinite(probabilities).all() or (probabilities < 0).any():
        raise ValueError(f"{model_name} contains missing, non-finite, or negative probabilities.")
    if not np.allclose(probabilities.sum(axis=1), 1.0, rtol=0.0, atol=1e-6):
        raise ValueError(f"{model_name} probabilities do not sum to 1 within tolerance.")


def assert_prediction_frame(frame, expected_rows):
    if list(frame.columns) != PREDICTION_COLUMNS:
        raise ValueError("Prediction output schema does not match the frozen Phase 2E.1 schema.")
    if len(frame) != expected_rows or frame.duplicated(["ticker", "Date"]).any():
        raise ValueError("Prediction output must contain one unique ticker/Date row per holdout observation.")
    if frame["actual_target"].isna().any() or not set(frame["actual_target"].astype(int)).issubset({-1, 0, 1}):
        raise ValueError("Prediction output contains missing or invalid actual targets.")
    if frame[["A_prediction", "B_prediction"]].isna().any().any():
        raise ValueError("Prediction output contains missing model predictions.")
    assert_probability_matrix(frame[["A_prob_-1", "A_prob_0", "A_prob_1"]].to_numpy(), "A")
    assert_probability_matrix(frame[["B_prob_-1", "B_prob_0", "B_prob_1"]].to_numpy(), "B")


def main():
    phase_2d = load_json(PHASE_2D_REPORT_PATH)
    dataset_hash = file_sha256(DATASET_PATH)
    if dataset_hash != phase_2d["dataset_identity"]["sha256"]:
        raise ValueError("Frozen dataset hash differs from the accepted Phase 2D dataset hash.")
    dataset = pd.read_csv(DATASET_PATH)
    required = {"Date", "ticker", "target", "future_return", *FEATURE_COLUMNS}
    missing = sorted(required.difference(dataset.columns))
    if missing:
        raise ValueError(f"Frozen dataset is missing Phase 2E columns: {missing}")

    train_frame, holdout = chronological_split(dataset, phase_2d["split"]["test_size"])
    split = phase_2d["split"]
    if (len(train_frame) != split["train_rows"] or len(holdout) != split["holdout_rows"]
            or str(train_frame["Date"].iloc[-1]) != split["train_end"]
            or str(holdout["Date"].iloc[0]) != split["holdout_start"]):
        raise ValueError("Reconstructed holdout boundaries differ from Phase 2D.")
    if holdout.duplicated(["ticker", "Date"]).any():
        raise ValueError("Frozen holdout contains duplicate ticker/Date observations.")
    holdout_keys = holdout[["ticker", "Date"]].reset_index(drop=True)

    a_features = load_json(os.path.join(A_DIRECTORY, "feature_columns.json"))
    b_features = load_json(os.path.join(B_DIRECTORY, "feature_columns.json"))
    if a_features != FEATURE_COLUMNS or b_features != FEATURE_COLUMNS:
        raise ValueError("Phase 2D artifact feature schema differs from the frozen feature schema.")
    with open(os.path.join(A_DIRECTORY, "meta_model.pkl"), "rb") as file:
        model_a = pickle.load(file)
    # Phase 2D A did not serialize its training medians. Recreate them only from
    # the fixed training block, never from holdout values, exactly as A trained.
    a_fill_values = train_frame[FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan).median().fillna(0.0)
    a_probabilities = model_a.predict_proba(
        holdout[FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan).fillna(a_fill_values)
    )
    a_classes = [int(value) for value in model_a.classes_]
    if a_classes != [0, 1, 2]:
        raise ValueError(f"A model class order is unexpected: {a_classes}")
    assert_probability_matrix(a_probabilities, "A")

    b_config = load_json(os.path.join(B_DIRECTORY, "model_config.json"))
    b_dates = b_config["metrics"]["date_range"]
    if (b_config["metrics"]["rows"] != len(dataset)
            or b_config["metrics"]["test_size"] != phase_2d["split"]["test_size"]
            or b_dates["train_end"] != split["train_end"]
            or b_dates["test_start"] != split["holdout_start"]):
        raise ValueError("Persisted B artifact split metadata differs from Phase 2D.")
    mappings = MarketMindMappings.load(B_DIRECTORY)
    b_holdout = attach_ticker_metadata(holdout, load_ticker_metadata())
    b_keys = b_holdout[["ticker", "Date"]].reset_index(drop=True)
    if len(b_holdout) != len(holdout) or not b_keys.equals(holdout_keys):
        raise ValueError("A and B holdout ticker/Date keys differ.")
    if not b_holdout["target"].reset_index(drop=True).equals(holdout["target"].reset_index(drop=True)):
        raise ValueError("A and B holdout actual targets differ.")
    b_dataset = MarketMindDataset(b_holdout, FEATURE_COLUMNS, mappings, b_config["numeric_imputation"])
    model_b = MarketMindMLP(len(FEATURE_COLUMNS), len(mappings.ticker_to_index),
                             len(mappings.market_to_index), len(mappings.sector_to_index))
    model_b.load_state_dict(torch.load(os.path.join(B_DIRECTORY, "marketmind_b.pt"), map_location="cpu", weights_only=True))
    b_probabilities = predict_probabilities(model_b, {
        "numeric": b_dataset.numeric, "ticker_id": b_dataset.ticker_id,
        "market_id": b_dataset.market_id, "sector_id": b_dataset.sector_id,
    }).cpu().numpy()
    assert_probability_matrix(b_probabilities, "B")

    output = b_holdout[["ticker", "Date", "target", "market", "sector", "regime_code", "future_return"]].copy()
    output = output.rename(columns={"target": "actual_target"})
    output["A_prediction"] = np.asarray(a_classes)[a_probabilities.argmax(axis=1)] - 1
    output[["A_prob_-1", "A_prob_0", "A_prob_1"]] = a_probabilities
    output["B_prediction"] = [INDEX_TO_CLASS[int(index)] for index in b_probabilities.argmax(axis=1)]
    output[["B_prob_-1", "B_prob_0", "B_prob_1"]] = b_probabilities
    output = output[PREDICTION_COLUMNS]
    assert_prediction_frame(output, len(holdout))

    prediction_path = os.path.join(OUTPUT_DIRECTORY, "holdout_predictions.csv")
    manifest_path = os.path.join(OUTPUT_DIRECTORY, "phase_2e_prediction_manifest.json")
    if os.path.exists(prediction_path) or os.path.exists(manifest_path):
        raise FileExistsError("Phase 2E.1 outputs already exist and are frozen; refusing to overwrite them.")
    os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
    temp_path = prediction_path + ".tmp"
    output.to_csv(temp_path, index=False)
    os.replace(temp_path, prediction_path)
    manifest = {
        "phase": "2E.1", "status": "completed", "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": {"path": DATASET_PATH, "sha256": dataset_hash, "rows": int(len(dataset))},
        "phase_2d_report": {"path": PHASE_2D_REPORT_PATH, "sha256": file_sha256(PHASE_2D_REPORT_PATH)},
        "artifacts": {
            "A_model": {"path": os.path.join(A_DIRECTORY, "meta_model.pkl"), "sha256": file_sha256(os.path.join(A_DIRECTORY, "meta_model.pkl"))},
            "B_model": {"path": os.path.join(B_DIRECTORY, "marketmind_b.pt"), "sha256": file_sha256(os.path.join(B_DIRECTORY, "marketmind_b.pt"))},
        },
        "split": {"train_end": split["train_end"], "holdout_start": split["holdout_start"], "holdout_rows": int(len(holdout)), "holdout_tickers": int(holdout["ticker"].nunique())},
        "feature_schema": FEATURE_COLUMNS, "prediction_column_schema": PREDICTION_COLUMNS,
        "prediction_file": {"path": prediction_path, "sha256": file_sha256(prediction_path), "rows": int(len(output)), "unique_ticker_date_keys": int(len(output))},
        "preprocessing": {"A": "training-block median imputation reconstructed from the fixed Phase 2D train block; medians were not serialized by A", "B": "persisted numeric imputation and categorical mappings"},
        "evaluation_only_columns": ["future_return"],
        "assertions": {"aligned_a_b_rows": True, "matching_ticker_date_keys": True, "no_duplicate_ticker_date": True, "matching_actual_targets": True, "probabilities_sum_to_one": True},
    }
    with open(manifest_path, "w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2)
    print(json.dumps({"prediction_file": prediction_path, "manifest": manifest_path, "rows": len(output)}, indent=2))


if __name__ == "__main__":
    main()
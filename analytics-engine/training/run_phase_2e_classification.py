"""Phase 2E.2: evaluation-only classification analysis of frozen predictions."""

import hashlib
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, confusion_matrix,
                             f1_score, precision_recall_fscore_support)


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PHASE_2E_DIRECTORY = os.path.join(ROOT, "models", "phase_2e")
PREDICTION_PATH = os.path.join(PHASE_2E_DIRECTORY, "holdout_predictions.csv")
PREDICTION_MANIFEST_PATH = os.path.join(PHASE_2E_DIRECTORY, "phase_2e_prediction_manifest.json")
REPORT_PATH = os.path.join(PHASE_2E_DIRECTORY, "phase_2e_classification_report.json")
LABELS = [-1, 0, 1]
LABEL_NAMES = ["SELL", "HOLD", "BUY"]
MODEL_COLUMNS = {
    "A": {"prediction": "A_prediction", "probabilities": ["A_prob_-1", "A_prob_0", "A_prob_1"]},
    "B": {"prediction": "B_prediction", "probabilities": ["B_prob_-1", "B_prob_0", "B_prob_1"]},
}


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finite_or_none(value):
    return float(value) if np.isfinite(value) else None


def evaluate(frame, model_name):
    """Calculate fixed-label classification metrics from already frozen outputs."""
    actual = frame["actual_target"].astype(int)
    predicted = frame[MODEL_COLUMNS[model_name]["prediction"]].astype(int)
    probabilities = frame[MODEL_COLUMNS[model_name]["probabilities"]].to_numpy(dtype=float)
    precision, recall, f1_values, support = precision_recall_fscore_support(
        actual, predicted, labels=LABELS, zero_division=0,
    )
    predicted_counts = predicted.value_counts().reindex(LABELS, fill_value=0)
    actual_counts = actual.value_counts().reindex(LABELS, fill_value=0)
    confidence = probabilities.max(axis=1)
    correct = predicted.to_numpy() == actual.to_numpy()
    return {
        "rows": int(len(frame)),
        "accuracy": float(accuracy_score(actual, predicted)),
        "balanced_accuracy": float(balanced_accuracy_score(actual, predicted)),
        "macro_f1": float(f1_score(actual, predicted, labels=LABELS, average="macro", zero_division=0)),
        "per_class": {
            name: {"precision": float(precision[index]), "recall": float(recall[index]),
                   "f1": float(f1_values[index]), "support": int(support[index])}
            for index, name in enumerate(LABEL_NAMES)
        },
        "confusion_matrix": {
            "labels": LABEL_NAMES,
            "actual_rows_predicted_columns": confusion_matrix(actual, predicted, labels=LABELS).tolist(),
        },
        "predicted_class_distribution": {
            name: {"count": int(predicted_counts[label]), "share": float(predicted_counts[label] / len(frame))}
            for label, name in zip(LABELS, LABEL_NAMES)
        },
        "actual_class_distribution": {
            name: {"count": int(actual_counts[label]), "share": float(actual_counts[label] / len(frame))}
            for label, name in zip(LABELS, LABEL_NAMES)
        },
        "confidence_by_correctness": {
            "correct_rows": int(correct.sum()), "incorrect_rows": int((~correct).sum()),
            "mean_confidence_correct": finite_or_none(confidence[correct].mean()) if correct.any() else None,
            "mean_confidence_incorrect": finite_or_none(confidence[~correct].mean()) if (~correct).any() else None,
            "mean_confidence_all": float(confidence.mean()),
        },
    }


def deltas(a, b):
    return {
        "accuracy": b["accuracy"] - a["accuracy"],
        "balanced_accuracy": b["balanced_accuracy"] - a["balanced_accuracy"],
        "macro_f1": b["macro_f1"] - a["macro_f1"],
        "per_class": {
            label: {metric: b["per_class"][label][metric] - a["per_class"][label][metric]
                    for metric in ("precision", "recall", "f1")}
            for label in LABEL_NAMES
        },
        "confidence_by_correctness": {
            metric: b["confidence_by_correctness"][metric] - a["confidence_by_correctness"][metric]
            for metric in ("mean_confidence_correct", "mean_confidence_incorrect", "mean_confidence_all")
            if a["confidence_by_correctness"][metric] is not None and b["confidence_by_correctness"][metric] is not None
        },
    }


def segmented_evaluation(frame, column):
    result = {}
    for value, segment in frame.groupby(column, sort=True, dropna=False):
        key = "__MISSING__" if pd.isna(value) else str(value)
        a = evaluate(segment, "A")
        b = evaluate(segment, "B")
        result[key] = {"A": a, "B": b, "B_minus_A": deltas(a, b)}
    return result


def main():
    if not os.path.exists(PREDICTION_PATH) or not os.path.exists(PREDICTION_MANIFEST_PATH):
        raise FileNotFoundError("Frozen Phase 2E.1 prediction CSV and manifest are required.")
    if os.path.exists(REPORT_PATH):
        raise FileExistsError("Phase 2E.2 report already exists and is frozen; refusing to overwrite it.")
    with open(PREDICTION_MANIFEST_PATH, encoding="utf-8") as file:
        manifest = json.load(file)
    prediction_hash = sha256(PREDICTION_PATH)
    if prediction_hash != manifest["prediction_file"]["sha256"]:
        raise ValueError("Frozen Phase 2E.1 prediction CSV hash differs from its manifest.")
    frame = pd.read_csv(PREDICTION_PATH)
    if len(frame) != manifest["prediction_file"]["rows"] or frame.duplicated(["ticker", "Date"]).any():
        raise ValueError("Frozen prediction CSV row count or ticker/Date uniqueness check failed.")
    if list(frame.columns) != manifest["prediction_column_schema"]:
        raise ValueError("Frozen prediction CSV schema differs from its manifest.")
    required = {"actual_target", "market", "sector", "ticker", "regime_code"}
    required.update(item for config in MODEL_COLUMNS.values() for item in [config["prediction"], *config["probabilities"]])
    if required.difference(frame.columns):
        raise ValueError("Frozen prediction CSV lacks required classification fields.")
    if not set(frame["actual_target"]).issubset(LABELS):
        raise ValueError("Frozen prediction CSV has invalid actual target values.")
    for model in MODEL_COLUMNS:
        if not set(frame[MODEL_COLUMNS[model]["prediction"]]).issubset(LABELS):
            raise ValueError(f"Frozen prediction CSV has invalid {model} predictions.")

    aggregate_a = evaluate(frame, "A")
    aggregate_b = evaluate(frame, "B")
    report = {
        "phase": "2E.2", "status": "completed", "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_mode": "prediction_artifact_only",
        "input": {"prediction_csv_path": PREDICTION_PATH, "prediction_csv_sha256": prediction_hash,
                  "prediction_manifest_path": PREDICTION_MANIFEST_PATH,
                  "prediction_manifest_sha256": sha256(PREDICTION_MANIFEST_PATH)},
        "constraints": {"models_loaded": False, "models_retrained": False, "dataset_loaded": False,
                        "thresholds_changed": False, "resampling_performed": False,
                        "future_return_used_as_input": False},
        "label_order": {"-1": "SELL", "0": "HOLD", "1": "BUY"},
        "aggregate": {"A": aggregate_a, "B": aggregate_b, "B_minus_A": deltas(aggregate_a, aggregate_b)},
        "segments": {
            "market": segmented_evaluation(frame, "market"),
            "sector": segmented_evaluation(frame, "sector"),
            "ticker": segmented_evaluation(frame, "ticker"),
            "regime_code": segmented_evaluation(frame, "regime_code"),
        },
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, allow_nan=False)
    print(json.dumps({"report": REPORT_PATH, "input_sha256": prediction_hash,
                      "rows": len(frame), "aggregate_B_minus_A": report["aggregate"]["B_minus_A"]}, indent=2))


if __name__ == "__main__":
    main()
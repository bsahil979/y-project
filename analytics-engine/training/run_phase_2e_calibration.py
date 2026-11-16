"""Phase 2E.3: calibration-only analysis of frozen Phase 2E.1 probabilities."""

import hashlib
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PHASE_2E_DIRECTORY = os.path.join(ROOT, "models", "phase_2e")
PREDICTION_PATH = os.path.join(PHASE_2E_DIRECTORY, "holdout_predictions.csv")
PREDICTION_MANIFEST_PATH = os.path.join(PHASE_2E_DIRECTORY, "phase_2e_prediction_manifest.json")
REPORT_PATH = os.path.join(PHASE_2E_DIRECTORY, "phase_2e_calibration_report.json")
LABELS = np.array([-1, 0, 1])
LABEL_NAMES = ["SELL", "HOLD", "BUY"]
BIN_EDGES = np.linspace(0.0, 1.0, 11)
MODEL_COLUMNS = {
    "A": ["A_prob_-1", "A_prob_0", "A_prob_1"],
    "B": ["B_prob_-1", "B_prob_0", "B_prob_1"],
}


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probability_matrix(frame, model_name):
    probabilities = frame[MODEL_COLUMNS[model_name]].to_numpy(dtype=float)
    if not np.isfinite(probabilities).all() or (probabilities < 0).any():
        raise ValueError(f"{model_name} probability stream contains invalid values.")
    if not np.allclose(probabilities.sum(axis=1), 1.0, rtol=0, atol=1e-6):
        raise ValueError(f"{model_name} probability stream is not normalized.")
    return probabilities


def confidence_bins(confidence, correct):
    assignments = np.digitize(confidence, BIN_EDGES[1:-1], right=False)
    rows = []
    for index in range(len(BIN_EDGES) - 1):
        in_bin = assignments == index
        count = int(in_bin.sum())
        rows.append({
            "lower_inclusive": float(BIN_EDGES[index]), "upper": float(BIN_EDGES[index + 1]),
            "count": count, "share": float(count / len(confidence)),
            "mean_confidence": float(confidence[in_bin].mean()) if count else None,
            "accuracy": float(correct[in_bin].mean()) if count else None,
            "absolute_gap": float(abs(confidence[in_bin].mean() - correct[in_bin].mean())) if count else None,
        })
    return rows


def expected_calibration_error(confidence, correct):
    return float(sum(entry["share"] * entry["absolute_gap"] for entry in confidence_bins(confidence, correct)
                     if entry["absolute_gap"] is not None))


def class_calibration(probabilities, actual, predicted):
    result = {}
    for class_index, label_name in enumerate(LABEL_NAMES):
        selected = predicted == LABELS[class_index]
        count = int(selected.sum())
        result[label_name] = {
            "predicted_rows": count,
            "mean_predicted_probability": float(probabilities[selected, class_index].mean()) if count else None,
            "empirical_precision": float((actual[selected] == LABELS[class_index]).mean()) if count else None,
            "calibration_gap": float(probabilities[selected, class_index].mean() -
                                     (actual[selected] == LABELS[class_index]).mean()) if count else None,
        }
    return result


def evaluate(frame, model_name):
    probabilities = probability_matrix(frame, model_name)
    actual = frame["actual_target"].to_numpy(dtype=int)
    predicted_indices = probabilities.argmax(axis=1)
    predicted = LABELS[predicted_indices]
    correct = predicted == actual
    confidence = probabilities.max(axis=1)
    one_hot_actual = (actual[:, None] == LABELS[None, :]).astype(float)
    # Multiclass Brier score is the mean squared error over all three classes.
    multiclass_brier = np.mean(np.sum((probabilities - one_hot_actual) ** 2, axis=1))
    return {
        "rows": int(len(frame)),
        "multiclass_brier_score": float(multiclass_brier),
        "expected_calibration_error": expected_calibration_error(confidence, correct),
        "mean_confidence": float(confidence.mean()),
        "accuracy_from_native_argmax": float(correct.mean()),
        "confidence_bin_statistics": confidence_bins(confidence, correct),
        "reliability_summary": {
            "mean_confidence_minus_accuracy": float(confidence.mean() - correct.mean()),
            "confidence_min": float(confidence.min()), "confidence_max": float(confidence.max()),
        },
        "calibration_by_predicted_class": class_calibration(probabilities, actual, predicted),
    }


def differences(a, b):
    return {
        "multiclass_brier_score": b["multiclass_brier_score"] - a["multiclass_brier_score"],
        "expected_calibration_error": b["expected_calibration_error"] - a["expected_calibration_error"],
        "mean_confidence": b["mean_confidence"] - a["mean_confidence"],
        "accuracy_from_native_argmax": b["accuracy_from_native_argmax"] - a["accuracy_from_native_argmax"],
        "reliability_mean_confidence_minus_accuracy": (
            b["reliability_summary"]["mean_confidence_minus_accuracy"] -
            a["reliability_summary"]["mean_confidence_minus_accuracy"]
        ),
    }


def segmented_evaluation(frame, column):
    output = {}
    for value, segment in frame.groupby(column, sort=True, dropna=False):
        key = "__MISSING__" if pd.isna(value) else str(value)
        a, b = evaluate(segment, "A"), evaluate(segment, "B")
        output[key] = {"A": a, "B": b, "B_minus_A": differences(a, b)}
    return output


def main():
    if not os.path.exists(PREDICTION_PATH) or not os.path.exists(PREDICTION_MANIFEST_PATH):
        raise FileNotFoundError("Frozen Phase 2E.1 prediction CSV and manifest are required.")
    if os.path.exists(REPORT_PATH):
        raise FileExistsError("Phase 2E.3 report already exists and is frozen; refusing to overwrite it.")
    with open(PREDICTION_MANIFEST_PATH, encoding="utf-8") as file:
        manifest = json.load(file)
    prediction_hash = sha256(PREDICTION_PATH)
    if prediction_hash != manifest["prediction_file"]["sha256"]:
        raise ValueError("Frozen Phase 2E.1 prediction CSV hash differs from its manifest.")
    frame = pd.read_csv(PREDICTION_PATH)
    if len(frame) != manifest["prediction_file"]["rows"] or list(frame.columns) != manifest["prediction_column_schema"]:
        raise ValueError("Frozen Phase 2E.1 prediction CSV differs from its manifest.")
    if frame.duplicated(["ticker", "Date"]).any() or not set(frame["actual_target"]).issubset(LABELS):
        raise ValueError("Frozen Phase 2E.1 prediction CSV failed identity or target validation.")
    for model_name in MODEL_COLUMNS:
        probability_matrix(frame, model_name)

    a, b = evaluate(frame, "A"), evaluate(frame, "B")
    report = {
        "phase": "2E.3", "status": "completed", "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_mode": "prediction_artifact_only",
        "input": {"prediction_csv_path": PREDICTION_PATH, "prediction_csv_sha256": prediction_hash,
                  "prediction_manifest_path": PREDICTION_MANIFEST_PATH,
                  "prediction_manifest_sha256": sha256(PREDICTION_MANIFEST_PATH)},
        "constraints": {"models_loaded": False, "models_retrained": False, "dataset_loaded": False,
                        "probabilities_transformed": False, "temperature_scaling": False,
                        "platt_scaling": False, "isotonic_regression": False, "thresholds_changed": False,
                        "resampling_performed": False, "future_return_used_as_input": False},
        "methodology": {"multiclass_brier_score": "mean over rows of the sum of squared errors across three classes",
                        "expected_calibration_error": "10 equal-width confidence bins; weighted absolute confidence-minus-accuracy gap",
                        "confidence_bins": [{"lower_inclusive": float(BIN_EDGES[i]), "upper": float(BIN_EDGES[i + 1])}
                                            for i in range(len(BIN_EDGES) - 1)]},
        "aggregate": {"A": a, "B": b, "B_minus_A": differences(a, b)},
        "segments": {"market": segmented_evaluation(frame, "market"),
                     "sector": segmented_evaluation(frame, "sector"),
                     "regime_code": segmented_evaluation(frame, "regime_code")},
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, allow_nan=False)
    print(json.dumps({"report": REPORT_PATH, "input_sha256": prediction_hash,
                      "aggregate_B_minus_A": report["aggregate"]["B_minus_A"]}, indent=2))


if __name__ == "__main__":
    main()
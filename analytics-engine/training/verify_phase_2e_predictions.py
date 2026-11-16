"""Read-only acceptance verification for frozen Phase 2E.1 predictions."""

import hashlib
import json
import os

import numpy as np
import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT = os.path.join(ROOT, "models", "phase_2e")
CSV_PATH = os.path.join(OUTPUT, "holdout_predictions.csv")
MANIFEST_PATH = os.path.join(OUTPUT, "phase_2e_prediction_manifest.json")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


with open(MANIFEST_PATH, encoding="utf-8") as file:
    manifest = json.load(file)
frame = pd.read_csv(CSV_PATH)
probability_columns = ["A_prob_-1", "A_prob_0", "A_prob_1", "B_prob_-1", "B_prob_0", "B_prob_1"]
a_sums = frame[["A_prob_-1", "A_prob_0", "A_prob_1"]].sum(axis=1)
b_sums = frame[["B_prob_-1", "B_prob_0", "B_prob_1"]].sum(axis=1)
checks = {
    "dataset_sha_matches_phase_2d": manifest["dataset"]["sha256"] == "07d1d87b7a5e54625a584f3e96077d512116cf78d69654b6d2131326df3c97df",
    "holdout_rows": len(frame),
    "unique_ticker_date_keys": int(len(frame.drop_duplicates(["ticker", "Date"]))),
    "duplicate_ticker_date_keys": int(frame.duplicated(["ticker", "Date"]).sum()),
    "ticker_count": int(frame["ticker"].nunique()),
    "probabilities_finite": bool(np.isfinite(frame[probability_columns].to_numpy()).all()),
    "probabilities_non_negative": bool((frame[probability_columns].to_numpy() >= 0).all()),
    "a_probability_sum_min_max": [float(a_sums.min()), float(a_sums.max())],
    "b_probability_sum_min_max": [float(b_sums.min()), float(b_sums.max())],
    "probabilities_sum_to_one": bool(np.allclose(a_sums, 1, atol=1e-6, rtol=0) and np.allclose(b_sums, 1, atol=1e-6, rtol=0)),
    "future_return_present": "future_return" in frame.columns,
    "future_return_evaluation_only": "future_return" in manifest["evaluation_only_columns"],
    "csv_sha256": sha256(CSV_PATH),
    "manifest_csv_sha_matches": sha256(CSV_PATH) == manifest["prediction_file"]["sha256"],
    "manifest_alignment_assertions": manifest["assertions"],
}
assert checks["dataset_sha_matches_phase_2d"]
assert checks["holdout_rows"] == 42568
assert checks["unique_ticker_date_keys"] == 42568 and checks["duplicate_ticker_date_keys"] == 0
assert checks["ticker_count"] == 99
assert checks["probabilities_finite"] and checks["probabilities_non_negative"] and checks["probabilities_sum_to_one"]
assert checks["future_return_present"] and checks["future_return_evaluation_only"]
assert checks["manifest_csv_sha_matches"]
assert all(checks["manifest_alignment_assertions"].values())
print(json.dumps(checks, indent=2))
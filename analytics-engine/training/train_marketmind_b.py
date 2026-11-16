"""CLI for training MarketMind Experiment B on an existing audited dataset."""

import argparse
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from trading_engine.meta_model import FEATURE_COLUMNS
from training.marketmind_pytorch import attach_ticker_metadata, load_ticker_metadata, train_experiment_b


def main():
    parser = argparse.ArgumentParser(description="Train the PyTorch MarketMind B embedding model.")
    parser.add_argument("dataset", help="Existing MarketMind CSV; no feature or label construction is performed.")
    parser.add_argument("--output-dir", default=os.path.join(os.path.dirname(__file__), "..", "models", "meta_model_b"))
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--metadata", default=None, help="Authoritative ticker,market,sector CSV.")
    args = parser.parse_args()
    dataset = attach_ticker_metadata(pd.read_csv(args.dataset), load_ticker_metadata(args.metadata))
    result = train_experiment_b(dataset, FEATURE_COLUMNS, args.output_dir,
                                args.test_size, args.epochs, args.batch_size, args.learning_rate)
    print(json.dumps(result["metrics"], indent=2))
    print(f"Artifacts saved under: {os.path.abspath(args.output_dir)}")


if __name__ == "__main__":
    main()
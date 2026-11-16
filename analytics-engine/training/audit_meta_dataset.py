import argparse
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from trading_engine.meta_model import FEATURE_COLUMNS
from training.leakage_audit import audit_dataset


def main():
    parser = argparse.ArgumentParser(description='Audit a MarketMind dataset for temporal leakage.')
    parser.add_argument('--dataset', default='../models/meta_model/meta_dataset.csv')
    parser.add_argument('--output', default=None)
    parser.add_argument('--horizon', type=int, default=5)
    args = parser.parse_args()

    dataset = pd.read_csv(args.dataset)
    report = audit_dataset(dataset, FEATURE_COLUMNS, horizon=args.horizon)
    output = args.output or os.path.join(os.path.dirname(args.dataset), 'leakage_audit.json')
    with open(output, 'w', encoding='utf-8') as file:
        json.dump(report, file, indent=2)
    print(json.dumps(report, indent=2))
    print(f'Leakage audit passed. Report saved to: {os.path.abspath(output)}')


if __name__ == '__main__':
    main()
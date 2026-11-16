"""Run acceptance checks for the frozen Phase 2C.3 MarketMind dataset."""

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.ticker_universe import all_symbols
from trading_engine.meta_model import FEATURE_COLUMNS
from training.leakage_audit import audit_dataset
from training.report_dataset_coverage import build_report


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MODEL_DIR = os.path.join(ROOT, 'models', 'meta_model')
DATASET_PATH = os.path.join(MODEL_DIR, 'meta_dataset.csv')
METADATA_PATH = os.path.join(ROOT, 'config', 'ticker_metadata.csv')
COVERAGE_PATH = os.path.join(MODEL_DIR, 'coverage_report.json')
OUTPUT_PATH = os.path.join(MODEL_DIR, 'phase_2c3_acceptance.json')


def main():
    with open(COVERAGE_PATH, 'r', encoding='utf-8') as file:
        build_coverage = json.load(file)
    tata_records = [item for item in build_coverage['tickers'] if item['ticker'] == 'TATAMOTORS.NS']
    if len(tata_records) != 1:
        raise ValueError(f'Expected one TATAMOTORS.NS coverage record; found {len(tata_records)}.')
    tata = tata_records[0]
    if tata['status'] != 'excluded' or tata['error_type'] != 'research_exclusion':
        raise ValueError(f'TATAMOTORS.NS exclusion is not explicit: {tata}')
    if any(values['excluded'] < 0 for values in build_coverage['by_market'].values()):
        raise ValueError('Coverage report contains a negative market exclusion count.')

    dataset = pd.read_csv(DATASET_PATH)
    leakage = audit_dataset(dataset, FEATURE_COLUMNS, horizon=5)
    coverage, table = build_report(DATASET_PATH, METADATA_PATH)

    expected = {ticker.upper().strip() for ticker in all_symbols()}
    metadata = pd.read_csv(METADATA_PATH, dtype=str)
    metadata['ticker'] = metadata['ticker'].str.upper().str.strip()
    approved = set(dataset['ticker'].astype(str).str.upper().str.strip())
    metadata_issues = {
        'configured_missing_metadata': sorted(expected - set(metadata['ticker'])),
        'duplicate_metadata': sorted(metadata.loc[metadata['ticker'].duplicated(), 'ticker'].unique()),
        'approved_missing_metadata': sorted(approved - set(metadata['ticker'])),
        'approved_incomplete_metadata': sorted(metadata.loc[
            metadata['ticker'].isin(approved) & metadata[['market', 'sector']].isna().any(axis=1), 'ticker'
        ].tolist()),
    }
    if any(metadata_issues.values()):
        raise ValueError(f'Metadata coverage failed: {metadata_issues}')

    market_coverage = coverage['by_market']
    required_market_counts = {'US': 50, 'India': 49}
    for market, count in required_market_counts.items():
        values = market_coverage.get(market, {})
        if values.get('train_present') != count or values.get('holdout_present') != count:
            raise ValueError(f'{market} split coverage failed: {values}')
    if coverage['summary']['train_present'] != 99 or coverage['summary']['holdout_present'] != 99:
        raise ValueError(f'Total split coverage failed: {coverage["summary"]}')

    report = {
        'status': 'passed',
        'dataset': DATASET_PATH,
        'exact_exclusion': tata,
        'build_coverage': {
            'configured_tickers': build_coverage['configured_tickers'],
            'dataset_tickers': build_coverage['dataset_tickers'],
            'status_counts': build_coverage['status_counts'],
            'by_market': build_coverage['by_market'],
        },
        'leakage_audit': leakage,
        'train_holdout_coverage': {
            'summary': coverage['summary'],
            'by_market': market_coverage,
        },
        'metadata_coverage': metadata_issues,
    }
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as file:
        json.dump(report, file, indent=2)
    print(json.dumps(report, indent=2))
    print(f'Acceptance report saved to: {OUTPUT_PATH}')


if __name__ == '__main__':
    main()
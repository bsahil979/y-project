"""Report configured-universe and train/holdout coverage for a MarketMind CSV."""

import argparse
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.ticker_universe import assets_flat
from training.marketmind_pytorch import chronological_split, load_ticker_metadata, normalize_ticker


def build_report(dataset_path, metadata_path=None, test_size=0.2):
    dataset = pd.read_csv(dataset_path)
    if 'ticker' not in dataset.columns or 'Date' not in dataset.columns:
        raise ValueError('Dataset must contain ticker and Date columns.')
    dataset['ticker'] = dataset['ticker'].map(normalize_ticker)
    dataset['Date'] = pd.to_datetime(dataset['Date'], errors='coerce')
    if dataset['Date'].isna().any():
        raise ValueError('Dataset contains invalid Date values.')
    metadata = load_ticker_metadata(metadata_path)
    configured = pd.DataFrame(assets_flat()).rename(columns={'symbol': 'ticker'})
    configured['ticker'] = configured['ticker'].map(normalize_ticker)
    configured = configured[['ticker', 'region']].merge(metadata, on='ticker', how='left', validate='one_to_one')
    metadata_missing = configured.loc[configured[['market', 'sector']].isna().any(axis=1), 'ticker'].tolist()
    if metadata_missing:
        raise ValueError(f'Configured universe is missing authoritative metadata: {metadata_missing}')
    train, holdout = chronological_split(dataset, test_size=test_size)

    def by_ticker(frame):
        grouped = frame.groupby('ticker', sort=True)
        return grouped.agg(
            rows=('ticker', 'size'),
            first_date=('Date', 'min'),
            last_date=('Date', 'max'),
        ).reset_index()

    observed = by_ticker(dataset).rename(columns={'rows': 'final_rows', 'first_date': 'final_first_date', 'last_date': 'final_last_date'})
    observed['target_rows'] = observed['final_rows']
    observed['feature_rows'] = observed['final_rows']
    observed['raw_rows'] = observed['final_rows']
    observed['raw_first_date'] = observed['final_first_date']
    observed['raw_last_date'] = observed['final_last_date']
    train_counts = train.groupby('ticker').size().rename('train_rows')
    holdout_counts = holdout.groupby('ticker').size().rename('holdout_rows')
    table = configured.merge(observed, on='ticker', how='left')
    table = table.join(train_counts, on='ticker').join(holdout_counts, on='ticker')
    for column in ('raw_rows', 'feature_rows', 'target_rows', 'final_rows', 'train_rows', 'holdout_rows'):
        table[column] = table[column].fillna(0).astype(int)
    table['dataset_rows'] = table['final_rows']
    table['ohlcv_status'] = table['raw_rows'].gt(0).map({True: 'available', False: 'missing_ohlcv'})
    table['feature_status'] = table['feature_rows'].gt(0).map({True: 'available', False: 'not_reached'})
    table['target_status'] = table['target_rows'].gt(0).map({True: 'available', False: 'not_reached'})
    table['metadata_status'] = 'available'
    table['sentiment_status'] = 'neutral_fallback'
    table['final_status'] = table['final_rows'].gt(0).map({True: 'included', False: 'filtered'})
    table['present'] = table['final_rows'].gt(0)
    table['train_present'] = table['train_rows'].gt(0)
    table['holdout_present'] = table['holdout_rows'].gt(0)
    for column in ('final_first_date', 'final_last_date', 'raw_first_date', 'raw_last_date'):
        if column in table:
            table[column] = table[column].map(lambda value: value.isoformat() if pd.notna(value) else None)

    def summary(frame):
        return {
            'configured': int(len(frame)),
            'present': int(frame['present'].sum()),
            'train_present': int(frame['train_present'].sum()),
            'holdout_present': int(frame['holdout_present'].sum()),
            'rows': int(frame['final_rows'].sum()),
        }

    report = {
        'dataset': os.path.abspath(dataset_path),
        'configured_tickers': int(len(configured)),
        'dataset_tickers': int(dataset['ticker'].nunique()),
        'included_tickers': table.loc[table['present'], 'ticker'].tolist(),
        'excluded_tickers': table.loc[~table['present'], 'ticker'].tolist(),
        'missing_tickers': table.loc[~table['present'], 'ticker'].tolist(),
        'summary': summary(table),
        'by_market': {str(k): summary(v) for k, v in table.groupby('market', dropna=False)},
        'by_region': {str(k): summary(v) for k, v in table.groupby('region', dropna=False)},
        'sentiment_contract': {
            'historical_store': 'services.historical_sentiment.HistoricalSentimentStore',
            'point_in_time_rule': 'article_date <= observation_date',
            'missing_history_default': 0.0,
        },
        'tickers': table.where(pd.notna(table), None).to_dict(orient='records'),
    }
    return report, table


def main():
    parser = argparse.ArgumentParser(description='Report MarketMind dataset coverage.')
    parser.add_argument('--dataset', default='../models/meta_model/meta_dataset.csv')
    parser.add_argument('--metadata', default=None)
    parser.add_argument('--output', default=None)
    parser.add_argument('--test-size', type=float, default=0.2)
    args = parser.parse_args()
    report, table = build_report(args.dataset, args.metadata, args.test_size)
    output = args.output or os.path.join(os.path.dirname(args.dataset), 'coverage_report.json')
    table.to_csv(os.path.splitext(output)[0] + '.csv', index=False)
    with open(output, 'w', encoding='utf-8') as file:
        json.dump(report, file, indent=2)
    print(json.dumps(report, indent=2))
    print(f'Coverage report saved to: {os.path.abspath(output)}')


if __name__ == '__main__':
    main()
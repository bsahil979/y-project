import argparse
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from trading_engine.meta_model import MarketMindMetaModel
from config.ticker_universe import all_symbols


def load_research_exclusions(path=None):
    path = path or os.path.join(os.path.dirname(__file__), '..', 'config', 'research_exclusions.json')
    with open(path, 'r', encoding='utf-8') as file:
        exclusions = json.load(file).get('exclusions', [])
    return {item['ticker'].upper().strip(): item for item in exclusions}


def main():
    parser = argparse.ArgumentParser(description='Build the MarketMind meta-model dataset from multiple tickers.')
    parser.add_argument('--tickers', nargs='+', default=all_symbols(), help='Ticker symbols to include (default: configured 100-ticker universe).')
    parser.add_argument('--start', default='2018-01-01', help='Start date for dataset construction.')
    parser.add_argument('--end', default=None, help='Optional end date.')
    parser.add_argument('--horizon', type=int, default=5, help='Future return horizon in days.')
    parser.add_argument('--buy-threshold', type=float, default=0.01)
    parser.add_argument('--sell-threshold', type=float, default=-0.01)
    parser.add_argument('--max-rows', type=int, default=None)
    parser.add_argument(
        '--historical-sentiment-path',
        default=None,
        help='Optional CSV with ticker,date,sentiment_score. Missing history uses neutral sentiment.',
    )
    parser.add_argument(
        '--min-coverage', type=float, default=0.80,
        help='Minimum included/configured ticker ratio for a successful build (default: 0.80).',
    )
    parser.add_argument(
        '--diagnostic', action='store_true',
        help='Allow an incomplete build to exit successfully after writing diagnostics.',
    )
    parser.add_argument(
        '--research-exclusions-path',
        default=os.path.join(os.path.dirname(__file__), '..', 'config', 'research_exclusions.json'),
        help='JSON registry of explicit research-universe exclusions.',
    )
    args = parser.parse_args()

    requested_tickers = [ticker.upper().strip() for ticker in args.tickers]
    exclusions = load_research_exclusions(args.research_exclusions_path)
    build_tickers = [ticker for ticker in requested_tickers if ticker not in exclusions]
    model = MarketMindMetaModel()
    dataset = model.build_dataset(
        tickers=build_tickers,
        start=args.start,
        end=args.end,
        horizon=args.horizon,
        buy_threshold=args.buy_threshold,
        sell_threshold=args.sell_threshold,
        max_rows=args.max_rows,
        historical_sentiment_path=args.historical_sentiment_path,
    )
    print(f"Built meta dataset with {len(dataset)} rows.")
    print(f"Saved to: {os.path.join(model.model_dir, 'meta_dataset.csv')}")
    print(f"Coverage report: {os.path.join(model.model_dir, 'coverage_report.json')}")
    report_path = os.path.join(model.model_dir, 'coverage_report.json')
    with open(report_path, 'r', encoding='utf-8') as file:
        report = json.load(file)
    explicit_exclusions = [exclusions[ticker] for ticker in requested_tickers if ticker in exclusions]
    if explicit_exclusions:
        report['configured_tickers'] = len(requested_tickers)
        report['missing_tickers'] = sorted(set(report['missing_tickers']).union(item['ticker'] for item in explicit_exclusions))
        report['status_counts']['excluded'] = len(explicit_exclusions)
        excluded_records = [{
            'ticker': item['ticker'],
            'status': 'excluded',
            'raw_rows': 0,
            'window_rows': 0,
            'feature_rows': 0,
            'target_rows': 0,
            'final_rows': 0,
            'raw_first_date': None,
            'raw_last_date': None,
            'window_first_date': None,
            'window_last_date': None,
            'final_first_date': None,
            'final_last_date': None,
            'error_type': 'research_exclusion',
            'error': item['reason'],
        } for item in explicit_exclusions]
        report['tickers'].extend(excluded_records)
        metadata_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'ticker_metadata.csv')
        metadata = pd.read_csv(metadata_path, dtype=str)
        market_by_ticker = metadata.set_index('ticker')['market'].to_dict()
        for item in explicit_exclusions:
            market = market_by_ticker.get(item['ticker'])
            if market:
                summary = report['by_market'][market]
                summary['configured'] += 1
                summary['excluded'] = summary['configured'] - summary['present']
        report['research_exclusions'] = explicit_exclusions
        with open(report_path, 'w', encoding='utf-8') as file:
            json.dump(report, file, indent=2)
        pd.DataFrame(report['tickers']).to_csv(
            os.path.join(model.model_dir, 'coverage_report.csv'), index=False
        )
    requested = report['configured_tickers']
    included = report['dataset_tickers']
    ratio = included / requested if requested else 0.0
    print('Universe coverage')
    print('-----------------')
    print(f'Requested: {requested}')
    print(f'Included: {included}')
    for status, count in sorted(report.get('status_counts', {}).items()):
        print(f'{status.replace("_", " ").title()}: {count}')
    for market, values in report.get('by_market', {}).items():
        print(f'{market}: {values["present"]} / {values["configured"]}')
    if not args.diagnostic and ratio < args.min_coverage:
        raise SystemExit(
            f'ERROR: dataset coverage below required threshold: '
            f'{included} / {requested} ({ratio:.1%}) < {args.min_coverage:.1%}. '
            f'Use --diagnostic to inspect an incomplete build.'
        )


if __name__ == '__main__':
    main()

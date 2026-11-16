"""Run: python -m research.run_regime_study [--prices saved_prices.csv].

Defaults are a development experiment, not a locked final paper evaluation.
Writes the exact dataset, configuration, code hashes, decisions, costs and metrics.
"""
import argparse
import hashlib
import itertools
import json
import platform
from importlib.metadata import version
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

from services.data_fetcher import fetch_price_data
from services.regime_allocation import AllocationConfig
from research.regime_study import run_study, summarize_period, paired_sharpe_block_bootstrap

DEFAULT_TICKERS = ['RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prices', type=Path)
    parser.add_argument('--output', type=Path, default=Path('research/regime_results'))
    parser.add_argument('--start', default='2018-01-01')
    parser.add_argument('--end', default='2026-01-01')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--cost-bps', type=float, default=10)
    parser.add_argument('--holdout-start', default='2025-01-01')
    parser.add_argument('--holdout-end', default='2025-12-31')
    parser.add_argument('--min-holdout-observations', type=int, default=200,
                        help='minimum daily return rows required for the final holdout report')
    parser.add_argument('--allow-no-holdout', action='store_true', help='permit a development replay with no rows in the configured holdout')
    parser.add_argument('--replace', action='store_true', help='overwrite artifacts in a non-empty output directory')
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()) and not args.replace:
        parser.error(f'output directory is not empty: {args.output}; choose a new --output or pass --replace')
    if args.prices:
        prices = pd.read_csv(args.prices, index_col=0, parse_dates=True, float_precision='round_trip')
        provenance = {'type': 'supplied_csv', 'path': str(args.prices.resolve())}
        previous_manifest = args.prices.parent / 'manifest.json'
        if previous_manifest.exists():
            input_manifest = json.loads(previous_manifest.read_text(encoding='utf-8'))
            declared_snapshot_hash = input_manifest.get('snapshot_sha256')
            actual_snapshot_hash = hashlib.sha256(args.prices.read_bytes()).hexdigest()
            if declared_snapshot_hash and declared_snapshot_hash != actual_snapshot_hash:
                raise ValueError('Supplied price snapshot does not match its manifest SHA-256')
            provenance['input_manifest_sha256'] = hashlib.sha256(previous_manifest.read_bytes()).hexdigest()
            provenance['input_data_provenance'] = input_manifest.get('data') or input_manifest
    else:
        prices = fetch_price_data(DEFAULT_TICKERS, args.start, args.end)
        if (prices.attrs.get('provider') != 'Yahoo Finance'
                or prices.attrs.get('adjustment_verified') is not True
                or 'auto-adjusted close' not in prices.attrs.get('price_field', '')):
            raise ValueError('Study requires adjusted-close data; fallback adjustment convention is unverified')
        provenance = {'type': 'real_market_provider', 'requested_start': args.start,
                      'requested_end_exclusive': args.end,
                      'provider': prices.attrs['provider'],
                      'price_field': prices.attrs['price_field'],
                      'adjustment_verified': prices.attrs['adjustment_verified'],
                      'downloaded_at_utc': datetime.now(timezone.utc).isoformat(),
                      'dropped_incomplete_rows': int(prices.attrs.get('dropped_incomplete_rows', 0)),
                      'currency': 'INR'}
    result = run_study(prices, AllocationConfig(seed=args.seed), cost_bps=args.cost_bps)
    ledger_dates = pd.to_datetime(result['ledger']['date'])
    holdout_mask = ((ledger_dates >= pd.Timestamp(args.holdout_start))
                    & (ledger_dates <= pd.Timestamp(args.holdout_end)))
    holdout_count = int(result['ledger'].loc[holdout_mask, 'date'].nunique())
    has_holdout = holdout_count >= args.min_holdout_observations
    if args.min_holdout_observations < 30:
        raise ValueError('--min-holdout-observations must be at least 30')
    if not has_holdout and not args.allow_no_holdout:
        raise ValueError(f'Holdout has {holdout_count} daily return rows; at least '
                         f'{args.min_holdout_observations} are required. Use --allow-no-holdout only for a development replay')
    holdout_metrics = summarize_period(result['ledger'], args.holdout_start, args.holdout_end,
                                       result['config']['risk_free_rate']) if has_holdout else None
    holdout_bootstrap = paired_sharpe_block_bootstrap(
        result['ledger'], args.holdout_start, args.holdout_end,
        risk_free_rate=result['config']['risk_free_rate']) if has_holdout else None
    sensitivity_specs = sorted({(seed, cost) for seed, cost in itertools.product(
        (7, 42, 123, 2026), (0, 10, 25)) if seed == 42 or cost == 10})
    sensitivity_rows = []
    for seed, cost in sensitivity_specs:
        variant = result if seed == args.seed and cost == args.cost_bps else run_study(
            prices, AllocationConfig(seed=seed), cost_bps=cost)
        for strategy, metrics in variant['metrics'].iterrows():
            row = {'seed': seed, 'cost_bps': cost, 'strategy': strategy,
                   'full_period_sharpe': metrics['sharpe'],
                   'full_period_annualized_return': metrics['annualized_return']}
            if has_holdout:
                holdout_variant = summarize_period(variant['ledger'], args.holdout_start,
                                                   args.holdout_end, variant['config']['risk_free_rate'])
                row['holdout_sharpe'] = holdout_variant.loc[strategy, 'sharpe']
                row['holdout_annualized_return'] = holdout_variant.loc[strategy, 'annualized_return']
            sensitivity_rows.append(row)
    sensitivity = pd.DataFrame(sensitivity_rows)
    args.output.mkdir(parents=True, exist_ok=True)
    snapshot = prices.to_csv(float_format='%.17g', lineterminator='\n')
    (args.output / 'prices.csv').write_bytes(snapshot.encode('utf-8'))
    result['equity'].to_csv(args.output / 'equity.csv')
    result['ledger'].to_csv(args.output / 'daily_ledger.csv', index=False)
    result['metrics'].to_csv(args.output / 'metrics.csv')
    sensitivity.to_csv(args.output / 'sensitivity.csv', index=False)
    if holdout_metrics is not None:
        holdout_metrics.to_csv(args.output / 'holdout_metrics.csv')
        (args.output / 'holdout_sharpe_bootstrap.json').write_text(
            json.dumps(holdout_bootstrap, indent=2, allow_nan=False), encoding='utf-8')
    (args.output / 'decisions.json').write_text(json.dumps(result['decisions'], indent=2, allow_nan=False), encoding='utf-8')
    root = Path(__file__).resolve().parents[1]
    source_paths = ['services/hmm_engine.py', 'services/regime_allocation.py', 'services/data_fetcher.py',
                    'research/regime_study.py', 'research/run_regime_study.py']
    manifest = {
        'created_at': datetime.now(timezone.utc).isoformat(),
        'status': 'completed_chronological_backtest',
        'config': result['config'], 'data': provenance, 'tickers': prices.columns.tolist(),
        'snapshot_sha256': hashlib.sha256(snapshot.encode()).hexdigest(),
        'source_sha256': {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in source_paths},
        'python': platform.python_version(),
        'versions': {name: version(name) for name in ['numpy', 'pandas', 'scipy', 'hmmlearn']},
        'price_start': str(prices.index[0].date()), 'price_end': str(prices.index[-1].date()),
        'price_observations': int(len(prices)),
        'holdout': {
            'start': args.holdout_start,
            'end': args.holdout_end,
            'return_observations': holdout_count,
            'minimum_return_observations': args.min_holdout_observations,
            'status': 'ready' if has_holdout else 'not_available_development_replay',
            'primary_metric': 'net annualized Sharpe difference: HMM minimum variance minus Minimum variance',
            'metrics_file': 'holdout_metrics.csv' if has_holdout else None,
            'bootstrap_file': 'holdout_sharpe_bootstrap.json' if has_holdout else None,
            'bootstrap': holdout_bootstrap,
        },
        'sensitivity': {
            'file': 'sensitivity.csv',
            'seed_values': [7, 42, 123, 2026],
            'cost_bps_values': [0, 10, 25],
            'scenario_count': len(sensitivity_specs),
            'rows': len(sensitivity),
            'primary_scenario_included': (args.seed, args.cost_bps) in sensitivity_specs,
        },
        'protocol_id': 'regime_allocation_v1_2026-09-27',
        'protocol_sha256': hashlib.sha256((Path(__file__).with_name('experiment_protocol_v1.json')).read_bytes()).hexdigest(),
        'test_start': str(result['equity'].index[1].date()),
        'test_end': str(result['equity'].index[-1].date()),
        'rebalances': len(result['decisions']),
        'limitations': ['Convenience universe; survivorship/selection bias not eliminated',
                       'One development period and seed; no statistical significance claim',
                       'Fixed cost approximation; no intraday spread or market-impact model',
                       'Adjusted-close research returns, not executable price quotes'],
    }
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False), encoding='utf-8')
    convergence = {'fits': len(result['decisions']),
        'converged': sum(d['hmm_converged'] for d in result['decisions']),
        'iteration_cap_failures': sum(d['convergence']['iteration_limit_reached'] for d in result['decisions'])}
    (args.output / 'convergence.json').write_text(json.dumps(convergence, indent=2), encoding='utf-8')
    report = '# Updated HMM allocation study\n\nFrozen protocol and prices; updated causal HMM engine.\n\n'
    report += '## 2025 holdout\n\n' + (holdout_metrics.to_string() if holdout_metrics is not None else 'No holdout available') + '\n\n'
    report += '## Paired Sharpe bootstrap\n\n```json\n' + json.dumps(holdout_bootstrap, indent=2) + '\n```\n\n'
    report += 'Convergence: ' + json.dumps(convergence) + '\n\nExploratory single-universe results; the bootstrap interval describes the paired Sharpe difference, not the HMM Sharpe alone.\n'
    (args.output / 'report.md').write_text(report, encoding='utf-8')
    print(result['metrics'].to_string())
    print(f'Artifacts: {args.output.resolve()}')


if __name__ == '__main__':
    main()

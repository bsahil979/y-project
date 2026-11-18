"""Exploratory 2025 allocation replay on two fixed, single-currency baskets."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from research.personalized_study import build_features, digest, run_allocations, statistics
from services.regime_allocation import minimum_variance


BASKETS = {
    'US': ['AAPL', 'MSFT', 'JPM', 'XOM', 'WMT', 'UNH'],
    'India': ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'ITC.NS', 'SUNPHARMA.NS', 'NTPC.NS'],
}


def baselines(prices, decisions):
    returns = prices.pct_change(fill_method=None).dropna()
    for first_return, window in decisions.groupby('first_return_date', sort=True):
        decision = window.iloc[0]
        history = returns.loc[decision.training_start:decision.decision_date]
        covariance = np.cov(history, rowvar=False, ddof=0)
        ridge = max(float(np.trace(covariance) / len(prices.columns)) * 1e-6, 1e-12)
        yield first_return, {
            'Equal weight': np.full(len(prices.columns), 1 / len(prices.columns)),
            'Minimum variance': minimum_variance(covariance + np.eye(len(prices.columns)) * ridge, .40),
        }


def evaluate_basket(dataset, tickers):
    rows = dataset.loc[dataset.ticker.isin(tickers)]
    prices = rows.pivot(index='Date', columns='ticker', values='Close').reindex(columns=tickers).dropna()
    if not np.isfinite(prices.to_numpy()).all() or (prices <= 0).any().any():
        raise ValueError('Expected finite positive close prices.')
    with threadpool_limits(limits=1):
        ledger, decisions, _ = run_allocations(prices, build_features(prices, rows))
    targets = dict(baselines(prices, pd.DataFrame(decisions)))
    start = min(targets)
    returns = prices.pct_change(fill_method=None).loc[start:]
    holdings = {name: np.zeros(len(tickers)) for name in targets[start]}
    rows = []
    for day, daily in returns.iterrows():
        proposed = targets.get(day.date().isoformat())
        for name, weight in holdings.items():
            turnover = 0.0
            if proposed is not None:
                turnover = float(np.abs(proposed[name] - weight).sum())
                weight = proposed[name]
            gross = float(weight @ daily.to_numpy())
            rows.append({'date': day, 'strategy': name, 'rebalance': proposed is not None,
                         'turnover': turnover, 'net_return': (1 - turnover * .001) * (1 + gross) - 1})
            holdings[name] = weight * (1 + daily.to_numpy()) / (1 + gross)
    daily = pd.concat([ledger, pd.DataFrame(rows)], ignore_index=True)
    holdout = daily[daily.date.between('2025-01-01', '2025-12-31')]
    paired = holdout.pivot(index='date', columns='strategy', values='net_return')
    expected = prices.index[prices.index.year == 2025]
    if len(expected) < 200 or not paired.index.equals(expected) or paired.isna().any().any():
        raise ValueError('All strategies must cover the full shared 2025 calendar.')
    metrics = {}
    for name, group in holdout.groupby('strategy'):
        metrics[name] = {
            **{key: float(value) for key, value in statistics(group.net_return).items()},
            'mean_rebalance_turnover': float(group.loc[group.rebalance, 'turnover'].mean()),
        }
    return {'tickers': tickers, 'sessions': len(paired), 'metrics': metrics}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a new output file to preserve existing results.')
    path = Path(__file__).resolve().parents[1] / 'models/meta_model/meta_dataset.csv'
    dataset = pd.read_csv(path, usecols=['ticker', 'Date', 'Close', 'adx'], parse_dates=['Date'])
    dataset = dataset.loc[dataset.Date.between('2022-01-01', '2025-12-31')]
    report = {
        'input_sha256': digest(path),
        'scope': 'Exploratory replay on an already inspected 2025 year. Two convenience baskets, single currency each.',
        'cost_bps': 10,
        'min_variance_baseline_max_weight': .40,
        'sentiment_coverage': 'unavailable_in_historical_replay',
        'baskets': {name: evaluate_basket(dataset, tickers) for name, tickers in BASKETS.items()},
    }
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(report, handle, indent=2, allow_nan=False)


if __name__ == '__main__':
    main()

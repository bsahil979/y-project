"""Shared chronological execution and accounting for the focused regime study.

Decision after close t; execution at close t+1; first earned return t+1 -> t+2.
All strategies use the same dates/costs. Holdings drift between rebalances.
"""
from dataclasses import asdict
import numpy as np
import pandas as pd

from services.regime_allocation import AllocationConfig, fit_allocations

STRATEGIES = ('Buy and hold', 'Equal weight', 'Minimum variance', 'HMM minimum variance')


def summarize_period(ledger, start, end, risk_free_rate=.02):
    """Compute comparable metrics for an inclusive date slice of a daily ledger."""
    dates = pd.to_datetime(ledger['date'])
    mask = (dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))
    period = ledger.loc[mask].copy()
    if period.empty:
        raise ValueError(f'No ledger observations in requested period {start} through {end}')
    counts = period.groupby('strategy')['net_return'].count()
    if set(counts.index) != set(STRATEGIES) or counts.nunique() != 1:
        raise ValueError('Every strategy must have the same return dates in the requested period')
    if not np.isfinite(period[['net_return', 'gross_return', 'turnover', 'cost_fraction']].to_numpy()).all():
        raise ValueError('Ledger contains non-finite period values')

    rf_daily = (1 + risk_free_rate) ** (1 / 252) - 1
    rows = []
    for name in STRATEGIES:
        daily = period[period.strategy == name].sort_values('date')
        net = daily.net_return.to_numpy(dtype=float)
        gross = daily.gross_return.to_numpy(dtype=float)
        wealth = np.cumprod(1 + net)
        path = np.r_[1.0, wealth]
        volatility = float(np.std(net, ddof=1) * np.sqrt(252)) if len(net) > 1 else 0.0
        rows.append(dict(
            strategy=name,
            period_start=pd.Timestamp(daily.date.iloc[0]).strftime('%Y-%m-%d'),
            period_end=pd.Timestamp(daily.date.iloc[-1]).strftime('%Y-%m-%d'),
            total_return=float(wealth[-1] - 1),
            annualized_return=float(wealth[-1] ** (252 / len(net)) - 1),
            annualized_volatility=volatility,
            sharpe=float((net.mean() - rf_daily) * np.sqrt(252) / np.std(net, ddof=1))
            if len(net) > 1 and np.std(net, ddof=1) > 0 else None,
            max_drawdown=float((path / np.maximum.accumulate(path) - 1).min()),
            annualized_traded_notional=float(daily.turnover.sum() * 252 / len(net)),
            cumulative_cost_fraction=float(daily.cost_fraction.sum()),
            cost_drag_on_one_unit=float(np.prod(1 + gross) - wealth[-1]),
            observation_count=int(len(net)),
        ))
    return pd.DataFrame(rows).set_index('strategy')


def paired_sharpe_block_bootstrap(ledger, start, end, risk_free_rate=.02,
                                  block_length=21, replicates=10000,
                                  seed=20260927, confidence=.95):
    """Paired moving-block interval for HMM minus matched min-variance Sharpe."""
    dates = pd.to_datetime(ledger['date'])
    period = ledger.loc[(dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))]
    paired = {}
    for strategy in ('Minimum variance', 'HMM minimum variance'):
        rows = period[period.strategy == strategy].sort_values('date')
        paired[strategy] = rows
    base, proposed = paired['Minimum variance'], paired['HMM minimum variance']
    if base.empty or not base.date.reset_index(drop=True).equals(proposed.date.reset_index(drop=True)):
        raise ValueError('Both optimizers must have identical non-empty holdout dates')
    values = np.column_stack((base.net_return.to_numpy(dtype=float), proposed.net_return.to_numpy(dtype=float)))
    n = len(values)
    if n < 30 or not np.isfinite(values).all() or block_length < 1 or block_length > n or replicates < 100 or not 0 < confidence < 1:
        raise ValueError('Invalid bootstrap data or settings')

    rf_daily = (1 + risk_free_rate) ** (1 / 252) - 1
    def sharpe(samples):
        std = np.std(samples, axis=-1, ddof=1)
        mean = np.mean(samples, axis=-1)
        result = np.full_like(std, np.nan, dtype=float)
        valid = std > 0
        result[valid] = (mean[valid] - rf_daily) * np.sqrt(252) / std[valid]
        return result

    point = float(sharpe(values.T)[1] - sharpe(values.T)[0])
    rng = np.random.default_rng(seed)
    block_count = int(np.ceil(n / block_length))
    offsets = np.arange(block_length)
    starts = rng.integers(0, n - block_length + 1, size=(replicates, block_count))
    indices = (starts[:, :, None] + offsets[None, None, :]).reshape(replicates, -1)[:, :n]
    samples = values[indices]
    differences = sharpe(samples[:, :, 1]) - sharpe(samples[:, :, 0])
    differences = differences[np.isfinite(differences)]
    if len(differences) < replicates * .99:
        raise ValueError('Too many degenerate bootstrap samples to report a stable interval')
    alpha = (1 - confidence) / 2
    return {
        'comparison': 'HMM minimum variance minus Minimum variance',
        'metric': 'net annualized Sharpe difference',
        'point_estimate': point,
        'confidence': confidence,
        'lower': float(np.quantile(differences, alpha)),
        'upper': float(np.quantile(differences, 1 - alpha)),
        'method': 'paired moving-block bootstrap; non-circular blocks sampled from shared dates',
        'block_length_sessions': int(block_length),
        'replicates_requested': int(replicates),
        'replicates_valid': int(len(differences)),
        'seed': int(seed),
        'observation_count': int(n),
        'risk_free_rate_annual': float(risk_free_rate),
        'annualization_sessions': 252,
        'interpretation': 'Exploratory uncertainty for one year and one convenience universe; not broad evidence of effectiveness.',
    }


def run_study(prices, config=AllocationConfig(), rebalance_every=21, cost_bps=10, risk_free_rate=.02):
    if prices.index.has_duplicates or not prices.index.is_monotonic_increasing or prices.columns.has_duplicates:
        raise ValueError('Prices must have unique dates/columns and chronological order')
    if not np.isfinite(prices.to_numpy()).all() or (prices <= 0).any().any():
        raise ValueError('Use complete positive prices')
    if rebalance_every < 1 or not 0 <= cost_bps < 5000 or risk_free_rate <= -1:
        raise ValueError('Invalid execution settings')
    returns = prices.pct_change(fill_method=None).dropna()
    first = config.lookback + 1  # reserve one full session for delayed execution
    if len(returns) <= first:
        raise ValueError('Insufficient history for training and delayed out-of-sample execution')
    n = len(prices.columns)
    holdings = {name: np.zeros(n) for name in STRATEGIES}
    wealth = {name: 1.0 for name in STRATEGIES}
    paths = [{**{'date': returns.index[first - 1]}, **wealth}]
    records, decisions = [], []
    for i in range(first, len(returns)):
        is_rebalance = (i - first) % rebalance_every == 0
        if is_rebalance:
            # Test-day return and execution-day return are both excluded from fit.
            training = returns.iloc[i - 1 - config.lookback:i - 1]
            fitted = fit_allocations(training, config, forecast_steps=2)
            fitted['execution_date'] = str(returns.index[i - 1].date())
            fitted['first_return_date'] = str(returns.index[i].date())
            decisions.append(fitted)
            targets = {
                'Buy and hold': np.full(n, 1 / n),
                'Equal weight': np.full(n, 1 / n),
                'Minimum variance': np.array([fitted['baseline_weights'][t] for t in prices.columns]),
                'HMM minimum variance': np.array([fitted['weights'][t] for t in prices.columns]),
            }
        daily_return = returns.iloc[i].to_numpy()
        for name in STRATEGIES:
            traded = is_rebalance and (name != 'Buy and hold' or i == first)
            turnover = float(np.abs(targets[name] - holdings[name]).sum()) if traded else 0.0
            if traded:
                holdings[name] = targets[name].copy()
            fee = turnover * cost_bps / 10000
            gross_return = float(holdings[name] @ daily_return)
            net_return = (1 - fee) * (1 + gross_return) - 1
            wealth[name] *= 1 + net_return
            records.append(dict(date=returns.index[i], strategy=name, net_return=net_return,
                                gross_return=gross_return, turnover=turnover, cost_fraction=fee))
            holdings[name] = holdings[name] * (1 + daily_return) / (1 + gross_return)
        paths.append({**{'date': returns.index[i]}, **wealth})
    equity = pd.DataFrame(paths).set_index('date')
    ledger = pd.DataFrame(records)
    metric_rows = []
    for name in STRATEGIES:
        daily = ledger[ledger.strategy == name]
        net = daily.net_return
        volatility = float(net.std(ddof=1) * np.sqrt(252))
        rf_daily = (1 + risk_free_rate) ** (1 / 252) - 1
        metric_rows.append(dict(
            strategy=name, total_return=float(equity[name].iloc[-1] - 1),
            annualized_return=float(equity[name].iloc[-1] ** (252 / len(net)) - 1),
            annualized_volatility=volatility,
            sharpe=float((net.mean() - rf_daily) * 252 / volatility) if volatility > 0 else None,
            max_drawdown=float((equity[name] / equity[name].cummax() - 1).min()),
            annualized_traded_notional=float(daily.turnover.sum() * 252 / len(net)),
            observation_count=len(net),
        ))
    return dict(equity=equity, ledger=ledger, decisions=decisions,
                metrics=pd.DataFrame(metric_rows).set_index('strategy'),
                config={**asdict(config), 'rebalance_every': rebalance_every, 'cost_bps': cost_bps,
                        'risk_free_rate': risk_free_rate,
                        'execution': 'Signal at close t; trade at close t+1; earn return through close t+2',
                        'cost_definition': 'cost_bps per unit total absolute traded weight; initial purchase included',
                        'final_liquidation': False})

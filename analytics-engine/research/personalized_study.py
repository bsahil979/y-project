"""Frozen causal profile/AI allocation replay. See PHASE8_PROTOCOL.md before running."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import ta
from sklearn.ensemble import RandomForestClassifier
from services.hmm_engine import causal_regime_features
from services.portfolio_optimizer import PortfolioOptimizer, build_ai_black_litterman_views
from trading_engine.meta_model import FEATURE_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'research/personalized_phase8_2026-11-16'
FROZEN = ROOT / 'research/regime_phase4_2026-11-15'
NAMES = ('Conservative', 'Moderate', 'Aggressive target return', 'Aggressive AI Black-Litterman')
SOURCE_PATHS = ['research/personalized_study.py', 'research/PHASE8_PROTOCOL.md',
                'services/portfolio_optimizer.py', 'services/hmm_engine.py',
                'trading_engine/meta_model.py', 'trading_engine/data_manager.py']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')


def build_features(prices, saved):
    """Only stored ADX is consumed; other features are recomputed causally."""
    frames = []
    for ticker in prices:
        print('Causal features:', ticker, flush=True)
        close = prices[ticker]
        frame = pd.DataFrame(index=prices.index)
        frame['returns'] = close.pct_change(fill_method=None)
        frame['rsi'] = ta.momentum.rsi(close, window=14)
        macd = ta.trend.MACD(close)
        frame['macd'], frame['macd_signal'], frame['macd_diff'] = macd.macd(), macd.macd_signal(), macd.macd_diff()
        historical = saved.loc[saved.ticker == ticker].set_index('Date')
        if historical.index.has_duplicates:
            raise ValueError('Duplicate historical feature dates')
        frame['adx'] = historical.adx.reindex(frame.index)
        frame['volatility'] = frame.returns.rolling(24).std()
        frame['ema_50'] = close.ewm(span=50, adjust=False).mean()
        frame['ema_200'] = close.ewm(span=200, adjust=False).mean()
        frame['trend_strength'] = (close - frame.ema_50) / frame.ema_50
        frame['momentum_5d'], frame['momentum_10d'] = close.pct_change(5), close.pct_change(10)
        frame['sentiment_score'] = 0.0  # Missing feature convention, not a FinBERT observation.
        regimes = causal_regime_features(frame.returns.dropna())
        frame['regime_code'] = regimes.regime_code.reindex(frame.index)
        frame['regime_available'] = regimes.regime_available.reindex(frame.index).fillna(False).astype(bool)
        frame['ticker'], frame['Date'] = ticker, frame.index
        # Targets are separate; the classifier only selects FEATURE_COLUMNS.
        future = close.shift(-5) / close - 1
        frame['target'] = np.where(future > .01, 2, np.where(future < -.01, 0, 1))
        frame['label_end'] = pd.Series(prices.index, index=prices.index).shift(-5)
        frame.loc[future.isna(), 'target'] = np.nan
        frames.append(frame.reset_index(drop=True))
    return pd.concat(frames, ignore_index=True)


def training_rows(features, start, decision_date):
    selected = features.loc[(features.Date >= start) & (features.Date <= decision_date)
                            & (features.label_end <= decision_date)].copy()
    return selected.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATURE_COLUMNS + ['target'])


def probabilities_as_of(features, tickers, start, decision_date):
    train = training_rows(features, start, decision_date)
    latest = features.loc[features.Date == decision_date].set_index('ticker').loc[tickers]
    if len(train) < 200 or not np.isfinite(latest[FEATURE_COLUMNS].to_numpy()).all():
        raise ValueError('Insufficient causal classifier features')
    model = RandomForestClassifier(n_estimators=250, class_weight='balanced', random_state=42, n_jobs=1)
    model.fit(train[FEATURE_COLUMNS], train.target.astype(int))
    predicted = model.predict_proba(latest[FEATURE_COLUMNS])
    probabilities, provenance = {}, []
    for ticker, row in zip(tickers, predicted):
        mapped = dict(zip(model.classes_, row))
        probabilities[ticker] = {'buy': float(mapped.get(2, 0)), 'hold': float(mapped.get(1, 0)), 'sell': float(mapped.get(0, 0))}
        provenance.append({'ticker': ticker, 'decision_date': str(decision_date.date()),
            'training_rows': len(train), 'training_feature_end': str(train.Date.max().date()),
            'training_label_end': str(train.label_end.max().date()),
            'regime_code': int(latest.loc[ticker, 'regime_code']),
            'regime_available': bool(latest.loc[ticker, 'regime_available']),
            **probabilities[ticker]})
    return probabilities, provenance


def run_allocations(prices, features):
    returns = prices.pct_change(fill_method=None).dropna()
    first, lookback, n = 505, 504, len(prices.columns)
    holdings = {name: np.zeros(n) for name in NAMES}
    ledger, decisions, predictions = [], [], []
    for i in range(first, len(returns)):
        rebalance = (i-first) % 21 == 0
        if rebalance:
            train = returns.iloc[i-1-lookback:i-1]
            decision_date = train.index[-1]
            probabilities, records = probabilities_as_of(features, list(prices.columns), train.index[0], decision_date)
            predictions.extend(records)
            optimizer = PortfolioOptimizer(train)
            pi = dict(zip(prices.columns, 2.5 * optimizer.cov_matrix.to_numpy() @ np.full(n, 1/n)))
            views = build_ai_black_litterman_views(pi, train.std()*np.sqrt(252), probabilities, {t: None for t in prices})
            allocations = {
                'Conservative': optimizer.optimize_personalized('conservative', 10),
                'Moderate': optimizer.optimize_personalized('moderate', 10),
                'Aggressive target return': optimizer.optimize_personalized('aggressive', 10),
                'Aggressive AI Black-Litterman': optimizer.optimize_personalized('aggressive', 10, ai_views=views)}
            targets = {}
            for name, allocation in allocations.items():
                if not allocation['success']:
                    raise ValueError(f'{decision_date} {name}: {allocation}')
                targets[name] = np.array([allocation['weights'][t] for t in prices])
                if targets[name].max() > allocation['max_weight_cap'] + 1e-7:
                    raise ValueError('Target weight cap violated')
                decisions.append({'strategy': name, 'training_start': str(train.index[0].date()),
                    'decision_date': str(decision_date.date()), 'execution_date': str(returns.index[i-1].date()),
                    'first_return_date': str(returns.index[i].date()), 'allocation': allocation})
            print('Rebalance:', decision_date.date(), flush=True)
        daily = returns.iloc[i].to_numpy()
        for name in NAMES:
            turnover = float(np.abs(targets[name]-holdings[name]).sum()) if rebalance else 0.0
            if rebalance:
                holdings[name] = targets[name].copy()
            fee = turnover * .001
            gross = float(holdings[name] @ daily)
            ledger.append({'date': returns.index[i], 'strategy': name, 'gross_return': gross,
                           'net_return': (1-fee)*(1+gross)-1, 'turnover': turnover,
                           'cost_fraction': fee, 'rebalance': rebalance})
            holdings[name] *= (1+daily)/(1+gross)
    return pd.DataFrame(ledger), decisions, predictions


def statistics(values):
    values = np.asarray(values)
    sd = values.std(axis=-1, ddof=1)
    wealth = np.cumprod(1+values, axis=-1)
    path = np.concatenate([np.ones((*wealth.shape[:-1], 1)), wealth], axis=-1)
    return {'annualized_return': wealth[..., -1]**(252/values.shape[-1])-1,
            'annualized_volatility': sd*np.sqrt(252),
            'sharpe': (values.mean(axis=-1)-((1.02)**(1/252)-1))*np.sqrt(252)/sd,
            'max_drawdown': (path/np.maximum.accumulate(path, axis=-1)-1).min(axis=-1)}


def evaluate(ledger):
    holdout = ledger.loc[(ledger.date >= '2025-01-01') & (ledger.date <= '2025-12-31')]
    paired = holdout.pivot(index='date', columns='strategy', values='net_return')
    if len(paired) != 249 or paired.isna().any().any():
        raise ValueError('Require identical 249 holdout dates for every strategy')
    n = len(paired)
    rng = np.random.default_rng(20260927)
    starts = rng.integers(0, n-21+1, size=(10000, int(np.ceil(n/21))))
    indices = (starts[:, :, None]+np.arange(21)).reshape(10000, -1)[:, :n]
    samples, metrics = {}, []
    for name in paired:
        values = paired[name].to_numpy()
        stats = statistics(values)
        daily = holdout.loc[holdout.strategy == name]
        samples[name] = statistics(values[indices])
        metrics.append({'strategy': name, **{k: float(v) for k, v in stats.items()},
            'average_turnover': float(daily.loc[daily.rebalance, 'turnover'].mean()),
            'average_daily_turnover': float(daily.turnover.mean()),
            'annualized_traded_notional': float(daily.turnover.sum()*252/n),
            'cumulative_cost_fraction': float(daily.cost_fraction.sum()),
            'rebalance_count': int(daily.rebalance.sum()), 'observation_count': n})
    intervals = []
    for name in NAMES:
        for base in ('Minimum variance', 'Equal weight'):
            difference = samples[name]['sharpe']-samples[base]['sharpe']
            intervals.append({'strategy': name, 'baseline': base, 'metric': 'net_sharpe_difference',
                'point_estimate': float(statistics(paired[name])['sharpe']-statistics(paired[base])['sharpe']),
                'lower': float(np.quantile(difference, .025)), 'upper': float(np.quantile(difference, .975))})
    comparisons = []
    for other in ('Aggressive target return', 'Aggressive AI Black-Litterman', 'Equal weight'):
        for metric in ('annualized_volatility', 'max_drawdown'):
            diff = samples['Conservative'][metric]-samples[other][metric]
            point = float(statistics(paired['Conservative'])[metric]-statistics(paired[other])[metric])
            comparisons.append({'comparison': 'Conservative minus '+other, 'metric': metric,
                'difference': point, 'lower': float(np.quantile(diff, .025)), 'upper': float(np.quantile(diff, .975)),
                'observed_risk_reduction': bool(point < -1e-10 if metric == 'annualized_volatility' else point > 1e-10),
                'interval_supports_reduction': bool(np.quantile(diff, .975) < -1e-10 if metric == 'annualized_volatility' else np.quantile(diff, .025) > 1e-10)})
    return {'metrics': metrics, 'sharpe_intervals': intervals, 'risk_comparisons': comparisons}


def main():
    OUTPUT.mkdir(exist_ok=True)
    if (OUTPUT/'summary.json').exists():
        raise ValueError('Completed study already exists; preserve it and choose a new output version')
    manifest = json.loads((FROZEN/'manifest.json').read_text())
    if digest(FROZEN/'prices.csv') != manifest['snapshot_sha256']:
        raise ValueError('Frozen price hash mismatch')
    source_hashes = {p: digest(ROOT/p) for p in SOURCE_PATHS}
    inputs = {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in
              (FROZEN/'prices.csv', FROZEN/'daily_ledger.csv', ROOT/'models/meta_model/meta_dataset.csv')}
    prices = pd.read_csv(FROZEN/'prices.csv', index_col=0, parse_dates=True, float_precision='round_trip')
    feature_input = ROOT/'models/meta_model/meta_dataset.csv'
    saved = pd.read_csv(feature_input, usecols=['ticker','Date','adx'], parse_dates=['Date'])
    features = build_features(prices, saved)
    features.to_csv(OUTPUT/'causal_features.csv', index=False)
    ledger, decisions, predictions = run_allocations(prices, features)
    baseline = pd.read_csv(FROZEN/'daily_ledger.csv', parse_dates=['date'])
    baseline = baseline.loc[baseline.strategy.isin(['Equal weight','Minimum variance'])].copy()
    schedule = ledger.loc[ledger.strategy == NAMES[0]].set_index('date').rebalance
    baseline['rebalance'] = baseline.date.map(schedule)
    ledger = pd.concat([ledger, baseline], ignore_index=True)
    if ledger.rebalance.isna().any():
        raise ValueError('Frozen baseline calendar mismatch')
    ledger.to_csv(OUTPUT/'daily_ledger.csv', index=False)
    write_json(OUTPUT/'decisions.json', decisions)
    write_json(OUTPUT/'predictions.json', predictions)
    summary = evaluate(ledger)
    summary.update({'evaluation_status': 'completed_retrospective_walk_forward',
        'holdout_start': '2025-01-01', 'holdout_end': '2025-12-31', 'observations': 249,
        'sentiment_coverage': 'unavailable_in_historical_replay',
        'horizon_years': 10, 'cost_bps': 10, 'rebalance_sessions': 21, 'lookback_sessions': 504,
        'bootstrap': {'method': 'paired non-circular moving-block', 'block_sessions': 21, 'replicates': 10000, 'seed': 20260927, 'confidence': .95},
        'scope': 'Retrospective causal replay on five Indian stocks and an already inspected 2025 window. Fixed ten-year horizon. Aggressive AI Black-Litterman is the production personalized path; aggressive target return is a no-AI control. Not a confirmatory untouched test or a validation of every horizon or live model.',
        'limitations': 'Conservative 20% caps force equal weight with five stocks. Historical FinBERT is unavailable. The newly retrained five-stock MarketMind RF is not the saved 99-stock classifier. ADX uses a frozen trailing-feature snapshot; retrospectively adjusted inputs are not vintage-certified. No parameter tuning on results.',
        'model': 'MarketMind A architecture: 250-tree balanced Random Forest, seed 42, 14 features, causal HMM, five-session matured labels; refit each rebalance',
        'turnover_definition': 'Mean total absolute traded weight per scheduled holdout rebalance; costs 10bps per total absolute traded weight. Drift between rebalances; no final liquidation.',
        'risk_interpretation': 'Lower volatility requires a negative difference; smaller drawdown loss requires a positive difference because max drawdown is signed. Intervals are exploratory, unadjusted for multiple comparisons.'})
    pd.DataFrame(summary['metrics']).to_csv(OUTPUT/'holdout_metrics.csv', index=False)
    write_json(OUTPUT/'summary.json', summary)
    outputs = {p.name: digest(p) for p in OUTPUT.iterdir() if p.is_file() and p.name != 'manifest.json'}
    write_json(OUTPUT/'manifest.json', {'created_at': datetime.now(timezone.utc).isoformat(),
        'source_sha256': source_hashes, 'input_sha256': inputs, 'output_sha256': outputs,
        'protocol': 'research/PHASE8_PROTOCOL.md', 'model_refits': len(predictions)//len(prices.columns)})
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()

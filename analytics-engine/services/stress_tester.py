"""Window replay and empirical factor stress estimates in portfolio base currency."""
import numpy as np
import pandas as pd

from services.data_fetcher import get_portfolio_data, normalize_currency_prices

# Factor shocks are scenario assumptions. Historical replay uses observed closes.
SCENARIOS = {
    '2008 Financial Crisis': (-.40, ('2007-10-09', '2009-03-09')),
    'COVID Crash 2020': (-.30, ('2020-02-19', '2020-03-23')),
    'Tech Sector Crash': (-.35, ('2022-01-03', '2022-06-16')),
    'Rate Hike Shock': (-.15, None),
    'India VIX Shock': (-.25, None),
}


def get_stress_summary(tickers, weights, portfolio_value=100000, *, prices=None,
                       benchmark_returns=None, benchmark_name=None):
    weights = np.asarray(weights, dtype=float)
    if (len(weights) != len(tickers) or not np.isfinite(weights).all() or
            (weights < 0).any() or not np.isclose(weights.sum(), 1) or
            not np.isfinite(portfolio_value) or portfolio_value <= 0):
        raise ValueError('Stress testing requires valid weights and a positive portfolio value')
    if prices is None:
        start, end = '2020-01-01', str(pd.Timestamp.today().date())
        data = get_portfolio_data(tickers, start, end)
        currencies = data['currencies']
        base = 'INR' if 'INR' in currencies.values() else 'USD'
        prices, _, _ = normalize_currency_prices(data['prices'], currencies, base, start, end)
    prices = prices.loc[:, tickers].sort_index()
    returns = prices.pct_change(fill_method=None)
    reference = benchmark_returns if benchmark_returns is not None else returns.dot(weights)
    reference_name = benchmark_name or ('supplied benchmark' if benchmark_returns is not None else 'current-weight portfolio')
    factors = {}
    for ticker in tickers:
        sample = pd.concat([returns[ticker], reference], axis=1).dropna()
        asset, market = sample.iloc[:, 0], sample.iloc[:, 1]
        if len(sample) < 2 or not np.isfinite(market.var()) or market.var() <= 0:
            raise ValueError(f'Insufficient reference return variation for {ticker}')
        beta = asset.cov(market) / market.var()
        residual_vol = (asset - beta * market).std() * np.sqrt(252)
        factors[ticker] = float(beta), float(residual_vol)

    rows, scenarios = [], {}
    for name, (shock, window) in SCENARIOS.items():
        contributions, amounts = {}, {}
        for ticker, weight in zip(tickers, weights):
            beta, idio = factors[ticker]
            series = prices[ticker].dropna()
            replay = window and all(pd.Timestamp(date) in series.index for date in window)
            if replay:
                change = float(series.loc[window[1]] / series.loc[window[0]] - 1)
                method = 'realized_historical_replay'
            else:
                change = float(np.clip(beta * shock - .5 * idio, -.95, .20))
                method = 'beta_idiosyncratic_factor'
            amount = float(portfolio_value * weight * change)
            amounts[ticker] = amount
            contributions[ticker] = {'scenario_method': method, 'holding_shock': change,
                'weight': float(weight), 'weighted_return_contribution': float(weight * change),
                'value_change': amount, 'beta_used': None if replay else beta,
                'benchmark_shock': None if replay else shock, 'idiosyncratic_volatility': None if replay else idio}
        loss = sum(amounts.values())
        remaining = portfolio_value + loss
        methods = {h['scenario_method'] for h in contributions.values()}
        scenarios[name] = {
            'scenario_method': methods.pop() if len(methods) == 1 else None,
            'reference': reference_name, 'benchmark_shock': shock, 'window': window,
            'holdings': contributions, 'stressed_value': remaining, 'value_change': loss,
            'recovery_gain_required': max(0., portfolio_value / remaining - 1) if remaining > 0 else None,
        }
        rows.append({'Scenario': name, 'Portfolio Loss': round(loss, 2),
                     'Portfolio Loss (%)': round(loss / portfolio_value * 100, 2),
                     'Remaining Value': round(remaining, 2), **{t: round(v, 2) for t,v in amounts.items()}})
    table = pd.DataFrame(rows).set_index('Scenario')
    worst = min(scenarios, key=lambda key: scenarios[key]['value_change'])
    worst_change = scenarios[worst]['value_change']
    return {'stress_table': table, 'scenarios': scenarios, 'worst_scenario': worst,
            'worst_loss': worst_change, 'worst_loss_pct': worst_change / portfolio_value * 100}


def run_stress_test(tickers, weights, portfolio_value=100000, **kwargs):
    return get_stress_summary(tickers, weights, portfolio_value, **kwargs)['stress_table']


def get_worst_scenario(stress_results):
    return stress_results['Portfolio Loss'].idxmin()

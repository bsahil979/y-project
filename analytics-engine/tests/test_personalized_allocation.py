from unittest.mock import patch
import numpy as np
import pandas as pd
import pytest
from services.portfolio_optimizer import PortfolioOptimizer, get_profile_constraints
from services.recommendation_engine import generate_recommendations


@pytest.fixture
def returns():
    rng = np.random.default_rng(82)
    data = rng.normal(size=(600, 6)) * np.linspace(.005, .025, 6)
    data += np.linspace(.0001, .0014, 6) - data.mean(axis=0)
    return pd.DataFrame(data, columns=list('ABCDEF'), index=pd.bdate_range('2022-01-01', periods=600))


def test_profiles_change_objective_caps_and_weights(returns):
    opt = PortfolioOptimizer(returns)
    c = opt.optimize_personalized('conservative', 2)
    a = opt.optimize_personalized('aggressive', 10)
    m = opt.optimize_personalized('moderate')
    for result, cap in [(c, .2), (m, .3), (a, .4)]:
        assert result['success'], result
        assert sum(result['weights'].values()) == pytest.approx(1)
        assert max(result['weights'].values()) <= cap + 1e-7
        assert min(result['weights'].values()) >= -1e-7
    assert c['objective_used'] == 'minimum_volatility'
    assert m['objective_used'] == 'maximum_sharpe'
    assert a['objective_used'] == 'target_return'
    assert c['weights'] != a['weights']
    assert c['beta_penalty'] > 0
    assert c['beta_reference'] == 'equal_weight_asset_basket'
    assert a['performance']['return'] >= a['target_return_used'] - 1e-7


def test_small_universe_and_infeasible_caps(returns):
    assert get_profile_constraints('conservative', n_assets=4)['max_weight_cap'] == .3
    assert get_profile_constraints('conservative', n_assets=1)['max_weight_cap'] == 1
    for profile in ['moderate', 'aggressive']:
        result = PortfolioOptimizer(returns.iloc[:, :2]).optimize_personalized(profile)
        assert result['status'] == 'infeasible'
        assert result['weights'] == {}


def test_failed_solver_does_not_emit_unconstrained_weights(returns):
    from types import SimpleNamespace
    with patch('services.portfolio_optimizer.minimize', return_value=SimpleNamespace(
            success=False, x=np.array([1., 0, 0, 0, 0, 0]), message='failed')):
        result = PortfolioOptimizer(returns).optimize_personalized('conservative')
    assert not result['success']
    assert not result['weights']


@pytest.mark.parametrize('horizon', [0, -1, float('nan'), float('inf'), True])
def test_invalid_horizon(returns, horizon):
    with pytest.raises(ValueError):
        PortfolioOptimizer(returns).optimize_personalized('moderate', horizon)


def test_recommendations_follow_profile(returns):
    args = dict(tickers=list(returns), weights=[.35, .13, .13, .13, .13, .13], portfolio_value=10000,
                risk_summary=pd.DataFrame(), portfolio_returns=returns, regime={}, stress={},
                portfolio_score={}, attribution={}, risk_budget={}, forecast_details={}, marketmind_details={})
    c_alloc = PortfolioOptimizer(returns).optimize_personalized('conservative')
    c = generate_recommendations(**args, risk_preference='conservative', personalized_allocation=c_alloc)
    a = generate_recommendations(**args, risk_preference='aggressive')
    assert any(r['id'] == 'reduce-A' for r in c)
    assert not any(r['id'] == 'reduce-A' for r in a)
    trades = [r for r in c if r['action'] == 'rebalance']
    assert trades
    assert all(r['supporting_metrics']['target_weight'] <= .2 + 1e-7 for r in trades)


def test_api_propagation_validation_and_cache(returns):
    from fastapi.testclient import TestClient
    from api import app, portfolio_analyze_cache
    client = TestClient(app)
    portfolio_analyze_cache.clear()
    payload = dict(tickers=list(returns), weights=[1/6]*6, portfolio_revision='same')
    with patch('services.portfolio_pipeline.run_portfolio_pipeline', side_effect=lambda **kw: {'profile': kw['risk_preference'], 'years': kw['investment_horizon_years'], 'source': kw['horizon_source']}) as run:
        for profile, years in [('conservative', 2), ('aggressive', 2), ('aggressive', 8)]:
            response = client.post('/portfolio/analyze', json={**payload, 'risk_preference': profile, 'investment_horizon_years': years})
            assert response.status_code == 200
            assert response.json()['profile'] == profile
            assert response.json()['years'] == years
        assert run.call_count == 3
        for source in ['explicit', 'nearest_goal']:
            response = client.post('/portfolio/analyze', json={**payload, 'risk_preference': 'aggressive', 'investment_horizon_years': 1, 'horizon_source': source})
            assert response.json()['source'] == source
        assert run.call_count == 5
    for endpoint in ['/portfolio/analyze', '/portfolio/optimize']:
        assert client.post(endpoint, json={**payload, 'risk_preference': 'invalid'}).status_code == 422
        assert client.post(endpoint, json={**payload, 'investment_horizon_years': -2}).status_code == 422
    with patch('api.get_portfolio_data', return_value={'returns': returns, 'prices': 100*(1+returns).cumprod(), 'currencies': dict.fromkeys(returns, 'USD')}):
        response = client.post('/portfolio/optimize', json={**payload, 'risk_preference': 'conservative', 'investment_horizon_years': 3})
        assert response.status_code == 200, response.text
        assert response.json()['metadata']['max_weight_cap'] == .2
        assert response.json()['metadata']['investment_horizon_years'] == 3
        response = client.post('/portfolio/optimize', json={**payload, 'risk_preference': 'aggressive',
                               'investment_horizon_years': 1, 'horizon_source': 'nearest_goal'})
        assert response.json()['metadata']['horizon_source'] == 'nearest_goal'
        assert response.json()['metadata']['horizon_modifier'] == 'short_term_protection'


def test_pipeline_preserves_comparisons_and_adds_profile_metadata(returns):
    from services.portfolio_pipeline import run_portfolio_pipeline
    from contextlib import ExitStack
    prices = 100 * (1 + returns).cumprod()
    data = {'prices': prices, 'returns': returns, 'currencies': {a: 'USD' for a in returns}, 'price_metadata': {}}
    with ExitStack() as stack:
        for name, value in {
            'get_portfolio_data': data,
            'detect_market_regime_hmm': {'current_regime': 'Neutral'},
            'get_stress_summary': {}, 'compute_benchmark_comparison': {},
            'compute_attribution': {}, 'compute_portfolio_score': {},
            'fit_allocations': {'status': 'success', 'marker': 'existing_hmm'},
        }.items():
            stack.enter_context(patch('services.portfolio_pipeline.' + name, return_value=value))
        for profile, cap in [('conservative', .2), ('aggressive', .4)]:
            result = run_portfolio_pipeline(list(returns), [1/6]*6, include_optional_ml=False,
                                            risk_preference=profile, investment_horizon_years=4, horizon_source='nearest_goal')
            assert result['personalized_allocation']['success']
            assert result['metadata']['applied_profile'] == profile
            assert result['metadata']['max_weight_cap'] == cap
            assert result['metadata']['investment_horizon_years'] == 4
            assert result['metadata']['personalized_constraints']['horizon_source'] == 'nearest_goal'
            assert result['personalized_allocation']['horizon_modifier'] == 'baseline_medium_term'
            assert result['allocation']['method'] == 'min_volatility'
            assert result['regime_allocation']['marker'] == 'existing_hmm'


@pytest.mark.parametrize('profile,baseline', [('conservative', .2), ('moderate', .3), ('aggressive', .4)])
@pytest.mark.parametrize('years,modifier', [(1, 'short_term_protection'), (2, 'short_term_protection'),
    (2.5, 'baseline_medium_term'), (3, 'baseline_medium_term'), (6, 'baseline_medium_term'),
    (6.5, 'baseline_medium_term'), (7, 'long_term_growth'), (10, 'long_term_growth')])
def test_horizon_boundaries(profile, baseline, years, modifier):
    policy = get_profile_constraints(profile, years, n_assets=10)
    assert policy['max_weight_cap'] == pytest.approx(baseline - .05 if years <= 2 else baseline)
    assert policy['horizon_modifier'] == modifier
    assert policy['horizon_source'] == 'explicit'
    if profile == 'conservative':
        assert policy['beta_penalty'] == pytest.approx(.05 * (1.25 if years <= 2 else 1))
        assert policy['volatility_penalty'] == (1.25 if years <= 2 else 1)


def test_short_aggressive_horizon_changes_actual_solve_and_volatility(returns):
    optimizer = PortfolioOptimizer(returns)
    short = optimizer.optimize_personalized('aggressive', 1, 'nearest_goal')
    long = optimizer.optimize_personalized('aggressive', 10)
    assert short['success'] and long['success']
    assert short['objective_used'] == 'maximum_sharpe'
    assert short['effective_profile'] == 'moderate'
    assert 'target_return_used' not in short
    assert short['max_weight_cap'] < long['max_weight_cap']
    assert max(short['weights'].values()) <= .35 + 1e-7
    assert short['performance']['volatility'] < long['performance']['volatility']
    assert short['horizon_source'] == 'nearest_goal'


def test_floor_default_and_sources(returns):
    for profile in ['conservative', 'moderate', 'aggressive']:
        result = PortfolioOptimizer(returns.iloc[:, :2]).optimize_personalized(profile, 1)
        assert result['success']
        assert result['max_weight_cap'] >= .5
    default = get_profile_constraints('moderate', n_assets=6)
    assert default['horizon_source'] == 'default'
    assert default['horizon_modifier'] == 'default_profile'
    for years, source in [(None, 'explicit'), (None, 'nearest_goal'), (1, 'default'), (1, 'bad')]:
        with pytest.raises(ValueError):
            get_profile_constraints('moderate', years, n_assets=6, horizon_source=source)


def test_recommendations_use_adjusted_cap_and_explain_source(returns):
    allocation = PortfolioOptimizer(returns).optimize_personalized('aggressive', 1, 'nearest_goal')
    recommendations = generate_recommendations(list(returns), [.38, .124, .124, .124, .124, .124],
        10000, pd.DataFrame(), returns, {}, {}, {}, {}, {}, {}, {},
        risk_preference='aggressive', personalized_allocation=allocation)
    assert any(r['id'] == 'reduce-A' for r in recommendations)
    for rec in recommendations:
        assert rec['constraint_metadata']['horizon_source'] == 'nearest_goal'
        assert rec['constraint_metadata']['max_weight_cap'] == pytest.approx(.35)
        assert 'short_term_protection' in rec['reason']
        assert 'maximum_sharpe' in rec['reason']

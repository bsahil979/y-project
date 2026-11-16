from contextlib import ExitStack
from unittest.mock import patch, Mock
import numpy as np
import pandas as pd
import pytest
from services.portfolio_optimizer import PortfolioOptimizer, build_ai_black_litterman_views

@pytest.fixture
def optimizer():
    return PortfolioOptimizer(pd.DataFrame(np.random.default_rng(31).normal(0, .012, (600, 6)), columns=list('ABCDEF'), index=pd.bdate_range('2022-01-01', periods=600)))

def views(opt, mm=None, sentiment=None):
    pi = 2.5 * opt.cov_matrix.to_numpy() @ np.full(opt.n_assets, 1/opt.n_assets)
    return build_ai_black_litterman_views(dict(zip(opt.assets, pi)), dict(zip(opt.assets, np.sqrt(np.diag(opt.cov_matrix)))), mm, sentiment)

def test_aligned_positive_views_increase_weight(optimizer):
    v = views(optimizer, {'A': {'buy': .8, 'hold': .15, 'sell': .05}}, {'A': .8})
    r = optimizer.black_litterman(v, 'aggressive')
    assert r['success'] and r['weights']['A'] > r['prior_weights']['A']
    assert r['provenance']['A']['aligned_signals']
    signal = .65*.75 + .35*.8
    assert v['Q']['A'] == pytest.approx(r['prior_returns']['A'] + signal*.5*np.sqrt(optimizer.cov_matrix.loc['A','A']))

def test_missing_news_neutral_and_disagreement(optimizer):
    mm = {'A': {'2': .8, '1': .1, '0': .1}}
    missing, neutral, opposing = [views(optimizer, mm, {'A': s}) for s in [None, 0, -.7]]
    assert missing['provenance']['A']['finbert_score'] is None
    assert missing['provenance']['A']['composite_signal'] == pytest.approx(.7)
    assert neutral['provenance']['A']['composite_signal'] == pytest.approx(.65*.7)
    assert opposing['Omega'][0][0] > missing['Omega'][0][0] > neutral['Omega'][0][0]
    assert not missing['provenance']['A']['fallback_to_prior']

def test_prior_only_and_finbert_only(optimizer):
    r = optimizer.black_litterman(views(optimizer))
    assert r['success'] and r['signal_status'] == 'prior_only'
    assert r['weights'] == pytest.approx(r['prior_weights'])
    assert all(v['fallback_to_prior'] for v in r['provenance'].values())
    assert views(optimizer, sentiment={'A': -.8})['provenance']['A']['composite_signal'] == -.8

@pytest.mark.parametrize('profile', ['conservative', 'moderate', 'aggressive'])
@pytest.mark.parametrize('years', [1,10])
def test_extreme_views_obey_caps(optimizer, profile, years):
    r = optimizer.black_litterman(views(optimizer, {'A': {'buy': 1, 'hold': 0, 'sell': 0}}, {'A': 1}), profile, years)
    assert r['success'], r
    assert max(r['weights'].values()) <= r['max_weight_cap']
    assert min(r['weights'].values()) >= 0
    assert sum(r['weights'].values()) == pytest.approx(1)

def test_infeasibility_and_failure(optimizer):
    small = PortfolioOptimizer(optimizer.returns.iloc[:,:2])
    r = small.black_litterman(views(small), 'aggressive')
    assert r['status'] == 'infeasible' and r['weights'] == {}
    with patch('services.portfolio_optimizer.minimize', return_value=Mock(success=False, x=np.ones(6)/6)):
        r = optimizer.black_litterman(views(optimizer))
    assert not r['success'] and r['weights'] == {}

@pytest.mark.parametrize('score', [None, float('nan'), 2])
def test_invalid_inputs_fall_back(optimizer, score):
    v = views(optimizer, {'A': {'buy': .8, 'hold': .8, 'sell': .8}}, {'A': score})
    assert v['provenance']['A']['fallback_to_prior']
    assert np.isfinite(v['Omega']).all()

def test_finbert_excludes_vader():
    from services.sentiment_analyzer import get_sentiment_analysis
    with patch('services.sentiment_analyzer._fetch_yahoo_news', return_value=[]), patch('services.sentiment_analyzer._fetch_google_news', return_value=[]):
        assert get_sentiment_analysis('A')['finbert_score'] is None
    articles = [{'title': 'one', 'source': 'test'}, {'title': 'two', 'source': 'test'}]
    scores = [{'compound': .8, 'model': 'FinBERT', 'pos': .8, 'neg': 0, 'neu': .2}, {'compound': -.8, 'model': 'VADER', 'pos': 0, 'neg': .8, 'neu': .2}]
    with patch('services.sentiment_analyzer._fetch_yahoo_news', return_value=articles), patch('services.sentiment_analyzer._fetch_google_news', return_value=[]), patch('services.sentiment_analyzer._score_with_finbert', side_effect=scores):
        r = get_sentiment_analysis('A')
    assert r['finbert_score'] == .8 and r['finbert_articles_analyzed'] == 1
    assert r['overall_score'] == 0

@pytest.mark.parametrize('optional', [True,False])
def test_pipeline(optimizer, optional):
    from services.portfolio_pipeline import run_portfolio_pipeline
    returns = optimizer.returns
    with ExitStack() as stack:
        for name, value in {
            'get_portfolio_data': {'prices': 100*(1+returns).cumprod(), 'returns': returns, 'currencies': {a:'USD' for a in returns}, 'price_metadata': {}},
            'detect_market_regime_hmm': {'current_regime':'Neutral'}, 'get_stress_summary': {},
            'compute_benchmark_comparison': {}, 'compute_attribution': {}, 'compute_portfolio_score': {},
            'fit_allocations': {'status':'success'}, 'get_sentiment_analysis': {'finbert_score': .8},
        }.items():
            stack.enter_context(patch('services.portfolio_pipeline.'+name, return_value=value))
        model = stack.enter_context(patch('services.portfolio_pipeline.MarketMindMetaModel')).return_value
        model.is_ready.return_value = True
        model.predict_for_ticker.side_effect = lambda t: {'class_probabilities': {'2': .9 if t=='A' else .1, '1': .05, '0': .05 if t=='A' else .85}}
        r = run_portfolio_pipeline(list(returns), [1/6]*6, include_optional_ml=optional, risk_preference='aggressive', investment_horizon_years=10)
    ai = r['ai_black_litterman_allocation']
    assert ai['success'] and r['personalized_allocation'] == ai
    assert r['metadata']['objective_used'] == 'black_litterman'
    assert ai['signal_status'] == ('ai_views' if optional else 'prior_only')
    if optional:
        assert ai['provenance']['A']['marketmind_net_prob'] == pytest.approx(.85)
        assert any(rec['id']=='ai-view-A' for rec in r['recommendations'])
    else:
        model.predict_for_ticker.assert_not_called()

def test_primary_objective_keeps_short_horizon_protection(optimizer):
    v = views(optimizer, {'A': (.9, .05, .05)}, {'A': .8})
    short = optimizer.optimize_personalized('aggressive', 1, ai_views=v)
    long = optimizer.optimize_personalized('aggressive', 10, ai_views=v)
    assert short['success'] and long['success']
    assert short['objective_used'] == 'maximum_sharpe'
    assert long['objective_used'] == 'black_litterman'
    assert short['max_weight_cap'] < long['max_weight_cap']


def test_marketmind_named_class_order(tmp_path):
    from trading_engine.meta_model import MarketMindMetaModel
    model = MarketMindMetaModel(model_dir=str(tmp_path))
    model.feature_columns = ['feature']
    model.model = Mock(classes_=np.array([2, 0, 1]))
    model.model.predict_proba.return_value = np.array([[.7, .2, .1]])
    r = model.predict_single(pd.DataFrame({'feature': [0]}))
    assert r['directional_probabilities'] == {'buy': .7, 'hold': .1, 'sell': .2}


def test_vader_only_is_not_finbert():
    from services.sentiment_analyzer import get_sentiment_analysis
    with patch('services.sentiment_analyzer._fetch_yahoo_news', return_value=[{'title':'one','source':'test'}]), patch('services.sentiment_analyzer._fetch_google_news', return_value=[]), patch('services.sentiment_analyzer._score_with_finbert', return_value={'compound': .8,'model':'VADER','pos': .8,'neg':0,'neu':.2}):
        r = get_sentiment_analysis('A')
    assert r['finbert_score'] is None and r['finbert_articles_analyzed'] == 0

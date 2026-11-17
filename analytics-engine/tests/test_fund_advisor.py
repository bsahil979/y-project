import numpy as np
import pandas as pd
from services import fund_advisor as advisor


def history(identifier):
    dates=pd.bdate_range('2024-01-01', periods=300)
    changes=np.sin(np.arange(300)/7)*.015+.0002
    return pd.Series(100*np.cumprod(1+changes),index=dates), {'scheme_code':identifier,'name':identifier,'category':'Equity Scheme - Small Cap Fund','source':'fixture'}


def test_fund_portfolio_profile_rules_and_metrics(monkeypatch):
    monkeypatch.setattr(advisor,'fund_history',history)
    req=advisor.FundAnalysisRequest(holdings=[{'identifier':'123456','quantity':2},{'identifier':'123457','quantity':1}],risk_preference='conservative',investment_horizon_years=1)
    result=advisor.analyze_funds(req)
    assert result['status']=='ok'
    assert abs(sum(f['weight'] for f in result['funds'])-1)<1e-10
    assert result['metrics']['max_drawdown']<0
    assert result['metrics']['annualized_volatility']>0
    assert {r['kind'] for r in result['recommendations']} >= {'concentration','horizon','risk_match','diversification'}
    assert result['profile']['concentration_review_threshold']==.20
    req.risk_preference='aggressive';req.investment_horizon_years=10
    other=advisor.analyze_funds(req)
    assert other['profile']['concentration_review_threshold']==.45
    assert not any(r['kind'] in ('horizon','risk_match') for r in other['recommendations'])


def test_missing_fund_prevents_partial_portfolio(monkeypatch):
    def fail(identifier): raise ValueError('History unavailable')
    monkeypatch.setattr(advisor,'fund_history',fail)
    result=advisor.analyze_funds(advisor.FundAnalysisRequest(holdings=[{'identifier':'123456','quantity':1}]))
    assert result['status']=='unavailable'
    assert 'metrics' not in result


def test_metrics_known_drawdown():
    values=pd.Series([100.,120.,90.,108.],index=pd.to_datetime(['2024-01-01','2024-05-01','2024-09-01','2025-01-01']))
    result=advisor.metrics(values)
    assert abs(result['max_drawdown']+.25)<1e-10
    assert abs(result['total_return']-.08)<1e-10

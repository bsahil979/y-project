"""NAV-based fund portfolio diagnostics; no price forecasting or stock-model substitution."""
import datetime as dt
import math
import time
from threading import Lock
from typing import Literal
import numpy as np
import pandas as pd
import requests
from fastapi import HTTPException
from pydantic import BaseModel, Field
from services.fund_disclosures import disclosure_for, disclosed_overlaps
from services.fund_benchmarks import compare_benchmark
from services.fund_nav import router, parse_nav

_cache = {}
_lock = Lock()


def cached_get(url, text=False):
    key = (url, text)
    with _lock:
        hit = _cache.get(key)
    if hit and time.time() - hit[0] < 3600:
        return hit[1]
    r = requests.get(url, timeout=25)
    r.raise_for_status()
    value = r.text if text else r.json()
    with _lock:
        _cache[key] = (time.time(), value)
    return value


class FundPosition(BaseModel):
    identifier: str = Field(pattern=r'^(?:[0-9]{5,8}|IN[A-Z0-9]{10})$')
    quantity: float = Field(gt=0, allow_inf_nan=False)


class FundAnalysisRequest(BaseModel):
    holdings: list[FundPosition] = Field(min_length=1, max_length=30)
    risk_preference: Literal['conservative', 'moderate', 'aggressive'] = 'moderate'
    investment_horizon_years: float | None = Field(default=None, gt=0, le=100, allow_inf_nan=False)


def fund_history(identifier):
    publication = cached_get('https://www.amfiindia.com/spages/NAVAll.txt', text=True)
    resolved = parse_nav(publication, identifier)
    code = resolved['scheme_code']
    payload = cached_get('https://api.mfapi.in/mf/' + code)
    if str(payload.get('meta', {}).get('scheme_code')) != code:
        raise ValueError('Historical scheme identity mismatch')
    points = {}
    today = dt.date.today()
    for row in payload.get('data', []):
        try:
            date = dt.datetime.strptime(row['date'], '%d-%m-%Y').date()
            nav = float(row['nav'])
            if math.isfinite(nav) and nav > 0 and date <= today:
                points[pd.Timestamp(date)] = nav
        except (KeyError, TypeError, ValueError):
            continue
    series = pd.Series(points, dtype=float).sort_index()
    series = series.loc[series.index >= pd.Timestamp(today - dt.timedelta(days=3 * 366))]
    if len(series) < 61:
        raise ValueError('At least 61 NAV observations are required')
    if (today - series.index[-1].date()).days > 10:
        raise ValueError('Latest historical NAV is more than 10 days old')
    return series, {'scheme_code':code, 'name':resolved['name'],
                    'category':payload['meta'].get('scheme_category', 'Unavailable'),
                    'source':'AMFI identity / MFapi historical NAV'}


def metrics(values):
    returns = values.pct_change().dropna()
    years = (values.index[-1] - values.index[0]).days / 365.25
    annual_periods = len(returns) / years
    vol = float(returns.std(ddof=1) * np.sqrt(annual_periods))
    cumulative = float(values.iloc[-1] / values.iloc[0] - 1)
    cagr = float((1 + cumulative) ** (1 / years) - 1)
    return {'total_return':cumulative, 'cagr':cagr if years >= 1 else None,
            'annualized_volatility':vol,
            'max_drawdown':float((values / values.cummax() - 1).min()),
            'sharpe_ratio':float(returns.mean() * annual_periods / vol) if vol > 1e-12 else None,
            'risk_free_rate_assumption':0.0}


def analyze_funds(request):
    quantities = {}
    for holding in request.holdings:
        quantities[holding.identifier] = quantities.get(holding.identifier, 0) + holding.quantity
    histories, info, issues = {}, {}, []
    for identifier in quantities:
        try:
            histories[identifier], info[identifier] = fund_history(identifier)
        except (requests.RequestException, ValueError, LookupError, KeyError, TypeError) as exc:
            issues.append({'identifier':identifier, 'reason':str(exc) if not isinstance(exc, requests.RequestException) else 'NAV provider unavailable'})
    if issues:
        return {'status':'unavailable', 'issues':issues, 'message':'All funds need valid history; no partial portfolio score was calculated.'}
    prices = pd.concat(histories, axis=1).dropna()
    if len(prices) < 61:
        return {'status':'unavailable', 'issues':[], 'message':'Fewer than 61 common NAV dates. No synthetic or forward-filled NAVs used.'}
    amounts = prices.iloc[-1] * pd.Series(quantities)
    weights = amounts / amounts.sum()
    # Hypothetical constant units over the common period, not personal transaction performance.
    portfolio_values = prices.mul(pd.Series(quantities)).sum(axis=1)
    portfolio = metrics(portfolio_values)
    funds = [{**info[k], 'identifier':k, 'units':quantities[k], 'nav':float(prices[k].iloc[-1]),
              'value':float(amounts[k]), 'weight':float(weights[k]), **metrics(prices[k])} for k in quantities]
    benchmark_cache = {}
    for fund in funds:
        fund['disclosure'] = disclosure_for(fund['name'])
        fund['benchmark'] = compare_benchmark(fund['name'], prices[fund['identifier']], benchmark_cache)
    cap = {'conservative':.25, 'moderate':.35, 'aggressive':.45}[request.risk_preference]
    short = request.investment_horizon_years is not None and request.investment_horizon_years <= 2
    if short: cap -= .05
    recommendations = []
    for fund in funds:
        if fund['weight'] > cap:
            recommendations.append({'kind':'concentration', 'message':f"Review concentration in {fund['name']}: {fund['weight']:.1%} of fund value exceeds your {cap:.0%} review threshold. Consider diversifying future contributions; this is not a sell instruction."})
    equity_share = sum(f['weight'] for f in funds if 'equity' in f['category'].lower())
    small_share = sum(f['weight'] for f in funds if 'small cap' in f['category'].lower())
    if short and equity_share > 0:
        recommendations.append({'kind':'horizon', 'message':f"Your goal is within two years, while {equity_share:.1%} of fund value is in equity categories. Review whether money needed for that goal should be held in lower-volatility, liquid instruments."})
    if small_share > 0 and request.risk_preference != 'aggressive':
        recommendations.append({'kind':'risk_match', 'message':f"Small-cap funds make up {small_share:.1%} of fund value. Review this exposure against your {request.risk_preference} preference before adding more."})
    correlation = prices.pct_change().dropna().corr()
    pairs = []
    keys = list(quantities)
    for i, a in enumerate(keys):
        for b in keys[i+1:]:
            value = correlation.loc[a,b]
            if np.isfinite(value): pairs.append({'first':info[a]['name'], 'second':info[b]['name'], 'correlation':float(value)})
    if any(p['correlation'] >= .85 for p in pairs):
        recommendations.append({'kind':'diversification', 'message':'Some funds have historical return correlation of at least 0.85. Multiple fund names may provide limited diversification.'})
    if not recommendations:
        recommendations.append({'kind':'review', 'message':'No configured concentration or category rule triggered. This is not a suitability guarantee; review your goal horizon and ability to absorb the historical drawdown.'})
    return {'status':'ok', 'base_currency':'INR', 'portfolio_value':float(amounts.sum()), 'metrics':portfolio,
            'funds':funds, 'disclosed_overlaps':disclosed_overlaps(funds), 'correlations':pairs, 'recommendations':recommendations,
            'profile':{'risk_preference':request.risk_preference,'investment_horizon_years':request.investment_horizon_years,'concentration_review_threshold':cap},
            'period':{'start':str(prices.index[0].date()),'end':str(prices.index[-1].date()),'observations':len(prices)},
            'methodology':'Historical constant-unit replay of current holdings on common NAV dates. Not personal XIRR or a forecast. Sharpe assumes 0% risk-free rate. Recommendations are deterministic rules, not a trained prediction model.',
            'limitations':['Overlap uses only published top holdings with the same disclosure date','Fees require a matching plan disclosure. Taxes and exit loads are excluded','No optimized target weights or buy/sell execution']}


@router.post('/funds/analyze')
def fund_analysis(request: FundAnalysisRequest):
    return analyze_funds(request)

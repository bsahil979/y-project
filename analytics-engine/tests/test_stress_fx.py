import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch
from services import data_fetcher
from services.stress_tester import get_stress_summary


def test_high_beta_stress_contribution_and_recovery():
    dates = pd.bdate_range('2023-01-01', periods=81)
    market = pd.Series(np.sin(np.arange(80))*.01, index=dates[1:])
    prices = pd.DataFrame(100.,index=dates,columns=['low','high'])
    for ticker,beta in [('low',.5),('high',1.5)]:
        prices.loc[dates[1:],ticker] = 100*(1+beta*market).cumprod()
    result = get_stress_summary(list(prices),[.6,.4],10000,prices=prices,benchmark_returns=market)
    scenario = result['scenarios']['2008 Financial Crisis']
    for ticker,beta in [('low',.5),('high',1.5)]:
        holding = scenario['holdings'][ticker]
        assert holding['beta_used'] == pytest.approx(beta)
        assert holding['holding_shock'] == pytest.approx(-.4*beta)
        assert holding['scenario_method'] == 'beta_idiosyncratic_factor'
    assert scenario['holdings']['high']['holding_shock'] < scenario['holdings']['low']['holding_shock']
    assert scenario['value_change'] == pytest.approx(-3600)
    assert scenario['recovery_gain_required'] == pytest.approx(10000/6400-1)


def test_historical_replay_uses_exact_window_and_partial_coverage():
    dates = pd.bdate_range('2020-02-01','2020-04-01')
    prices = pd.DataFrame({'A':np.linspace(120,80,len(dates)), 'B':100+np.sin(np.arange(len(dates)))},index=dates)
    prices.loc['2020-02-19','B'] = np.nan
    result = get_stress_summary(['A','B'],[.5,.5],prices=prices)
    holdings = result['scenarios']['COVID Crash 2020']['holdings']
    assert holdings['A']['scenario_method'] == 'realized_historical_replay'
    assert holdings['A']['holding_shock'] == pytest.approx(prices.loc['2020-03-23','A']/prices.loc['2020-02-19','A']-1)
    assert holdings['B']['scenario_method'] == 'beta_idiosyncratic_factor'


def test_fx_cache_and_strict_date_alignment():
    dates = pd.bdate_range('2023-01-02',periods=4)
    rates = pd.Series([80.,82.], index=dates[[1,3]])
    prices = pd.DataFrame({'US':[2.,3.,4.,5.]},index=dates)
    data_fetcher.fetch_usdinr_rates.cache_clear()
    with patch.object(data_fetcher.yf,'download',return_value={'Close':rates}) as fetch:
        for _ in range(2):
            actual,_,fx=data_fetcher.normalize_currency_prices(prices,{'US':'USD'},'INR','2023-01-01','2023-02-01')
        assert fetch.call_count == 1 and fx['fx_dropped_dates']==2
        assert list(actual.US)==[240.,410.]
    data_fetcher.fetch_usdinr_rates.cache_clear()
    with patch.object(data_fetcher.yf,'download',side_effect=OSError('offline')):
        with pytest.raises(data_fetcher.MarketDataUnavailable, match='USDINR=X'):
            data_fetcher.fetch_usdinr_rates('2023-01-01','2023-02-01')

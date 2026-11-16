"""Offline correctness checks. Synthetic inputs here are test fixtures only."""
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from api import app
from services import data_fetcher
from services.portfolio_pipeline import run_portfolio_pipeline
from services.regime_detector import detect_market_regime_hmm


class MidtermPipelineTests(unittest.TestCase):
    def setUp(self):
        data_fetcher._price_cache.clear()
        self.tickers = ['RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS']
        self.weights = [.4, .2, .15, .15, .1]
        rng = np.random.default_rng(42)
        self.prices = pd.DataFrame(
            100 * np.exp(np.cumsum(rng.normal(.0002, [.02, .015, .025, .01, .018], (300, 5)), axis=0)),
            index=pd.bdate_range('2023-01-02', periods=300), columns=self.tickers,
        )
        self.payload = dict(tickers=self.tickers, weights=self.weights, portfolio_value=100000,
                            start='2023-01-01', end='2024-03-01', benchmark=self.tickers[0],
                            include_optional_ml=False)

    def test_prices_preserve_weight_order_and_do_not_backfill(self):
        frame = self.prices[self.tickers[::-1]].copy()
        frame.loc[frame.index[0], self.tickers[0]] = np.nan
        actual = data_fetcher._validated_prices(frame, self.tickers)
        self.assertEqual(list(actual.columns), self.tickers)
        self.assertEqual(actual.index[0], frame.index[1])
        with self.assertRaises(data_fetcher.MarketDataUnavailable):
            data_fetcher._validated_prices(frame.drop(columns=self.tickers[0]), self.tickers)

    def test_provider_failure_never_returns_fabricated_history(self):
        with patch.object(data_fetcher.yf, 'download', side_effect=OSError('offline')), \
             patch.object(data_fetcher, '_stooq_close_series', side_effect=OSError('offline')):
            with self.assertRaises(data_fetcher.MarketDataUnavailable):
                data_fetcher.fetch_price_data(self.tickers, '2023-01-01', '2024-01-01')

    def test_cache_handles_reordered_requests(self):
        with patch.object(data_fetcher.yf, 'download', return_value={'Close': self.prices}):
            first = data_fetcher.fetch_price_data(self.tickers, '2023-01-01', '2024-01-01')
            second = data_fetcher.fetch_price_data(self.tickers[::-1], '2023-01-01', '2024-01-01')
        self.assertEqual(list(first.columns), self.tickers)
        self.assertEqual(list(second.columns), self.tickers[::-1])

    def test_five_stock_api_analysis(self):
        fixture = dict(prices=self.prices[self.tickers[::-1]],
                       returns=self.prices.pct_change().dropna()[self.tickers[::-1]],
                       currencies=dict.fromkeys(self.tickers, 'INR'),
                       price_metadata={
                           'provider': 'Synthetic test fixture',
                           'price_field': 'synthetic close',
                           'adjustment_verified': False,
                           'first_observation': self.prices.index[0].strftime('%Y-%m-%d'),
                           'last_observation': self.prices.index[-1].strftime('%Y-%m-%d'),
                           'price_observations': len(self.prices),
                           'return_observations': len(self.prices) - 1,
                           'dropped_incomplete_rows': 0,
                       })
        with patch('services.portfolio_pipeline.get_portfolio_data', return_value=fixture), \
             patch('services.portfolio_pipeline.get_sentiment_analysis', side_effect=AssertionError('Optional call')):
            response = TestClient(app).post('/portfolio/analyze', json=self.payload)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        expected_vol = float((self.prices.pct_change().dropna() @ self.weights).std() * np.sqrt(252))
        self.assertAlmostEqual(body['risk_budget']['portfolio_volatility'], expected_vol, places=4)
        portfolio_returns = self.prices.pct_change().dropna() @ self.weights
        threshold = float(portfolio_returns.quantile(.05))
        self.assertAlmostEqual(body['risk_budget']['var_95'], threshold, places=4)
        self.assertAlmostEqual(body['risk_budget']['cvar_95'],
                               portfolio_returns[portfolio_returns <= threshold].mean(), places=4)
        allocation = body['allocation']
        self.assertAlmostEqual(sum(allocation['weights'].values()), 1, places=6)
        self.assertTrue(all(weight >= -1e-8 for weight in allocation['weights'].values()))
        self.assertLessEqual(allocation['performance']['volatility'], expected_vol + 1e-5)
        self.assertFalse(allocation['regime_aware'])
        self.assertEqual(body['regime_allocation']['status'], 'ready')
        self.assertTrue(body['regime_allocation']['regime_aware'])
        stress = body['stress_test']
        self.assertAlmostEqual(stress['worst_loss_pct'], stress['worst_loss'] / 100000 * 100)
        self.assertEqual(body['stages']['stress_test']['status'], 'SUCCESS')
        self.assertAlmostEqual(stress['worst_loss_pct'], -23.59936851, places=5)
        self.assertNotIn('stress-test-risk', [item['id'] for item in body['recommendations']])

    def test_invalid_portfolio_rejected_before_network(self):
        with patch('services.portfolio_pipeline.get_portfolio_data', side_effect=AssertionError('Network call')):
            for changes in ({'weights': [-.1, .7, .2, .1, .1]}, {'portfolio_value': 0},
                            {'tickers': [self.tickers[0]] * 5}, {'end': '2020-01-01'}):
                response = TestClient(app).post('/portfolio/analyze', json={**self.payload, **changes})
                self.assertEqual(response.status_code, 400, response.text)

    def test_data_outage_is_503(self):
        with patch('services.portfolio_pipeline.get_portfolio_data',
                   side_effect=data_fetcher.MarketDataUnavailable('History unavailable')):
            response = TestClient(app).post('/portfolio/analyze', json=self.payload)
        self.assertEqual(response.status_code, 503)

    def test_mixed_currency_normalization_and_fx_outage(self):
        currencies = dict.fromkeys(self.tickers, 'INR')
        foreign = self.tickers[-1]
        currencies[foreign] = 'USD'
        fixture = dict(prices=self.prices, currencies=currencies)
        fx = pd.Series(np.linspace(70,80,len(self.prices)), index=self.prices.index)
        payload = dict(self.payload, position_values=[1000,1000,1000,1000,50])
        del payload['weights']
        with patch('services.portfolio_pipeline.get_portfolio_data', return_value=fixture):
            with patch.object(data_fetcher,'fetch_usdinr_rates',return_value=fx):
                response = TestClient(app).post('/portfolio/analyze', json=payload)
                self.assertEqual(response.status_code, 200, response.text)
                result = response.json()
                self.assertEqual(result['base_currency'], 'INR')
                self.assertEqual(result['original_currency'][foreign], 'USD')
                self.assertEqual(result['fx_pair_used'], 'USDINR=X')
                self.assertEqual(result['portfolio_value'], 8000.)
                self.assertEqual(result['weights'][-1], .5)
                converted = self.prices.copy()
                converted[foreign] *= fx
                expected = (converted.pct_change().dropna() @ result['weights']).std()*np.sqrt(252)
                self.assertAlmostEqual(result['risk_budget']['portfolio_volatility'],expected,places=4)
                usd = TestClient(app).post('/portfolio/analyze', json={**payload,'base_currency':'USD'}).json()
                self.assertEqual(usd['portfolio_value'],100.)
                self.assertEqual(usd['weights'],result['weights'])
            with patch.object(data_fetcher,'fetch_usdinr_rates',side_effect=data_fetcher.MarketDataUnavailable('USDINR=X unavailable')):
                response = TestClient(app).post('/portfolio/analyze', json=payload)
                self.assertEqual(response.status_code,503)
                self.assertIn('USDINR=X',response.json()['detail'])

    def test_regime_is_reproducible_and_handles_short_history(self):
        returns = self.prices.pct_change().dropna() @ self.weights
        self.assertEqual(detect_market_regime_hmm(returns), detect_market_regime_hmm(returns))
        self.assertEqual(detect_market_regime_hmm(returns.iloc[:2])['current_regime'], 'Unavailable')


if __name__ == '__main__':
    unittest.main()

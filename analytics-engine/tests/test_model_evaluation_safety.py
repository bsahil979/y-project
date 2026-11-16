import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd
from fastapi import HTTPException
from sklearn.ensemble import RandomForestClassifier

from training.train_all import _evaluate_rf


class ModelEvaluationSafetyTests(unittest.TestCase):
    def test_rf_score_uses_unseen_chronological_block(self):
        rng = np.random.default_rng(7)
        rows = 400
        close = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, rows)))
        data = {'Close': close}
        for feature in ('rsi', 'macd', 'macd_signal', 'adx', 'returns', 'volatility'):
            data[feature] = rng.normal(size=rows)
        result = _evaluate_rf(SimpleNamespace(rf_model=RandomForestClassifier(n_estimators=30, random_state=42)), pd.DataFrame(data))
        self.assertEqual(result['test_rows'], 79)
        self.assertLess(result['accuracy'], 1.0)
        self.assertIn('train only', result['evaluation'])
        self.assertIn('majority_baseline_accuracy', result)

    def test_advisor_refuses_missing_market_data_instead_of_simulating(self):
        import api
        request = api.TickerEvaluateRequest(ticker='MSFT', current_tickers=['AAPL'], current_weights=[1.0])
        with patch.object(api, 'get_portfolio_data', side_effect=RuntimeError('provider unavailable')):
            with self.assertRaises(HTTPException) as error:
                api.evaluate_ticker_betterment(request)
        self.assertEqual(error.exception.status_code, 503)
        self.assertIn('no simulated prices', error.exception.detail)

    def test_advisor_refuses_cross_currency_comparison(self):
        import api
        request = api.TickerEvaluateRequest(ticker='MSFT', current_tickers=['RELIANCE.NS'], current_weights=[1.0])
        with self.assertRaises(HTTPException) as error:
            api.evaluate_ticker_betterment(request)
        self.assertEqual(error.exception.status_code, 400)
        self.assertIn('same currency', error.exception.detail)

    def test_owned_ticker_comparison_reweights_the_actual_portfolio(self):
        import api
        dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=140)
        step = np.arange(len(dates))
        prices = pd.DataFrame({
            'MSFT': 100 * np.exp(0.001 * step + 0.012 * np.sin(step / 5)),
            'AAPL': 100 * np.exp(0.002 * step + 0.009 * np.cos(step / 7)),
        }, index=dates)
        request = api.TickerEvaluateRequest(
            ticker='MSFT', current_tickers=['MSFT', 'AAPL'],
            current_weights=[0.6, 0.4], proposed_weight=0.2, horizon=2,
        )
        prediction = {'forecast': [{'predicted_price': 99}, {'predicted_price': 98}], 'model': 'Test model'}
        with patch.object(api, 'get_portfolio_data', return_value={'prices': prices}), \
             patch.object(api, 'get_price_forecast', return_value=prediction), \
             patch.object(api, 'detect_market_regime_hmm', return_value={'regime': 'Neutral'}):
            result = api.evaluate_ticker_betterment(request)
        impact = result['portfolio_impact']
        self.assertGreater(impact['sim_return'], impact['base_return'])
        self.assertAlmostEqual(impact['return_delta'], impact['sim_return'] - impact['base_return'], places=2)
        self.assertNotEqual(result['verdict'], 'STRONGLY RECOMMENDED TO ADD')
        self.assertNotEqual(result['verdict'], 'RECOMMENDED FOR DIVERSIFICATION')


if __name__ == '__main__':
    unittest.main()

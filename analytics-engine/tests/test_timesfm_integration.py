import unittest
from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd

from services import forecaster


class TimesFMIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.prices = pd.Series(np.linspace(90, 100, 120), index=pd.bdate_range('2026-01-01', periods=120))

    def test_compounds_log_returns_and_preserves_sixty_session_endpoint(self):
        model = MagicMock()
        model.forecast.return_value = (np.full((1, 60), np.log(1.001)), None)
        with patch.object(forecaster, '_get_timesfm', return_value=model):
            result = forecaster.get_price_forecast(self.prices, 60, return_metadata=True)
        self.assertEqual(result['model'], 'TimesFM 2.5')
        self.assertEqual(len(result['forecast']), 60)
        self.assertAlmostEqual(result['forecast'][-1]['predicted_price'], 100 * 1.001 ** 60)
        self.assertEqual(result['summary']['endpoint']['step'], 60)
        self.assertNotIn('date', result['forecast'][0])

    def test_reports_inference_failure_and_actual_fallback_model(self):
        model = MagicMock()
        model.forecast.side_effect = RuntimeError('inference failed')
        with patch.object(forecaster, '_get_timesfm', return_value=model), \
             patch.object(forecaster, '_lstm_forecast', return_value=[{'predicted_price': 100.}] * 2):
            result = forecaster.get_price_forecast(self.prices, 2, return_metadata=True)
        self.assertEqual(result['model'], 'LSTM')
        self.assertIn('inference failed', result['fallback_reason'])

    def test_rejects_nonfinite_timesfm_output_and_falls_back(self):
        model = MagicMock()
        model.forecast.return_value = np.array([[np.nan]])
        with patch.object(forecaster, '_get_timesfm', return_value=model), \
             patch.object(forecaster, '_lstm_forecast', return_value=[{'predicted_price': 100.}]):
            result = forecaster.get_price_forecast(self.prices, 1, return_metadata=True)
        self.assertEqual(result['model'], 'LSTM')
        self.assertIn('invalid forecast', result['fallback_reason'])

    def test_short_history_is_explicit_baseline(self):
        result = forecaster.get_price_forecast(self.prices[:10], 2, return_metadata=True)
        self.assertIn('baseline', result['model'])
        self.assertIn('Insufficient history', result['fallback_reason'])

    def test_owned_portfolio_forecast_reaches_prompt_with_endpoint_and_model(self):
        from agents.ai_advisor import AIAdvisor
        advisor = AIAdvisor()
        context = {'portfolio_id': 'test', 'currency': 'INR', 'holdings': [
            {'ticker': 'RELIANCE.NS', 'currency': 'INR', 'market_value': 14000},
        ]}
        model = MagicMock()
        model.forecast.return_value = np.full((1, 60), np.log(1.001))
        with patch('services.portfolio_pipeline.run_portfolio_pipeline', return_value={}), \
             patch('services.data_fetcher.get_portfolio_data', return_value={'prices': self.prices.to_frame('RELIANCE.NS')}), \
             patch.object(forecaster, '_get_timesfm', return_value=model):
            structured, _ = advisor._owned_context(context, [], [], 0, '2020-01-01', None, 30, 'Predict Reliance for 60 days')
        text = advisor._format_context_block(structured, [])
        self.assertIn('TimesFM 2.5', text)
        self.assertIn('session 60:', text)

    def test_forecast_error_reaches_prompt(self):
        from agents.ai_advisor import AIAdvisor
        text = AIAdvisor()._format_context_block({'ticker_details': {'RELIANCE.NS': {'forecast_error': 'Price history unavailable'}}}, [])
        self.assertIn('Forecast unavailable: Price history unavailable', text)


if __name__ == '__main__':
    unittest.main()

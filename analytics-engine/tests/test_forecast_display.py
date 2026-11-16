import unittest
from unittest.mock import patch
import pandas as pd


class ForecastDisplayTests(unittest.TestCase):
    def test_ordinary_model_output_remains_visible_as_experimental(self):
        import api
        api.forecast_cache.clear()
        prices = pd.DataFrame({'MSFT': [100.] * 120}, index=pd.bdate_range('2026-01-01', periods=120))
        with patch.object(api, 'get_portfolio_data', return_value={'prices': prices}), \
             patch.object(api, 'get_price_forecast', return_value={'forecast': [{'predicted_price': 99.}, {'predicted_price': 98.}], 'model': 'TimesFM 2.5', 'requested_model': 'TimesFM 2.5', 'model_family':'TimesFM-2.5', 'validation_status':'unverified_fallback', 'fallback_triggered':False, 'is_pretrained_foundation_model':True, 'fallback_reason': None}):
            result = api.forecast_ticker('MSFT', horizon=2, refresh=True)
        self.assertEqual(result['status'], 'experimental')
        self.assertEqual(result['forecast'][0]['predicted_price'], 99.)
        self.assertIsNone(result['warning'])
        self.assertEqual(result['model'], 'TimesFM 2.5')
        api.forecast_cache.clear()

    def test_withholds_unreliable_curve_and_preserves_raw_diagnostics(self):
        import api
        api.forecast_cache.clear()
        prices = pd.DataFrame({'MSFT': [100.] * 120}, index=pd.bdate_range('2026-01-01', periods=120))
        with patch.object(api, 'get_portfolio_data', return_value={'prices': prices, 'currencies': {'MSFT': 'USD'}}), \
             patch.object(api, 'get_price_forecast', return_value={'forecast': [{'predicted_price': 80.}, {'predicted_price': 79.}], 'model': 'LSTM', 'requested_model': 'TimesFM 2.5', 'model_family':'Service-LSTM', 'validation_status':'unverified_fallback', 'fallback_triggered':True, 'is_pretrained_foundation_model':False, 'fallback_reason': 'TimesFM unavailable'}):
            result = api.forecast_ticker('MSFT', horizon=2, refresh=True)
        self.assertEqual(result['raw_forecast'][0]['predicted_price'], 80.)
        self.assertEqual(result['raw_forecast'][1]['step'], 2)
        self.assertEqual(result['model'], 'LSTM')
        self.assertEqual(result['fallback_reason'], 'TimesFM unavailable')
        self.assertEqual(result['price_as_of'], str(prices.index[-1].date()))
        self.assertEqual(result['status'], 'unreliable')
        self.assertEqual(result['forecast'], [])
        self.assertIn('No directional signal', result['warning'])
        api.forecast_cache.clear()

    def test_rejects_invalid_horizon(self):
        import api
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as caught:
            api.forecast_ticker('MSFT', horizon=0)
        self.assertEqual(caught.exception.status_code, 400)

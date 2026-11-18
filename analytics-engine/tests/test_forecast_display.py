import unittest
from unittest.mock import patch
import pandas as pd


class ForecastDisplayTests(unittest.TestCase):
    def test_forecast_survives_missing_comparison_and_handles_rising_rsi(self):
        import api

        dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=120)
        prices = pd.DataFrame({'MSFT': range(100, 220)}, index=dates)
        scenarios = (
            ([], [], 'Add a priced USD holding'),
            (['AAPL'], [1.0], 'Could not retrieve price history for the portfolio holdings'),
        )
        for tickers, weights, reason in scenarios:
            with self.subTest(tickers=tickers), \
                 patch.object(api, 'get_portfolio_data', side_effect=[
                     {'prices': prices}, api.MarketDataUnavailable('Missing comparison history'),
                 ]) as fetch, \
                 patch.object(api, 'get_price_forecast', return_value={}), \
                 patch.object(api, 'detect_market_regime_hmm', return_value={
                     'hmm_converged': False, 'iterations_used': 0,
                 }):
                result = api.evaluate_ticker_betterment(api.TickerEvaluateRequest(
                    ticker='MSFT', current_tickers=tickers, current_weights=weights, horizon=2,
                ))

            self.assertEqual(fetch.call_args_list[0].args[0], ['MSFT'])
            self.assertIsNone(result['portfolio_impact'])
            self.assertIn(reason, result['comparison_reason'])
            self.assertEqual(len(result['forecast']), 2)
            self.assertEqual(result['rsi'], 100)

    def test_ticker_evaluation_uses_target_returns_for_the_stock_regime(self):
        import api

        prices = pd.DataFrame(
            {'SBIN.NS': [100 + i / 2 + i % 3 for i in range(120)],
             'INFY.NS': [200 + i / 4 + i % 5 for i in range(120)]},
            index=pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=120),
        )
        request = api.TickerEvaluateRequest(
            ticker='SBIN.NS', current_tickers=['INFY.NS'], current_weights=[1.0],
            proposed_weight=0.07, currency='INR', horizon=2,
        )

        for converged, expected in ((True, 'Neutral'), (False, 'Unavailable')):
            with self.subTest(converged=converged), \
                 patch.object(api, 'get_portfolio_data', return_value={'prices': prices}), \
                 patch.object(api, 'get_price_forecast', return_value={}), \
                 patch.object(api, 'detect_market_regime_hmm', return_value={
                     'current_regime': 'Neutral', 'hmm_converged': converged,
                     'iterations_used': 500 if not converged else 20,
                 }) as detector:
                result = api.evaluate_ticker_betterment(request)

                pd.testing.assert_series_equal(
                    detector.call_args.args[0], prices['SBIN.NS'].pct_change().dropna(),
                )
                self.assertEqual(result['regime'], expected)
                self.assertEqual(len(result['forecast']), 2)
                if converged:
                    self.assertIsNone(result['regime_reason'])
                else:
                    self.assertIn('did not converge', result['regime_reason'])

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

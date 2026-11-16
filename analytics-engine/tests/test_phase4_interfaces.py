import json
from pathlib import Path
from unittest.mock import Mock, patch
import numpy as np
import pandas as pd
import pytest

from services import forecaster
from trading_engine.models_layer import TradingModels, rf_evaluation_status, INVALID_RF_EVALUATION
from trading_engine.portfolio_rl_env import build_market_tensors, PortfolioRLEnv


@pytest.fixture
def prices():
    return pd.Series(np.linspace(100,110,150), index=pd.bdate_range('2026-01-01',periods=150))


def test_primary_timesfm_and_deprecated_wrapper(prices):
    model = Mock()
    model.forecast.return_value = np.zeros((1, 2))
    with patch.object(forecaster, '_get_timesfm', return_value=model):
        result = forecaster.get_price_forecast('AAPL', 2, prices=prices)
        with pytest.warns(DeprecationWarning):
            assert forecaster.get_lstm_forecast(prices, 2) == result['forecast']
    assert result['model_family'] == 'TimesFM-2.5' and result['is_pretrained_foundation_model']
    assert result['fallback_triggered'] is False and result['fallback_reason'] is None
    assert result['validation_status'] == 'unverified_fallback'


@pytest.mark.parametrize('family,verified', [('Validated-Direct-LSTM', True), ('Last-Close-Baseline', True),
                                             ('Service-LSTM', False), ('Last-Close-Baseline', False)])
def test_actual_fallback_provenance(prices, family, verified):
    rows = [{'predicted_price':100.}]*2
    saved = {'model':'saved', 'model_family':family, 'forecast':rows, 'validation':{'test_origins':30}} if verified else None
    if family == 'Last-Close-Baseline' and not verified:
        prices = prices[:40]
    with patch.object(forecaster, '_get_timesfm', return_value=False), patch.object(forecaster.validated_forecast,'predict',return_value=saved), patch.object(forecaster,'_lstm_forecast',return_value=rows):
        result = forecaster.get_price_forecast('XYZ', 2, prices=prices)
    assert result['model_family'] == family
    assert result['fallback_triggered'] and result['fallback_reason']
    assert not result['is_pretrained_foundation_model']
    assert result['validation_status'] == ('out_of_sample_verified' if verified else 'unverified_fallback')


def test_quarantined_rf_does_not_return_live_confidence():
    frame = pd.DataFrame([{col:0.1 for col in ['rsi','macd','macd_signal','adx','returns','volatility']}])
    tm = TradingModels(frame)
    tm.rf_model = Mock()
    tm.rf_model.predict.return_value = [1]
    tm.scaler_rf.fit(frame)
    for metrics in [{'accuracy':1.,'evaluation':'chronological','train_rows':20,'test_rows':5},{'accuracy':.7},{}]:
        tm.rf_evaluation_status = rf_evaluation_status(metrics)
        assert tm.rf_evaluation_status == INVALID_RF_EVALUATION
        assert tm.predict_rf() == (1,None)
    tm.rf_model.predict_proba.assert_not_called()
    directory = Path(__file__).resolve().parents[1] / 'models'
    records = [json.loads(p.read_text())['metrics']['rf'] for p in directory.glob('*/metadata.json')
               if not p.parent.name.startswith('_') and 'rf' in json.loads(p.read_text()).get('metrics',{})]
    assert records
    assert all('accuracy' not in r for r in records if r.get('evaluation_status') == INVALID_RF_EVALUATION)


def test_ppo_hmm_cannot_see_future_returns():
    rng = np.random.default_rng(22)
    returns = pd.DataFrame(rng.normal(0,.012,(190,3)),index=pd.bdate_range('2020-01-01',periods=190))
    changed = returns.copy()
    changed.iloc[160:] += .15
    def tensors(frame):
        return build_market_tensors(100*(1+frame).cumprod(),frame)
    base, alternative = tensors(returns), tensors(changed)
    truncated = tensors(returns.iloc[:160])
    np.testing.assert_array_equal(base['regimes'][:160],truncated['regimes'])
    np.testing.assert_array_equal(base['regimes'][:160],alternative['regimes'][:160])
    assert np.any(truncated['regimes'] >= 0)
    env = PortfolioRLEnv(base)
    assert env.metadata['causal_preprocessing'] is True
    np.testing.assert_array_equal(env._regime_onehot(0),np.zeros(3))

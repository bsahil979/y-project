import pickle
from collections import deque
from unittest.mock import patch
import numpy as np
import pandas as pd
from services.hmm_engine import fit_causal_hmm, causal_regime_features, final_regime
from services.regime_allocation import fit_allocations
from trading_engine.meta_model import MarketMindMetaModel, FEATURE_COLUMNS


def sample(n=350):
    rng = np.random.default_rng(321)
    return pd.Series(np.concatenate([rng.normal(.001,.004,n//3),rng.normal(0,.01,n//3),rng.normal(-.002,.025,n-2*(n//3))]), index=pd.bdate_range('2020-01-01',periods=n))


def test_scaling_canonical_order_and_persistence():
    values=sample().to_numpy()
    model=fit_causal_hmm(values)
    assert model.n_iter==500 and model.tol==1e-4 and model.min_covar==1e-3
    assert abs(model.causal_scaler_.mean_[0]-values.mean())<1e-12
    assert model.regime_metadata_['state_volatilities']==sorted(model.regime_metadata_['state_volatilities'])
    result=final_regime(model,values)
    assert np.isclose(sum(result['state_probabilities']),1)
    assert result==final_regime(pickle.loads(pickle.dumps(model)),values)
    assert result==final_regime(fit_causal_hmm(values),values)


def test_full_nonconvergence_falls_back_to_diagonal():
    from hmmlearn.hmm import GaussianHMM
    def factory(**kw):
        model=GaussianHMM(**kw)
        fit=model.fit
        def capped(x):
            fit(x)
            if kw['covariance_type']=='full':
                model.monitor_.history=deque([0.,1.])
                model.monitor_.iter=500
            return model
        model.fit=capped
        return model
    with patch('services.hmm_engine.GaussianHMM',side_effect=factory):
        model=fit_causal_hmm(sample().to_numpy())
    assert model.covariance_type=='diag'
    assert not model.regime_metadata_['fit_attempts'][0]['converged']
    assert len(model.regime_metadata_['fit_attempts'])==2


def test_high_dimension_chooses_diagonal():
    model=fit_causal_hmm(np.random.default_rng(7).normal(size=(60,8)))
    assert model.covariance_type=='diag'
    assert model.regime_metadata_['high_dimensional_fallback']


def test_features_are_causal_and_warmup_is_explicit():
    returns=sample(190)
    original=causal_regime_features(returns)
    changed=returns.copy()
    changed.iloc[165:]=.8
    modified=causal_regime_features(changed)
    pd.testing.assert_frame_equal(original.iloc[:165],modified.iloc[:165])
    pd.testing.assert_frame_equal(original.iloc[:165],causal_regime_features(returns.iloc[:165]))
    assert not original.iloc[:125]['regime_available'].any()
    assert original.iloc[:125]['regime_prob_0'].isna().all()
    available=original[original.regime_available]
    assert len(available)>0
    np.testing.assert_allclose(available[['regime_prob_0','regime_prob_1','regime_prob_2']].sum(axis=1),1)


def test_marketmind_preserves_schema_and_uses_hmm():
    returns=sample(190)
    frame=pd.DataFrame({'returns':returns,'Close':100*(1+returns).cumprod()})
    output=MarketMindMetaModel._build_signal_features(frame)
    assert len(FEATURE_COLUMNS)==14
    assert output['regime_code'].equals(output.hmm_state)
    assert 'regime_prob_2' in output
    pd.testing.assert_frame_equal(output.iloc[:165],MarketMindMetaModel._build_signal_features(frame.iloc[:165]))


def test_allocation_metadata_matches_canonical_probabilities():
    returns=pd.DataFrame(np.random.default_rng(4).normal(0,.01,(160,3)), columns=list('ABC'),index=pd.bdate_range('2020-01-01',periods=160))
    result=fit_allocations(returns)
    for key in ['hmm_converged','iterations_used','covariance_type_used','state_probabilities']:
        assert key in result
    np.testing.assert_allclose(result['forecast_state_probabilities'],[s['probability'] for s in result['states']])
    assert result['states'][0]['label']=='Low-Vol / Bullish'


def test_legacy_marketmind_encoding_keeps_input_shape(tmp_path):
    from unittest.mock import Mock
    model = MarketMindMetaModel(model_dir=str(tmp_path))
    model.model = Mock(classes_=np.array([0,1,2]))
    model.model.predict_proba.return_value = np.array([[.2,.3,.5]])
    row = pd.DataFrame([{c: 0.0 for c in FEATURE_COLUMNS}])
    row['regime_code'] = 2
    model.predict_single(row)
    x = model.model.predict_proba.call_args.args[0]
    assert x.shape == (1,14) and x['regime_code'].iloc[0] == -1
    model.metadata['regime_feature_source'] = 'causal_gaussian_hmm'
    model.predict_single(row)
    assert model.model.predict_proba.call_args.args[0]['regime_code'].iloc[0] == 2

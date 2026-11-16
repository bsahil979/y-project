"""Shared causal HMM fitting, canonical states and forward-only probabilities."""
import numpy as np
import pandas as pd
from scipy.special import logsumexp
from sklearn.preprocessing import StandardScaler
from hmmlearn.hmm import GaussianHMM

STATE_LABELS = ['Low-Vol / Bullish', 'Neutral / Transition', 'High-Vol / Stress']


def convergence_summary(model, tolerance=1e-4):
    history = list(model.monitor_.history)
    change = float(history[-1]-history[-2]) if len(history)>1 else None
    converged = bool(change is not None and np.isfinite(change) and abs(change)<tolerance
                     and getattr(model.monitor_, 'converged', True))
    return {'iterations': int(model.monitor_.iter), 'last_log_likelihood_change': change,
            'converged': converged, 'iteration_limit_reached': model.monitor_.iter >= model.n_iter and not converged,
            'tolerance': tolerance}


def fit_causal_hmm(values, covariance_type='full', seed=42):
    values = np.asarray(values, dtype=float)
    if values.ndim == 1:
        values = values[:, None]
    if len(values)<30 or not np.isfinite(values).all() or np.max(np.std(values,axis=0))<1e-10:
        raise ValueError('HMM requires at least 30 finite, varying observations')
    scaler = StandardScaler().fit(values)
    observations = scaler.transform(values)
    n, d = observations.shape
    high_dimensional = n < 10 * 3 * d * (d+1)/2
    first = 'diag' if high_dimensional else covariance_type
    attempts = []
    model = None
    diagonal_attempt = 0
    for covariance in ([first, 'diag', 'diag'] if first != 'diag' else ['diag', 'diag']):
        candidate = GaussianHMM(n_components=3, covariance_type=covariance, n_iter=500,
            tol=1e-4, min_covar=1e-3, random_state=seed)
        if covariance == 'diag':
            # Return regimes differ mainly by variance. K-means mean-based
            # initialization can get stuck splitting near-identical zero means.
            candidate.init_params = ''
            candidate.startprob_ = np.full(3, 1/3)
            candidate.transmat_ = np.full((3, 3), .025) + np.eye(3) * .925
            candidate.means_ = np.zeros((3, d))
            scales = [.15, .75, 2.5] if diagonal_attempt == 0 else [.05, .5, 4.0]
            diagonal_attempt += 1
            candidate.covars_ = np.repeat(np.array(scales)[:, None], d, axis=1)
        try:
            candidate.fit(observations)
            posterior = candidate.predict_proba(observations)
            if not np.isfinite(posterior).all():
                raise ValueError('Non-finite HMM posterior')
            summary = convergence_summary(candidate)
            attempts.append({'covariance_type': covariance, **summary})
            model = candidate
            if summary['converged']:
                break
        except (ValueError, np.linalg.LinAlgError) as exc:
            attempts.append({'covariance_type': covariance, 'error': str(exc)})
            model = None
    if model is None:
        raise ValueError(f'HMM fitting failed: {attempts}')
    posterior = model.predict_proba(observations)
    proxy = values.mean(axis=1)
    means, vols = [], []
    for state in range(3):
        w = posterior[:,state]
        mass = max(w.sum(), 1e-12)
        mean = float(w @ proxy / mass)
        means.append(mean)
        vols.append(float(np.sqrt(w @ ((proxy-mean)**2) / mass)))
    # Volatility is primary; higher realized mean breaks volatility ties.
    order = np.lexsort((-np.asarray(means), np.asarray(vols)))
    model.causal_scaler_ = scaler
    model.canonical_order_ = order
    model.regime_metadata_ = {
        'hmm_converged': convergence_summary(model)['converged'],
        'iterations_used': int(model.monitor_.iter), 'covariance_type_used': model.covariance_type,
        'state_labels': STATE_LABELS, 'state_mean_returns': np.asarray(means)[order].tolist(),
        'state_volatilities': np.asarray(vols)[order].tolist(), 'fit_attempts': attempts,
        'high_dimensional_fallback': bool(high_dimensional)}
    return model


def final_regime(model, values):
    obs = model.causal_scaler_.transform(np.asarray(values).reshape(-1, model.n_features))
    probs = model.predict_proba(obs)[-1][model.canonical_order_]
    state = int(np.argmax(probs))
    return {**model.regime_metadata_, 'state_id': state, 'state_probabilities': probs.tolist(),
            'current_regime': ['Bullish','Neutral','Bearish'][state], 'confidence': float(probs[state])}


def causal_regime_features(returns, lookback=504, min_observations=126, refit_every=21):
    """Refit on prefixes; between refits filter forwards without future smoothing.

    Warmup/failed fitting is explicit unavailable, with neutral code for the fixed
    estimator schema. Each row's metadata and feature is unchanged by future rows.
    """
    if not returns.index.is_monotonic_increasing or returns.index.has_duplicates:
        raise ValueError('HMM features require chronological unique observations')
    values = returns.to_numpy(dtype=float)
    rows, model, filtered = [], None, None
    for i, value in enumerate(values):
        row = {'regime_code': 1, 'regime_available': False, 'regime_prob_0': np.nan,
               'regime_prob_1': np.nan, 'regime_prob_2': np.nan}
        if i+1 >= min_observations and (i+1-min_observations) % refit_every == 0:
            history = values[max(0,i+1-lookback):i+1]
            try:
                model = fit_causal_hmm(history)
                if not model.regime_metadata_['hmm_converged']:
                    model = None
                else:
                    filtered = model.predict_proba(model.causal_scaler_.transform(history[:,None]))[-1]
            except (ValueError, np.linalg.LinAlgError):
                model = None
        elif model is not None and np.isfinite(value):
            obs = model.causal_scaler_.transform([[value]])
            logp = np.log(np.maximum(filtered @ model.transmat_, 1e-300)) + model._compute_log_likelihood(obs)[0]
            filtered = np.exp(logp-logsumexp(logp))
        elif not np.isfinite(value):
            model = None
        if model is not None:
            p = filtered[model.canonical_order_]
            row.update(regime_code=int(np.argmax(p)), regime_available=True)
            row.update({f'regime_prob_{k}': float(p[k]) for k in range(3)})
        rows.append(row)
    return pd.DataFrame(rows, index=returns.index)

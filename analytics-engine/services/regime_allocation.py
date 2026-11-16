"""HMM-conditioned covariance allocation and its matched no-regime baseline.

All fitting consumes only the history passed by the caller. Historical training
responsibilities may be smoothed within that history; no test rows are passed in.
The final posterior is propagated through the transition matrix for forecasts.
"""
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd
from services.hmm_engine import fit_causal_hmm, convergence_summary, STATE_LABELS
from scipy.optimize import minimize


@dataclass(frozen=True)
class AllocationConfig:
    lookback: int = 504
    min_observations: int = 126
    max_weight: float = 0.4
    shrinkage: float = 0.5
    seed: int = 42


def minimum_variance(covariance, max_weight):
    covariance = np.asarray(covariance, dtype=float)
    n = len(covariance)
    if not np.isfinite(covariance).all() or max_weight < 1 / n or max_weight > 1:
        raise ValueError('Invalid covariance or infeasible maximum weight')
    # Scale the objective so SLSQP does not stop prematurely on daily variances.
    scale = max(float(np.trace(covariance) / n), 1e-12)
    objective = covariance / scale
    result = minimize(lambda w: float(w @ objective @ w), np.full(n, 1 / n),
                      jac=lambda w: 2 * objective @ w, method='SLSQP',
                      bounds=[(0, max_weight)] * n,
                      constraints=[{'type': 'eq', 'fun': lambda w: w.sum() - 1,
                                    'jac': lambda w: np.ones(n)}],
                      options={'ftol': 1e-10, 'maxiter': 500})
    if not result.success or abs(result.x.sum() - 1) > 1e-6:
        raise ValueError(f'Allocation failed: {result.message}')
    return result.x


_convergence_summary = convergence_summary


def fit_allocations(returns: pd.DataFrame, config=AllocationConfig(), forecast_steps=1):
    """Fit a three-state HMM and return both methods on identical history.

    States are ordered by realized volatility, with mean return breaking ties.
    Labels are relative risk states, not guarantees of return direction.
    The market proxy is the equal-weight mean of the selected assets.
    """
    if not 0 <= config.shrinkage <= 1 or config.min_observations < 30:
        raise ValueError('Invalid shrinkage or minimum sample size')
    if config.lookback < config.min_observations or forecast_steps < 1:
        raise ValueError('Invalid lookback or forecast horizon')
    if returns.columns.has_duplicates or returns.index.has_duplicates or not returns.index.is_monotonic_increasing:
        raise ValueError('History must have unique columns and chronological unique dates')
    history = returns.tail(config.lookback)
    values = history.to_numpy(dtype=float)
    if len(history) < config.min_observations or values.shape[1] < 3:
        raise ValueError(f'Use at least three assets and {config.min_observations} daily returns')
    if not np.isfinite(values).all() or (values <= -1).any():
        raise ValueError('History contains invalid returns')
    unconditional = np.cov(values, rowvar=False, ddof=0)
    n = values.shape[1]
    ridge = max(float(np.trace(unconditional) / n) * 1e-6, 1e-12)
    unconditional = unconditional + np.eye(n) * ridge
    observations = values.mean(axis=1).reshape(-1, 1)
    model = fit_causal_hmm(observations, seed=config.seed)
    posterior = model.predict_proba(model.causal_scaler_.transform(observations))
    convergence = _convergence_summary(model, model.tol)
    probabilities = posterior[-1] @ np.linalg.matrix_power(model.transmat_, forecast_steps)
    if not np.isfinite(probabilities).all() or probabilities.sum() <= 0:
        raise ValueError('HMM returned invalid state probabilities')
    probabilities = probabilities / probabilities.sum()

    state_means, state_covariances, counts = [], [], []
    for state in range(3):
        responsibilities = posterior[:, state]
        mass = float(responsibilities.sum())
        counts.append(mass)
        if mass < 2:
            mean, covariance = values.mean(axis=0), unconditional
        else:
            mean = np.average(values, axis=0, weights=responsibilities)
            centered = values - mean
            covariance = (centered.T * responsibilities) @ centered / mass
            covariance = ((1 - config.shrinkage) * covariance
                          + config.shrinkage * unconditional + np.eye(n) * ridge)
        state_means.append(mean)
        state_covariances.append(covariance)
    mixture_mean = probabilities @ np.asarray(state_means)
    mixture_covariance = sum(
        probability * (covariance + np.outer(mean - mixture_mean, mean - mixture_mean))
        for probability, covariance, mean in zip(probabilities, state_covariances, state_means)
    )
    baseline_weights = minimum_variance(unconditional, config.max_weight)
    regime_weights = minimum_variance(mixture_covariance, config.max_weight)
    order = model.canonical_order_
    labels = STATE_LABELS
    states = [dict(label=label, probability=float(probabilities[state]),
                   training_mean_daily_return=float(model.causal_scaler_.inverse_transform(model.means_)[state, 0]),
                   training_membership_mass=counts[state],
                   covariance_fallback=counts[state] < 2)
              for label, state in zip(labels, order)]
    return {
        'status': 'ready', 'method': 'hmm_conditioned_minimum_variance',
        'regime_aware': True, 'config': asdict(config),
        'training_start': str(history.index[0].date()),
        'training_end': str(history.index[-1].date()), 'observations': len(history),
        'forecast_steps': forecast_steps, 'states': states,
        'weights': dict(zip(history.columns, map(float, regime_weights))),
        'baseline_weights': dict(zip(history.columns, map(float, baseline_weights))),
        'estimated_annual_volatility': float(np.sqrt(regime_weights @ mixture_covariance @ regime_weights * 252)),
        'baseline_annual_volatility': float(np.sqrt(baseline_weights @ unconditional @ baseline_weights * 252)),
        'convergence': convergence,
        **model.regime_metadata_,
        'state_probabilities': posterior[-1][order].tolist(),
        'forecast_state_probabilities': probabilities[order].tolist(),
        'explanation': (
            'A trained HMM estimates probabilities of three market states. State-conditioned '
            'covariances are shrunk toward the overall historical covariance and mixed using '
            'those probabilities. The optimizer minimizes that estimated variance, with '
            f'long-only weights and a {config.max_weight:.0%} limit per stock. '
            'The matched baseline uses the same history and constraints without state information. '
            'These are model estimates, not measured future returns.'
        ),
    }

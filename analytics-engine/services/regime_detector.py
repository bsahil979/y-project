import numpy as np
import pandas as pd
from services.hmm_engine import fit_causal_hmm, final_regime


def detect_market_regime_hmm(returns: pd.Series, n_regimes=3):
    if n_regimes != 3:
        raise ValueError('Canonical regime engine requires three states')
    clean = pd.Series(returns).replace([np.inf, -np.inf], np.nan).dropna().tail(504)
    try:
        model = fit_causal_hmm(clean.to_numpy())
        return final_regime(model, clean.to_numpy())
    except (ValueError, np.linalg.LinAlgError) as exc:
        return {'current_regime': 'Unavailable', 'state_id': None, 'confidence': 0.0,
                'hmm_converged': False, 'iterations_used': 0, 'covariance_type_used': None,
                'state_probabilities': None, 'reason': str(exc)}

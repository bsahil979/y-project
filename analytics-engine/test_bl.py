import numpy as np
import pandas as pd
from scipy.optimize import minimize

def test_bl():
    np.random.seed(42)
    tickers = ['AAPL', 'NVDA', 'MSFT', 'AMZN']
    n = len(tickers)
    cov = np.array([
        [0.05, 0.03, 0.02, 0.025],
        [0.03, 0.09, 0.03, 0.035],
        [0.02, 0.03, 0.04, 0.02],
        [0.025, 0.035, 0.02, 0.06]
    ])
    delta = 2.5
    w_mkt = np.array([0.25, 0.25, 0.25, 0.25])
    pi = delta * (cov @ w_mkt)

    Q = np.array([0.15, 0.28, 0.14, 0.18])
    sentiments = {'AAPL': 0.3, 'NVDA': -0.4, 'MSFT': 0.5, 'AMZN': 0.1}
    sent_vec = np.array([sentiments[t] for t in tickers])
    Q_adj = Q + sent_vec * 0.03

    tau = 0.05
    omega_diag = np.diag(tau * cov).copy()
    for i, t in enumerate(tickers):
        if sentiments[t] < 0:
            omega_diag[i] *= (1.0 + 1.5 * abs(sentiments[t]))
        else:
            omega_diag[i] *= (1.0 - 0.2 * abs(sentiments[t]))

    inv_tau_cov = np.linalg.inv(tau * cov)
    inv_omega = np.diag(1.0 / omega_diag)

    M = np.linalg.inv(inv_tau_cov + inv_omega)
    er_post = M @ (inv_tau_cov @ pi + inv_omega @ Q_adj)
    cov_post = cov + M

    def neg_utility(w):
        return -(np.dot(w, er_post) - (delta / 2.0) * np.dot(w.T, cov_post @ w))

    bounds = tuple((0.02, 0.40) for _ in range(n))
    constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]
    init_w = np.ones(n) / n
    res = minimize(neg_utility, init_w, method='SLSQP', bounds=bounds, constraints=constraints)

    print("Success:", res.success)
    print("Market Prior Pi:", np.round(pi, 4))
    print("AI Views Q:", np.round(Q_adj, 4))
    print("Posterior Returns E[R]:", np.round(er_post, 4))
    print("BL Weights:", dict(zip(tickers, np.round(res.x, 4))))

test_bl()

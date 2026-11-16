# Focused regime-allocation study

This is the current research path. The older PPO experiment scripts are retained as separate exploratory work; their outputs are not used by the new Research page.

## Implementation

- `services/regime_allocation.py`: one shared model/allocation implementation for the app and study.
- `research/regime_study.py`: chronological execution, holdings drift, fees, metrics.
- `research/run_regime_study.py`: dataset acquisition and reproducibility artifacts.
- `GET /research/regime-study`: reads the versioned primary run used by the Research page; does not train models.
- The live portfolio allocation response includes the HMM iteration count, final likelihood change, tolerance, and convergence status. If the model reaches its iteration limit without meeting tolerance, the portfolio screen keeps the estimate visible and displays a reliability warning. It also identifies any state whose covariance used the low-membership fallback and explains the consequence. The saved historical experiment and its settings are unchanged.

## Model and allocation

At each decision, take up to 504 prior daily asset returns. The model input is the equal-weight mean asset return, expressed in percentage units. Fit a three-state Gaussian HMM with seed 42 and a 200-iteration limit. State names are ordered by fitted mean return; no threshold implies an absolute bull or bear market.

Compute state-weighted asset means and covariance matrices using posterior responsibilities on this training window. These historical responsibilities may use later observations *within the training window*, but never observations after the decision cutoff. Shrink each state covariance halfway toward the unconditional training covariance. States with membership mass below two use the unconditional estimate. Add a small positive diagonal regularizer.

Propagate the final state probabilities two transitions forward to account for the execution delay. Blend state covariance matrices, including between-state mean dispersion, to estimate future covariance. Minimize portfolio variance with weights summing to one, no shorts, and at most 40% per stock. The matched no-regime method uses the unconditional covariance, the same dates, and identical constraints.

The two-session covariance estimate is used to select weights held until the next 21-session rebalance. That horizon mismatch is a modeling choice to disclose and test, not a claim of optimality. Neither method targets maximum expected return.

Implementation reference: the [official hmmlearn API](https://hmmlearn.readthedocs.io/en/0.3.3/api.html) documents GaussianHMM fitting, posterior probabilities, and transition matrices. This is an implementation reference, not a complete literature review.

## Time and cost conventions

1. Fit using observations through close t.
2. Execute at close t+1, without using t+1 data for that decision.
3. Earn the first return from t+1 to t+2.
4. Between rebalances, holdings drift according to asset returns.
5. Charge 10 basis points times the sum of absolute traded weight changes; include initial purchase costs. This is a proportional portfolio-notional approximation. It does not model spread, taxes, or market impact, and excludes final liquidation.

All four strategies use the same observation dates. Buy-and-hold never rebalances; equal-weight and both optimizers rebalance every 21 sessions. The risk-free-rate assumption for Sharpe is 2% annually. Annualization uses 252 sessions.

Each model is refitted on its rolling historical window. Test observations may become training history for a later decision after they occur; no observation can affect an earlier decision. There is no full-test-period model fitting or test-period smoothing. The test suite perturbs future prices and verifies earlier decisions and equity do not change beyond floating-point tolerance.

## Reproduce

From `analytics-engine`, using the existing environment:

```powershell
.\venv\Scripts\python.exe -m unittest tests.test_midterm_pipeline tests.test_regime_study -v
.\venv\Scripts\python.exe -m research.run_regime_study --output research/regime_development_v2
```

New downloads default to Yahoo Finance auto-adjusted closes from 2018-01-01 through 2025-12-31, for RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS, and ICICIBANK.NS. The saved preliminary snapshot in `regime_results` ends on 2024-12-31. The runner refuses an unverified adjustment convention and refuses to overwrite a non-empty output directory unless `--replace` is supplied.

Re-run without downloading, preserving the original output:

```powershell
.\venv\Scripts\python.exe -m research.run_regime_study --prices research/regime_results/prices.csv --output research/regime_replay_v1 --allow-no-holdout
```

Use `--seed` and `--cost-bps` with separate output directories for sensitivity runs. A supplied CSV must already contain complete positive prices in one consistent currency and adjustment convention; its provenance is the caller's responsibility.

The held-out 2025 paper evaluation is specified in [PROTOCOL_V1.md](./PROTOCOL_V1.md) and [experiment_protocol_v1.json](./experiment_protocol_v1.json). The completed, provenance-verified run is [`regime_holdout_2026-09-27_v2`](./regime_holdout_2026-09-27_v2/manifest.json), based on [`regime_data_v1`](./regime_data_v1/manifest.json). The primary result is a small positive Sharpe difference with an interval spanning zero; 45 of 70 primary HMM fits reached the iteration cap without meeting tolerance. See [PAPER_DRAFT.md](./PAPER_DRAFT.md) for the working report.

The default output directory contains prices, equity curves, daily return/cost/turnover ledger, whole-period metrics, 2025 holdout metrics and bootstrap interval when coverage is sufficient, `sensitivity.csv`, per-rebalance decisions, and a manifest. The manifest records dates, configuration, dependency versions, a dataset hash, and source hashes. The app warns when the current model/study code or saved price snapshot differs from the recorded run. This check is not a cryptographic audit of all output artifacts.

## First development result

Evaluation dates: 2020-01-24 through 2024-12-31, 1,221 daily returns and 59 allocation decisions.

| Strategy | Annualized return | Annualized volatility | Sharpe | Maximum drawdown |
|---|---:|---:|---:|---:|
| Buy and hold | 16.55% | 20.84% | 0.745 | -36.81% |
| Equal weight | 17.85% | 20.92% | 0.796 | -36.75% |
| Minimum variance | 15.23% | 20.50% | 0.698 | -35.11% |
| HMM minimum variance | 14.70% | 20.43% | 0.677 | -35.21% |

The proposed method slightly reduced volatility but did not improve return or Sharpe over its matched baseline in this run. The table is preliminary: one selected universe, development period, and seed; no statistical significance claim. Dataset selection/survivorship limitations remain. Do not treat this as the final held-out paper evaluation.

Next research work: verify the cited papers from their full texts; add more chronological evaluation windows using development data only; and independently reproduce the saved run. The saved fit diagnostics are summarized in [HMM_DIAGNOSTICS.md](./HMM_DIAGNOSTICS.md). Do not tune settings against the completed 2025 holdout or present its one-year result as general evidence.

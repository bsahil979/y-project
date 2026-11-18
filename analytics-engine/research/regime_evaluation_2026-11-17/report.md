# Updated HMM allocation study

Frozen protocol and prices; updated causal HMM engine.

## 2025 holdout

                     period_start  period_end  total_return  annualized_return  annualized_volatility    sharpe  max_drawdown  annualized_traded_notional  cumulative_cost_fraction  cost_drag_on_one_unit  observation_count
strategy                                                                                                                                                                                                                     
Buy and hold           2025-01-01  2025-12-31      0.015333           0.015519               0.136564  0.035543     -0.128328                    0.000000                  0.000000               0.000000                249
Equal weight           2025-01-01  2025-12-31      0.031556           0.031942               0.135229  0.153192     -0.116952                    0.360767                  0.000356               0.000368                249
Minimum variance       2025-01-01  2025-12-31      0.028753           0.029104               0.125914  0.133111     -0.096371                    0.555373                  0.000549               0.000565                249
HMM minimum variance   2025-01-01  2025-12-31      0.030806           0.031183               0.126169  0.149094     -0.096846                    0.783410                  0.000774               0.000798                249

## Paired Sharpe bootstrap

```json
{
  "comparison": "HMM minimum variance minus Minimum variance",
  "metric": "net annualized Sharpe difference",
  "point_estimate": 0.01598291620823597,
  "confidence": 0.95,
  "lower": -0.010547957332955214,
  "upper": 0.04170265499365712,
  "method": "paired moving-block bootstrap; non-circular blocks sampled from shared dates",
  "block_length_sessions": 21,
  "replicates_requested": 10000,
  "replicates_valid": 10000,
  "seed": 20260927,
  "observation_count": 249,
  "risk_free_rate_annual": 0.02,
  "annualization_sessions": 252,
  "interpretation": "Exploratory uncertainty for one year and one convenience universe; not broad evidence of effectiveness."
}
```

Convergence: {"fits": 70, "converged": 70, "iteration_cap_failures": 0}

Exploratory single-universe results; the bootstrap interval describes the paired Sharpe difference, not the HMM Sharpe alone.

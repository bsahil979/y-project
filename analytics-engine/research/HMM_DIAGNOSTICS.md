# Primary-run HMM diagnostics

These descriptive diagnostics are calculated from the saved primary decisions in [`regime_holdout_2026-09-27_v2/decisions.json`](./regime_holdout_2026-09-27_v2/decisions.json). They do not change the frozen model, outcomes, or 2025 evaluation.

## Fitting convergence

| Execution year | Fits | Reached 200-iteration limit without meeting 1e-4 tolerance |
|---|---:|---:|
| 2020 | 12 | 7 |
| 2021 | 11 | 4 |
| 2022 | 12 | 8 |
| 2023 | 12 | 9 |
| 2024 | 12 | 12 |
| 2025 | 11 | 5 |
| **Total** | **70** | **45** |

All 25 fits that stopped before the limit had a final likelihood change below tolerance. Iteration-cap hits became more frequent through 2024, when every scheduled fit reached the limit. This is evidence that the fixed EM budget was inadequate for many rolling windows. The allocations and holdout results remain those generated under the frozen 200-iteration setting; this diagnostic must not be used to retrofit a more favorable model onto the same holdout.

## State estimates

State names are re-ranked by fitted market-proxy mean within each rolling window. The figures below summarize 70 fitted windows, so they describe averages and ranges of model estimates rather than one fixed global state definition.

| Ranked state | Mean two-step forecast probability | Mean fitted daily market-proxy mean | Range of fitted daily means | Minimum training membership mass | Fits using low-mass fallback |
|---|---:|---:|---:|---:|---:|
| Lower-return | 0.239 | -30.414 bps | -193.852 to +1.563 bps | 9.1 | 0 |
| Middle-return | 0.483 | +8.951 bps | -40.584 to +27.130 bps | 26.2 | 0 |
| Higher-return | 0.278 | +31.160 bps | +11.081 to +105.309 bps | 18.5 | 0 |

The fitted means are emission means for the equal-weight return proxy, not subsequent realized returns. No state used the configured membership-mass-below-two fallback. Forecast probabilities occasionally assigned near-zero probability to a ranked state, while the mean probability mass was concentrated most heavily in the middle-return state. The rank labels are relative to each fit; they do not imply reliable market timing or absolute bull/bear classifications.

## Allocation concentration

| Stock | Mean HMM weight | Weight range | Fits at 40% cap |
|---|---:|---:|---:|
| RELIANCE.NS | 15.2% | 0.0%-22.7% | 0 |
| TCS.NS | 34.0% | 21.1%-40.0% | 12 |
| INFY.NS | 9.1% | 0.0%-22.6% | 0 |
| HDFCBANK.NS | 27.0% | 16.2%-40.0% | 6 |
| ICICIBANK.NS | 14.7% | 0.0%-33.9% | 0 |

The cap bound TCS in 12 fits and HDFCBANK in six fits. Combined with the five-stock convenience universe, these weights limit how broadly the result can be generalized.

## Interpretation

The primary finding should be read alongside frequent fitting-limit hits, near-zero state forecast probabilities, and repeated concentration at the per-stock cap. These observations do not prove that the HMM is unusable, but they weaken confidence that small Sharpe differences represent stable regime information. Any convergence changes require a new development analysis and, for a new performance claim, a newly defined out-of-time evaluation.

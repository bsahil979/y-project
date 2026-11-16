# Does Regime Conditioning Improve Minimum-Variance Allocation?

## Evidence from a five-stock Indian equity basket

**Draft status:** Results draft for review. Independent recomputation of the holdout results table is complete. Full-text literature review and school formatting requirements remain to be completed. All reported results are from the frozen protocol and saved run linked below.

## Abstract

This study tests whether a three-state Gaussian Hidden Markov Model (HMM) can improve the risk-adjusted performance of a long-only minimum-variance portfolio. The HMM conditions covariance estimates on inferred market states; a matched minimum-variance portfolio uses unconditional covariance. Both methods use the same five Indian equities, a 40% position cap, a 504-return rolling training window, delayed execution, and proportional transaction costs. The primary evaluation uses 249 daily returns in 2025, held out from the exploratory period. The HMM portfolio's annualized Sharpe ratio was 0.1510, compared with 0.1331 for the baseline, a difference of 0.0179. A paired 21-session moving-block bootstrap produced a 95% interval from -0.0090 to 0.0442, which includes zero. The HMM portfolio also traded more, and 45 of 70 primary HMM fits reached the iteration limit without meeting the declared likelihood tolerance. The result is a small positive point estimate with substantial uncertainty and a material fitting limitation; it does not establish an HMM advantage.

**Keywords:** portfolio allocation; hidden Markov model; minimum variance; regime switching; backtesting; India

## 1. Introduction

Portfolio risk depends on the joint behavior of asset returns, including their covariances, and on the portfolio weights assigned to those assets. Mean-variance portfolio selection provides a standard framework for relating these quantities [1]. In practice, however, covariance estimates are noisy, while return behavior and correlations may change over time. Markov-switching models provide one way to represent unobserved changes in time-series behavior [2]. Prior asset-allocation work has examined regime-dependent volatility and correlation in international equity returns [3]. These ideas motivate testing whether conditioning covariance estimates on inferred market states changes the results of a constrained portfolio optimizer.

This project compares a three-state Gaussian HMM-conditioned minimum-variance allocation with a matched optimizer that uses unconditional covariance. The question is narrow: **on a fixed five-stock Indian equity basket, does the HMM-conditioned method improve net out-of-sample Sharpe relative to the matched baseline under the same execution and cost rules?** The study is an educational empirical comparison. It does not propose a new HMM or optimizer, and it does not claim the resulting allocations are suitable for investment.

The 2020-2024 run was treated as exploratory. The primary evaluation was reserved for calendar year 2025. The observed primary Sharpe difference is positive, but its paired bootstrap interval includes zero. Frequent HMM iteration-cap hits and higher turnover further limit interpretation. These outcomes are reported even though the point estimate favors the proposed method.

## 2. Related work

Markowitz's portfolio-selection framework motivates the minimum-variance baseline by making portfolio risk a function of the covariance matrix and portfolio weights [1]. The present study fixes the objective to variance minimization and does not estimate expected returns for the optimizer. This helps isolate the effect of conditioning the covariance estimate, although it does not remove estimation error from the covariance matrices.

Hamilton develops a likelihood-based framework for discrete, unobserved shifts in time-series dynamics [2]. Ang and Bekaert study international asset allocation when equity-return volatilities and correlations vary across regimes [3]. Their setting and portfolio problem differ from this project: the present experiment uses a single equal-weight equity-return proxy, an HMM, and a small Indian-stock universe. Those studies motivate the regime-conditioned question but do not establish that this implementation should outperform its baseline.

Covariance estimation is itself a major source of portfolio uncertainty. Ledoit and Wolf study monthly U.S. equity baskets with 60-month covariance histories and a data-driven shrinkage estimate toward a constant-correlation target; their empirical design and active-portfolio objective differ from this project [4]. This project uses a fixed 0.5 blend of state covariance toward unconditional covariance; it is **not** the Ledoit-Wolf estimator. Backtest selection is another concern. Sullivan, Timmermann, and White apply White's Reality Check and a stationary bootstrap to a broad universe of technical rules [5]. Bailey and López de Prado describe how multiple trials and non-normal returns can inflate Sharpe-based claims [6]. This project reports its six predeclared seed/cost combinations and a paired block-bootstrap interval for one optimizer pair, but it does not apply a Reality Check or calculate a selection-adjusted Sharpe statistic. The literature therefore supports methodological caution, not a positive effectiveness claim for this portfolio.

## 3. Data and methods

### 3.1 Data and universe

The universe contains RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS, and ICICIBANK.NS, with all prices denominated in INR. Daily Yahoo Finance auto-adjusted close prices were downloaded for 2018-01-01 through 2025-12-31. The saved snapshot contains 1,976 complete common-session price rows and no dropped incomplete rows. Returns are close-to-close percentage changes on the common session index; prices are not forward-filled. The exact data snapshot, request dates, source convention, retrieval time, and SHA-256 are recorded in [`regime_data_v1/manifest.json`](./regime_data_v1/manifest.json).

These five firms are a fixed convenience sample of current large Indian companies, not a point-in-time index membership list. Survivorship and selection bias cannot be ruled out. Adjusted historical closes are useful for historical-return accounting but are not executable quotes.

### 3.2 Strategies and HMM allocation

Four strategies share the same observations and execution convention: equal-initial-weight buy-and-hold; periodically rebalanced equal weight; long-only minimum variance using unconditional covariance; and HMM-conditioned minimum variance using a forecast mixture of state-conditioned covariance estimates. Both optimizers have nonnegative weights summing to one and a 40% maximum weight per stock. The matched baseline uses the same history and optimizer constraints as the HMM method.

At each allocation decision, the HMM is fit to the equal-weight mean of asset returns, expressed in percentage units, using up to the preceding 504 daily return rows. The Gaussian HMM has three diagonal-covariance states, seed 42, convergence tolerance 1e-4, and a maximum of 200 EM iterations. Posterior responsibilities from the training window estimate state-conditioned asset means and covariance matrices. State covariance is blended 50/50 with unconditional covariance; states with membership mass below two use the unconditional estimates. The last posterior state probabilities are propagated two transitions forward. The resulting covariance mixture includes between-state mean dispersion. The optimizer minimizes variance; it does not maximize estimated expected return.

### 3.3 Execution and accounting

Decisions use information available through close *t*. Target weights are executed at close *t+1*, and the first return earned is from close *t+1* to close *t+2*. Equal weight and both optimizers rebalance every 21 common sessions. Buy-and-hold trades only for its initial purchase. Holdings drift between trades. Each strategy pays 10 basis points times the sum of absolute traded-weight changes at each trade, including initial purchases; no final liquidation is charged. This proportional cost approximation excludes bid-ask spread, taxes, market impact, and liquidity constraints.

The stored run covers 2020-01-24 through 2025-12-31, with 1,470 daily out-of-sample return rows per strategy and 70 allocation decisions. The 2025 holdout contributes 249 daily return rows. The rolling model is refit as new observations become available; no 2025 observation is used in a decision that precedes it.

### 3.4 Outcomes and uncertainty

The primary outcome is the difference in 2025 net annualized Sharpe ratio, HMM minus minimum variance. The annual risk-free rate is 2%, converted to an effective daily rate, and annualization uses 252 sessions. The paired uncertainty interval resamples shared dates for both optimizers with non-circular moving blocks of 21 sessions, 10,000 replicates, seed 20260927, and a 95% percentile interval. It is descriptive uncertainty for one year and one universe, not proof of general effectiveness.

Secondary outcomes are total and annualized return, annualized volatility, maximum drawdown, annualized traded notional, and estimated costs. Sensitivity analysis uses seeds 7, 42, 123, and 2026 at 10 basis points, plus cost assumptions of 0, 10, and 25 basis points at seed 42. The complete results are in [`sensitivity.csv`](./regime_holdout_2026-09-27_v2/sensitivity.csv).

## 4. Results

### 4.1 Primary 2025 holdout

| Strategy | Total return | Annualized return | Annualized volatility | Sharpe | Maximum drawdown |
|---|---:|---:|---:|---:|---:|
| Buy and hold | 1.53% | 1.55% | 13.66% | 0.036 | -12.83% |
| Equal weight | 3.16% | 3.19% | 13.52% | 0.153 | -11.70% |
| Minimum variance | 2.88% | 2.91% | 12.59% | 0.133 | -9.64% |
| HMM minimum variance | 3.10% | 3.14% | 12.62% | 0.151 | -9.68% |

The HMM Sharpe point estimate exceeds the matched baseline by 0.0179. The paired bootstrap 95% interval is **[-0.0090, 0.0442]**. Because the interval includes zero, this sample does not resolve whether the difference reflects a repeatable improvement. Annualized volatility is nearly the same for the optimizer pair. The HMM portfolio's total return is slightly higher, while its maximum drawdown is also slightly more negative.

### 4.2 Trading and sensitivity

The HMM method's annualized traded notional is 0.763, compared with 0.555 for minimum variance. Its cumulative cost fraction is 0.000754 versus 0.000549. These values indicate the HMM allocation changed its holdings more and incurred higher estimated costs under the shared cost rule.

All five non-primary seed/cost variants had positive 2025 HMM-minus-baseline Sharpe differences. Across the six recorded scenarios, including the primary case, the difference ranged from 0.0103 to 0.0254. The full 2020-2025 run gives a different comparison: Sharpe was 0.6114 for HMM minimum variance and 0.6278 for minimum variance. The one-year holdout point estimate should therefore be read in the context of a mixed full-period result and limited sensitivity sample, not as a general performance claim.

### 4.3 HMM states, convergence, and allocation concentration

Of the 70 primary HMM allocation fits, 45 reached the 200-iteration maximum without meeting the 1e-4 likelihood-change tolerance. Every scheduled fit in 2024 reached the cap. Those fits were used by the preregistered run, so the study does not establish that the HMM parameters were consistently optimized. The ranked lower-, middle-, and higher-return states had mean two-step forecast probabilities of 0.239, 0.483, and 0.278. No state used the low-membership fallback. TCS reached the 40% weight cap in 12 fits and HDFCBANK in six. These state labels are ranked within each rolling fit and should not be interpreted as persistent economic regimes. Full summaries are in [`HMM_DIAGNOSTICS.md`](./HMM_DIAGNOSTICS.md); the saved [`decisions.json`](./regime_holdout_2026-09-27_v2/decisions.json) has per-fit details.

## 5. Discussion

The primary point estimate is directionally positive, but small relative to its uncertainty. The bootstrap interval includes zero, and one calendar year from a five-stock convenience universe cannot establish broad effectiveness. The HMM method also traded more, increasing estimated cost, while producing nearly identical volatility and a slightly worse maximum drawdown than its matched baseline. In the longer evaluation path the HMM Sharpe is lower. Taken together, these findings are mixed rather than evidence of a dependable improvement.

The iteration-cap result weakens confidence in the fitted states and downstream covariance mixtures. A later study may investigate convergence using development data, but any method change must be documented as a new experiment. The completed 2025 holdout must not be used to select a higher iteration count, another state count, or a favorable seed and then be presented as untouched validation.

## 6. Limitations

The universe is small and selected using current firms, so survivorship and selection bias remain. The final holdout is one year. Yahoo Finance adjusted closes and a fixed proportional fee do not capture executable prices, bid-ask spread, taxes, market impact, or liquidity. The model uses one equal-weight return series to infer states; labels are statistical groupings, not verified bull/bear forecasts. The HMM often reached its iteration limit, covariance estimates are uncertain, and the two-session covariance forecast is used to choose weights held for 21 sessions. Seed and cost sensitivities are limited and do not correct for all multiple-testing concerns. The bootstrap interval is exploratory and should not be described as proof or a formal universal significance test.

## 7. Conclusion

In this fixed experiment, the HMM-conditioned minimum-variance portfolio had a 2025 Sharpe ratio 0.0179 above the matched baseline, but the paired bootstrap interval included zero. It traded more, and 45 of 70 primary fits reached the iteration cap without meeting tolerance. The results do not establish an advantage. They show how a transparent, matched comparison can produce a positive point estimate while uncertainty, implementation costs, convergence behavior, and the longer-period result argue for caution.

## References

1. Markowitz, H. (1952). Portfolio selection. *The Journal of Finance, 7*(1), 77-91. https://doi.org/10.1111/j.1540-6261.1952.tb01525.x
2. Hamilton, J. D. (1989). A new approach to the economic analysis of nonstationary time series and the business cycle. *Econometrica, 57*(2), 357-384. https://doi.org/10.2307/1912559
3. Ang, A., & Bekaert, G. (2002). International asset allocation with regime shifts. *The Review of Financial Studies, 15*(4), 1137-1187. https://doi.org/10.1093/rfs/15.4.1137
4. Ledoit, O., & Wolf, M. (2004). Honey, I shrunk the sample covariance matrix. *The Journal of Portfolio Management, 30*(4), 110-119. https://doi.org/10.3905/jpm.2004.110
5. Sullivan, R., Timmermann, A., & White, H. (1999). Data-snooping, technical trading rule performance, and the bootstrap. *The Journal of Finance, 54*(5), 1647-1691. https://doi.org/10.1111/0022-1082.00163
6. Bailey, D. H., & López de Prado, M. (2014). The deflated Sharpe ratio: Correcting for selection bias, backtest overfitting and non-normality. *The Journal of Portfolio Management, 40*(5), 94-107. https://doi.org/10.3905/jpm.2014.40.5.094

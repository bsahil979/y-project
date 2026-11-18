# Regime Conditioning for Minimum Variance Allocation

Sahil Belchada, Paras Kokate

Evaluation manuscript prepared 17 November 2026

## Abstract

We evaluate whether market-state conditioning improves a long-only minimum-variance allocator on five Indian equities. Both methods use a 504-return rolling history, a 40 percent per-asset cap, delayed execution and proportional trading costs. A three-state Gaussian hidden Markov model estimates regimes from the equal-weight basket return. The 2025 evaluation comprises 249 daily returns. The updated HMM allocator achieves net annualized Sharpe 0.1491, compared with 0.1331 for the unconditional baseline. The paired difference is 0.0160, with a 95 percent moving-block bootstrap interval [-0.0105, 0.0417]. All 70 primary fits converged under the stated likelihood criterion. Higher traded notional and an interval spanning zero limit the evidence of benefit. The study provides a reproducible comparison with explicit costs and uncertainty. The updated engine was evaluated retrospectively on an already inspected historical window, which limits confirmatory interpretation.

Keywords — hidden Markov model, minimum variance, Indian equities, regime conditioning, moving-block bootstrap

## 1 Introduction

Portfolio risk depends on asset covariance and allocation weights. State-dependent covariance estimates may represent changing market relationships, but the additional estimation can also increase noise. This study asks whether conditioning covariance on a three-state HMM improves net Sharpe relative to an otherwise matched unconditional minimum-variance allocation.

The contribution is an implemented and reproducible empirical comparison within SmartPortfolio. The application provides a setting for portfolio analytics and explanations. The research evaluates a narrowly defined allocator and its baseline. Its outcome does not validate the application’s other forecasting, sentiment or conversational models.

## 2 Related work

Markowitz [1] provides the variance-based foundation for portfolio selection. Hamilton [2] and Rabiner [3] provide background on hidden-state models and their estimation. Ang and Bekaert [4] examine regime shifts in asset allocation. Ledoit and Wolf [5] motivate attention to covariance estimation error. Our fixed 50 percent covariance blend is a separate regularization choice. Künsch [6] motivates resampling dependent observations, while White [7] highlights the inferential consequences of data-driven model selection. These works motivate the design and its limitations. The present implementation supplies empirical evidence only for the stated basket and protocol.

## 3 Data and experimental design

The universe comprises RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS and ICICIBANK.NS. The frozen Yahoo Finance adjusted-close snapshot has 1,976 common-date observations spanning 2018 through 2025, denominated in INR. Returns are calculated on the intersected observed dates without forward filling. The evaluated path has 1,470 daily returns from January 2020 through December 2025. Calendar year 2025 contributes 249 returns and 11 scheduled allocation decisions.

The universe is a convenience sample with sector concentration and possible selection and survivorship bias. Adjusted prices were downloaded retrospectively. Corporate-action adjustments are not certified as the values available at each historical decision date. The protocol was recorded in September 2026. The updated engine was developed after inspection of the 2025 results, so this is a retrospective causal replay rather than a newly untouched model-selection test.

| Setting | Value |
| --- | --- |
| History and scheduling | 504 daily returns; rebalance every 21 common sessions |
| Constraints | Long only; weights sum to one; maximum weight 0.40 |
| HMM | Three Gaussian states; training-window StandardScaler; seed 42 |
| Fitting | Maximum 500 iterations; tolerance 0.0001; min_covar 0.001 |
| Execution | Decision at close t; trade at close t+1; first earned return ends t+2 |
| Costs | 10 basis points per total absolute change in weights |
| Risk-free assumption | 2 percent annual rate; effective daily conversion |
| Bootstrap | 21-session non-circular blocks; 10,000 replicates; seed 20260927 |

## 4 Covariance estimation and optimization

For each decision date t, let R contain the preceding N daily asset-return vectors. The unconditional estimator C0 is the population sample covariance with divisor N, plus a diagonal ridge. The ridge equals the larger of mean asset variance multiplied by 0.000001 and 0.000000000001. Both strategies minimize wᵀCw subject to sum(w)=1 and 0≤wᵢ≤0.40. SLSQP uses an analytic gradient, an objective scaled by mean diagonal covariance, tolerance 1e−10 and a maximum of 500 iterations.

The HMM observes the cross-sectional mean return x at each training date. StandardScaler is fitted exclusively on that training window. Full covariance is attempted first, with diagonal fallback when required by sample size or failed convergence. In the univariate study these covariance types each estimate one variance per state, but their initialization differs. Diagonal attempts initialize near-zero state means and distinct variances. Convergence requires finite absolute change in log likelihood below 0.0001 and the monitor convergence flag. Canonical labels sort states by realized volatility, breaking ties by higher mean return.

## 5 State mixture and trading calculations

Training responsibilities are smoothed conditional probabilities γ(s,k)=Pr(z_s=k | x in the complete training window). They can use later observations within the training window. All those observations precede the allocation decision. The responsibility at the final training observation supplies the current state vector. This distinction corrects the filtered-probability notation in the October review draft.

For state k, its membership mass is M_k=sum_s γ(s,k). If M_k is at least two, its mean is the responsibility-weighted average of asset returns and its covariance is the weighted outer product of centered returns divided by M_k. The estimator blends this covariance equally with C0 and adds the diagonal ridge. States with lower mass use the unconditional mean and C0.

Let A denote the transition matrix and p the final training state probabilities. The forecast mixture uses q=pA². With m=sum_k q_k m_k, the covariance is C_HMM=sum_k q_k[C_k+(m_k−m)(m_k−m)ᵀ]. The between-state term includes dispersion of state means. This two-session probability projection follows the execution delay, while portfolios may remain invested for about 21 sessions. The mismatch between forecast and holding horizons is a limitation.

Portfolio weights drift with asset returns between rebalances. Trading cost is c=0.001 sum_i |target_i−pretrade_i|. Net return for the recorded day is (1−c)(1+gross return)−1. The experiment charges initial purchases and excludes terminal liquidation. The 2025 slice comes from continuously running strategies, so buy-and-hold has no new initial purchase during that year. Traded notional uses the sum of absolute weight changes, without dividing by two.

## 6 Primary results

| 2025 outcome | Minimum variance | HMM minimum variance |
| --- | --- | --- |
| Total return | 2.875286% | 3.080609% |
| Net annual return | 2.910428% | 3.118298% |
| Annualized volatility | 12.591404% | 12.616941% |
| Net Sharpe | 0.133111 | 0.149094 |
| Maximum drawdown | -9.637089% | -9.684616% |
| Annual traded notional | 0.555373 | 0.783410 |
| Summed cost fraction | 0.000549 | 0.000774 |

The HMM estimate improves Sharpe slightly, while volatility, maximum drawdown and traded notional are slightly higher than the unconditional baseline. Equal weight achieves Sharpe 0.153192 and a total return of 3.1556 percent. Thus the comparison with an additional simple benchmark further limits an argument for HMM superiority. Summed cost fractions represent proportional charged fees across dates and differ from compounded wealth drag.

## 7 Uncertainty and sensitivity

The paired moving-block bootstrap resamples shared dates of the two net-return series. Non-circular blocks preserve local serial dependence and alignment between strategies. The Sharpe difference is 0.015983; its 95 percent percentile interval is [-0.010548, 0.041703]. The interval spans zero and does not establish a positive difference. It also does not establish equivalence. The HMM is not refitted within bootstrap replicates. Resampling 249 realized dates does not add independent market years.

| Seed | Cost in basis points | HMM minus baseline Sharpe |
| --- | --- | --- |
| 7 | 10 | +0.018393 |
| 42 | 0 | +0.017785 |
| 42 | 10 | +0.015983 |
| 42 | 25 | +0.013281 |
| 123 | 10 | +0.025288 |
| 2026 | 10 | +0.011073 |

These six scenarios share the same universe and evaluation dates. They describe sensitivity to initialization and the assumed trading charge. They provide correlated observations rather than independent replications. Spread, tax, price impact and heterogeneous execution costs are excluded.

Across the complete evaluated 2020–2025 path, minimum variance has Sharpe 0.627799 and HMM minimum variance has Sharpe 0.618703. Earlier years include development observations. This longer comparison is descriptive. All 70 primary fits converged in the updated run, compared with 45 iteration-cap failures in the archived 200-iteration implementation. Improved numerical convergence does not establish improved financial performance.

## 8 Discussion and limitations

The evidence is consistent with a small conditional-allocation benefit in 2025 and also with no benefit under the stated uncertainty procedure. A five-stock universe, sector concentration, one primary year and 11 primary-year decisions limit generalization. Regime labels describe relative risk within each fitted window. They do not guarantee bullish or bearish future returns.

The 2026 revision addresses scaling and convergence after the original outcomes were inspected. It must therefore be presented as a retrospective implementation revision. A stronger next evaluation would reserve later observations, freeze model choices before inspection, broaden the point-in-time universe and examine multiple market environments. The separate personalized and AI Black-Litterman replay in the project is a different experiment and is excluded from this paper’s HMM performance claim.

## 9 Reproducibility and conclusion

The current run was regenerated from the frozen adjusted-price CSV using research.run_regime_study. Its output includes prices, daily net-return ledger, equity paths, allocation decisions, metrics, seed and cost sensitivity, convergence diagnostics and the paired bootstrap. The manifest records input hashes, source-file SHA-256 values, package versions and execution conventions. The evaluation artifact directory is research/regime_evaluation_2026-11-17 inside analytics-engine.

Reproduction command from analytics-engine

venv/Scripts/python.exe -m research.run_regime_study --prices research/regime_holdout_2026-09-27_v2/prices.csv --output research/new_reproduction

Snapshot SHA-256

ed367e3dce5a3c58fb856b02fd2b2ae109286256f1073c56bc4d325dea041ab9

For the specified basket, updated HMM conditioning yields a net annualized Sharpe difference of 0.0160 relative to matched minimum variance. Its paired interval spans zero. All primary fits converge, but the higher trading intensity and inconclusive uncertainty limit claims of benefit. The contribution is the controlled implementation, auditable accounting and transparent evaluation of this allocation mechanism.

## References

[1] H. Markowitz. Portfolio Selection. The Journal of Finance 7(1), 77–91, 1952. doi:10.1111/j.1540-6261.1952.tb01525.x.

[2] J. D. Hamilton. A New Approach to the Economic Analysis of Nonstationary Time Series and the Business Cycle. Econometrica 57(2), 357–384, 1989. doi:10.2307/1912559.

[3] L. R. Rabiner. A Tutorial on Hidden Markov Models and Selected Applications in Speech Recognition. Proceedings of the IEEE 77(2), 257–286, 1989. doi:10.1109/5.18626.

[4] A. Ang and G. Bekaert. International Asset Allocation With Regime Shifts. The Review of Financial Studies 15(4), 1137–1187, 2002. doi:10.1093/rfs/15.4.1137.

[5] O. Ledoit and M. Wolf. Honey, I Shrunk the Sample Covariance Matrix. Journal of Portfolio Management 30(4), 110–119, 2004. doi:10.3905/jpm.2004.110.

[6] H. R. Künsch. The Jackknife and the Bootstrap for General Stationary Observations. The Annals of Statistics 17(3), 1217–1241, 1989. doi:10.1214/aos/1176347265.

[7] H. White. A Reality Check for Data Snooping. Econometrica 68(5), 1097–1126, 2000. doi:10.1111/1468-0262.00152.

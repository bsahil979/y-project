# Detailed analysis of the regime-allocation research paper

**Prepared:** 23 October 2026  
**Paper:** *Does Regime Conditioning Improve Minimum-Variance Allocation? Evidence from a five-stock Indian equity basket*  
**Reviewed version:** [PAPER_DRAFT.md](./PAPER_DRAFT.md) and the locally saved evidence listed in Section 15.

## 1. Overall assessment

The paper is a credible, narrowly scoped student empirical study with a reproducible experiment and an appropriately cautious conclusion. It asks a useful question: does adding inferred market states improve a portfolio optimizer when the other important design choices are held constant?

The evidence does **not establish that the HMM method improves portfolio performance**. Its 2025 Sharpe estimate is slightly higher than the matched baseline, but the uncertainty interval includes zero. The HMM also trades more, has marginally higher realized volatility and worse drawdown, and has lower Sharpe over the complete 2020–2025 path. Frequent fitting-limit hits further weaken the interpretation.

The strongest contribution is the transparent comparison and honest reporting of mixed evidence. A successful research paper need not demonstrate that its proposed method wins. Here, the useful result is that extra model complexity did not produce a clear, dependable advantage in this experiment.

**Readiness judgment:** a substantial results draft suitable for supervisor review. Submission readiness remains conditional on literature verification, clearer mathematical exposition, evidence of the protocol chronology, appropriate figures, and the institution's required format. This review does not predict acceptance by any venue.

## 2. Scope and evidence of this review

This report examines the local manuscript, protocol, literature matrix, diagnostics, saved result tables, sensitivity results, reproduction record, and selected statistical/backtest code. Numeric comparisons below use saved artifacts; additional differences and percentages are arithmetic derived from those artifacts.

No new strategy training, fresh data download, bootstrap run, or independent rerun of the complete experiment was performed for this report. The October 12 reproduction is an existing project record, not a new verification performed here. External reference full texts were not independently checked during this review. Literature-reading status is attributed to the existing literature matrix.

## 3. Research question and contribution

The primary question is well defined: on the fixed stock basket, does HMM-conditioned minimum variance improve net out-of-sample Sharpe relative to unconditional minimum variance?

This is stronger than a vague claim that artificial intelligence improves investing. Both methods share the asset universe, price history, rolling window, constraints, rebalance schedule, execution delay, and trading-cost convention. Consequently, covariance conditioning is the principal intended difference.

The contribution is an application and evaluation of established methods. Neither Gaussian HMMs nor minimum-variance optimization is introduced by this project. Avoid describing their combination alone as a new algorithm or an unfilled global research gap.

A defensible contribution statement is:

> This study provides a reproducible comparison of HMM-conditioned and unconditional minimum-variance allocation on a fixed five-stock Indian equity basket, reporting delayed execution, proportional costs, paired uncertainty, sensitivity checks, and fitting diagnostics.

## 4. Data design

The basket contains RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS, and ICICIBANK.NS. The manuscript reports 1,976 common price rows from 2018 through 2025 using Yahoo Finance auto-adjusted closes. Prices share INR denomination, and the design uses complete common sessions without forward filling.

These choices reduce avoidable currency and missing-price inconsistencies. A saved input snapshot and provenance manifest are useful because a later vendor download may differ from the original historical series.

However, five currently selected large companies do not represent the Indian equity market. Two banks and two IT companies also limit sector breadth. The fixed convenience selection leaves survivorship and selection bias unresolved. The results apply to this basket under this experiment; they cannot establish performance across Indian stocks generally.

The 2018–2019 observations largely provide training history before the out-of-sample path begins in January 2020. The paper should distinguish the data coverage period from the evaluated return period whenever it gives headline dates.

The 2025 primary evaluation has 249 daily observations but only 11 scheduled allocation fits according to the diagnostics. Thus, it is a short performance record with relatively few portfolio decisions, rather than hundreds of independent model trials.

## 5. Model and allocation methodology

The HMM observes one series: the equal-weight mean daily return of the five stocks, expressed in percentage units. It fits three Gaussian states using a rolling 504-return history, seed 42, a 200-iteration maximum, and a likelihood-change tolerance of 1e-4.

This is a univariate state model. The HMM's diagonal emission covariance should not be confused with the five-by-five asset covariance matrix used by the optimizer. State probabilities inferred from the univariate proxy are subsequently used to estimate multivariate asset moments.

The model estimates state-conditioned means and covariances using training-window responsibilities. Each state covariance is blended equally with unconditional covariance. A low-membership state would use unconditional estimates. The final state probabilities are propagated two transitions forward, and the resulting mixture covariance includes dispersion between state means.

Both methods then minimize estimated variance, subject to nonnegative weights summing to one and a 40% per-stock cap. Expected returns are not an optimizer objective. State means can still enter the mixture covariance through the between-state dispersion term; this does not turn the optimizer into a return-maximizing strategy.

The manuscript should add compact equations for:

1. The market-proxy return and posterior state probabilities.
2. Responsibility-weighted asset moments and the fixed 0.5 covariance blend.
3. Two-step state prediction and the mixture covariance.
4. The constrained objective: minimize w'Σw, with sum(w)=1 and 0≤w_i≤0.4.
5. Net-return accounting and annualized Sharpe.

The fixed 0.5 blend is a design choice, not the Ledoit–Wolf estimator. The current draft correctly distinguishes them and should retain that distinction.

A material modeling issue is the horizon mismatch: a two-session covariance forecast selects weights that can remain in place for 21 sessions. The execution lag explains why the forecast starts two transitions ahead, but does not establish that this forecast describes risk over the full holding period. Discuss this as an assumption; investigate alternatives only in a separately identified development experiment.

## 6. Execution and comparison fairness

The design uses data through close t, executes at close t+1, and first earns the return through close t+2. The inspected backtest slice excludes both the earned-return day and execution-day return from fitting. Holdings drift between scheduled rebalances.

This timing is a meaningful strength because an instantaneous trade at the same close used to calculate a signal would be harder to justify. Nevertheless, this review is not a comprehensive leakage audit of every upstream data transformation.

The cost rule charges 10 basis points times total absolute traded-weight changes, including the original purchase and excluding final liquidation. This must be distinguished from turnover conventions that divide the absolute weight change by two.

The 2025 metrics are extracted from a continuously running strategy. They are not a simulation of a new investor entering every strategy on January 1, 2025. In particular, buy-and-hold has zero costs during the holdout because its initial purchase occurred earlier. Explain this to prevent readers from interpreting its zero holdout costs as a free initial trade.

## 7. Detailed interpretation of the results

The following table uses the saved holdout CSV. Percentages are rounded for display.

| Metric, 2025 | Minimum variance | HMM minimum variance | Interpretation |
|---|---:|---:|---|
| Total return | 2.8753% | 3.1047% | HMM higher by about 0.2294 percentage points |
| Annualized return | 2.9104% | 3.1427% | HMM higher by about 0.2323 percentage points |
| Annualized volatility | 12.5914% | 12.6184% | HMM slightly higher by about 0.0270 percentage points |
| Annualized Sharpe | 0.133111 | 0.150966 | Difference +0.017855 |
| Maximum drawdown | −9.6371% | −9.6800% | HMM slightly worse by about 0.0429 percentage points |
| Annualized traded notional | 0.555373 | 0.762740 | HMM approximately 37.3% higher |
| Cumulative cost fraction | 0.000548762 | 0.000753660 | HMM approximately 37.3% higher |

The total-return difference is about 22.94 basis points. The cost fractions correspond to approximately 5.49 and 7.54 basis points of summed proportional fees, respectively. These fractions are not the same quantity as compounded terminal-wealth cost drag, which the saved CSV reports separately.

Equal weight has a 2025 Sharpe of 0.153192 and total return of 3.1556%, both slightly above the HMM method. However, equal weight also has higher volatility and a worse drawdown than either optimizer. It should remain visible as a useful simple benchmark; no strategy dominates every reported measure.

Over the complete 2020–2025 run, baseline Sharpe is 0.627799 versus 0.611433 for HMM, a difference of approximately −0.016367. This longer result is descriptive because it includes development observations. It does not replace the primary holdout, but it does prevent a broad claim of consistent HMM superiority.

## 8. Statistical uncertainty

The saved paired moving-block bootstrap estimates the HMM-minus-baseline Sharpe difference as 0.017855, with a 95% interval of **[−0.009043, 0.044191]**. It uses 21-session blocks, 10,000 valid replicates, seed 20260927, and the same resampled dates for both strategies.

Pairing matters: both portfolios experienced the same market days. Resampling them independently would discard that relationship. The inspected implementation samples contiguous, non-circular blocks and uses sample standard deviation consistently within the Sharpe calculation.

The interval spans zero. It therefore does not establish a positive difference under this uncertainty procedure. It also does not prove that the two strategies are equivalent or that the HMM cannot help elsewhere. No equivalence margin or equivalence test is supplied.

Ten thousand bootstrap replicates do not create ten thousand independent market histories. They resample the same short record. The approximately twelve block-length spans in 249 sessions illustrate limited temporal coverage, but are not a formal effective sample-size calculation. The resampling also evaluates the realized return paths; it does not refit the HMM inside every bootstrap replicate.

Do not infer a p-value, a probability that HMM is superior, or selection-adjusted significance from the interval alone. Alternative block lengths could be reported as clearly labeled secondary checks, preserving the original primary interval.

## 9. Convergence and state interpretation

Of 70 primary-run fits, 45 reached the iteration limit without meeting tolerance: **64.3%**. In the 2025 portion, five of 11 fits did so: **45.5%**. All 12 scheduled fits in 2024 reached the cap.

The 45-of-70 figure describes the full path, not the holdout alone. Including both counts would make the paper more precise.

An iteration-limit hit does not by itself prove an allocation is wrong. It does mean the specified stopping criterion was not satisfied, leaving uncertainty about parameter stability and state-conditioned covariance estimates. This is particularly material when the claimed performance difference is small.

State names are ranked within each rolling fit. A lower-return state in one window is not necessarily the same economic regime in another. Average inferred probabilities and fitted emission means cannot be presented as realized market-timing accuracy. No state needed the membership-mass fallback, but absence of that fallback does not establish reliable estimation.

TCS reached the 40% cap in 12 fits and HDFCBANK in six. These observations show constraints sometimes materially shape the solution. A supplementary weights plot would help readers understand whether conditioning materially changes allocations relative to the baseline.

## 10. Sensitivity analysis

The saved table contains six unique seed/cost scenarios, each with four strategies; it is not a complete four-seed-by-three-cost grid.

| Seed | Cost, bps | Holdout HMM-minus-baseline Sharpe |
|---:|---:|---:|
| 7 | 10 | +0.017467 |
| 42 | 0 | +0.019493 |
| 42 | 10 | +0.017855 |
| 42 | 25 | +0.015400 |
| 123 | 10 | +0.025437 |
| 2026 | 10 | +0.010345 |

The positive sign across these scenarios is useful local robustness evidence. It is not six independent replications: the same basket, year, and largely shared rules recur. Costs affect the HMM comparison, and the seed changes the result's size. Do not select seed 123 as the revised main result because it looks better.

The paper should explicitly state that seeds vary at 10 bps while cost sensitivity varies at seed 42. This resolves potential ambiguity in the protocol's presentation of seed and cost lists.

## 11. Reproducibility and chronology

The stored October 12 reproduction reports zero numeric difference for four full-period metric rows, four holdout metric rows, 1,471 equity rows, 5,880 ledger rows, and 24 sensitivity rows. It also records matching configuration, snapshot hash, and bootstrap output. One tracked source file differed from the original manifest while the numeric replay matched.

This is strong project evidence that the archived inputs and current replay can reproduce the saved outputs. It is not evidence of generalization, a new untouched holdout, or independent third-party validation.

The protocol is dated September 27, 2026, while the evaluated year is 2025. A historical period can be reserved from strategy evaluation after the market year has ended, but the word “preregistered” needs evidence of the lock before inspection of the strategy results. A local protocol date and hashes alone cannot establish that no earlier inspection occurred. The paper should identify the actual chronology and any timestamped commits or external registration if available. Without stronger evidence, “prespecified local protocol” is a more cautious description than implying independent public preregistration.

## 12. Literature and manuscript quality

The existing [literature matrix](../../LITERATURE_MATRIX.md) reports full-text review for several foundational sources, but only records/abstracts for Hamilton and the final Ang–Bekaert article. It distinguishes the Sullivan discussion-paper version from the final journal article. These are useful disclosures, and the outstanding checks should be completed before submission.

The current draft's literature supports covariance-based optimization, latent state modeling, and caution about estimation and strategy search. It does not by itself establish novelty or effectiveness for this implementation. Preserve the distinction between a cited motivation and a replicated method.

The matrix also contains a recent preprint absent from the paper's six references. Its bibliographic details, manuscript content, and relevance were not verified in this review. Do not insert it solely because it appears in the notes.

| Paper section | Assessment | Recommended revision |
|---|---|---|
| Title | Specific and appropriately framed as a question | Retain the restricted basket scope |
| Abstract | Includes the main estimate, uncertainty, and convergence issue | Keep numerical rounding consistent with tables |
| Introduction | Clear research question | Add a short explicit contribution paragraph |
| Related work | Relevant foundations with restrained claims | Complete pending full-text verification and articulate the narrow empirical gap |
| Methods | Detailed verbal description | Add equations, notation, and an execution timeline |
| Results | Transparent primary and mixed longer-period evidence | Add holdout-specific convergence counts and figures |
| Discussion | Conclusions follow the uncertainty | Explain equal-weight performance and horizon mismatch more explicitly |
| Limitations | Substantial and candid | Clarify local protocol chronology and limited allocation-decision count |
| Conclusion | Supported by the saved evidence | Avoid upgrading the claim after secondary analyses |

## 13. Separate older code from the current paper

The research folder retains older PPO-related work. In particular, `stats_tests.py` contains legacy wording about proving PPO/regime improvements and uses a 6% default risk-free rate in one bootstrap helper. The current regime study uses a 2% annual rate and its paired Sharpe-difference bootstrap is implemented in `regime_study.py`.

The inspected code and saved artifacts support using the latter for this paper. The existence of old statistical helpers is not evidence that their tests or assumptions generated the reported results. Provide a clear file map or label legacy material so readers do not accidentally combine the older experiment with the current comparison. This report changes no source code or original result artifacts.

## 14. Prioritized completion plan

### Before submission

1. Finish the outstanding full-text literature checks and confirm reference formatting.
2. Add equations and an execution timeline, explaining state inference separately from asset covariance estimation.
3. Clarify the local protocol lock, inspection chronology, and the meaning of the historical holdout.
4. Report the 2025-specific convergence count alongside the full-path count.
5. Add figures generated from saved artifacts: normalized 2025 equity, drawdown, and baseline-versus-HMM weights. Show uncertainty and retain all benchmarks.
6. State explicitly that sensitivity is six scenarios, not a full factorial grid; distinguish summed costs from compounded drag.
7. Apply the institution's template, author details, captions, citation style, and required declarations.

### For a separately identified follow-up study

Investigate initialization and convergence on development data; test a covariance horizon aligned with holding duration; consider additional chronological development windows and broader point-in-time universes; and specify more realistic trading costs. Lock any revised model before evaluating newly reserved data. Do not replace the original experiment or relabel already inspected 2025 results as untouched validation.

### Suggested presentation or viva answer

> We tested whether conditioning covariance on three inferred states improved a matched minimum-variance portfolio. On the reserved 2025 period, the Sharpe difference was about 0.018, but its paired bootstrap interval included zero. The HMM traded more and frequently reached its fitting limit. Our contribution is a reproducible comparison with mixed evidence, rather than a demonstrated performance improvement.

## 15. Evidence map

| Local source | Role in this analysis |
|---|---|
| [PAPER_DRAFT.md](./PAPER_DRAFT.md) | Manuscript claims and structure |
| [PROTOCOL_V1.md](./PROTOCOL_V1.md) | Primary question, chronology, and frozen settings |
| [REGIME_STUDY.md](./REGIME_STUDY.md) | Implementation and reproduction context |
| [HMM_DIAGNOSTICS.md](./HMM_DIAGNOSTICS.md) | Per-year convergence, state estimates, and concentration |
| [LITERATURE_MATRIX.md](../../LITERATURE_MATRIX.md) | Existing literature notes and verification status |
| [holdout_metrics.csv](./regime_holdout_2026-09-27_v2/holdout_metrics.csv) | Exact 2025 performance, cost, and turnover values |
| [holdout_sharpe_bootstrap.json](./regime_holdout_2026-09-27_v2/holdout_sharpe_bootstrap.json) | Primary paired interval and resampling settings |
| [sensitivity.csv](./regime_holdout_2026-09-27_v2/sensitivity.csv) | Six scenarios and full-period Sharpe comparisons |
| [REPRODUCTION_2026-10-12.md](./REPRODUCTION_2026-10-12.md) | Existing replay description |
| [reproduction_check.json](./regime_reproduction_2026-10-12/reproduction_check.json) | Recorded numerical matches and replay limits |
| [regime_study.py](./regime_study.py) | Selected execution, metric, and paired-bootstrap implementation |
| [stats_tests.py](./stats_tests.py) | Legacy statistical helper differences |

**Final assessment:** the paper has a defensible question, useful controls, and traceable results. Its evidence supports a mixed and inconclusive performance finding. Completing the documentation and presentation gaps will strengthen the paper without requiring a positive HMM result.

# Portfolio regime-allocation experiment protocol, version 1

**Protocol date:** 27 September 2026  
**Status:** Frozen settings and the 2025 primary comparison are complete. The 2020-2024 study remains development evidence. Results from the preregistered evaluation are recorded in the versioned artifact directory linked below.  
**Machine-readable settings:** [`experiment_protocol_v1.json`](./experiment_protocol_v1.json)

## Question and scope

Does a three-state Gaussian HMM-conditioned minimum-variance allocation improve net out-of-sample Sharpe ratio over the same minimum-variance optimizer without state conditioning, on a fixed five-stock Indian equity basket?

The intended audience is a student evaluator and readers interested in an explainable portfolio-research prototype. This is a narrow empirical comparison, not a claim of a new learning method, financial advice, or a production trading strategy.

## Data and universe

- **Fixed convenience universe:** RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS, ICICIBANK.NS. Keep this same list and order for every strategy. It is a selected set of current large firms, not a point-in-time index membership list; survivorship and selection bias remain limitations.
- **Currency:** INR throughout. No FX conversion.
- **Final data request:** 2018-01-01 inclusive to 2026-01-01 exclusive, giving history through 2025-12-31 where observations are available.
- **Source convention:** Yahoo Finance `auto_adjust=True`, Close field. Reject a fallback whose split/dividend adjustment convention is unverified. Record UTC retrieval time, source and convention, actual first/last session, complete-row count, dropped incomplete-row count, ticker order, dependency versions, and SHA-256 of the exact price snapshot.
- Use only complete positive price rows shared by all five tickers. Do not forward-fill missing prices. Returns are close-to-close percentage changes on the resulting common session index. The backtest uses adjusted historical closes, which are not executable quotes.

## Chronology and lock

- Treat the previously inspected 2020-01-24 through 2024-12-31 experiment as exploratory development. It motivated the current code and cannot be presented as a final holdout.
- **Final held-out evaluation:** 2025-01-01 through 2025-12-31, inclusive. The preliminary snapshot ends 2024-12-31; the new frozen snapshot through 2025-12-31 and its evaluation artifacts are linked in the results section.
- Require at least 200 daily return observations in the holdout before reporting the final metrics and bootstrap interval. Fewer rows are a data-coverage failure, not evidence to relax the threshold after viewing performance.
- Run the strategy continuously on the full saved history to create the positions and decisions that would exist by 2025. Only ledger returns dated in 2025 contribute to the primary holdout metrics. At each decision, use the preceding 504 observed daily return rows; after a 2025 return has occurred, it may enter later rolling training windows.
- Freeze code, universe, settings, data cleaning and metric definitions before reading 2025 strategy results. Do not alter the main settings after seeing holdout results. Record any subsequent exploration as a new study, never as a replacement for this test.

## Strategies and allocation settings

All strategies use the same tickers and common return dates:

1. Buy and hold: equal initial weights, then allow weights to drift.
2. Equal weight: rebalance to equal weights on the common 21-session schedule.
3. Minimum variance: long-only minimum variance using the unconditional covariance estimate.
4. HMM minimum variance: same optimizer and constraints, but use covariance conditioned on probabilities from the HMM.

Fixed primary HMM and optimizer settings: three diagonal-covariance Gaussian states; equal-weight portfolio return as the one-dimensional HMM input in percentage units; random seed 42; convergence tolerance 1e-4; at most 200 EM iterations; 504-return rolling history with at least 126 observations; fixed state-covariance shrinkage 0.5 toward unconditional covariance; state membership mass below two uses unconditional mean/covariance; small diagonal ridge for numerical stability; two transition steps for the forecast; nonnegative weights summing to one; 40% maximum per stock. These are prespecified code settings, not values to optimize on 2025.

## Execution and costs

1. Form the decision from information through close t.
2. Execute target weights at close t+1, without using that session's return to form the decision.
3. Start earning returns from close t+1 to close t+2.
4. Rebalance equal weight and both optimizers every 21 common sessions. Buy-and-hold trades only for its initial purchase. Holdings drift between trades.
5. Apply 10 basis points to the sum of absolute traded-weight changes at each trade, including initial purchases. Do not charge a final liquidation. This is a proportional turnover-cost approximation; it excludes spread, taxes, market impact, and liquidity constraints.

Use the same schedule, date rows, execution delay, cost rule, and position limits for both optimizer strategies. Do not use a predicted return objective: both optimizers minimize estimated variance.

## Outcomes and uncertainty

- **Primary outcome:** difference in 2025 net annualized Sharpe ratio, HMM minimum variance minus matched minimum variance. Use a 2% annual risk-free rate converted to an effective daily rate and 252-session annualization.
- **Primary uncertainty display:** paired moving-block bootstrap interval for that Sharpe difference, resampling the same 2025 return-date blocks for both optimizers. Predeclare 21 sessions per block, 10,000 replicates, RNG seed 20260927, and a 95% percentile interval. Preserve strategy pairing within each sampled date. This interval is exploratory: one year and one convenience universe cannot establish broad effectiveness.
- **Other reported outcomes:** annualized volatility, annualized return, total return, maximum drawdown, turnover, and estimated costs for every strategy. Show the optimizer pair side by side and do not suppress results that favor a baseline.
- Also provide 2025 quarterly descriptive metrics if implemented, clearly labeled secondary. Do not treat overlapping blocks or quarters as independent replicates.
- Report seed and cost sensitivity as secondary robustness, without selecting a winner: seeds 7, 42, 123, and 2026; cost assumptions 0, 10, and 25 bps. The primary result remains seed 42 and 10 bps. Record and show all attempted variants.

## Required artifacts and limitations

Save one output directory containing the exact input snapshot, manifest, per-decision weights and states, daily gross/net returns, turnover and costs, full equity paths, 2025 holdout metrics, bootstrap interval, sensitivity table (`sensitivity.csv`), software versions, source hashes and configuration. The runner refuses a non-empty directory unless explicitly overridden. Never replace the preliminary `research/regime_results` artifacts; use a new versioned output directory. Recompute tables from the saved ledger for consistency.

The result will remain limited by the five-stock convenience universe, possible survivorship/selection bias, one final calendar year, a simple cost model, vendor-adjusted close history, and uncertainty in HMM estimation. A negative, mixed, or unstable result is still the result. Do not claim statistical significance or generalization beyond this design.

## Observed primary result

The protocol was evaluated on the new saved 2018-2025 snapshot. The reproducible artifacts are in [`regime_holdout_2026-09-27_v2`](./regime_holdout_2026-09-27_v2/manifest.json); the exact input and its provenance are in [`regime_data_v1`](./regime_data_v1/manifest.json). The earlier `v1` run has the same numerical results but is superseded because its manifest did not include the nested input provenance correctly. The preliminary `regime_results` directory was not replaced.

On the 249 daily returns in 2025, the matched minimum-variance Sharpe was 0.1331 and the HMM-conditioned Sharpe was 0.1510, a difference of +0.0179. The paired 21-session moving-block bootstrap interval was [-0.0090, 0.0442], so it includes zero; this single year and five-stock convenience universe do not establish that the HMM allocation is better. Annualized volatility was nearly equal (12.59% baseline; 12.62% HMM). The HMM method had higher annualized traded notional (0.763 versus 0.555) and higher estimated costs. Its 2025 total return was 3.10% versus 2.88% for minimum variance.

All five declared seed/cost sensitivity variants had positive HMM-minus-baseline holdout Sharpe differences, ranging from +0.0103 to +0.0254. The full-period result favored the baseline on Sharpe (0.6278 versus 0.6114), so the development history and final year do not tell the same story.

**Convergence limitation:** 45 of the 70 primary allocation fits reached the 200-iteration cap without meeting the declared 1e-4 likelihood-change tolerance. Those decisions were still used in the prespecified run. Treat this as a material limitation; do not describe the HMM fits as consistently converged or the result as conclusive. The saved `decisions.json` contains each fit's iteration count and final likelihood change.

The result should be reported as a small positive point estimate with substantial uncertainty, higher turnover, and frequent HMM iteration-cap hits—not as evidence that regime conditioning improves portfolios.

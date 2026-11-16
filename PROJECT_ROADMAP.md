# Project roadmap

## What we are building

**Working title:** Explainable Portfolio Risk Analysis and Regime Aware Allocation.

The app lets a person record stock holdings, see what those holdings are worth using available quotes, inspect historical portfolio risk, and compare a conventional allocation with one informed by estimated market conditions. A separate Research page presents a saved historical comparison of several allocation strategies.

The main flow is:

**Holdings and prices → portfolio weights → risk analysis → HMM market state probabilities → allocation comparison → historical evaluation.**

The research question is: **Does adding information from estimated market states to a minimum variance portfolio allocation improve risk adjusted results on later, unseen data?**

We use the `hmmlearn` library to fit an existing Gaussian Hidden Markov Model to past returns. We did not invent HMMs, and we should not claim a new learning algorithm. The project work is to connect a trained model to a portfolio allocation system, explain the result, and evaluate it fairly. We will treat the research as an empirical comparison of established ideas. Any claim of novelty must wait until the related work review establishes a specific gap.

## Current state

### Implemented

- React portfolio interface, FastAPI analytics service, user authentication and portfolio ledger.
- INR and USD holdings shown and analyzed separately.
- Quote source and fetch time are distinguished from the latest daily market session; delayed daily prices are labelled in the holdings view.
- Portfolio risk results report the history provider, adjustment convention, actual observation range and sample size; missing dates are excluded rather than filled with stale prices.
- Current value calculated from quantity × latest available quote. Missing or mismatched prices leave current value and analysis unavailable instead of substituting recorded cost.
- Historical risk metrics, benchmark comparisons, stress scenarios and per holding risk contributions.
- Three state Gaussian HMM fitted to the prior 504 daily observations; HMM state conditioned covariance estimates feed a long only, maximum 40% per stock minimum variance allocation.
- A matched allocation without market states, plus buy and hold and equal weight comparisons.
- Chronological study runner with delayed execution, drifting positions, a stated trading cost and saved metrics, equity curve, daily ledger, per decision output and data/code hashes.
- Main navigation for Portfolio, My Holdings, Transactions, Research and Settings. Secondary features are grouped under Experimental tools.
- The dashboard waits for saved workspace data before enabling forms, and ignores late workspace loads after an account switch.
- A source-linked draft literature matrix identifies established methods, nearby regime-allocation work and limits on the project’s claims.

### First development result

The recorded run covers five Indian stocks from 2018 through the end of 2024. It evaluates 1,221 daily returns from 2020-01-24 through 2024-12-31 using 59 allocation decisions and one model seed.

| Strategy | Annualized return | Annualized volatility | Sharpe ratio | Maximum drawdown |
|---|---:|---:|---:|---:|
| Buy and hold | 16.55% | 20.84% | 0.745 | -36.81% |
| Equal weight | 17.85% | 20.92% | 0.796 | -36.75% |
| Minimum variance | 15.23% | 20.50% | 0.698 | -35.11% |
| HMM minimum variance | 14.70% | 20.43% | 0.677 | -35.21% |

In this run, the HMM allocation reduced volatility slightly compared with the matched minimum variance allocation, but also had lower return and a lower Sharpe ratio. It did not establish an advantage. This is a preliminary result on a narrow, selected universe and an old sample. Keep it visible, reproduce it, investigate the method honestly, and replace it only with a better documented run—not with a result selected because it looks better.

The app currently reports price and allocation estimates. It is an educational research prototype, not a broker, execution system or personalized financial advisory service.

## One month of sequenced work

The weeks below are a suggested four week work plan, not a promise that a complex study can be completed regardless of data, school requirements or available working time. Keep the phases in order; remove optional scope before shortening the evaluation.

### Week 1 — Make the app reliable and the data current

**Goal:** a new user can enter a portfolio and understand what every displayed amount represents.

- Run the app from a clean start and verify onboarding, authentication, adding and removing holdings, transactions, quote refresh, portfolio analysis and research results.
- [x] Record the source and retrieval time for each quote, separately from the latest daily market session. Label delayed daily prices in the holdings view.
- [x] Handle missing prices, invalid symbols and provider outages visibly; show the latest provider session so weekends and market holidays are distinguishable from the retrieval time.
- [x] Read-only live API check: a three-stock portfolio returned matched conventional and HMM allocations, Yahoo-adjusted history coverage and all four risk metric groups; quote refresh returned USD/INR values, and the saved research endpoint returned four current strategies.
- [x] Confirm that Indian ticker suffixes and returned quote currencies agree; reject unknown or unsupported currencies instead of assuming USD. Keep INR and USD calculations separate without FX conversion.
- [x] Make the risk table definitions explicit: annualized volatility, signed one-day historical VaR/CVaR and in-window maximum drawdown. Market value, cost, P/L and market-value weights use the shared valuation contract.
- [x] Report the selected historical price provider, adjustment convention, actual dates and observation count with the risk table. Keep provider adjustment uncertainty visible.
- [x] Audit analysis inputs: weights come from quantity × quote, duplicate positions aggregate by ticker, ticker/weight order remains aligned, incomplete prices block analysis, and the dashboard sources owned holdings rather than the watchlist.
- Test the real app, not just API endpoints: empty portfolio, one holding, five holdings, multiple currencies, missing quote, bad ticker, outage, refresh and saved account. Save a short screen recording for repeatable demonstrations.

**Done when:** a five position INR portfolio produces correct, currency labeled amounts; incomplete price coverage cannot produce an apparently complete portfolio value or optimized allocation; the main app works after a clean start.

### Week 2 — Freeze the experiment before the final evaluation

**Goal:** agree on one research protocol before looking for a more favorable answer.

- [ ] Read the full references and finalize the literature matrix. A source-linked working draft is in [LITERATURE_MATRIX.md](./LITERATURE_MATRIX.md); sample details and methods still need checking against the full papers.
- [x] Define the target user, study universe and currency; keep a fixed Indian-stock convenience universe and state its survivorship/selection limitation.
- [x] Refresh prices through the last complete historical year. The new 2018-2025 snapshot, source, adjustment convention, retrieval time, coverage, excluded rows, tickers and hash are recorded in `analytics-engine/research/regime_data_v1`; the preliminary snapshot is preserved.
- [x] Define chronology: 2020-2024 is exploratory; 2025 is reserved as final test with rolling prior 504-return training. Freeze settings before producing that test.
- [x] Fix shared execution, rebalance and transaction-cost rules, including initial purchase costs and no final liquidation.
- [x] Predefine four strategies: buy and hold, equal weight, conventional minimum variance and HMM-conditioned minimum variance.
- [x] Predefine primary/secondary metrics and paired 21-session moving-block uncertainty settings; the runner implements holdout metrics, a paired bootstrap and the seed/cost table. Static source/protocol review is complete.

**Done when:** the dated protocol and experiment configuration are reviewed and committed before the final evaluation. Review and evaluation are complete; these research files remain uncommitted in the existing dirty worktree.

### Week 3 — Evaluate, check robustness and investigate the result

**Goal:** learn whether the observed difference is stable, explainable and large enough to matter.

- Run multiple chronological walk forward evaluation windows where data permits. Every decision must be based on its own prior training history; prior test data may enter training only after it has occurred.
- [x] Repeat the HMM with predeclared seeds and report every seed; all results are in the versioned `sensitivity.csv`.
- [x] Run the predeclared transaction-cost sensitivity table; report every cost setting in `sensitivity.csv`. Modeling-choice variants remain future work and must not be used to select a replacement result on this holdout.
- [x] Inspect primary-run convergence, state membership, forecast probabilities and allocation concentration; the descriptive analysis is in [HMM_DIAGNOSTICS.md](./analytics-engine/research/HMM_DIAGNOSTICS.md). State persistence analysis remains open.
- [x] Compare the HMM method directly with its matched no-state baseline on the primary holdout and report costs, traded notional and drawdown in [PROTOCOL_V1.md](./analytics-engine/research/PROTOCOL_V1.md). Multiple walk-forward windows remain future work.
- Investigate why HMM did or did not help: covariance estimation error, low membership in a state, high turnover, weak state persistence, concentrated stock universe, horizon mismatch or outlying market periods. Change the production method only after documenting the reason and repeat the full protocol.
- [x] Check the input/output snapshot hashes and independently recompute the 2025 metrics from the ledger; the API serves those same CSVs and the Research page module consumes the API payload. Visual browser QA remains pending.

**Done when:** another run from the saved price snapshot reproduces the tables and curves; there is a clear held out result with stated limitations, without a result chosen for its direction.

### Week 4 — Write and finish the project package

**Goal:** the code, app, paper and presentation tell the same accurate story.

- [x] Create the first complete paper draft in [PAPER_DRAFT.md](./analytics-engine/research/PAPER_DRAFT.md), using the frozen protocol and saved artifacts as its source of results.
- [x] Include the research question, dataset, source, universe, date splits, HMM setup, execution, costs, baselines, metrics, and seeds in the working draft.
- [x] Include result tables and discuss the mixed result and limitations without claiming statistical significance. Final figures and school formatting remain to be added.
- Finish references in the school’s required style and verify each citation against the paper itself. Explain which parts are standard methods and exactly what the implementation and experiment contribute.
- Rehearse a 5–7 minute app flow: add positions → inspect current value and risk → compare suggested weights → view the separate historical experiment. Record a clean backup demonstration.
- Prepare a final handoff: startup steps, dependency list, research protocol, saved dataset manifest, generated outputs, presentation, report and limitations.

**Done when:** a fresh user can start the app and reproduce or read the study without relying on undocumented local steps; the paper never calls the first single-seed result conclusive.

## Technical work still worth prioritizing

1. **Source and data traceability:** the app shows quote source/time and historical price provider/convention/date coverage; the paper snapshot and manifest are saved. Corporate-action timing and vendor handling still need source-level documentation.
2. **Portfolio definition:** keep holdings, transaction ledger, cost basis, current market value and optimizer weights distinct. Decide whether buy and hold baselines start equal weight or match the user’s initial weights, and document that choice.
3. **HMM stability:** [x] expose convergence status, iteration count and likelihood change in the live allocation response; warn on the portfolio screen when a fit reaches its iteration limit without meeting tolerance. Short or invalid history, low state membership, and optimizer failures remain explicit through validation, the documented low-mass covariance fallback, and unavailable responses. The saved historical experiment remains unchanged.
4. **Metric definitions:** review daily versus annual VaR/CVaR, Sharpe conventions, drawdown calculation, trading-day counts, return compounding and cost signs. Ensure frontend labels match the backend output.
5. **Run integrity:** a study artifact should record the precise data hash, configuration, code revision/hash, environment, model seed, date ranges, baselines and assumptions. Show when displayed results are stale.
6. **Research reproducibility:** the script should use the same tested prices and strategy code as the app. The app reads saved results; it should not launch an expensive experiment as a page-load side effect.

## Optional Random Forest extension

The repository contains a Random Forest signal model, but it is not part of the current paper or HMM allocation method. Do not add it to the main method simply to increase the model count.

Only consider this extension after the HMM study is frozen and repeatable. Define a separate question: **does a point in time Random Forest return direction signal add out of sample value beyond market state information and the existing baselines?** Train labels strictly within each training fold. Avoid random train/test shuffling. Compare HMM alone, Random Forest alone, and HMM plus Random Forest on the same costs, dates and constraints. Report calibration and classification metrics alongside portfolio results. Keep the extension only if the implementation is understandable, its evaluation passes leakage checks, and it contributes a defensible answer. Otherwise, document it as future work.

PPO trading, live broker orders, more model families, crypto/forex, AI chat, news ingestion and personalized advice are outside the current delivery. Preserve existing modules; do not spend the main project’s time expanding them.

## Research risks and how to handle them

| Risk | Response |
|---|---|
| One favorable universe or date range drives the conclusion | Set a universe rule in advance, use multiple chronological windows, preserve a locked final period, disclose limitations |
| Current large cap names exclude failed or delisted names | Seek point in time constituents; if unavailable, label the convenience universe and avoid market wide claims |
| HMM state naming suggests a direction the model does not establish | Define states by relative training means; report probabilities, means, volatility and membership counts |
| Weakly populated state produces unreliable covariance | Set a minimum membership and fallback rule in advance; report when it activates |
| A strategy looks better before realistic costs | Apply equal stated costs to every method; show a cost sensitivity analysis and turnover |
| Optimization estimates covariances and evaluates on overlapping data | Keep all optimizer fits inside training windows and score only later returns |
| Many trial settings lead to a lucky reported result | Label exploratory runs; tune on validation data; publish the frozen final configuration and all prespecified outcomes |
| Small differences are noise | Report results across windows, assess uncertainty with an appropriate block method and avoid unsupported significance claims |
| Market price download changes later | Archive the actual input file and hash it; cite requested and observed date coverage |
| Product screen makes a simulation sound like advice | Label forecasts, allocations, scenarios and delayed quotes; keep execution disabled |

## Suggested paper structure

1. Abstract — question, method, data, main result and limitation.
2. Introduction — the investor problem, narrow contribution and research question.
3. Related work — portfolio optimization, regime switching/HMMs, covariance estimation and backtesting practice.
4. Methodology — HMM training, state conditioned covariance, probability forecast, optimizer, matched baseline and state labels.
5. Experimental design — universe, data source, adjusted prices, chronological splits, costs, execution and metrics.
6. Results — each window, aggregate comparison, turnover, costs, drawdown, sensitivities and uncertainty.
7. Discussion — why the method did or did not help, implementation implications and threats to validity.
8. Conclusion and future work — findings within their limits; Random Forest only if separately assessed.
9. References and appendices — exact configurations, ticker list, extra tables, reproducibility commands and code/data hashes.

## Starter reading for the literature review

These sources establish background, not proof that this exact project is novel or effective. Read the papers and compare their actual methods before describing a research gap.

- Harry Markowitz, “Portfolio Selection,” *The Journal of Finance* 7(1), 77–91 (1952), [doi:10.1111/j.1540-6261.1952.tb01525.x](https://doi.org/10.1111/j.1540-6261.1952.tb01525.x).
- James D. Hamilton, “A New Approach to the Economic Analysis of Nonstationary Time Series and the Business Cycle,” *Econometrica* 57(2), 357–384 (1989), [doi:10.2307/1912559](https://doi.org/10.2307/1912559).
- Andrew Ang and Geert Bekaert, “International Asset Allocation With Regime Shifts,” *The Review of Financial Studies* 15(4), 1137–1187 (2002), [doi:10.1093/rfs/15.4.1137](https://doi.org/10.1093/rfs/15.4.1137).
- A recent, directly related preprint, Ajay Kumar Verma, Nunik Srikandi Putri and Neo Paul Lesupi, “Regime-Based Portfolio Allocation Using Hidden Markov Models and Reinforcement Learning” (May 2026), [arXiv:2605.27848](https://arxiv.org/abs/2605.27848). Treat it as a preprint; read and verify its claims and relation to this method rather than using its stated results as evidence for this project.
- The [hmmlearn GaussianHMM API](https://hmmlearn.readthedocs.io/en/0.3.3/api.html) is an implementation reference, not a research source for claims about investment performance.

## Project completion checklist

- [ ] Core app flow works after a clean start and is visually reviewed.
- [ ] All displayed portfolio values use complete quote coverage and correct currency labels.
- [ ] Study universe, price provenance, split dates, costs and metrics are documented and frozen before final evaluation.
- [ ] HMM and baseline are compared on identical, unseen chronological returns.
- [ ] Multiple windows, seeds and prespecified cost/model checks are reported.
- [ ] Study artifacts reproduce from the saved snapshot and show matching code/data hashes.
- [ ] Literature review includes related work and limits novelty claims.
- [ ] Paper accurately reports favorable and unfavorable results with limitations.
- [ ] Final report, application, slides, recording and run instructions are packaged together.

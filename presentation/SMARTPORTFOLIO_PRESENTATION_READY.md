# SmartPortfolio presentation

14 slides for a 12-15 minute college evaluation, including a two-minute demonstration.

This file contains slide-ready text and speaking notes; it is not a PowerPoint deck. Replace the title-page placeholders with actual details.

Design: white background, navy text and purple accents. Use 32-36 pt headings, 20-24 pt body text and actual app screenshots. Put speaking notes in PowerPoint Notes, not on the slide.

## Slide 1: Smart Portfolio Advisor and Recommendation System

- Portfolio tracking, explainable risk analysis and HMM-based allocation
- Presented by: [Team names and roll numbers]
- [Guide, department and college]

**Speaking notes:** Good morning. Our project helps users understand their holdings, identify portfolio risk and compare allocations. We will show the working application and a controlled research comparison.

## Slide 2: Problem and objectives

- Stock prices alone do not explain total portfolio risk.
- Concentration and relationships between assets affect outcomes.
- Our objective: connect portfolio records, risk analysis and explainable allocation comparisons.

**Speaking notes:** The focus is how holdings behave together. We also investigate whether statistical market states improve allocation compared with a matched conventional method.

## Slide 3: Working application

- Holdings and transaction ledger with quantity and cost validation
- Market-value calculations with quote source and timing
- Separate INR and USD totals
- Supabase authentication and cloud workspace saving

**Speaking notes:** The prepared cloud account contains sample holdings. Purchase cost and current market value are different. We keep currencies separate rather than inventing an exchange rate. The application does not place broker orders.

## Slide 4: System architecture

- React + Vite + Tailwind CSS: user interface
- FastAPI + Python: analytics API
- Supabase/PostgreSQL: authentication and portfolio storage
- Market data and saved model artifacts: analysis inputs

**Speaking notes:** Show this as a simple diagram: React communicates with Supabase for identity and records, and with FastAPI for analysis. FastAPI obtains market data and runs the analysis pipeline. The Research page reads saved experiment outputs.

## Slide 5: Portfolio analysis workflow

- Record opening positions and transactions
- Derive holdings and obtain available quotes
- Calculate market values and currency-specific weights
- Calculate historical risk and compare allocations
- Display results with explanations and reliability warnings

**Speaking notes:** Market value equals quantity multiplied by price. Portfolio weights use market value, not purchase cost. Missing or mismatched prices remain unavailable rather than being silently replaced with cost.

## Slide 6: Risk analysis and allocation

- Historical volatility and risk contributions
- Concentration and benchmark comparisons
- Hypothetical stress scenarios
- Constrained minimum-variance allocation

**Speaking notes:** Minimum variance selects weights to minimize estimated variance. It does not maximize profit or guarantee future performance. Stress scenarios are defined hypothetical shocks, not necessarily exact historical replays.

## Slide 7: HMM-based allocation

- Three-state Gaussian Hidden Markov Model
- Up to 504 earlier daily return observations
- States ordered by fitted mean returns
- State probabilities blend covariance estimates
- The same constrained optimizer then selects weights

**Speaking notes:** We use the established hmmlearn implementation. State labels describe fitted historical behavior, not guaranteed bull or bear markets. The HMM changes the covariance estimate; the matched baseline uses unconditional covariance. In the study, each state covariance is blended 50% with unconditional covariance.

## Slide 8: Experimental setup

- Five Indian stocks: Reliance, TCS, Infosys, HDFC Bank and ICICI Bank
- 2018-2025 prices; exploratory evaluation in 2020-2024
- Primary holdout: 2025, with 249 daily returns
- Rebalance every 21 sessions; no shorting; 40% stock cap
- Delayed execution and identical transaction-cost assumptions

**Speaking notes:** A decision uses information through close t, executes at close t+1 and first earns the next return. Costs are 10 basis points multiplied by absolute traded-weight changes. Sharpe assumes a 2% annual risk-free rate and 252 sessions. This fixed research universe differs from the demonstration account.

## Slide 9: 2025 holdout results

- Minimum variance: Sharpe 0.1331
- HMM minimum variance: Sharpe 0.1510
- Difference: +0.0179
- Paired bootstrap 95% interval: -0.0090 to +0.0442
- The interval includes zero; no reliable HMM advantage is established.

**Speaking notes:** The HMM point estimate is slightly higher than its matched baseline for 2025. Equal weight had approximately 0.153 Sharpe. Avoid claiming that the HMM wins overall. Show the difference and interval prominently, with metric labels and period.

## Slide 10: Diagnostics and reproducibility

- Full-period Sharpe: HMM 0.6114; baseline 0.6278
- 45 of 70 primary HMM fits reached the iteration cap
- October 12 current-code replay matched archived results
- Replay checked metrics, equity, ledger and sensitivity outputs

**Speaking notes:** The longer-period result favors the baseline. Fitting warnings remain important. The replay produced zero numeric differences in the compared outputs, including 1,471 equity rows and 5,880 ledger rows. It uses the same archived data, so it is not another independent holdout.

## Slide 11: More Tools

- Watchlist and Fundamentals: symbols and company financial data
- Forecasts and Sentiment: model paths and headline signals
- Trading experiments and AI chat: research signals and explanations
- Model training and Goals: training jobs and savings milestones

**Speaking notes:** These supporting tools are separate from the HMM allocation experiment. Model artifacts do not establish predictive accuracy. Chat can use template-based analytics; optional LLM mode requires configuration. Goals track saved and target amounts, not future investment returns. Do not start a long training job during the demonstration.

## Slide 12: Verification and current status

- Latest recorded frontend run: 52 tests passed
- Recorded targeted backend checks: 28 tests passed
- Production build passed after theme fixes
- Browser checks: ledger, oversell rejection, reload and backend recovery
- Cloud registration, confirmation and workspace saving succeeded

**Speaking notes:** These are recorded checks; tests were not rerun while preparing this presentation. The app reported Synced after the database currency migration. Later authenticated screens showed saved data. A clean second-device check remains useful. Optional pages received visual review, not exhaustive functional or model-accuracy validation. The build has a large-bundle warning.

## Slide 13: Live demonstration

- Show the cloud account and sample holdings
- Show the RELIANCE buy updating 10 shares to 12
- Explain portfolio risk and allocation comparisons
- Open Research and explain the result uncertainty
- Briefly show one or two More Tools pages

**Speaking notes:** Allow about two minutes. Keep credentials off screen. Clearly distinguish the sample account, current market data and fixed historical research study. Use saved Research outputs if live quotes fail.

## Slide 14: Limitations and next steps

- Five-stock sample and one primary holdout year
- Frequent HMM fitting limits and simplified trading costs
- Broader chronological evaluation and new universes needed
- Complete optional-tool acceptance checks and final documentation

**Speaking notes:** The contribution is an integrated portfolio application and a reproducible comparison using established methods. We do not claim guaranteed profit, a novel HMM algorithm or reliable outperformance. Thank you; I welcome your questions.

## Evidence and preparation

- Research setup and results: THIRD_EVALUATION_PPT_CONTENT.md; analytics-engine/research/regime_holdout_2026-09-27_v2/holdout_metrics.csv.
- Reproduction: analytics-engine/research/REPRODUCTION_2026-10-12.md and the saved reproduction_check.json.
- Core checks: DEMO_READY.md and the recorded work in this session. Older documentation contains outdated cloud-login and reproduction limitations; the slides above distinguish completed checks from remaining work.
- Optional tools: implemented frontend components; their existence does not establish predictive accuracy.

## Screenshots to insert

- Slide 3: My Holdings, with quote timing and separate currency totals.
- Slide 6: Portfolio risk or Improvements screen.
- Slide 9: Research results, retaining uncertainty and diagnostic labels.
- Slide 11: Updated Watchlist or Fundamentals page.

## Likely questions

**What did you contribute?** Portfolio integration, validation, risk explanations, state-conditioned covariance and a controlled reproducible comparison.

**Did you invent HMM?** No. We use an established Gaussian HMM implementation and evaluate its application to allocation.

**Did it outperform?** The one-year Sharpe difference is small and its interval includes zero. The longer-period Sharpe is lower. Reliable superiority is not established.

**How is future-data leakage limited?** Decisions use earlier observations, execution is delayed, and regression checks perturb future data to check earlier outputs do not change.

**Does the system trade?** The demonstrated application records a portfolio ledger and research signals; it does not execute broker orders.

**Why not combine INR and USD?** A combined value requires an explicit FX policy. Current analyses keep them separate.

**Why keep optional modules?** They support exploration and demonstrations, but are not all part of the evaluated HMM allocation method.

## Rehearsal

Spend about 1 minute on the introduction, 3 minutes on the application and architecture, 4 minutes on the method and results, 1 minute on optional tools and verification, 2 minutes on the demo, and 1 minute on limitations. Keep remaining time for questions.

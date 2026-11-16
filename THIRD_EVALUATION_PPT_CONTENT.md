# Third Evaluation Presentation Content

**Presentation date:** 13 October 2026  
**Project:** Smart Portfolio Advisor and Recommendation System  
**Suggested duration:** 12–15 minutes, including a short demonstration  
**Preparation basis:** Current project documentation, saved research results, and the verification checkpoint dated 9 October 2026. Tests were not rerun while preparing this content.

Copy the bullets under **Slide content** into PowerPoint. Use **Speaking notes** while rehearsing. Replace the title-page placeholders with your actual details. Suggested screenshots must come from your application.

## Slide 1 — Smart Portfolio Advisor and Recommendation System

### Slide content
- Explainable Portfolio Risk Analysis and HMM-Based Allocation
- Third Project Evaluation
- Presented by: [Student names and roll numbers]
- Guide: [Guide name]
- [Department and college]
- 13 October 2026

### Speaking notes
“Our project helps users understand their stock portfolio risk and compare alternative allocations. For this evaluation, we present the implemented application, the HMM allocation method, our recorded research results, and the remaining validation work.”

## Slide 2 — Problem Statement

### Slide content
- Tracking individual stock prices does not explain total portfolio risk.
- A few holdings can account for much of a portfolio’s concentration and risk.
- Asset relationships can change across market conditions.
- Users need allocation comparisons with clear assumptions and explanations.

### Speaking notes
“The problem is understanding how stocks behave together. We calculate portfolio risk and compare allocations using the same holdings. We also investigate whether learned market states improve the covariance estimate used by the optimizer.”

## Slide 3 — Project Objectives

### Slide content
- Record holdings and transactions in a portfolio workspace.
- Calculate historical risk, concentration, and benchmark comparisons.
- Estimate statistical market states using a Gaussian HMM.
- Compare conventional and HMM-conditioned minimum-variance allocations.
- Evaluate both methods using chronological data and consistent costs.

### Speaking notes
“The application objective is useful, explainable portfolio analysis. The research objective is a controlled comparison of allocation with and without HMM information.”

## Slide 4 — Current Progress at the Third Evaluation

### Slide content
- Portfolio, holdings, transactions, Research, and Settings form the main workflow.
- Latest available quotes support market-value portfolio weights.
- INR and USD portfolios receive separate valuations and analyses.
- HMM-conditioned allocation and its matched baseline are implemented.
- Saved research outputs include metrics, equity curves, and model diagnostics.
- Automated verification is recorded. Complete browser acceptance testing remains pending.

### Speaking notes
“The project has progressed beyond the earlier conventional-allocation milestone to an implemented regime-conditioned comparison and a recorded holdout study. These are current capabilities. We should only describe them as changes since evaluation two if they match what we actually presented then.”

### Suggested visual
A screenshot of the main portfolio dashboard. Do not add an unsupported completion percentage.

## Slide 5 — System Architecture

### Slide content
| Layer | Technology | Responsibility |
|---|---|---|
| User interface | React, Vite, Tailwind CSS, Recharts | Portfolio inputs and result visualization |
| Analytics API | Python, FastAPI | Input validation and analysis orchestration |
| Persistence | Supabase / PostgreSQL | Authentication and portfolio persistence |
| Data input | Market quotes and historical prices | Valuation and historical return series |
| Analysis | Risk calculations, Gaussian HMM, optimization | Risk estimates and allocation comparisons |

### Speaking notes
“The frontend sends the portfolio to FastAPI. The backend validates inputs and obtains the required prices, then calculates risk and allocation outputs. Supabase supports authentication and persistence. The Research page reads saved experimental outputs rather than retraining a model on every page load.”

## Slide 6 — Portfolio Analysis Workflow

### Slide content
1. The user records purchases and sales.
2. The application derives holdings and retrieves available quotes.
3. Quantity multiplied by price determines market value and portfolio weights.
4. Historical returns support risk and allocation calculations.
5. The interface displays results, explanations, and reliability warnings.

### Speaking notes
“Purchase cost supports the transaction record. Current portfolio weights use the latest available market values. Missing or currency-mismatched prices block the affected analysis instead of silently replacing market values with purchase costs. INR and USD holdings remain separate.”

### Suggested visual
Holdings screenshot showing quantity, market value, and quote timing.

## Slide 7 — Risk Analysis and Conventional Allocation

### Slide content
- Historical volatility measures variation in portfolio returns.
- Risk contributions identify holdings that drive portfolio risk.
- Concentration shows how investment is distributed across holdings.
- Benchmark comparisons place performance in context.
- Minimum-variance allocation uses historical covariance to select weights.
- Stress scenarios show losses under specified hypothetical shocks.

### Speaking notes
“The optimizer minimizes estimated variance. It does not maximize profit or guarantee lower future risk. Stress scenarios illustrate defined shocks, so a named scenario must not be described as an exact historical replay.”

## Slide 8 — HMM-Based Allocation Method

### Slide content
- Input: equal-weight average daily return of the selected stocks.
- Model: three-state Gaussian Hidden Markov Model.
- Training: up to 504 earlier daily return observations per decision.
- States: lower, middle, and higher fitted mean returns.
- State probabilities blend state-conditioned covariance estimates.
- The optimizer selects weights from the resulting covariance estimate.

### Speaking notes
“We use the established Gaussian HMM implementation from hmmlearn. The model learns statistical states without manually supplied labels. We rank states by fitted mean return. These labels do not guarantee future bull or bear markets. Each state covariance receives a 50% blend with unconditional covariance to reduce instability.”

### Optional technical explanation
The optimization objective is to minimize wᵀΣw. In the recorded study, weights are nonnegative, sum to one, and cannot exceed 40% per stock. The HMM version changes Σ, while the matched baseline uses unconditional covariance.

## Slide 9 — Research Question and Fair Comparison

### Slide content
**Does HMM conditioning improve out-of-sample risk-adjusted performance over a matched minimum-variance allocation?**

- Compare buy-and-hold, rebalanced equal weight, minimum variance, and HMM minimum variance.
- Use the same stock universe and observation dates.
- Apply identical constraints to both optimizers.
- Apply the same execution delay and transaction-cost rule.
- Primary outcome: 2025 Sharpe difference between the two optimizers.

### Speaking notes
“The matched baseline isolates the effect of adding HMM information. Equal weight and buy-and-hold provide simpler comparisons. We use Sharpe to assess return relative to risk under a stated risk-free-rate assumption.”

## Slide 10 — Dataset and Experimental Setup

### Slide content
| Setting | Recorded study |
|---|---|
| Stocks | Reliance, TCS, Infosys, HDFC Bank, ICICI Bank |
| Currency and source | INR, Yahoo Finance auto-adjusted closes |
| Dataset | 2018–2025, 1,976 common-session price rows |
| Exploratory evaluation | 2020–2024 |
| Primary holdout | 2025, 249 daily returns |
| Rebalancing | Every 21 common sessions |
| Optimizer constraints | No short selling, maximum 40% per stock |
| Cost assumption | 10 basis points × absolute traded-weight changes |

### Speaking notes
“A decision uses information through close t, executes at close t+1, and first earns the return from t+1 to t+2. Holdings drift between trades. Sharpe uses a 2% annual risk-free rate and 252 sessions for annualization. The five stocks are a convenience sample, which limits generalization.”

## Slide 11 — Recorded 2025 Holdout Results

### Slide content
| Strategy | Annualized return | Annualized volatility | Sharpe | Maximum drawdown |
|---|---:|---:|---:|---:|
| Buy and hold | 1.55% | 13.66% | 0.036 | -12.83% |
| Equal weight | 3.19% | 13.52% | 0.153 | -11.70% |
| Minimum variance | 2.91% | 12.59% | 0.133 | -9.64% |
| HMM minimum variance | 3.14% | 12.62% | 0.151 | -9.68% |

- HMM-minus-baseline Sharpe difference: **+0.0179**.
- Paired bootstrap 95% interval: **-0.0090 to +0.0442**.
- The interval includes zero. The result does not establish an HMM advantage.

### Speaking notes
“The HMM has a slightly higher Sharpe than its matched baseline in 2025. Equal weight has a slightly higher Sharpe than the HMM. The uncertainty interval includes zero, so we cannot claim reliable superiority. Volatility and drawdown are very similar for the two optimizers.”

### Evidence
Numbers come from `analytics-engine/research/regime_holdout_2026-09-27_v2/holdout_metrics.csv`. The interval is reported in `analytics-engine/research/PAPER_DRAFT.md`. These are saved experiment results, not current dashboard forecasts.

## Slide 12 — Interpretation and Model Diagnostics

### Slide content
- HMM allocation traded more than conventional minimum variance.
- Full-period 2020–2025 Sharpe: HMM **0.6114**, baseline **0.6278**.
- **45 of 70** primary HMM fits reached the iteration limit without meeting tolerance.
- Results vary with evaluation period and model settings.
- The evidence supports further investigation, with no general superiority claim.

### Speaking notes
“The positive one-year point estimate must be considered alongside the longer-period result and fitting problems. The application now exposes convergence and covariance-fallback warnings. Changes to model settings require a documented new experiment rather than tuning against the completed holdout.”

## Slide 13 — Verification and Current Status

### Slide content
- Recorded checkpoint: **9 October 2026**.
- Frontend: **39 tests passed**, production build succeeded.
- Backend: **26 targeted tests passed**.
- API startup and research-output retrieval succeeded.
- Quote checks returned valid INR/USD quotes and structured invalid-symbol errors.
- Complete browser acceptance testing and visual evidence remain pending.

### Speaking notes
“These are recorded checks, not tests rerun today. The checkpoint also flagged that current allocation code differs from the saved experiment’s source hash. We retain the original result as historical evidence and need a separately named reproduction before claiming that current code produces the same result.”

### Presenter preparation note
The frontend build has a large JavaScript chunk warning. Market-provider access can fail under restricted network conditions. These are limitations to explain if asked, not reasons to claim the app is fully validated.

## Slide 14 — Application Demonstration

### Slide content
1. Open a prepared five-stock INR portfolio.
2. Show holdings, market values, and quote timestamps.
3. Explain concentration and risk contributions.
4. Compare conventional and HMM-conditioned allocations.
5. Open Research and explain the saved results and warnings.

### Speaking notes
“I will demonstrate the main portfolio workflow and then connect the application outputs to our research comparison. The live analysis and the recorded research study use different settings, so their numbers need not match.”

### Demo preparation
- Rehearse login, portfolio loading, and each screen before the evaluation.
- Use a dedicated demo workspace and existing example holdings.
- Capture real screenshots and a short backup recording after rehearsal.
- If live data is unavailable, identify screenshots and saved outputs as recorded evidence.
- Keep the live demonstration to approximately two minutes.

## Slide 15 — Limitations and Remaining Work

### Slide content
| Limitation | Next step |
|---|---|
| Five-stock sample and one-year holdout | Expand future evaluation periods and universes |
| Frequent HMM convergence failures | Investigate fitting behavior using development data |
| Simplified transaction costs | Evaluate spread, taxes, and execution assumptions |
| Current code differs from saved run | Produce a separate reproducibility run |
| Browser acceptance testing incomplete | Verify complete workflows and capture evidence |
| Literature review and report formatting incomplete | Complete verified related work and final documentation |

### Speaking notes
“Our remaining work focuses on validation and reproducibility. We will investigate model changes using development data and define fresh evaluation data for any new performance claim. The two-session covariance forecast used for a 21-session holding period is also a modeling choice that requires further testing.”

## Slide 16 — Conclusion and Questions

### Slide content
- Implemented portfolio risk analysis and allocation comparison.
- Connected HMM state estimates to covariance-based optimization.
- Completed a recorded chronological study with matched baselines.
- Observed mixed results and documented uncertainty and fitting limitations.
- Next focus: reproducibility, browser validation, and final research documentation.

**Thank you. Questions?**

### Speaking notes
“The project’s contribution is the integrated application and transparent evaluation of an HMM allocation method. The study does not establish that adding regimes improves performance. We have identified the remaining validation work clearly.”

## Optional Appendix — Likely Evaluator Questions

**What is your contribution if HMM already exists?**  
We integrate validated portfolio inputs, risk calculations, HMM-conditioned covariance estimation, constrained allocation, explanations, and a reproducible comparison. We do not claim to invent HMM or a new optimizer.

**Why use HMM?**  
It models unobserved statistical states and transitions between them. We investigate whether conditioning covariance on those states changes allocation performance.

**Did you train the model yourself?**  
The system fits an established Gaussian HMM to historical data using hmmlearn. Training learns model parameters. We did not implement the underlying fitting algorithm from scratch.

**How do you prevent future-data leakage?**  
Each decision uses only earlier observations. Execution occurs the following session. The test suite includes future-price perturbation checks to ensure earlier decisions and equity do not change.

**Did your model outperform?**  
Its 2025 Sharpe exceeds the matched baseline by 0.0179, but the 95% interval includes zero. Its full-period Sharpe is lower. We cannot claim a reliable advantage.

**Why does equal weight have a higher Sharpe than HMM?**  
The optimizer targets estimated variance, not maximum Sharpe. Lower estimated risk does not guarantee better realized risk-adjusted return.

**Why did 45 HMM fits reach the iteration limit?**  
Many rolling windows did not satisfy the declared convergence tolerance within 200 iterations. This limits confidence in those fits. We report the issue and will investigate it in a new development experiment.

**Where are LSTM, Random Forest, PPO, sentiment, and chat?**  
They remain optional experimental modules. They are not combined into the current HMM allocation research method. Their artifacts do not establish predictive accuracy.

**Does the project execute real trades?**  
The evaluated workflow analyzes portfolios and compares allocations. Live broker execution remains outside the demonstrated scope.

**Why keep currencies separate?**  
INR and USD values cannot be summed meaningfully without a defined exchange-rate conversion. The current application analyzes them separately.

**Why is the research output marked stale?**  
The saved run records source hashes. The checkpoint detected that current allocation code differs. The historical result remains identifiable, but reproducing it with current code is a separate task.

**Is the application complete?**  
Core modules and targeted automated checks are in place. Full browser workflow validation, independent reproduction with current code, and final report work remain pending.

## Opening and Closing Script

**Opening:** “Good morning. Our project is Smart Portfolio Advisor and Recommendation System. It helps users understand portfolio risk and compare alternative allocations. In this third evaluation, we will present the current application, our HMM-based method, and the results of a controlled research comparison.”

**Closing:** “We have implemented the portfolio-analysis workflow and evaluated HMM-conditioned allocation against matched baselines. The results are mixed, and we report the uncertainty and convergence limitations. Our next steps are independent reproduction, complete browser testing, and final documentation.”

## Final Preparation Checklist

- Add actual team, guide, and institution details.
- Use concise slide bullets. Keep speaking notes off the slide canvas.
- Add actual dashboard, allocation, and Research screenshots.
- Keep result dates, metric labels, and the uncertainty interval visible.
- Rehearse a 12–15 minute presentation with a two-minute demo.
- Confirm whether your college requires additional slides or a specific template.
- Avoid unsupported accuracy percentages, completion percentages, guaranteed-profit claims, and invented evaluation-two progress.

## Local Sources

- `PROJECT_DIRECTION.md`: current application scope and research question.
- `analytics-engine/research/REGIME_STUDY.md`: implemented methodology and accounting conventions.
- `analytics-engine/research/PAPER_DRAFT.md`: result interpretation and uncertainty interval.
- `analytics-engine/research/regime_holdout_2026-09-27_v2/holdout_metrics.csv`: numerical results.
- `analytics-engine/research/HMM_DIAGNOSTICS.md`: fitting limitations.
- `QA_CHECKPOINT_2026-10-09.md`: dated verification evidence and outstanding checks.
- `frontend/package.json`: frontend technology stack.

This file supplies presentation content and rehearsal notes. It is not a generated PowerPoint deck.

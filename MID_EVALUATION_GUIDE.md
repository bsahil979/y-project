# Mid-evaluation: portfolio risk and allocation

This guide records the earlier conventional-allocation milestone. Development has since added an experimental HMM-conditioned allocation and a chronological research comparison. For current scope and status, use [PROJECT_DIRECTION.md](./PROJECT_DIRECTION.md) and [REGIME_STUDY.md](./analytics-engine/research/REGIME_STUDY.md); the regime-aware rows and remaining-work descriptions below reflect the earlier milestone.

## Project statement

**Explainable Portfolio Risk Analysis and Optimization Using Machine Learning**

A user records stock holdings, reviews historical risk and concentration, sees an HMM market-regime estimate, and compares their allocation with a conventional minimum-volatility allocation. Explanations identify the calculation or model behind each output.

## What is verified

- Backend imports successfully in `analytics-engine/venv`.
- Seven targeted backend tests pass, covering API integration, weight alignment, invalid requests, market-data outages, risk metrics, allocation constraints, and reproducible regime detection.
- Seven existing frontend portfolio-ledger tests pass.
- Frontend production build succeeds (large-bundle warning remains).
- A real-provider five-stock request to `/portfolio/analyze` returns HTTP 200. The request and full response are saved in `analytics-engine/docs/midterm_analysis.json`.
- Visual browser testing is still pending: no browser was available to the automation session.

## Start the application

Use two PowerShell terminals from the project directory. Existing dependencies are already installed here.

Terminal 1:

```powershell
cd analytics-engine
.\venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
cd frontend
npm.cmd run dev -- --host 127.0.0.1
```

Open the URL printed by Vite, normally `http://127.0.0.1:5173`. Backend API documentation is at `http://127.0.0.1:8000/docs`.

## Five-minute demonstration

Use a separate demo workspace. Do not overwrite personal holdings. If an account already contains transactions, holdings are derived from those transactions; use the transaction workflow or a fresh demo account.

1. Introduce the problem: retail users need to understand portfolio concentration and risk.
2. Record the following **illustrative purchase entries** in INR. These purchase prices are example inputs, not claims about historical executions or current quotes.

| Stock | Quantity | Example average cost (INR) | Recorded cost weight |
|---|---:|---:|---:|
| RELIANCE.NS | 20 | 2,000 | 40% |
| TCS.NS | 5 | 4,000 | 20% |
| INFY.NS | 10 | 1,500 | 15% |
| HDFCBANK.NS | 10 | 1,500 | 15% |
| ICICIBANK.NS | 10 | 1,000 | 10% |

3. Open the dashboard. Explain that analytics currently uses recorded purchase-cost weights; current quotes are displayed separately. Indian-only portfolios select NIFTY 50 (`^NSEI`) as the benchmark.
4. Show portfolio volatility, per-stock risk contributions, and the HMM regime. A regime is a fitted statistical state, not a guaranteed prediction.
5. Open **Improvements**. Compare current and suggested weights, then read the explanation. The optimizer minimizes historical covariance-based volatility with long-only weights summing to one.
6. Explain the stress scenario. These are predefined hypothetical shocks, not a replay of each Indian stock during the named crisis. The verified example has a -40% shock, or INR 40,000 loss on INR 100,000.
7. Explain the research extension and remaining validation.

The recorded API check uses 2023-01-01 through an exclusive end date of 2026-09-01. It produced 14.81% current annualized volatility and 13.77% suggested volatility. The dashboard uses a current end date, so its figures can differ. These estimates use the same sample for optimization and measurement; they are **not out-of-sample performance results**.

## Re-run the recorded API check

From `analytics-engine`:

```powershell
.\venv\Scripts\python.exe scripts\verify_midterm.py
.\venv\Scripts\python.exe -m unittest tests.test_midterm_pipeline -v
```

The verification script downloads actual history and overwrites the dated evidence JSON only after success. If providers fail, the API returns an unavailable-data error instead of invented prices. The saved JSON is a backup analysis artifact, not a live or offline application mode.

## Claims to make accurately

| Component | Current status |
|---|---|
| Portfolio ledger and historical risk | Implemented; targeted tests pass |
| HMM regime detection | Implemented with fixed random seed; descriptive estimate on supplied history |
| Minimum-volatility allocation | Connected to main pipeline and Improvements tab |
| Regime-aware allocation | Planned research extension; current allocation does not consume HMM state |
| Forecasting and news sentiment | Existing optional modules; skipped by core dashboard analysis |
| PPO | Experimental; disabled in main analysis decisions |
| Research superiority over baselines | Not established |
| Visual end-to-end demo | Needs manual rehearsal |

## Suggested presentation order

1. Problem and user.
2. Objectives and frozen scope.
3. Architecture: React -> FastAPI -> real historical data -> risk/HMM/optimizer -> explanations.
4. Five-stock demonstration.
5. Verification evidence and preliminary in-sample allocation comparison.
6. Proposed research experiment.
7. Limitations and remaining three-week schedule.

## Paper plan

Research question: does incorporating market-regime information into allocation improve out-of-sample risk-adjusted performance over allocation without that information?

Use a fixed, disclosed Indian-stock universe and INR throughout the initial study. A universe chosen from today's constituents introduces selection/survivorship limitations; disclose them. The current five stocks are a convenience demo universe, not a representative investment study.

Before running experiments, specify a regime-conditioned allocation rule and a matched version without regime information. Use the same investment constraints, rebalancing dates, data, and costs in both. Compare with buy-and-hold, periodically rebalanced equal-weight, and conventional minimum-volatility allocation.

Use chronological training/test windows. Fit HMM parameters and state labels on training data only. At each test decision use only information available then; do not fit or smooth states over future test observations. Trade no earlier than the next permitted execution time. Use identical fees, turnover definitions, and execution assumptions for every strategy. Freeze choices before the final held-out evaluation.

Report return, volatility, Sharpe ratio, maximum drawdown, turnover, dates, transaction-cost assumptions, and results by test window. Repeat stochastic methods with disclosed seeds. Include a regime-ablation comparison and discuss weak or negative results honestly. Saved model files and in-sample fit do not establish predictive accuracy.

Paper sections: abstract (finish last), introduction, verified related work, methodology, experimental setup, results, limitations, conclusion, references. Literature review and citations still need research; no novelty or publication-acceptance claim is established.

## Remaining schedule

- Before mid-evaluation: rehearse the actual browser flow, capture a backup recording, prepare slides, and confirm the guide's required paper format.
- Week 2: implement the regime-conditioned allocation and matched baseline; audit time ordering and data provenance.
- Week 3: run frozen comparisons; produce tables and figures; draft methods and results.
- Week 4: revise the paper and report, resolve demo issues, rehearse the viva.

Avoid new broker integration, additional model families, and new dashboard modules until these deliverables are complete.

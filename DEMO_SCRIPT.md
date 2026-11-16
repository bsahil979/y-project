# SmartPortfolio: six-minute demonstration

## Before presenting

Run `run_all.bat` and open http://localhost:5173. Keep both services running. Use the existing demo workspace with five INR stocks and AAPL; do not sign out immediately before presenting. Live quotes require internet. The saved Research page works without a market-data download while the local backend is running.

## 0:00–0:40 — Explain the problem

“SmartPortfolio helps a person understand their stock holdings, where their risk is concentrated, and how alternative allocations compare. It is a portfolio-analysis and research prototype. It does not place real trades.”

## 0:40–1:40 — Show holdings

Open My Holdings. Point out quantity, purchase cost, market value, profit/loss, and price source/date. Explain that current value is quantity multiplied by the available quote, whereas purchase cost is historical. Prices may be delayed. Show INR and USD as separate totals; the app does not invent an exchange rate to combine them.

## 1:40–2:30 — Show the transaction ledger

Open Transactions. Show the recorded two-share RELIANCE.NS buy and explain how opening inventory of 10 becomes 12. To demonstrate validation, try a sell of 999 shares in INR: it should show the available inventory and reject the entry. This is a sample portfolio ledger, not a broker order.

## 2:30–3:30 — Explain analysis

Open Portfolio. Show current-value weights, historical volatility and benchmark comparison. In Risk & Budget, explain that concentration is about contributions to portfolio risk, not just the number of stocks. In Improvements, compare current weights, the no-regime optimizer and the HMM optimizer.

“The HMM learns three statistical return states from earlier data. It estimates state probabilities, which blend state-conditioned risk estimates. A minimum-variance optimizer then proposes weights under the same constraints as its no-state baseline. State names describe fitted historical returns; they do not guarantee tomorrow's market direction.”

## 3:30–5:15 — Show the experiment

Open Research. Explain that this is a separate fixed five-stock study, not the visitor's live portfolio. It uses rolling historical training, delayed execution and trading costs, with a 2025 evaluation period.

- Matched minimum-variance Sharpe: 0.1331.
- HMM minimum-variance Sharpe: 0.1510.
- Difference: +0.0179; paired bootstrap interval approximately [-0.0090, 0.0442].
- The interval includes zero. The result does not establish that the HMM method is better.
- The full-period Sharpe favored the no-state baseline; HMM turnover was higher.
- 45 of 70 primary HMM fits hit their iteration cap without meeting tolerance. Keep this limitation visible.

“On October 12 we reran the current code on the archived prices. Metrics, equity, daily ledger, sensitivities and bootstrap results matched the original. This checks reproducibility; it is not another independent holdout.”

## 5:15–6:00 — Reliability and conclusion

Explain the verified behavior: oversells are rejected, holdings survive reload, invalid symbols keep the affected total unavailable, valid quotes remain visible, and a disconnected backend shows an error and recovers on refresh.

“The contribution is the integrated system and reproducible comparison using established methods. The next research step is multiple chronological evaluation windows and broader data. Real cloud authentication and all optional tools are outside this demo's acceptance checks.”

## If the network fails

Keep the backend running and demonstrate the saved Research page. Use `analytics-engine/research/regime_reproduction_2026-10-12/holdout_metrics.csv` and `reproduction_check.json` as offline evidence. `scripts/qa-portfolio-response.json` is a saved sample API response, not a current quote feed.

## Common evaluator questions

**Did you invent HMM?** No. The project uses Gaussian HMMs from hmmlearn; the work is the data pipeline, portfolio integration, controlled comparison and evaluation.

**Why compare against minimum variance?** It keeps history and portfolio constraints matched so the comparison isolates the addition of state-conditioned covariance.

**Is it profitable?** The study reports historical outcomes with costs. It does not establish future profitability or superiority.

**What is still limited?** One convenience universe and primary year, possible selection bias, approximate costs, frequent iteration-cap hits and untested real cloud authentication.

## Backup recording

A new video recording has not been created by the browser runtime. Record this walkthrough manually if you need a video backup; the saved study artifacts above are available offline.

# Advisor validation

The archive and the production preview cover different questions. The preview checks that the app can return and display a result. A forward evaluation measures whether a prediction or allocation improves on a baseline.

## MarketMind

On the archived Phase 2E chronological split, a majority-class rule chosen from training labels returned BUY. Excluding the last five rows per ticker at the training boundary prevented use of targets whose forward window extends into the holdout. On 42,568 saved predictions from 3 December 2024 through 24 August 2026, accuracy was 38.07% for A, 38.47% for B, and 39.27% for the training-only baseline. The archived predictions do not verify the current serving feature path.

Reproduce the breakdown by market from `analytics-engine` with `python -m evaluations.marketmind_holdout`. The command checks the saved input hashes before scoring.

For a new evaluation, freeze the serving model, feature schema, label thresholds and model weights before collecting predictions. Record decisions and actual market session dates. Score only after the five-session labels mature, preserve the training-only majority baseline, and report balanced accuracy and macro F1 alongside accuracy.

## Forecasts and allocation

Use the forecast recorder described in the root README. Separate TimesFM from fallback models, compare every saved curve to the unchanged closing price, and report sample dates and sizes. Keep the original records when prices arrive.

Run the two-basket exploratory allocation check from `analytics-engine` with `python -m research.advisor_portfolio_replay --output evaluations/advisor_portfolio_replay_2025.json`. Use a new output filename for repeat runs. The backtest uses six US stocks and six Indian stocks in separate baskets, weights that drift between scheduled rebalances, a two-session decision-to-return lag, and 10 basis points per unit of traded weight. Compare net annualized return, Sharpe, drawdown and turnover against equal weight and capped minimum variance. The 2025 window has already been examined and historical FinBERT is unavailable.

In this replay, aggressive AI Black–Litterman had higher net Sharpe than both baselines in both baskets. Its average rebalance turnover was 39.42% in the US basket and 46.30% in India. Its US drawdown was deeper than either baseline. Conservative had a shallower drawdown than both US baselines, but a deeper drawdown than equal weight in India. These two exploratory baskets do not establish a general advantage. See [the full replay results](advisor_portfolio_replay_2025.json).

## Chat evaluation

Run the questions below on a dedicated demo portfolio with known values. For each response, independently record **numerical agreement**, **correct interpretation**, and **handling of missing information**. Mark a criterion as not applicable when the prompt does not exercise it. A verification badge only covers recognized numerical claims.

| Prompt | What to check |
| --- | --- |
| What percentage is invested in MSFT? | Use the current USD portfolio weight from the same snapshot. |
| Why did the proposed weight change? | Distinguish current and target weights and explain the selected objective and cap. |
| What is my maximum drawdown? | Use the reported value and explain that it measures a historical peak-to-trough decline. |
| What do unavailable FinBERT views tell us? | Acknowledge missing sentiment without interpreting it as neutral. |
| Will the portfolio beat its benchmark next year? | Explain the limits of historical comparisons without giving an unsupported probability. |

The local production preview tested the first question using one demo MSFT holding. The assistant reported 100%, which matched Advisor. This is one live result. The numerical grounding tests separately exercise recognition, discrepancy correction, and absent facts.

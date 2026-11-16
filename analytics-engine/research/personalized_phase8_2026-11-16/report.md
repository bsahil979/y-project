# Personalized allocation 2025 walk forward replay

Retrospective causal replay on five Indian stocks and an already inspected 2025 window. Fixed ten-year horizon. Aggressive AI Black-Litterman is the production personalized path; aggressive target return is a no-AI control. Not a confirmatory untouched test or a validation of every horizon or live model.

Conservative 20% caps force equal weight with five stocks. Historical FinBERT is unavailable. The newly retrained five-stock MarketMind RF is not the saved 99-stock classifier. ADX uses a frozen trailing-feature snapshot; retrospectively adjusted inputs are not vintage-certified. No parameter tuning on results.

MarketMind A architecture: 250-tree balanced Random Forest, seed 42, 14 features, causal HMM, five-session matured labels; refit each rebalance

Historical sentiment: unavailable_in_historical_replay

Mean total absolute traded weight per scheduled holdout rebalance; costs 10bps per total absolute traded weight. Drift between rebalances; no final liquidation.

| Strategy | Net annual return | Volatility | Net Sharpe | Max drawdown | Mean rebalance turnover |
|---|---:|---:|---:|---:|---:|
| Aggressive AI Black-Litterman | 1.246496% | 13.749619% | 0.014393 | -12.965962% | 49.022500% |
| Aggressive target return | -0.011655% | 12.753829% | -0.092835 | -10.514948% | 27.686675% |
| Conservative | 3.194199% | 13.522868% | 0.153192 | -11.695227% | 3.240658% |
| Equal weight | 3.194199% | 13.522868% | 0.153192 | -11.695227% | 3.240658% |
| Minimum variance | 2.910428% | 12.591404% | 0.133111 | -9.637089% | 4.988745% |
| Moderate | 0.090416% | 13.507414% | -0.072777 | -13.601107% | 27.245334% |

## Paired 95 percent Sharpe difference intervals

21-session moving blocks, 10000 replicates, seed 20260927.

| Strategy | Baseline | Difference | Lower | Upper |
|---|---|---:|---:|---:|
| Conservative | Minimum variance | 0.020081 | -0.610850 | 0.467959 |
| Conservative | Equal weight | -0.000000 | -0.000000 | 0.000000 |
| Moderate | Minimum variance | -0.205888 | -0.840116 | 0.391899 |
| Moderate | Equal weight | -0.225969 | -0.634110 | 0.284370 |
| Aggressive target return | Minimum variance | -0.225946 | -0.523001 | 0.029931 |
| Aggressive target return | Equal weight | -0.246027 | -0.794562 | 0.486285 |
| Aggressive AI Black-Litterman | Minimum variance | -0.118718 | -0.878259 | 0.453330 |
| Aggressive AI Black-Litterman | Equal weight | -0.138799 | -0.404541 | 0.081764 |

## What the risk comparison establishes

Conservative equals equal weight. Against AI Black-Litterman it has lower observed volatility and a shallower drawdown, but both paired intervals include zero. Against the historical target-return control it has higher volatility; the volatility-difference interval is entirely positive. Profile constraints do not guarantee monotonic realized risk ordering. All Sharpe-difference intervals against the baselines include zero.

Full precision, risk-comparison intervals, label-maturity audits, target weights and view provenance are in summary.json, predictions.json and decisions.json. The manifest validates inputs, sources and generated artifacts.

# Model evaluation audit — 4 November 2026

This is a development audit, not a page in the investor app. Artifact presence and successful inference establish that code runs; they do not establish predictive value.

| Component | Current evidence | Assessment |
| --- | --- | --- |
| TimesFM 2.5 | The cached checkpoint loads and the restarted advisor returned a live 30-session TimesFM result. A new chronological historical replay compared 24 origins across MSFT and RELIANCE.NS with a last-close baseline. Mean 30-step error was 5.280% of spot for TimesFM versus 5.146% for baseline. | Inference works. This small replay does not show an overall error advantage. TimesFM's pretraining cutoff is unverified, so this is not an untouched model holdout. |
| Per-ticker LSTM/RF/HMM/PPO | 100 ticker directories contain all expected artifacts. The old RF training routine fitted its scaler and forest on the entire series, then scored the last 20% of that same series. All 100 stored RF accuracies are 1.0. | Artifact coverage is good. Stored per-ticker RF scores are invalid as holdout evidence. HMM convergence is a fit diagnostic, not a forecast score. PPO artifacts do not establish an investor benefit. |
| Pooled BUY/HOLD/SELL models A/B | Saved Phase 2E holdout: 42,568 predictions across 99 tickers, beginning 2024-12-03. A accuracy 38.07%, macro F1 0.307; B accuracy 38.47%, macro F1 0.291. The largest actual class is 39.27%. | Neither model beats the simple majority-class accuracy baseline on this holdout. These signals should not be described as proven predictions. |
| Validated direct-return forecast | The one saved MSFT report selected the last-close baseline. LSTM validation MAE 4.590 versus baseline 4.578; test MAE 5.728 versus baseline 5.573 percentage points of cumulative log return. | This LSTM did not beat the baseline on MSFT. It does not validate TimesFM. |
| HMM allocation | The saved 2025 HMM-minus-matched-baseline Sharpe difference is +0.0179 with 95% interval [−0.0090, +0.0442]. 45 of 70 fits reached the iteration cap without declared convergence. | No reliable advantage established. Keep this work in development materials, outside the investor app. |

## Changes from this audit

- The user-facing Research and Model Training routes and navigation were removed. A short “How estimates work” page replaces the internal architecture and research lab page.
- The stock advisor now requires real, sufficiently recent market history, aligned same-currency holdings, and valid matching weights. It no longer creates random prices when the provider fails.
- When a forecast model fails, the advisor uses a named flat last-close baseline instead of an unlabelled directional momentum curve.
- Allocation comparisons reweight an already owned ticker correctly and use the same dated returns for before and after. The verdict is now a historical scenario summary rather than an instruction to buy.
- Future per-ticker RF evaluation refits a separate scaler and forest on the earlier 80% with a five-bar label embargo, scores only the final 20%, and reports the majority-class baseline. Existing metadata has **not** been relabelled as valid.
- `analytics-engine/evaluations/evaluate_timesfm_replay.py` saves the input hashes, per-origin errors, and baseline comparison without retraining. The saved run is `analytics-engine/evaluations/timesfm_replay_2026-11-04.json`.

## TimesFM replay detail

The replay uses the last twelve eligible historical origins per symbol, spaced 21 sessions apart, with a 30-session horizon. Error is the mean absolute error across the 30 forecast steps divided by the origin close. MSFT: TimesFM 6.794%, baseline 6.450%, TimesFM better at 5/12 origins. RELIANCE.NS: TimesFM 3.767%, baseline 3.841%, TimesFM better at 8/12 origins. The combined 24-origin comparison favors the baseline on mean error. Overlapping windows and only two selected symbols limit interpretation; the per-symbol results disagree.

Reproduce from `analytics-engine` with `venv\Scripts\python.exe -m evaluations.evaluate_timesfm_replay --max-origins 12 --stride 21`.

## Next evaluation gate

Before claiming forecasting quality, extend the fixed replay to more symbols, horizons, and market periods. Confirm the pretrained model's data cutoff or use genuinely future observations for a model holdout. Save per-symbol and aggregate MAE, directional accuracy, and calibration where meaningful. Do not tune on the final test block. For classifier signals, compare with majority-class and simple momentum baselines, and evaluate an explicit cost-aware decision rule before enabling trading language.

Sources: `analytics-engine/models/phase_2e/phase_2e_classification_report.json`, `analytics-engine/models/phase_2e/phase_2e_prediction_manifest.json`, `analytics-engine/models/forecast_v2/MSFT/report.json`, `analytics-engine/research/PROTOCOL_V1.md`, `analytics-engine/training/train_all.py`.

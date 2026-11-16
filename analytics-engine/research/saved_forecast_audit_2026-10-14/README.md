# Existing MSFT forecast checkpoint audit

Both original checkpoints load successfully with their original saved scalers. No checkpoint or scaler was modified or refitted. The full-data snapshot ends on 13 October 2026. Results are diagnostics, not certified untouched out-of-sample evidence: actual training cutoffs cannot be verified from file modification timestamps alone.

## Current inference

Latest close: **$543.45**.

| Checkpoint | First forecast | Session 30 | Interpretation |
|---|---:|---:|---|
| MSFT price-level LSTM | $477.20 | $470.97 | First-step drop of 12.19%; reproduces the problematic graph |
| Universal return LSTM | $543.27 | $535.43 | Avoids the large level discontinuity, but that alone does not establish predictive quality |

The MSFT scaler has a saved price range of approximately $350.45–$537.65. The latest price is above that range. This indicates extrapolation, but does not by itself prove the cause of the error. Its weights were modified on 30 August, whereas the scaler and metadata were modified on 24 August. Their pairing is not proven incorrect, but the provenance is incomplete. The recorded older validation metrics cannot safely be assigned to the current weights.

The universal model uses simple percentage returns with `scaler_returns.pkl`, then compounds predicted returns from the observed close. It must not use the MSFT price scaler.

## Diagnostic replay

Forecast origins are after 31 August 2026, later than both checkpoint modification dates. Each origin supplies only preceding prices to inference. Saved weights and scalers stay frozen. MAE below is terminal-price absolute error in USD, separately for each horizon.

| Horizon | Origins | MSFT LSTM MAE | Universal LSTM MAE | Last-close baseline MAE |
|---|---:|---:|---:|---:|
| 1 session | 29 | $34.61 | $5.81 | $5.77 |
| 5 sessions | 25 | $37.62 | $10.27 | $9.64 |
| 20 sessions | 10 | $55.95 | $33.84 | $28.59 |
| 30 sessions | 0 | Not available | Not available | Not available |

The universal checkpoint is substantially better than the current MSFT checkpoint in this replay, but both have higher MAE than the baseline at every available horizon. There are too few recent observations for a completed 30-session evaluation. Longer horizons overlap, and the sample is small.

## Decision

Do not promote either checkpoint as a validated 30-session directional forecast from this evidence. The current baseline selection remains unchanged. An explicit experimental model comparison could display either checkpoint, provided its limitations and baseline comparison remain visible. That is a separate interface decision.

## Evidence

- `audit.json`: checkpoint/scaler hashes, scaler ranges, current inference, metrics, and limitations.
- `metrics.csv`: terminal-price error results by horizon.
- `latest_predictions.json`: unmodified 30-step model outputs.
- `prices.csv`: exact input snapshot used for this audit.
- `../audit_saved_forecasts.py`: reproducible evaluator.

The existing output directory is protected from overwrite by the evaluator. Use a new output directory when repeating it.

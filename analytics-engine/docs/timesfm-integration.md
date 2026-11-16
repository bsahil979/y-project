# TimesFM project integration

Updated 23 October 2026. This feature belongs to the application; the frozen HMM paper experiment is unchanged.

## Runtime

`services/forecaster.py` loads the pretrained `google/timesfm-2.5-200m-pytorch` checkpoint. The installed `timesfm==3.0.0` package exposes the TimesFM 2.5 implementation. Constructing its model class alone does not load weights.

Weights are stored under `analytics-engine/models/timesfm_cache` (approximately 925 MB). Subsequent loads use the local checkpoint without a network request. First setup needs Hugging Face access. Loading and inference are serialized because the cached model is shared across requests.

Inputs are up to 512 historical log returns. Predicted log returns are compounded from the latest observed price. Horizons of 1–60 sessions are supported. Outputs use session numbers rather than invented exchange-session dates.

The main `/forecast/{ticker}` endpoint, advisor forecast tools, and advisor context now request the actual model metadata. Owned-portfolio forecast questions explicitly fetch a forecast instead of relying on descriptive RAG text. The context includes the first sessions and the requested endpoint. Tool summaries preserve endpoints when bulk arrays are compacted.

Responses include `model`, `requested_model`, `fallback_reason`, `horizon`, and `horizon_unit`. If TimesFM loading or inference fails, the existing LSTM or insufficient-history last-close baseline is identified explicitly. Invalid model output is rejected. The main chart endpoint retains its first-step discontinuity check and withholds a curve whose initial estimate differs from spot by more than 10%.

These outputs remain experimental. Successful inference does not demonstrate predictive accuracy. The HMM study's evaluation is not validation of TimesFM.

## Verification performed

- Downloaded the pretrained checkpoint and confirmed it loads successfully.
- Ran genuine TimesFM inference on the archived `RELIANCE.NS` series in `research/regime_holdout_2026-09-27_v2/prices.csv`, for 60 sessions.
- Returned model: `TimesFM 2.5`; fallback reason: none; 60 forecast rows.
- Archived last close: approximately INR 1563.1726; session 1 estimate: INR 1565.2153; session 60 estimate: INR 1549.1273. These are a historical integration check, not a current market outlook or paper result.
- Targeted regression coverage includes log-return compounding, complete horizon, invalid output fallback, actual model attribution, short history, owned-portfolio forecast context, forecast errors, and chart withholding.
- All 20 targeted tests passed, and the frontend production build passed.
- Restarted the local backend and requested `/forecast/RELIANCE.NS?horizon=60&refresh=1`: HTTP 200, model `TimesFM 2.5`, no fallback, 60 forecast rows, output version 6, experimental status.

Run targeted checks from `analytics-engine`:

```powershell
.\venv\Scripts\python.exe -m unittest tests.test_timesfm_integration tests.test_forecast_display tests.test_advisor_context tests.test_llm_budget -q
```

Run `npm.cmd run build` from `frontend` to verify the UI build. Restart any non-reloading backend after changing Python code and reload the frontend before opening a new forecast request.

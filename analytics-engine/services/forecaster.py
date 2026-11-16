import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import datetime
import torch
import torch.nn as nn
import logging
import os
import threading
import re
import warnings
from services import validated_forecast
from services.data_fetcher import get_portfolio_data

logger = logging.getLogger(__name__)

_timesfm_model = None
_timesfm_error = None
_timesfm_lock = threading.RLock()
TIMESFM_CHECKPOINT = "google/timesfm-2.5-200m-pytorch"
TIMESFM_CACHE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "timesfm_cache")


def _get_timesfm():
    with _timesfm_lock:
        return _load_timesfm()


def _load_timesfm():
    global _timesfm_model, _timesfm_error
    if _timesfm_model is None:
        try:
            from timesfm import TimesFM_2p5_200M_torch, configs
            from huggingface_hub import hf_hub_download
            from huggingface_hub.errors import LocalEntryNotFoundError

            try:
                checkpoint = hf_hub_download(TIMESFM_CHECKPOINT, 'model.safetensors',
                                             cache_dir=TIMESFM_CACHE, local_files_only=True)
            except LocalEntryNotFoundError:
                model = TimesFM_2p5_200M_torch.from_pretrained(
                    TIMESFM_CHECKPOINT, cache_dir=TIMESFM_CACHE, torch_compile=False,
                )
            else:
                model = TimesFM_2p5_200M_torch(torch_compile=False)
                model.load_checkpoint(checkpoint)
            fc = configs.ForecastConfig(
                max_context=512,
                max_horizon=128,
                normalize_inputs=True,
            )
            model.compile(forecast_config=fc)
            _timesfm_model = model
            _timesfm_error = None
            logger.info("TimesFM 2.5 200M loaded successfully")
        except Exception as exc:
            _timesfm_error = str(exc)
            logger.warning("TimesFM not available, falling back to LSTM: %s", exc)
            _timesfm_model = False
    return _timesfm_model


class LSTMModel(nn.Module):
    def __init__(self, input_size=1, hidden_size=50, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.fc(out[:, -1, :])  # Take last timestep
        return out


def _lstm_forecast(prices: pd.Series, horizon=30, train_epochs=8):
    """
    LSTM Neural Network Forecaster (PyTorch) for time-series price prediction.
    Uses a sequence-to-one architecture with 60-day lookback windows.
    """
    if len(prices) < 100:
        return [
            {"date": (datetime.datetime.now() + datetime.timedelta(days=i)).strftime('%Y-%m-%d'),
             "predicted_price": float(prices.iloc[-1])}
            for i in range(1, horizon + 1)
        ]

    # --- 1. Data Preparation ---
    data = prices.values.reshape(-1, 1).astype(np.float32)
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(data)

    lookback = 60

    X_train, y_train = [], []
    for i in range(lookback, len(scaled_data)):
        X_train.append(scaled_data[i - lookback:i, 0])
        y_train.append(scaled_data[i, 0])

    X_train = torch.tensor(np.array(X_train), dtype=torch.float32).unsqueeze(-1)  # [N, 60, 1]
    y_train = torch.tensor(np.array(y_train), dtype=torch.float32).unsqueeze(-1)  # [N, 1]

    # --- 2. Build & Train LSTM ---
    model = LSTMModel()
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    model.train()
    for epoch in range(max(1, int(train_epochs))):
        optimizer.zero_grad()
        output = model(X_train)
        loss = criterion(output, y_train)
        loss.backward()
        optimizer.step()

    # --- 3. Predict Future ---
    model.eval()
    last_window = torch.tensor(scaled_data[-lookback:], dtype=torch.float32).unsqueeze(0)  # [1, 60, 1]
    predictions = []

    with torch.no_grad():
        for _ in range(horizon):
            pred = model(last_window).item()
            predictions.append(pred)
            new_entry = torch.tensor([[[pred]]], dtype=torch.float32)
            last_window = torch.cat([last_window[:, 1:, :], new_entry], dim=1)

    # Inverse transform
    predictions = scaler.inverse_transform(np.array(predictions).reshape(-1, 1)).flatten()

    dates = [
        (datetime.datetime.now() + datetime.timedelta(days=i)).strftime('%Y-%m-%d')
        for i in range(1, horizon + 1)
    ]

    return [
        {"date": d, "predicted_price": float(p)}
        for d, p in zip(dates, predictions)
    ]


def get_price_forecast(ticker, horizon=30, train_epochs=8, return_metadata=True, *, prices=None):
    """
    Forecast using Google TimesFM 2.5 (200M param foundation model).
    Ticker requests try the validated checkpoint, service LSTM and last close in order.

    TimesFM works best on stationary series, so we forecast log-returns and
    convert back to price levels.
    """
    if isinstance(horizon, bool) or not isinstance(horizon, int) or not 1 <= horizon <= 60:
        raise ValueError('Forecast horizon must be between 1 and 60 sessions')
    if isinstance(ticker, pd.Series):
        prices, ticker = ticker, None
    elif not isinstance(ticker, str) or not re.fullmatch(r'[A-Za-z0-9^][A-Za-z0-9.^=&-]{0,39}', ticker):
        raise ValueError('Invalid forecast ticker')
    else:
        ticker = ticker.upper()
        if prices is None:
            end = datetime.date.today()
            data = get_portfolio_data([ticker], str(end - datetime.timedelta(days=1095)), str(end))
            frame = data['prices']
            prices = frame if isinstance(frame, pd.Series) else frame[ticker]
    prices = prices.dropna().astype(float)
    if prices.empty or not np.isfinite(prices.to_numpy()).all() or (prices <= 0).any():
        raise ValueError('Forecast requires finite positive prices')
    fallback_reason = None

    def result(rows, model, family, validation=None):
        if len(rows) != horizon or any(not np.isfinite(float(p['predicted_price'])) or float(p['predicted_price']) <= 0 for p in rows):
            raise ValueError('Model returned invalid forecast prices or horizon')
        rows = [{'step': i + 1, 'predicted_price': float(p['predicted_price'])} for i, p in enumerate(rows)]
        return {'forecast': rows, 'model': model, 'fallback_reason': fallback_reason,
                'model_family': family, 'is_pretrained_foundation_model': family == 'TimesFM-2.5',
                'fallback_triggered': fallback_reason is not None, 'validation': validation,
                'validation_status': 'out_of_sample_verified' if validation else 'unverified_fallback',
                'summary': {'first': rows[0], 'endpoint': rows[-1], 'spot_price': float(prices.iloc[-1])},
                'requested_model': 'TimesFM 2.5', 'horizon': horizon,
                'horizon_unit': 'sessions', 'status': 'experimental'} if return_metadata else rows

    if len(prices) < 30:
        fallback_reason = 'Insufficient history for TimesFM (need at least 30 prices)'
        return result([
            {"date": (datetime.datetime.now() + datetime.timedelta(days=i)).strftime('%Y-%m-%d'),
             "predicted_price": float(prices.iloc[-1])}
            for i in range(1, horizon + 1)
        ], "Last-close baseline (insufficient history)", "Last-Close-Baseline")

    # --- Try TimesFM on log-returns ---
    tfm = _get_timesfm()
    if tfm:
        try:
            log_returns = np.log(prices.values.astype(np.float64)[1:] / prices.values.astype(np.float64)[:-1])[-512:]
            log_returns = np.nan_to_num(log_returns, nan=0.0, posinf=0.0, neginf=0.0)

            with _timesfm_lock:
                point_forecasts = tfm.forecast(horizon=horizon, inputs=[log_returns])

            if isinstance(point_forecasts, tuple):
                fcst = np.array(point_forecasts[0])
            else:
                fcst = np.array(point_forecasts)

            # fcst shape: (1, horizon) — take first (and only) series
            future_returns = fcst[0] if fcst.ndim > 1 else fcst

            # Convert forecasted log-returns back to price levels
            last_price = float(prices.iloc[-1])
            predictions = [last_price]
            for r in future_returns:
                predictions.append(predictions[-1] * float(np.exp(r)))

            predictions = predictions[1:]  # drop the seed price

            dates = [
                (datetime.datetime.now() + datetime.timedelta(days=i)).strftime('%Y-%m-%d')
                for i in range(1, len(predictions) + 1)
            ]

            return result([
                {"date": d, "predicted_price": float(p)}
                for d, p in zip(dates, predictions)
            ], "TimesFM 2.5", "TimesFM-2.5")
        except Exception as exc:
            fallback_reason = 'TimesFM prediction failed: ' + str(exc)
            logger.warning("TimesFM forecast failed, falling back to LSTM: %s", exc)

    if not tfm:
        fallback_reason = 'TimesFM unavailable: ' + (_timesfm_error or 'model could not be loaded')

    if ticker:
        try:
            saved = validated_forecast.predict(prices, ticker, horizon)
            if saved:
                return result(saved['forecast'], saved['model'], saved['model_family'], saved['validation'])
        except (OSError, ValueError, RuntimeError, KeyError) as exc:
            fallback_reason += f'; validated forecast unavailable: {exc}'
    if len(prices) >= 100:
        try:
            return result(_lstm_forecast(prices, horizon, train_epochs), 'LSTM', 'Service-LSTM')
        except (ValueError, RuntimeError) as exc:
            fallback_reason += f'; service LSTM failed: {exc}'
    return result([{'predicted_price': prices.iloc[-1]}] * horizon, 'Last-close baseline', 'Last-Close-Baseline')


def get_lstm_forecast(prices: pd.Series, horizon=30, train_epochs=8, return_metadata=False):
    """Deprecated compatibility wrapper for callers supplying a price series."""
    warnings.warn('Use get_price_forecast', DeprecationWarning, stacklevel=2)
    return get_price_forecast(prices, horizon, train_epochs, return_metadata)

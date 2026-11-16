"""Legacy recursive checkpoint inference used by research and trading tools.

The price forecast service selects validated direct-return artifacts through
validated_forecast.predict. These universal recursive weights have a different
architecture and evaluation history.
"""
from pathlib import Path
import joblib
import numpy as np
import torch
from trading_engine.models_layer import LSTMModel

def checkpoint_prediction(model, scaler, prices, horizon, returns=False):
    values = np.asarray(prices, dtype=np.float64)
    sequence = np.diff(values) / values[:-1] if returns else values
    if len(sequence) < 60:
        raise ValueError('At least 60 input observations are required.')
    scaled = scaler.transform(sequence.reshape(-1, 1)).astype(np.float32)
    window = torch.tensor(scaled[-60:]).reshape(1, 60, 1)
    predictions = []
    with torch.no_grad():
        for _ in range(horizon):
            prediction = model(window).item()
            predictions.append(prediction)
            window = torch.cat([window[:, 1:], torch.tensor([[[prediction]]])], dim=1)
    output = scaler.inverse_transform(np.array(predictions).reshape(-1, 1)).ravel()
    if returns:
        output = values[-1] * np.cumprod(1 + output)
    return output


_cached_universal = None

def universal_forecast(prices, horizon):
    global _cached_universal
    if _cached_universal is None:
        directory = Path(__file__).resolve().parents[1] / 'models' / '_universal'
        model = LSTMModel()
        model.load_state_dict(torch.load(directory / 'lstm.pt', map_location='cpu', weights_only=True))
        model.eval()
        scaler = joblib.load(directory / 'scaler_returns.pkl')
        _cached_universal = model, scaler
    model, scaler = _cached_universal
    output = checkpoint_prediction(model, scaler, prices.to_numpy(dtype=float), horizon, returns=True)
    return [{'predicted_price': float(value)} for value in output]

"""Audit frozen LSTM checkpoints with original preprocessing; never retrain artifacts."""
from pathlib import Path
import datetime
import hashlib
import json
import argparse
import joblib
import numpy as np
import pandas as pd
import torch
from trading_engine.models_layer import LSTMModel


from services.saved_forecast import checkpoint_prediction


def audit(prices, ticker, output):
    torch.set_num_threads(2)
    root = Path(__file__).resolve().parents[1] / 'models'
    checkpoints = [
        ('Per-ticker price LSTM', root / ticker, 'scaler_lstm.pkl', False),
        ('Universal return LSTM', root / '_universal', 'scaler_returns.pkl', True),
    ]
    output.mkdir(parents=True, exist_ok=False)
    prices.to_csv(output / 'prices.csv')
    rows, reports, curves = [], [], {}
    for name, directory, scaler_name, return_space in checkpoints:
        weights_path, scaler_path = directory / 'lstm.pt', directory / scaler_name
        model = LSTMModel()
        model.load_state_dict(torch.load(weights_path, map_location='cpu', weights_only=True))
        model.eval()
        scaler = joblib.load(scaler_path)
        modified = datetime.datetime.fromtimestamp(max(weights_path.stat().st_mtime, scaler_path.stat().st_mtime)).date()
        # Use only later origins, but report timestamp provenance limitations explicitly.
        cutoff = max(modified, datetime.date(2026, 8, 31))
        values = prices.to_numpy(dtype=float)
        eligible = [i for i in range(61, len(prices) - 1) if prices.index[i].date() > cutoff]
        for horizon in (1, 5, 20, 30):
            errors, baseline_errors = [], []
            for origin in eligible:
                if origin + horizon >= len(prices):
                    continue
                forecast = checkpoint_prediction(model, scaler, values[:origin + 1], horizon, return_space)
                errors.append(float(forecast[-1] - values[origin + horizon]))
                baseline_errors.append(float(values[origin] - values[origin + horizon]))
            if errors:
                rows.append({'model': name, 'horizon': horizon, 'origins': len(errors),
                             'mae': float(np.mean(np.abs(errors))),
                             'rmse': float(np.sqrt(np.mean(np.square(errors)))),
                             'baseline_mae': float(np.mean(np.abs(baseline_errors))),
                             'baseline_rmse': float(np.sqrt(np.mean(np.square(baseline_errors))))})
        latest = checkpoint_prediction(model, scaler, values, 30, return_space)
        curves[name] = latest.tolist()
        reports.append({'model': name, 'weights': str(weights_path), 'scaler': str(scaler_path),
                        'weights_sha256': hashlib.sha256(weights_path.read_bytes()).hexdigest(),
                        'scaler_sha256': hashlib.sha256(scaler_path.read_bytes()).hexdigest(),
                        'artifact_modified': str(modified), 'evaluation_origin_after': str(cutoff),
                        'scaler_min': scaler.data_min_.tolist(), 'scaler_max': scaler.data_max_.tolist(),
                        'latest_close': float(values[-1]), 'first_prediction': float(latest[0]),
                        'session_30_prediction': float(latest[-1]),
                        'first_step_change_pct': float((latest[0] / values[-1] - 1) * 100)})
    pd.DataFrame(rows).to_csv(output / 'metrics.csv', index=False)
    report = {'ticker': ticker, 'price_start': str(prices.index[0].date()),
              'price_end': str(prices.index[-1].date()), 'checkpoints': reports, 'metrics': rows,
              'limitations': 'Artifact timestamps are not verified training cutoffs. This is a diagnostic replay, not certified untouched out-of-sample validation. Long-horizon origins overlap and sample sizes are small. No checkpoint selection or retraining was performed.'}
    (output / 'audit.json').write_text(json.dumps(report, indent=2))
    (output / 'latest_predictions.json').write_text(json.dumps(curves, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ticker', default='MSFT')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    ticker = args.ticker.upper().strip()
    source = Path(__file__).resolve().parents[1] / 'models' / 'forecast_v2' / ticker / 'prices.csv'
    frame = pd.read_csv(source, index_col=0, parse_dates=True)
    prices = frame.iloc[:, 0]
    report = audit(prices, ticker, Path(args.output))
    print(json.dumps(report, indent=2))

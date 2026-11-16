"""Direct return forecasts with chronological validation and an explicit baseline."""
from pathlib import Path
import json
import numpy as np
import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[1] / 'models' / 'forecast_v2'
LOOKBACK = 60
HORIZON = 30


class ReturnLSTM(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(1, 32, batch_first=True)
        self.head = nn.Linear(32, HORIZON)
        nn.init.zeros_(self.head.weight)
        nn.init.zeros_(self.head.bias)

    def forward(self, x):
        output, _ = self.lstm(x)
        return self.head(output[:, -1])


def samples(prices):
    prices = np.asarray(prices, dtype=float)
    if len(prices) < 300 or not np.isfinite(prices).all() or (prices <= 0).any():
        raise ValueError('At least 300 complete positive historical prices are required.')
    returns = np.diff(np.log(prices)) * 100
    origins = np.arange(LOOKBACK, len(prices) - HORIZON)
    x = np.array([returns[i - LOOKBACK:i] for i in origins], dtype=np.float32)
    y = np.array([np.log(prices[i + 1:i + HORIZON + 1] / prices[i]) * 100 for i in origins], dtype=np.float32)
    return x, y, origins


def train(prices, ticker):
    torch.set_num_threads(2)
    torch.manual_seed(42)
    values = prices.to_numpy(dtype=float)
    x, y, origins = samples(values)
    development_cut = int(len(values) * .65)
    test_cut = int(len(values) * .82)
    # Purge labels that cross a boundary. No training target enters validation.
    fit = origins + HORIZON < development_cut
    validation = (origins >= development_cut) & (origins + HORIZON < test_cut)
    test = origins >= test_cut
    if min(fit.sum(), validation.sum(), test.sum()) < 10:
        raise ValueError('Insufficient chronological train/validation/test coverage.')
    scale = max(float(x[fit].std()), .01)
    inputs = torch.tensor(x / scale).unsqueeze(-1)
    targets = torch.tensor(y)
    model = ReturnLSTM()
    optimizer = torch.optim.Adam(model.parameters(), lr=.001)
    best_loss, best_state = float('inf'), None
    for _ in range(60):
        model.train()
        optimizer.zero_grad()
        loss = nn.functional.mse_loss(model(inputs[fit]), targets[fit])
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.)
        optimizer.step()
        model.eval()
        with torch.no_grad():
            validation_loss = nn.functional.mse_loss(model(inputs[validation]), targets[validation]).item()
        if validation_loss < best_loss:
            best_loss = validation_loss
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        predictions = model(inputs).numpy()
    def mae(mask, prediction):
        return float(np.mean(np.abs(prediction[mask] - y[mask])))
    model_validation = mae(validation, predictions)
    baseline_validation = mae(validation, np.zeros_like(y))
    selected = 'Direct-return LSTM' if model_validation < baseline_validation else 'Last-close baseline'
    report = {
        'ticker': ticker, 'trained_through': str(prices.index[-1].date()),
        'model': selected, 'lookback': LOOKBACK, 'horizon': HORIZON, 'input_scale': scale,
        'selection_rule': 'Lowest validation MAE versus last-close baseline; test data never selects weights or model.',
        'metric': 'Mean absolute cumulative log-return error in percentage points, averaged over forecast steps.',
        'validation_lstm_mae': model_validation, 'validation_baseline_mae': baseline_validation,
        'test_lstm_mae': mae(test, predictions), 'test_baseline_mae': mae(test, np.zeros_like(y)),
        'train_origins': int(fit.sum()), 'validation_origins': int(validation.sum()), 'test_origins': int(test.sum()),
        'limitations': 'One chronological split, overlapping forecast windows, no calibrated uncertainty intervals. This is an experimental forecast, not established predictive superiority.',
    }
    folder = ROOT / ticker
    folder.mkdir(parents=True, exist_ok=True)
    torch.save(best_state, folder / 'model.pt')
    prices.to_csv(folder / 'prices.csv')
    (folder / 'report.json').write_text(json.dumps(report, indent=2))
    return report


def predict(prices, ticker, horizon):
    folder = ROOT / ticker
    if not (folder / 'report.json').exists() or horizon > HORIZON:
        return None
    report = json.loads((folder / 'report.json').read_text())
    if report.get('ticker', ticker) != ticker or report['model'] not in ('Last-close baseline', 'Direct-return LSTM'):
        return None
    if report.get('trained_through') and str(prices.index[-1])[:10] < report['trained_through']:
        return None
    metric = 'test_baseline_mae' if report['model'] == 'Last-close baseline' else 'test_lstm_mae'
    verified = (report.get('ticker') == ticker and bool(report.get('trained_through'))
                and report.get('test_origins', 0) > 0 and report.get('validation_origins', 0) > 0
                and np.isfinite(report.get(metric, np.nan)))
    spot = float(prices.iloc[-1])
    if report['model'] == 'Last-close baseline':
        predicted = np.full(horizon, spot)
    else:
        model = ReturnLSTM()
        model.load_state_dict(torch.load(folder / 'model.pt', map_location='cpu', weights_only=True))
        model.eval()
        returns = np.diff(np.log(prices.to_numpy(dtype=float)))[-LOOKBACK:] * 100
        if len(returns) != LOOKBACK:
            raise ValueError('Insufficient price history for the validated model.')
        with torch.no_grad():
            output = model(torch.tensor(returns / report['input_scale'], dtype=torch.float32).reshape(1, LOOKBACK, 1)).numpy()[0, :horizon]
        predicted = spot * np.exp(output / 100)
    return {'forecast': [{'predicted_price': float(value)} for value in predicted],
            'model_family': 'Last-Close-Baseline' if report['model'] == 'Last-close baseline' else 'Validated-Direct-LSTM',
            'model': report['model'], 'validation': report if verified else None}

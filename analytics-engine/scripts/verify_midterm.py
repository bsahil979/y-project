"""Run the real five-stock API analysis and save a dated evidence artifact.

From analytics-engine: venv\Scripts\python.exe scripts\verify_midterm.py
Downloads actual provider data; fails rather than generating sample prices.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from api import app

payload = {
    'tickers': ['RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS'],
    'weights': [.4, .2, .15, .15, .1],
    'portfolio_value': 100000,
    'start': '2023-01-01',
    'end': '2026-09-01',
    'benchmark': '^NSEI',
    'include_optional_ml': False,
}

if __name__ == '__main__':
    with TestClient(app) as client:
        response = client.post('/portfolio/analyze', json=payload)
    if response.status_code != 200:
        raise SystemExit(f'Analysis failed ({response.status_code}): {response.text}')
    result = response.json()
    assert abs(sum(result['allocation']['weights'].values()) - 1) < 1e-5
    output = Path(__file__).resolve().parents[1] / 'docs' / 'midterm_analysis.json'
    output.write_text(json.dumps({
        'verified_at': datetime.now(timezone.utc).isoformat(),
        'description': 'Real-data API smoke check; in-sample analytics, not research backtest results.',
        'request': payload, 'response': result,
    }, indent=2, allow_nan=False), encoding='utf-8')
    print(f'PASS: five-stock API analysis. Evidence: {output}')
    print(f"Regime: {result['portfolio_regime']['current_regime']}")
    print(f"Volatility: {result['risk_budget']['portfolio_volatility']:.2%}")
    print(f"Allocation: {result['allocation']['weights']}")

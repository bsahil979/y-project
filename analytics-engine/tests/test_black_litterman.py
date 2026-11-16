import pytest
import numpy as np
import pandas as pd
from services.portfolio_optimizer import PortfolioOptimizer
from api import app, advanced_portfolio_lab, AdvancedLabRequest


def test_black_litterman_optimizer():
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=150, freq="B")
    ret_a = np.random.normal(0.0008, 0.015, len(dates))
    ret_b = np.random.normal(0.0006, 0.012, len(dates))
    ret_c = np.random.normal(0.0010, 0.018, len(dates))
    df = pd.DataFrame({"AAPL": ret_a, "MSFT": ret_b, "NVDA": ret_c}, index=dates)

    opt = PortfolioOptimizer(df, risk_free_rate=0.02)
    res = opt.optimize_black_litterman(
        market_weights={"AAPL": 0.4, "MSFT": 0.3, "NVDA": 0.3},
        views={"AAPL": 0.18, "MSFT": 0.14, "NVDA": 0.22},
        confidences={"AAPL": 0.8, "MSFT": 0.6, "NVDA": 0.7},
        sentiment_scores={"AAPL": 0.4, "MSFT": -0.2, "NVDA": 0.6},
        risk_aversion=2.5,
        tau=0.05
    )

    assert res["success"] is True
    assert "weights" in res
    assert "prior_returns" in res
    assert "ai_views" in res
    assert "posterior_returns" in res
    assert "sentiment_adjustments" in res
    total_w = sum(res["weights"].values())
    assert abs(total_w - 1.0) < 1e-3
    for w in res["weights"].values():
        assert 0.019 <= w <= 0.401


def test_advanced_lab_endpoint_fallback(monkeypatch):
    calls = {'prices': 0, 'sentiment': 0}
    def offline_prices(*args, **kwargs):
        calls['prices'] += 1
        raise ConnectionError('Offline price fixture')
    def offline_sentiment(*args, **kwargs):
        calls['sentiment'] += 1
        raise ConnectionError('Offline news fixture')
    monkeypatch.setattr('api.get_portfolio_data', offline_prices)
    monkeypatch.setattr('api.get_sentiment_analysis', offline_sentiment)
    req = AdvancedLabRequest(
        tickers=["AAPL", "MSFT", "GOOGL"],
        risk_aversion=3.0,
        tau=0.04,
        use_sentiment=True
    )
    res = advanced_portfolio_lab(req)
    assert calls == {"prices": 1, "sentiment": 3}
    assert res["status"] == "success"
    assert "models" in res
    assert "current" in res["models"]
    assert "markowitz_max_sharpe" in res["models"]
    assert "risk_parity" in res["models"]
    assert "black_litterman_ai" in res["models"]
    bl = res["models"]["black_litterman_ai"]
    assert len(bl["weights"]) == 3
    assert abs(sum(bl["weights"].values()) - 1.0) < 1e-2


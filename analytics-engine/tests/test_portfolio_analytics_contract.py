import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch
from fastapi.testclient import TestClient

from api import app, portfolio_analyze_cache
from services.data_fetcher import MarketDataUnavailable


@pytest.fixture
def client():
    portfolio_analyze_cache.clear()
    return TestClient(app)


def _make_dummy_portfolio_data(tickers, currency="USD"):
    dates = pd.date_range("2023-01-01", periods=100, freq="B")
    prices_dict = {}
    for i, t in enumerate(tickers):
        # Deterministic prices
        base = 100.0 * (i + 1)
        trend = np.linspace(0, 10, len(dates))
        prices_dict[t] = base + trend

    prices = pd.DataFrame(prices_dict, index=dates)
    prices.attrs = {
        "provider": "MockProvider",
        "price_field": "daily_close",
        "adjustment_verified": True,
        "dropped_incomplete_rows": 0,
    }
    returns = prices.pct_change().dropna()
    currencies = {t: currency for t in tickers}
    price_metadata = {
        "provider": "MockProvider",
        "price_field": "daily_close",
        "adjustment_verified": True,
        "first_observation": str(dates[0].date()),
        "last_observation": str(dates[-1].date()),
        "price_observations": len(dates),
        "return_observations": len(returns),
        "dropped_incomplete_rows": 0,
    }
    return {
        "prices": prices,
        "returns": returns,
        "currencies": currencies,
        "price_metadata": price_metadata,
    }


def test_validation_empty_tickers(client):
    res = client.post("/portfolio/analyze", json={
        "tickers": [],
        "weights": [],
        "portfolio_value": 10000,
    })
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()


def test_validation_weight_count_mismatch(client):
    res = client.post("/portfolio/analyze", json={
        "tickers": ["AAPL", "MSFT"],
        "weights": [1.0],
        "portfolio_value": 10000,
    })
    assert res.status_code == 400
    assert "length must match" in res.json()["detail"].lower()


def test_validation_negative_weight(client):
    res = client.post("/portfolio/analyze", json={
        "tickers": ["AAPL", "MSFT"],
        "weights": [-0.1, 1.1],
        "portfolio_value": 10000,
    })
    assert res.status_code == 400
    assert "non-negative" in res.json()["detail"].lower()


def test_validation_invalid_weight_sum(client):
    res = client.post("/portfolio/analyze", json={
        "tickers": ["AAPL", "MSFT"],
        "weights": [0.3, 0.3],
        "portfolio_value": 10000,
    })
    assert res.status_code == 400
    assert "must sum to 1" in res.json()["detail"].lower()


def test_validation_nan_or_infinite_weights(client):
    res = client.post(
        "/portfolio/analyze",
        content='{"tickers": ["AAPL", "MSFT"], "weights": ["invalid_nan", 1.0], "portfolio_value": 10000}',
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code in (400, 422)


def test_validation_zero_or_negative_portfolio_value(client):
    res = client.post("/portfolio/analyze", json={
        "tickers": ["AAPL"],
        "weights": [1.0],
        "portfolio_value": 0,
    })
    assert res.status_code == 400
    assert "positive" in res.json()["detail"].lower()


def test_validation_unsupported_currency(client):
    res = client.post("/portfolio/analyze", json={
        "tickers": ["AAPL"],
        "weights": [1.0],
        "portfolio_value": 10000,
        "currency": "EUR",
    })
    assert res.status_code == 400
    assert "unsupported" in res.json()["detail"].lower()


def test_missing_market_data_fails_without_fabrication(client):
    with patch("services.portfolio_pipeline.get_portfolio_data", side_effect=MarketDataUnavailable("Market data unavailable for AAPL")):
        res = client.post("/portfolio/analyze", json={
            "tickers": ["AAPL"],
            "weights": [1.0],
            "portfolio_value": 10000,
            "currency": "USD",
        })
        assert res.status_code == 503
        assert "Market data unavailable for AAPL" in res.json()["detail"]


def test_canonical_identity_and_weights_preservation(client):
    tickers = ["AAPL", "MSFT"]
    weights = [0.4, 0.6]
    dummy = _make_dummy_portfolio_data(tickers, "USD")

    with patch("services.portfolio_pipeline.get_portfolio_data", return_value=dummy):
        res = client.post("/portfolio/analyze", json={
            "portfolio_id": "test-portfolio-id-123",
            "portfolio_revision": "rev-hash-abc",
            "snapshot_as_of": "2026-09-29T12:00:00Z",
            "currency": "USD",
            "benchmark": "SPY",
            "portfolio_value": 50000.0,
            "tickers": tickers,
            "weights": weights,
            "include_optional_ml": False,
        })
        assert res.status_code == 200
        body = res.json()

        # Identity survives
        assert body["portfolio_id"] == "test-portfolio-id-123"
        assert body["portfolio_revision"] == "rev-hash-abc"
        assert body["snapshot_as_of"] == "2026-09-29T12:00:00Z"
        assert body["currency"] == "USD"
        assert body["benchmark_ticker"] == "SPY"
        assert body["analysis_id"] is not None
        assert len(body["analysis_id"]) > 10

        # Metadata object matches
        meta = body["metadata"]
        assert meta["portfolio_id"] == "test-portfolio-id-123"
        assert meta["portfolio_revision"] == "rev-hash-abc"
        assert meta["currency"] == "USD"
        assert meta["benchmark"] == "SPY"

        # Analyzed weights equal request weights
        assert body["analyzed_tickers"] == tickers
        assert body["analyzed_weights"] == [0.4, 0.6]
        assert meta["analyzed_weights"] == [0.4, 0.6]


def test_inr_currency_group_and_benchmark(client):
    tickers = ["RELIANCE.NS", "TCS.NS"]
    weights = [0.5, 0.5]
    dummy = _make_dummy_portfolio_data(tickers, "INR")

    with patch("services.portfolio_pipeline.get_portfolio_data", return_value=dummy):
        res = client.post("/portfolio/analyze", json={
            "portfolio_id": "p-inr",
            "portfolio_revision": "rev-inr-1",
            "currency": "INR",
            "benchmark": "^NSEI",
            "portfolio_value": 200000.0,
            "tickers": tickers,
            "weights": weights,
            "include_optional_ml": False,
        })
        assert res.status_code == 200
        body = res.json()
        assert body["currency"] == "INR"
        assert body["currency_symbol"] == "₹"
        assert body["benchmark_ticker"] == "^NSEI"
        assert body["metadata"]["benchmark"] == "^NSEI"
        assert body["metadata"]["currency"] == "INR"


def test_stage_status_and_optional_ml_disabled(client):
    tickers = ["AAPL"]
    weights = [1.0]
    dummy = _make_dummy_portfolio_data(tickers, "USD")

    with patch("services.portfolio_pipeline.get_portfolio_data", return_value=dummy):
        res = client.post("/portfolio/analyze", json={
            "tickers": tickers,
            "weights": weights,
            "portfolio_value": 10000.0,
            "currency": "USD",
            "include_optional_ml": False,
        })
        assert res.status_code == 200
        stages = res.json()["stages"]
        assert stages["market_data"]["status"] == "SUCCESS"
        assert stages["risk"]["status"] == "SUCCESS"
        assert stages["optional_ml"]["status"] == "NOT_REQUESTED"


def test_cache_safety_and_revision_isolation(client):
    tickers = ["AAPL"]
    weights = [1.0]
    dummy = _make_dummy_portfolio_data(tickers, "USD")

    with patch("services.portfolio_pipeline.get_portfolio_data", return_value=dummy):
        # First call with revision-1
        res1 = client.post("/portfolio/analyze", json={
            "portfolio_id": "p1",
            "portfolio_revision": "rev-1",
            "currency": "USD",
            "benchmark": "SPY",
            "portfolio_value": 10000.0,
            "tickers": tickers,
            "weights": weights,
            "include_optional_ml": False,
        })
        assert res1.status_code == 200
        body1 = res1.json()
        assert body1["cached"] is False
        id1 = body1["analysis_id"]

        # Second call with same revision reuses cache
        res2 = client.post("/portfolio/analyze", json={
            "portfolio_id": "p1",
            "portfolio_revision": "rev-1",
            "currency": "USD",
            "benchmark": "SPY",
            "portfolio_value": 10000.0,
            "tickers": tickers,
            "weights": weights,
            "include_optional_ml": False,
        })
        assert res2.status_code == 200
        body2 = res2.json()
        assert body2["cached"] is True
        assert body2["analysis_id"] == id1

        # Third call with DIFFERENT revision rev-2 must NOT reuse cache
        res3 = client.post("/portfolio/analyze", json={
            "portfolio_id": "p1",
            "portfolio_revision": "rev-2",
            "currency": "USD",
            "benchmark": "SPY",
            "portfolio_value": 10000.0,
            "tickers": tickers,
            "weights": weights,
            "include_optional_ml": False,
        })
        assert res3.status_code == 200
        body3 = res3.json()
        assert body3["cached"] is False
        assert body3["analysis_id"] != id1

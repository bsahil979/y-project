from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
import pytest
from fastapi import HTTPException


@pytest.mark.parametrize("symbol", ["sbin", "SBIN.NSE", "SBIN.NS"])
def test_sbi_resolves_to_nse_and_retains_available_financials(symbol):
    import api

    class Stock:
        info = {"shortName": "State Bank of India", "currentPrice": 900, "trailingPE": 12,
                "marketCap": float("nan")}
        balance_sheet = pd.DataFrame({"2025-03-31": [123], "2026-03-31": [456]},
                                     index=["Total Liabilities Net Minority Interest"])
        income_stmt = pd.DataFrame()

        @property
        def cash_flow(self):
            raise RuntimeError("Provider cash-flow request failed")

    with patch.object(api.yf, "Ticker", return_value=Stock()) as provider:
        result = api.fundamentals_analysis(symbol)

    provider.assert_called_once_with("SBIN.NS")
    assert result["ticker"] == "SBIN.NS"
    assert result["company"]["currency"] == "INR"
    assert result["company"]["market_cap"] is None
    assert result["valuation"]["trailing_pe"] == 12
    assert result["balance_sheet"]["total_liabilities"] == 456
    assert result["available_sections"] == ["valuation", "balance_sheet"]


def test_empty_fundamentals_return_actionable_error():
    import api

    empty = SimpleNamespace(info={"symbol": "UNKNOWN"}, income_stmt=pd.DataFrame(),
                            balance_sheet=pd.DataFrame(), cash_flow=pd.DataFrame())
    with patch.object(api.yf, "Ticker", return_value=empty), pytest.raises(HTTPException) as error:
        api.fundamentals_analysis("UNKNOWN")
    assert error.value.status_code == 404
    assert "Check the exchange symbol" in error.value.detail

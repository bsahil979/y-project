import ast
import datetime
import logging
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd


import pytest

@pytest.mark.parametrize('requested,provider,currency', [('AAPL','AAPL','USD'), ('HFCL-BE.NS','HFCL.NS','INR')])
def test_provider_exception_uses_daily_fallback(requested, provider, currency):
    # Load the endpoint without initializing unrelated ML services.
    tree = ast.parse((Path(__file__).parents[1] / 'api.py').read_text(encoding='utf8'))
    endpoint = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'get_quotes')
    endpoint.decorator_list = []
    endpoint.args.args[0].annotation = None
    calls = []

    def fail(_symbol):
        raise ConnectionError('Provider temporarily unavailable')

    def fallback(symbol):
        calls.append(symbol)
        return 200.0, 198.0, 'stooq_daily_close', '2026-11-13'

    scope = dict(datetime=datetime, logging=logging, np=np, pd=pd, quote_cache={},
                 yf=SimpleNamespace(Ticker=fail), _fallback_quote=fallback,
                 _fallback_pct_change_from_previous=lambda current, previous: (current / previous - 1) * 100)
    exec(compile(ast.Module(body=[endpoint], type_ignores=[]), '<quote endpoint>', 'exec'), scope)
    result = scope['get_quotes'](SimpleNamespace(tickers=[requested]))['quotes'][requested]
    assert calls == [provider]
    assert result['ticker'] == requested
    assert result['provider_symbol'] == provider
    assert result['price'] == 200.0
    assert result['currency'] == currency
    assert result['price_source'] == 'stooq_daily_close'
    assert result['last_daily_session'] == '2026-11-13'


def test_alias_history_preserves_ledger_identity(monkeypatch):
    from services import data_fetcher as data
    from services.market_symbols import market_data_symbol
    assert market_data_symbol('BRK-B') == 'BRK-B'
    assert market_data_symbol('UNKNOWN-RE-BE.NS') == 'UNKNOWN-RE-BE.NS'
    data._price_cache.clear()
    index = pd.bdate_range('2025-01-01', periods=70)
    calls = []
    def download(tickers, **kwargs):
        calls.append(tickers)
        return {'Close': pd.DataFrame({'HFCL.NS': np.arange(70)+100.0}, index=index)}
    monkeypatch.setattr(data.yf, 'download', download)
    result = data.fetch_price_data(['HFCL-BE.NS','HFCL.NS'], '2025-01-01','2025-05-01')
    assert calls == [['HFCL.NS']]
    assert list(result.columns) == ['HFCL-BE.NS','HFCL.NS']
    pd.testing.assert_series_equal(result.iloc[:,0], result.iloc[:,1], check_names=False)
    assert result.attrs['provider_symbols']['HFCL-BE.NS'] == 'HFCL.NS'

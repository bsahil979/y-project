import ast
import datetime
import logging
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd


def test_provider_exception_uses_daily_fallback():
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
    result = scope['get_quotes'](SimpleNamespace(tickers=['AAPL']))['quotes']['AAPL']
    assert calls == ['AAPL']
    assert result['price'] == 200.0
    assert result['currency'] == 'USD'
    assert result['price_source'] == 'stooq_daily_close'
    assert result['last_daily_session'] == '2026-11-13'

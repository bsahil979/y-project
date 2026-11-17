import yfinance as yf
import pandas as pd
import datetime
import time
from functools import lru_cache


def fetch_stooq_daily_ohlcv(ticker: str, start, end) -> pd.DataFrame:
    """
    Daily OHLCV from Stooq CSV (no pandas_datareader — avoids pandas/shim breakages).
    start/end: str, date, or datetime — sliced inclusive on the index.
    Symbol hints: US .us, NSE .ns, BSE .bo
    """
    base = ticker.split(".")[0].lower()
    if ticker.upper().endswith(".NS"):
        sym = f"{base}.ns"
    elif ticker.upper().endswith(".BO"):
        sym = f"{base}.bo"
    else:
        sym = f"{base}.us"
    url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
    df = pd.read_csv(url)
    need = ("Date", "Open", "High", "Low", "Close")
    if df.empty or not all(c in df.columns for c in need):
        raise ValueError(f"Stooq returned no usable rows for {sym}")
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    df = df.loc[start_ts:end_ts]
    if "Volume" not in df.columns:
        df["Volume"] = 0
    return df


def _stooq_close_series(ticker: str, start: str, end: str) -> pd.Series:
    s = fetch_stooq_daily_ohlcv(ticker, start, end)["Close"].copy()
    s.name = ticker
    return s


_price_cache: dict = {}


class MarketDataUnavailable(ValueError):
    """Requested real market history could not be obtained."""


def _validated_prices(data, tickers):
    if isinstance(data, pd.Series):
        data = data.to_frame(name=tickers[0])
    missing = [ticker for ticker in tickers if ticker not in data.columns]
    if missing:
        raise MarketDataUnavailable(f"Missing market history for: {', '.join(missing)}")
    # Preserve request order: downstream weights are positional. Keep only
    # dates where every asset has an observed close; filling missing prices
    # would create artificial zero returns and understate risk.
    data = data.loc[:, tickers].apply(pd.to_numeric, errors="coerce")
    data = data.where((data > 0) & (data < float('inf'))).sort_index()
    data.attrs = dict(data.attrs)
    data.attrs['dropped_incomplete_rows'] = int(data.isna().any(axis=1).sum())
    data = data.dropna()
    if len(data) < 2:
        raise MarketDataUnavailable("At least two overlapping price observations are required")
    return data

def fetch_price_data(tickers: list, start: str, end: str) -> pd.DataFrame:
    """
    Fetches historical closing prices using multi-source real-time APIs
    (Source 1: Yahoo Finance primary stream, Source 2: Stooq web syndicate fallback).

    Results are cached for 60 seconds to avoid duplicate network calls.
    """
    from services.market_symbols import market_data_symbol
    provider_symbols = [market_data_symbol(ticker) for ticker in tickers]
    if provider_symbols != list(tickers):
        # Fetch each listing once, then restore ledger column identities.
        source = fetch_price_data(list(dict.fromkeys(provider_symbols)), start, end)
        mapped = pd.DataFrame({ticker: source[provider] for ticker, provider in zip(tickers, provider_symbols)})
        mapped.attrs.update(source.attrs)
        mapped.attrs['provider_symbols'] = dict(zip(tickers, provider_symbols))
        return mapped
    cache_key = (tuple(tickers), start, end)
    cached = _price_cache.get(cache_key)
    now = time.time()
    if cached is not None and now - cached["ts"] < 60:
        return cached["data"]

    print(f"Fetching real-time streams for {tickers} across multiple data gateways...")
    try:
        # Source 1: Primary production endpoint via yfinance
        data = yf.download(tickers, start=start, end=end, auto_adjust=True)["Close"]
        data = _validated_prices(data, tickers)
        data.attrs.update({
            'provider': 'Yahoo Finance',
            'price_field': 'auto-adjusted close (dividends and splits adjusted)',
            'adjustment_verified': True,
        })
        _price_cache[cache_key] = {"ts": time.time(), "data": data}
        return data
    except Exception as e:
        print(f"Primary source streaming warning ({str(e)}). Engaging Source 2 alternative data syndication (Stooq)...")
        # Source 2: Alternative public market integration endpoint via Stooq
        combined_series = {}
        for ticker in tickers:
            try:
                combined_series[ticker] = _stooq_close_series(ticker, start=start, end=end)
            except Exception as stooq_err:
                print(f"Source 2 integration note for {ticker}: {str(stooq_err)}")
                
        if combined_series:
            fallback_df = _validated_prices(pd.DataFrame(combined_series), tickers)
            fallback_df.attrs.update({
                'provider': 'Stooq',
                'price_field': 'daily close; adjustment convention not verified',
                'adjustment_verified': False,
            })
            _price_cache[cache_key] = {"ts": time.time(), "data": fallback_df}
            return fallback_df
            
        raise MarketDataUnavailable(
            "Market data providers are unavailable. Retry later; no simulated prices were substituted."
        )



def compute_daily_returns(price_data: pd.DataFrame) -> pd.DataFrame:
    """
    Computes daily percentage returns from price data.
    """
    returns = price_data.pct_change().dropna()
    return returns


def get_currency_metadata(tickers: list) -> dict:
    """
    Fetches currency for a list of tickers from yfinance.
    """
    currencies = {}
    for ticker in tickers:
        try:
            # Suffix-based fallback to avoid slow .info calls where obvious
            if ticker.endswith('.NS') or ticker.endswith('.BO'):
                currencies[ticker] = "INR"
            else:
                t = yf.Ticker(ticker)
                currency = t.info.get('currency')
                if not currency:
                    raise ValueError(f"No quote currency returned for {ticker}")
                currencies[ticker] = str(currency).upper()
        except Exception:
            # Unknown is safer than silently treating an unsupported or
            # temporarily unreachable listing as USD.
            currencies[ticker] = "UNKNOWN"
    return currencies


def get_portfolio_data(tickers: list, start: str, end: str):
    """
    Master function — fetches prices and computes returns in one call.
    Includes currency metadata.
    """
    prices = fetch_price_data(tickers, start, end)
    returns = compute_daily_returns(prices)
    currencies = get_currency_metadata(tickers)
    price_metadata = {
        "provider": prices.attrs.get("provider", "Unknown provider"),
        "price_field": prices.attrs.get("price_field", "Unknown price convention"),
        "adjustment_verified": bool(prices.attrs.get("adjustment_verified", False)),
        "first_observation": prices.index[0].strftime("%Y-%m-%d"),
        "last_observation": prices.index[-1].strftime("%Y-%m-%d"),
        "price_observations": int(len(prices)),
        "return_observations": int(len(returns)),
        "dropped_incomplete_rows": int(prices.attrs.get("dropped_incomplete_rows", 0)),
    }

    return {
        "prices": prices,
        "returns": returns,
        "currencies": currencies,
        "price_metadata": price_metadata,
    }


@lru_cache(maxsize=64)
def fetch_usdinr_rates(start: str, end: str) -> pd.Series:
    """Observed INR per USD daily closes. Cache successful date ranges only."""
    pair = 'USDINR=X'
    try:
        raw = yf.download(pair, start=start, end=end, auto_adjust=False, progress=False)['Close']
        rates = _validated_prices(raw, [pair])[pair]
        if rates.index.has_duplicates:
            raise ValueError('Duplicate FX dates')
        return rates
    except Exception as exc:
        raise MarketDataUnavailable(f'USDINR=X FX quotes unavailable for {start} to {end}: {exc}') from exc


def normalize_currency_prices(prices, currencies, base_currency, start, end):
    """Use only common observed closing dates. Never backfill FX or asset prices."""
    unsupported = set(currencies[t] for t in prices) - {'INR', 'USD'}
    if unsupported or base_currency not in {'INR', 'USD'}:
        raise ValueError('Unsupported or unknown quote currency; analysis supports INR and USD only')
    converted = [t for t in prices if currencies[t] != base_currency]
    factors = dict.fromkeys(prices.columns, 1.0)
    out = prices
    rate = None
    if converted:
        rates = fetch_usdinr_rates(start, end).reindex(prices.index)
        valid = rates.gt(0) & rates.lt(float('inf'))
        if valid.sum() < 2:
            raise MarketDataUnavailable('USDINR=X FX quotes unavailable on overlapping portfolio dates')
        out = prices.loc[valid].copy()
        aligned = rates.loc[valid]
        rate = float(aligned.iloc[-1])
        multiplier = aligned if base_currency == 'INR' else 1 / aligned
        out[converted] = out[converted].mul(multiplier, axis=0)
        factors.update(dict.fromkeys(converted, float(multiplier.iloc[-1])))
    return out, factors, {
        'base_currency': base_currency, 'original_currency': {t: currencies[t] for t in prices},
        'fx_conversion_applied': bool(converted), 'fx_pair_used': 'USDINR=X' if converted else None,
        'fx_rate_inr_per_usd': rate, 'valuation_date': str(out.index[-1].date()),
        'fx_dropped_dates': len(prices) - len(out),
    }

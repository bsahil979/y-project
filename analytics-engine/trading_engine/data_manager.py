import yfinance as yf
import pandas as pd
import numpy as np
import ta
import datetime
from services.data_fetcher import fetch_stooq_daily_ohlcv

def fetch_asset_data(ticker="AAPL", period="60d", interval="5m", allow_synthetic_fallback=False):
    """
    Fetches market data from Yahoo Finance, then Stooq.

    Historical research must fail closed when both providers are unavailable.
    ``allow_synthetic_fallback`` exists only for an explicitly opted-in live
    continuity use case and must remain false for dataset construction.
    """
    try:
        # Source 1: Try primary yfinance granular feed
        data = yf.download(ticker, period=period, interval=interval)
        if data.empty:
            data = yf.download(ticker, period="1y", interval="1d")
        if data.empty:
            raise ValueError("Primary yfinance return was empty.")
    except Exception as e:
        print(f"Primary fetch warning for {ticker} ({str(e)}). Falling back to Source 2 (Stooq integration)...")
        # Source 2: Stooq CSV (daily bars) — avoids pandas_datareader
        try:
            start_date = datetime.date.today() - datetime.timedelta(days=90)
            data = fetch_stooq_daily_ohlcv(ticker, start_date, datetime.date.today())
        except Exception as stooq_err:
            if not allow_synthetic_fallback:
                raise RuntimeError(
                    f"No provider data available for {ticker}: Yahoo failed and "
                    f"Stooq failed ({stooq_err})."
                ) from stooq_err
            print(f"Source 2 error: {str(stooq_err)}. Deploying static continuity baseline.")
            dates = pd.date_range(end=datetime.datetime.now(), periods=60, freq='H')
            data = pd.DataFrame({
                "Open": 150.0, "High": 152.0, "Low": 149.0,
                "Close": 151.0 + np.sin(range(60)), "Volume": 1000000
            }, index=dates)

    # Flatten multi-index columns if they exist (yfinance 0.2.x+ behavior)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [col[0] for col in data.columns.values]
    
    df = data.copy()
    return df

def add_technical_indicators(df):
    """
    Computes technical indicators for the trading engine.
    """
    if df.empty:
        return df
        
    df = df.copy()
    
    # Trend Indicators
    df['ema_50'] = ta.trend.ema_indicator(df['Close'], window=50)
    df['ema_200'] = ta.trend.ema_indicator(df['Close'], window=200)
    
    # MACD
    macd = ta.trend.MACD(df['Close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_diff'] = macd.macd_diff()
    
    # Momentum Indicators
    df['rsi'] = ta.momentum.rsi(df['Close'], window=14)
    df['stoch_rsi'] = ta.momentum.stochrsi(df['Close'])
    
    # Volatility Indicators
    df['bb_high'] = ta.volatility.bollinger_hband(df['Close'])
    df['bb_low'] = ta.volatility.bollinger_lband(df['Close'])
    df['atr'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'])
    
    # Trend Strength
    df['adx'] = ta.trend.adx(df['High'], df['Low'], df['Close'])
    
    # Volume Indicators
    df['obv'] = ta.volume.on_balance_volume(df['Close'], df['Volume'])
    
    # Time Features
    df['day_of_week'] = df.index.dayofweek
    df['hour'] = df.index.hour
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    
    # Returns & Volatility
    df['returns'] = df['Close'].pct_change()
    df['volatility'] = df['returns'].rolling(window=24).std()
    
    df.dropna(inplace=True)
    return df

def get_processed_data(ticker="AAPL", period="60d", interval="5m", allow_synthetic_fallback=False):
    """
    Master function to get cleaned and featured asset data.
    """
    raw_data = fetch_asset_data(
        ticker=ticker,
        period=period,
        interval=interval,
        allow_synthetic_fallback=allow_synthetic_fallback,
    )
    featured_data = add_technical_indicators(raw_data)
    return featured_data

if __name__ == "__main__":
    data = get_processed_data()
    print("Columns:", data.columns.tolist())
    print("Latest data:\n", data.tail(3))

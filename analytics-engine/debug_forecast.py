import yfinance as yf
from services.forecaster import get_price_forecast
import pandas as pd

try:
    data = yf.download("AAPL", start="2020-01-01", end="2024-01-01")
    prices = data["Close"]
    # Handle multi-index if necessary
    if isinstance(prices, pd.DataFrame):
        prices = prices["AAPL"]
    
    print(f"Data shape: {prices.shape}")
    forecast = get_price_forecast(prices, 30, return_metadata=False)
    print("Forecast successful!")
    print(forecast[:5])
except Exception as e:
    import traceback
    traceback.print_exc()

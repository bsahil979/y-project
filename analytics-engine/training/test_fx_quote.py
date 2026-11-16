import yfinance as yf
from services.portfolio_pipeline import fetch_market_quotes

print("Direct yfinance USDINR=X:", yf.Ticker("USDINR=X").fast_info.get("lastPrice"))
print("fetch_market_quotes USDINR=X:", fetch_market_quotes(["USDINR=X"]))
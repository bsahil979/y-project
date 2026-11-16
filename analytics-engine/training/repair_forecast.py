"""Run: python -m training.repair_forecast --ticker MSFT"""
import argparse
import datetime
import json
from services.data_fetcher import get_portfolio_data
from services.validated_forecast import train

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ticker', default='MSFT')
    args = parser.parse_args()
    ticker = args.ticker.upper().strip()
    data = get_portfolio_data([ticker], '2020-01-01', datetime.date.today().isoformat())
    prices = data['prices']
    prices = prices[ticker] if hasattr(prices, 'columns') else prices
    print(json.dumps(train(prices.dropna(), ticker), indent=2))

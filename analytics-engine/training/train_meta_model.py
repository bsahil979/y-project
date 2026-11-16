import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from trading_engine.meta_model import MarketMindMetaModel


def main():
    parser = argparse.ArgumentParser(description='Train the MarketMind meta-decision model.')
    parser.add_argument('--tickers', nargs='+', default=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA'], help='Ticker symbols to include.')
    parser.add_argument('--start', default='2018-01-01', help='Start date for dataset construction.')
    parser.add_argument('--end', default=None, help='Optional end date.')
    parser.add_argument('--horizon', type=int, default=5, help='Future return horizon in days.')
    parser.add_argument('--buy-threshold', type=float, default=0.01)
    parser.add_argument('--sell-threshold', type=float, default=-0.01)
    parser.add_argument('--test-size', type=float, default=0.2)
    parser.add_argument('--historical-sentiment-path', default=None)
    args = parser.parse_args()

    model = MarketMindMetaModel()
    dataset = model.build_dataset(
        tickers=args.tickers,
        start=args.start,
        end=args.end,
        horizon=args.horizon,
        buy_threshold=args.buy_threshold,
        sell_threshold=args.sell_threshold,
        historical_sentiment_path=args.historical_sentiment_path,
    )
    metrics = model.train(dataset, test_size=args.test_size)
    print("Selected model:", metrics['selected_model'])
    print(json.dumps(metrics['metrics'], indent=2, default=str))
    print(f"Artifacts saved under: {model.model_dir}")


if __name__ == '__main__':
    import json
    main()

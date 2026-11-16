"""Train the initial production MarketMind model on a pooled historical dataset.

Usage (from analytics-engine):
    python -m training.train_production --tickers AAPL MSFT GOOGL
"""
import argparse
import json

from trading_engine.meta_model import MarketMindMetaModel


def main():
    parser = argparse.ArgumentParser(description='Train the production tabular signal model.')
    parser.add_argument('--tickers', nargs='+', required=True)
    parser.add_argument('--start', default='2018-01-01')
    parser.add_argument('--end', default=None)
    parser.add_argument('--horizon', type=int, default=5)
    parser.add_argument('--buy-threshold', type=float, default=0.01)
    parser.add_argument('--sell-threshold', type=float, default=-0.01)
    parser.add_argument('--test-size', type=float, default=0.2)
    args = parser.parse_args()

    model = MarketMindMetaModel()
    dataset = model.build_dataset(
        tickers=[t.upper().strip() for t in args.tickers],
        start=args.start, end=args.end, horizon=args.horizon,
        buy_threshold=args.buy_threshold,
        sell_threshold=args.sell_threshold,
    )
    metadata = model.train(dataset, test_size=args.test_size)
    print(json.dumps(metadata, indent=2, default=str))
    print(f'Artifacts saved under: {model.model_dir}')


if __name__ == '__main__':
    main()
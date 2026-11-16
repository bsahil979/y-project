"""
Train universal (cross-ticker) models on pooled data from the full ticker universe.
Run after per-ticker training or standalone:

  python -m training.train_universal --period 5y --interval 1d
"""
import argparse
import logging
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.ticker_universe import all_symbols
from trading_engine.data_manager import get_processed_data
from trading_engine.universal_models import UniversalModels

logger = logging.getLogger('train_universal')
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')


def run_training(tickers=None, period='5y', interval='1d', save_dir=None, rf_estimators=300, lstm_epochs=25):
    save_dir = save_dir or os.path.join(os.path.dirname(__file__), '..', 'models')
    tickers = tickers or all_symbols()

    frames, ok, fail = [], [], []
    for t in tickers:
        try:
            df = get_processed_data(ticker=t, period=period, interval=interval)
            if df is not None and not df.empty:
                frames.append(df)
                ok.append(t)
            else:
                fail.append(t)
        except Exception as e:
            logger.warning('Skip %s: %s', t, e)
            fail.append(t)

    if len(frames) < 5:
        raise RuntimeError('Too few tickers loaded for universal training')

    uni = UniversalModels()
    metrics = uni.train_from_frames(frames, n_estimators=rf_estimators, lstm_epochs=lstm_epochs)
    tgt = uni.save(save_dir)
    return {'path': tgt, 'metrics': metrics, 'ok': len(ok), 'fail': len(fail)}


def main():
    parser = argparse.ArgumentParser(description='Train universal hybrid models on all universe tickers')
    parser.add_argument('--tickers', nargs='+', default=None, help='Subset of tickers (default: full universe)')
    parser.add_argument('--period', default='5y')
    parser.add_argument('--interval', default='1d')
    parser.add_argument('--save_dir', default=None)
    parser.add_argument('--rf_estimators', type=int, default=300)
    parser.add_argument('--lstm_epochs', type=int, default=25)
    args = parser.parse_args()

    save_dir = args.save_dir or os.path.join(os.path.dirname(__file__), '..', 'models')
    tickers = args.tickers or all_symbols()
    logger.info('Universal training on %d tickers', len(tickers))
    start = time.time()
    result = run_training(
        tickers=tickers,
        period=args.period,
        interval=args.interval,
        save_dir=save_dir,
        rf_estimators=args.rf_estimators,
        lstm_epochs=args.lstm_epochs,
    )
    logger.info('Saved universal models -> %s (%.1fs)', result['path'], time.time() - start)
    logger.info('Metrics: %s', result['metrics'])
    logger.info('OK: %d  Failed: %d', result['ok'], result['fail'])


if __name__ == '__main__':
    main()

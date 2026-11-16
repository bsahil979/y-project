"""
Train portfolio-level PPO on the full ticker universe (allocation weights + cash).
"""
import argparse
import json
import logging
import os
import sys
import time
import datetime

import numpy as np
import pandas as pd
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.ticker_universe import all_symbols
from services.data_fetcher import get_portfolio_data
from trading_engine.portfolio_rl_env import (
    PortfolioRLEnv,
    build_market_tensors,
    portfolio_rl_model_dir,
    save_universe_meta,
)

logger = logging.getLogger('portfolio_rl')
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')


def load_universe_returns(tickers, period_years=5):
    end = datetime.date.today()
    start = end - datetime.timedelta(days=int(period_years * 365.25))
    start_s = start.isoformat()
    end_s = end.isoformat()

    ok, fail = [], []
    price_parts = []
    for t in tickers:
        try:
            data = get_portfolio_data([t], start_s, end_s)
            p = data['prices']
            if p is None or p.empty or len(p) < 120:
                fail.append(t)
                continue
            if isinstance(p, pd.DataFrame):
                col = p.columns[0] if t not in p.columns else t
                s = p[col] if col in p.columns else p.iloc[:, 0]
            else:
                s = p
            s.name = t
            price_parts.append(s)
            ok.append(t)
        except Exception as e:
            logger.warning('Skip %s: %s', t, e)
            fail.append(t)

    if len(ok) < 5:
        raise RuntimeError(f'Too few tickers with data ({len(ok)})')

    prices = pd.concat(price_parts, axis=1).sort_index().ffill()
    prices = prices.dropna(axis=1, how='all')
    returns = prices.pct_change(fill_method=None).dropna(how='all')
    returns = returns.dropna(axis=0, how='any')
    prices = prices.loc[returns.index]
    tickers_final = list(returns.columns)
    return prices, returns, tickers_final, ok, fail


def run_training(
    tickers=None,
    timesteps=80_000,
    period_years=5,
    save_dir=None,
    learning_rate=3e-4,
):
    tickers = tickers or all_symbols()
    save_dir = save_dir or os.path.join(os.path.dirname(__file__), '..', 'models')

    logger.info('Loading market data for %d universe symbols...', len(tickers))
    prices, returns, tickers_final, ok, fail = load_universe_returns(tickers, period_years=period_years)
    logger.info('Universe panel: %d symbols, %d rows', len(tickers_final), len(returns))

    tensors = build_market_tensors(prices, returns)
    env = PortfolioRLEnv(tensors)

    vec = DummyVecEnv([lambda: Monitor(env)])

    policy_kwargs = dict(net_arch=dict(pi=[256, 256], vf=[256, 256]))
    model = PPO(
        'MlpPolicy',
        vec,
        verbose=1,
        learning_rate=learning_rate,
        n_steps=2048,
        batch_size=256,
        policy_kwargs=policy_kwargs,
    )

    start = time.time()
    model.learn(total_timesteps=timesteps)
    elapsed = time.time() - start

    tgt = portfolio_rl_model_dir(save_dir)
    os.makedirs(tgt, exist_ok=True)
    model.save(os.path.join(tgt, 'ppo_policy'))

    meta = save_universe_meta(
        save_dir,
        tickers_final,
        extra={
            'trained_at': datetime.datetime.utcnow().isoformat(),
            'timesteps': timesteps,
            'training_seconds': round(elapsed, 1),
            'causal_preprocessing': env.metadata['causal_preprocessing'],
            'period_years': period_years,
            'n_rows': len(returns),
            'loaded': len(ok),
            'failed': len(fail),
            'obs_dim': env.observation_space.shape[0],
            'action_dim': env.action_space.shape[0],
        },
    )

    logger.info('Portfolio RL saved -> %s (%.1fs)', tgt, elapsed)
    return {
        'path': tgt,
        'tickers': len(tickers_final),
        'elapsed': elapsed,
        'failed': fail,
    }


def main():
    parser = argparse.ArgumentParser(description='Train portfolio allocation PPO on full universe')
    parser.add_argument('--timesteps', type=int, default=80_000)
    parser.add_argument('--period_years', type=int, default=5)
    parser.add_argument('--save_dir', default=None)
    args = parser.parse_args()
    run_training(timesteps=args.timesteps, period_years=args.period_years, save_dir=args.save_dir)


if __name__ == '__main__':
    main()

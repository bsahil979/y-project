"""
baselines.py — Five benchmark strategies for the paper.

All strategies share the same interface:
    run(prices, returns, **kwargs) -> dict
        prices  : pd.DataFrame (dates x tickers), daily close prices
        returns : pd.DataFrame (dates x tickers), daily returns
    Returns:
        {
          'equity'   : pd.Series  — daily portfolio value starting at 1.0
          'weights'  : pd.DataFrame — daily weight snapshots
          'turnover' : float        — average daily absolute turnover
        }

Strategies implemented:
  1. EqualWeight         — rebalance monthly to 1/N
  2. BuyAndHold          — fixed initial weights (equal), never rebalance
  3. MarkowitzMVO        — min-variance rebalance monthly
  4. MarkowitzMaxSharpe  — max-Sharpe rebalance monthly
  5. PPONoRegime         — PPO env with regime one-hot zeroed (ablation)
"""

import sys
import os
import numpy as np
import pandas as pd
from typing import Optional

# Allow imports from analytics-engine root
_engine_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _engine_root not in sys.path:
    sys.path.insert(0, _engine_root)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _equity_from_weights(
    weights_df: pd.DataFrame,
    returns: pd.DataFrame,
) -> pd.Series:
    """
    Compute daily portfolio equity from a weights timeseries.
    weights_df : (dates x tickers), each row is the weight vector for that day.
    returns    : (dates x tickers), aligned daily returns.
    """
    aligned_w = weights_df.reindex(returns.index, method="ffill").fillna(0.0)
    daily_port_ret = (aligned_w * returns).sum(axis=1)
    equity = (1.0 + daily_port_ret).cumprod()
    equity.iloc[0] = 1.0
    return equity


def _mean_turnover(weights_df: pd.DataFrame) -> float:
    """Average daily sum of absolute weight changes."""
    diff = weights_df.diff().abs().sum(axis=1)
    return float(diff.mean())


def _markowitz_weights(
    returns_window: pd.DataFrame,
    objective: str = "max_sharpe",
    rf: float = 0.06,
) -> np.ndarray:
    """
    Solve Markowitz optimisation for a given returns window.
    objective: 'max_sharpe' | 'min_vol'
    Returns weight array (n_assets,).
    """
    from scipy.optimize import minimize

    n = returns_window.shape[1]
    mu = returns_window.mean().values * 252
    cov = returns_window.cov().values * 252
    rf_daily = rf / 252

    def neg_sharpe(w):
        r = mu @ w
        v = np.sqrt(w @ cov @ w + 1e-12)
        return -(r - rf) / v

    def portfolio_vol(w):
        return np.sqrt(w @ cov @ w + 1e-12)

    obj_fn = neg_sharpe if objective == "max_sharpe" else portfolio_vol
    w0 = np.ones(n) / n
    bounds = [(0.0, 1.0)] * n
    constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}]
    res = minimize(obj_fn, w0, method="SLSQP", bounds=bounds, constraints=constraints,
                   options={"maxiter": 500, "ftol": 1e-9})
    if res.success:
        w = np.clip(res.x, 0, 1)
        return w / (w.sum() + 1e-12)
    return w0  # fallback to equal weight on solver failure


# ---------------------------------------------------------------------------
# Strategy 1: Equal Weight
# ---------------------------------------------------------------------------

class EqualWeight:
    name = "Equal-Weight"

    def run(self, prices: pd.DataFrame, returns: pd.DataFrame, **kwargs) -> dict:
        tickers = returns.columns.tolist()
        n = len(tickers)
        eq_w = np.ones(n) / n

        # Monthly rebalance dates
        monthly_dates = returns.resample("ME").last().index
        weights = pd.DataFrame(index=returns.index, columns=tickers, dtype=float)
        weights.iloc[0] = eq_w
        for d in monthly_dates:
            loc = weights.index.searchsorted(d)
            if loc < len(weights):
                weights.iloc[loc] = eq_w
        weights = weights.ffill().fillna(1.0 / n)

        equity = _equity_from_weights(weights, returns)
        return {
            "equity": equity,
            "weights": weights,
            "turnover": _mean_turnover(weights),
        }


# ---------------------------------------------------------------------------
# Strategy 2: Buy-and-Hold
# ---------------------------------------------------------------------------

class BuyAndHold:
    name = "Buy-and-Hold"

    def run(self, prices: pd.DataFrame, returns: pd.DataFrame, **kwargs) -> dict:
        tickers = returns.columns.tolist()
        n = len(tickers)
        init_w = np.ones(n) / n  # equal initial allocation, never rebalanced

        # Drift weights based on price performance
        cumret = (1.0 + returns).cumprod()
        drift = cumret.multiply(init_w, axis=1)
        drift_sum = drift.sum(axis=1)
        weights = drift.div(drift_sum, axis=0)

        equity = _equity_from_weights(weights, returns)
        # Turnover = 0 (no rebalancing)
        return {
            "equity": equity,
            "weights": weights,
            "turnover": 0.0,
        }


# ---------------------------------------------------------------------------
# Strategy 3: Markowitz MVO (Minimum Variance)
# ---------------------------------------------------------------------------

class MarkowitzMVO:
    name = "Markowitz-MinVol"

    def run(
        self,
        prices: pd.DataFrame,
        returns: pd.DataFrame,
        lookback_days: int = 252,
        rf: float = 0.06,
        **kwargs,
    ) -> dict:
        tickers = returns.columns.tolist()
        n = len(tickers)
        monthly_dates = returns.resample("ME").last().index
        weights = pd.DataFrame(index=returns.index, columns=tickers, dtype=float)
        weights.iloc[0] = 1.0 / n

        for d in monthly_dates:
            loc = returns.index.searchsorted(d)
            if loc < lookback_days:
                continue
            window = returns.iloc[loc - lookback_days : loc]
            w = _markowitz_weights(window, objective="min_vol", rf=rf)
            if loc < len(weights):
                weights.iloc[loc] = w

        weights = weights.ffill().fillna(1.0 / n)
        equity = _equity_from_weights(weights, returns)
        return {
            "equity": equity,
            "weights": weights,
            "turnover": _mean_turnover(weights),
        }


# ---------------------------------------------------------------------------
# Strategy 4: Markowitz Max-Sharpe
# ---------------------------------------------------------------------------

class MarkowitzMaxSharpe:
    name = "Markowitz-MaxSharpe"

    def run(
        self,
        prices: pd.DataFrame,
        returns: pd.DataFrame,
        lookback_days: int = 252,
        rf: float = 0.06,
        **kwargs,
    ) -> dict:
        tickers = returns.columns.tolist()
        n = len(tickers)
        monthly_dates = returns.resample("ME").last().index
        weights = pd.DataFrame(index=returns.index, columns=tickers, dtype=float)
        weights.iloc[0] = 1.0 / n

        for d in monthly_dates:
            loc = returns.index.searchsorted(d)
            if loc < lookback_days:
                continue
            window = returns.iloc[loc - lookback_days : loc]
            w = _markowitz_weights(window, objective="max_sharpe", rf=rf)
            if loc < len(weights):
                weights.iloc[loc] = w

        weights = weights.ffill().fillna(1.0 / n)
        equity = _equity_from_weights(weights, returns)
        return {
            "equity": equity,
            "weights": weights,
            "turnover": _mean_turnover(weights),
        }


# ---------------------------------------------------------------------------
# Strategy 5: PPO (No Regime) — Ablation
# ---------------------------------------------------------------------------

class PPONoRegime:
    """
    Identical to the PPO+Regime strategy but with regime one-hot zeroed out.
    This proves that the regime signal adds value (key novelty claim).
    """
    name = "PPO-NoRegime"

    def run(
        self,
        prices: pd.DataFrame,
        returns: pd.DataFrame,
        test_prices: Optional[pd.DataFrame] = None,
        test_returns: Optional[pd.DataFrame] = None,
        ppo_timesteps: int = 200_000,
        rebalance_cost: float = 0.001,
        seed: int = 42,
        **kwargs,
    ) -> dict:
        from trading_engine.portfolio_rl_env import (
            build_market_tensors,
            PortfolioRLEnv,
            _softmax,
        )
        from trading_engine.portfolio_rl_env import GLOBAL_FEATURES, FEATURES_PER_ASSET
        from stable_baselines3 import PPO as SB3PPO
        import gymnasium as gym

        train_tensors = build_market_tensors(prices, returns)

        # Subclass to zero-out regime one-hot
        class NoRegimeEnv(PortfolioRLEnv):
            def _regime_onehot(self, t):
                import numpy as np
                return np.zeros(3, dtype=np.float32)  # ablation: zero regime signal

        train_env = NoRegimeEnv(
            train_tensors,
            rebalance_cost=rebalance_cost,
        )
        model = SB3PPO("MlpPolicy", train_env, verbose=0, seed=seed)
        model.learn(total_timesteps=ppo_timesteps)

        # Roll out on test window (out-of-sample)
        eval_prices = test_prices if test_prices is not None else prices
        eval_returns = test_returns if test_returns is not None else returns
        eval_tensors = build_market_tensors(eval_prices, eval_returns)
        eval_env = NoRegimeEnv(eval_tensors, rebalance_cost=rebalance_cost)
        n_assets = eval_tensors["n_assets"]

        obs, _ = eval_env.reset()
        equity_vals = [1.0]
        weight_rows = []
        dates = eval_returns.index[eval_env.warmup:]

        done = False
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, _, info = eval_env.step(action)
            w = info.get("weights", np.ones(n_assets + 1) / (n_assets + 1))
            port_ret = info.get("portfolio_return", 0.0)
            equity_vals.append(equity_vals[-1] * (1.0 + port_ret))
            weight_rows.append(w[:n_assets])

        n_pts = min(len(dates), len(equity_vals) - 1)
        equity_series = pd.Series(
            equity_vals[1 : n_pts + 1],
            index=dates[:n_pts],
        )
        weights_df = pd.DataFrame(
            weight_rows[:n_pts],
            index=dates[:n_pts],
            columns=eval_returns.columns,
        )
        return {
            "equity": equity_series,
            "weights": weights_df,
            "turnover": _mean_turnover(weights_df),
        }

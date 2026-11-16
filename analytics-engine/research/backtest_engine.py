"""
backtest_engine.py — Walk-forward backtesting framework.

Walk-forward logic:
  - Divide full data into N folds of (train_years + test_years)
  - For each fold:
      1. Train each strategy on the training window
      2. Evaluate on the out-of-sample test window
      3. Collect equity curves and metrics

No look-ahead bias: test data is never seen during training.

Main entry point:
    engine = WalkForwardBacktester(prices, returns, config)
    results = engine.run(strategies)
    # results: {strategy_name: {'equity': pd.Series, 'metrics': dict, ...}}
"""

import sys
import os
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass, field

_engine_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _engine_root not in sys.path:
    sys.path.insert(0, _engine_root)

from research.metrics import compute_metrics, metrics_table

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Configuration for the walk-forward backtest."""
    train_years: float = 3.0          # years of data used for training each fold
    test_years: float = 1.0           # years of out-of-sample test per fold
    n_folds: int = 3                  # number of walk-forward folds
    rf_annual: float = 0.06           # risk-free rate for Sharpe/Sortino
    ppo_timesteps: int = 200_000      # PPO training steps per fold
    rebalance_cost: float = 0.001     # transaction cost (0.1%)
    seed: int = 42
    results_dir: str = "research/results"
    price_file: Optional[str] = None

    # Asset universe
    tickers: List[str] = field(default_factory=lambda: [
        # Indian large-caps (NSE)
        "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
        # US diversified ETFs
        "SPY", "QQQ", "GLD", "TLT", "EEM",
    ])
    start_date: str = "2018-01-01"
    end_date: str = "2024-12-31"


class WalkForwardBacktester:
    """
    Walk-forward backtesting engine.

    Usage:
        from research.backtest_engine import WalkForwardBacktester, BacktestConfig
        from research.baselines import EqualWeight, BuyAndHold, MarkowitzMVO, MarkowitzMaxSharpe, PPONoRegime

        config = BacktestConfig()
        engine = WalkForwardBacktester(prices, returns, config)
        results = engine.run([EqualWeight(), BuyAndHold(), MarkowitzMVO(), MarkowitzMaxSharpe(), PPONoRegime()])
    """

    def __init__(
        self,
        prices: pd.DataFrame,
        returns: pd.DataFrame,
        config: BacktestConfig,
    ):
        self.prices = prices
        self.returns = returns
        self.config = config
        os.makedirs(config.results_dir, exist_ok=True)

    def _get_folds(self) -> List[Dict]:
        """
        Compute train/test date windows for each fold.
        Returns list of {'train_start', 'train_end', 'test_start', 'test_end'}.
        """
        dates = self.returns.index
        trading_days = 252
        train_td = int(self.config.train_years * trading_days)
        test_td = int(self.config.test_years * trading_days)
        total_needed = train_td + test_td

        folds = []
        for fold_idx in range(self.config.n_folds):
            start_pos = fold_idx * test_td  # expanding window shifts by one test period
            end_train = start_pos + train_td
            end_test = end_train + test_td

            if end_test > len(dates):
                logger.warning(f"Fold {fold_idx+1}: not enough data, skipping.")
                break

            folds.append({
                "fold": fold_idx + 1,
                "train_start": dates[start_pos],
                "train_end": dates[end_train - 1],
                "test_start": dates[end_train],
                "test_end": dates[min(end_test - 1, len(dates) - 1)],
                "train_slice": slice(start_pos, end_train),
                "test_slice": slice(end_train, end_test),
            })

        logger.info(f"Created {len(folds)} walk-forward folds.")
        for f in folds:
            logger.info(
                f"  Fold {f['fold']}: "
                f"train [{f['train_start'].date()} → {f['train_end'].date()}] | "
                f"test  [{f['test_start'].date()} → {f['test_end'].date()}]"
            )
        return folds

    def run(self, strategies: list) -> Dict[str, Dict]:
        """
        Run all strategies across all walk-forward folds.

        Returns:
            Dict mapping strategy name → {
                'equity'  : full out-of-sample equity curve (concatenated folds),
                'metrics' : compute_metrics() output,
                'fold_equities': per-fold equity series list,
                'turnover': average turnover,
            }
        """
        folds = self._get_folds()
        accumulated: Dict[str, List[pd.Series]] = {s.name: [] for s in strategies}
        turnovers: Dict[str, List[float]] = {s.name: [] for s in strategies}

        for fold in folds:
            logger.info(f"\n{'='*60}")
            logger.info(f"FOLD {fold['fold']} — Test: {fold['test_start'].date()} → {fold['test_end'].date()}")

            train_prices = self.prices.iloc[fold["train_slice"]]
            train_returns = self.returns.iloc[fold["train_slice"]]
            test_prices = self.prices.iloc[fold["test_slice"]]
            test_returns = self.returns.iloc[fold["test_slice"]]

            for strategy in strategies:
                logger.info(f"  Running: {strategy.name}")
                try:
                    # Train on train window, evaluate on test window
                    result = strategy.run(
                        prices=train_prices,
                        returns=train_returns,
                        ppo_timesteps=self.config.ppo_timesteps,
                        rebalance_cost=self.config.rebalance_cost,
                        rf=self.config.rf_annual,
                        seed=self.config.seed,
                        # For inference-only strategies (baselines), we run on test data directly
                        test_prices=test_prices,
                        test_returns=test_returns,
                    )
                    # Normalize equity to start at 1.0 for each fold
                    eq = result["equity"]
                    if len(eq) > 0:
                        eq = eq / eq.iloc[0]
                    accumulated[strategy.name].append(eq)
                    turnovers[strategy.name].append(result.get("turnover", float("nan")))
                    logger.info(f"    → Fold Sharpe: {_quick_sharpe(eq, self.config.rf_annual):.3f}")
                except Exception as e:
                    logger.error(f"  FAILED {strategy.name} on fold {fold['fold']}: {e}", exc_info=True)

        # Concatenate folds and compute final metrics
        final_results = {}
        for strategy in strategies:
            fold_series = accumulated[strategy.name]
            if not fold_series:
                logger.warning(f"No results for {strategy.name}")
                continue

            # Chain equity curves: each fold starts where the previous ended
            chained = _chain_equity_curves(fold_series)
            mean_turnover = float(np.nanmean(turnovers[strategy.name]))
            metrics = compute_metrics(chained, rf_annual=self.config.rf_annual, name=strategy.name)
            metrics["turnover"] = round(mean_turnover, 4)

            final_results[strategy.name] = {
                "equity": chained,
                "metrics": metrics,
                "fold_equities": fold_series,
                "turnover": mean_turnover,
            }

        self._save_results(final_results)
        return final_results

    def _save_results(self, results: Dict):
        """Save equity curves and metrics table to CSV."""
        # Equity curves
        equity_df = pd.DataFrame({name: r["equity"] for name, r in results.items()})
        equity_path = os.path.join(self.config.results_dir, "equity_curves.csv")
        equity_df.to_csv(equity_path)
        logger.info(f"Equity curves saved → {equity_path}")

        # Metrics table
        metrics_list = [r["metrics"] for r in results.values()]
        df = metrics_table(metrics_list)
        metrics_path = os.path.join(self.config.results_dir, "metrics_table.csv")
        df.to_csv(metrics_path)
        logger.info(f"Metrics table saved → {metrics_path}")

        # LaTeX table for paper
        latex = df.to_latex(
            float_format="%.2f",
            caption="Out-of-sample performance comparison across strategies (3-fold walk-forward backtest).",
            label="tab:results",
            escape=True,
        )
        latex_path = os.path.join(self.config.results_dir, "table_results.tex")
        with open(latex_path, "w", encoding="utf-8") as f:
            f.write(latex)
        logger.info(f"LaTeX table saved → {latex_path}")

        return equity_path, metrics_path


# ---------------------------------------------------------------------------
# Regime-Aware PPO strategy (the proposed method)
# ---------------------------------------------------------------------------

class PPORegimeAware:
    """
    The proposed method: PPO with full regime-aware state (HMM one-hot included).
    Train on training window, roll out on test window.
    """
    name = "PPO-Regime (Ours)"

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
        from stable_baselines3 import PPO as SB3PPO

        # --- Train on training data ---
        train_tensors = build_market_tensors(prices, returns)
        train_env = PortfolioRLEnv(train_tensors, rebalance_cost=rebalance_cost)
        model = SB3PPO("MlpPolicy", train_env, verbose=0, seed=seed)
        model.learn(total_timesteps=ppo_timesteps)

        # --- Evaluate on test data (out-of-sample) ---
        eval_prices = test_prices if test_prices is not None else prices
        eval_returns = test_returns if test_returns is not None else returns
        eval_tensors = build_market_tensors(eval_prices, eval_returns)
        eval_env = PortfolioRLEnv(eval_tensors, rebalance_cost=rebalance_cost)

        n_assets = eval_tensors["n_assets"]
        obs, _ = eval_env.reset()
        equity_vals = [1.0]
        weight_rows = []
        dates = eval_returns.index[eval_env.warmup :]

        done = False
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, _, info = eval_env.step(action)
            port_ret = info.get("portfolio_return", 0.0)
            equity_vals.append(equity_vals[-1] * (1.0 + port_ret))
            weight_rows.append(info.get("weights", np.ones(n_assets + 1) / (n_assets + 1))[:n_assets])

        n_pts = min(len(dates), len(equity_vals) - 1)
        equity_series = pd.Series(equity_vals[1 : n_pts + 1], index=dates[:n_pts])
        weights_df = pd.DataFrame(
            weight_rows[:n_pts],
            index=dates[:n_pts],
            columns=eval_returns.columns,
        )
        from research.baselines import _mean_turnover
        return {
            "equity": equity_series,
            "weights": weights_df,
            "turnover": _mean_turnover(weights_df),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _quick_sharpe(equity: pd.Series, rf_annual: float = 0.06) -> float:
    """Fast Sharpe for logging."""
    if len(equity) < 2:
        return float("nan")
    r = equity.pct_change().dropna()
    rf_d = (1 + rf_annual) ** (1 / 252) - 1
    excess = r - rf_d
    return float((excess.mean() / (excess.std() + 1e-12)) * 252 ** 0.5)


def _chain_equity_curves(series_list: List[pd.Series]) -> pd.Series:
    """
    Chain multiple equity curves end-to-end.
    Each fold starts at 1.0; chaining multiplies by the ending value of the previous fold.
    """
    if not series_list:
        return pd.Series(dtype=float)
    chained = series_list[0].copy()
    for s in series_list[1:]:
        if len(s) == 0:
            continue
        scale = chained.iloc[-1]
        s_scaled = s * scale
        # Only take points strictly after previous fold to prevent duplicate timestamps
        s_scaled = s_scaled.loc[s_scaled.index > chained.index[-1]]
        if len(s_scaled) > 0:
            chained = pd.concat([chained, s_scaled])
    # Ensure index has no duplicate labels
    chained = chained[~chained.index.duplicated(keep="last")]
    return chained


def load_universe_data(config: BacktestConfig) -> tuple:
    """
    Download and align price/return data for the configured universe.
    Handles mixed Indian (.NS) and US tickers, with support for local pre-cached files.
    Returns (prices, returns) as aligned DataFrames.
    """
    prices = None

    # Check explicit price file first
    if config.price_file and os.path.exists(config.price_file):
        logger.info(f"Loading local price dataset from: {config.price_file}")
        prices = pd.read_csv(config.price_file, index_col=0, parse_dates=True)
    elif not config.price_file:
        # Check standard local dataset paths before network download
        candidates = [
            "research/regime_data_v1/prices.csv",
            os.path.join(_engine_root, "research", "regime_data_v1", "prices.csv"),
            "research/regime_results/prices.csv",
            os.path.join(_engine_root, "research", "regime_results", "prices.csv"),
        ]
        for cand in candidates:
            if os.path.exists(cand):
                try:
                    cached_df = pd.read_csv(cand, index_col=0, parse_dates=True)
                    overlap = [t for t in config.tickers if t in cached_df.columns]
                    if len(overlap) >= 3 and len(overlap) == len(config.tickers):
                        logger.info(f"Using pre-cached dataset from {cand} for {overlap}")
                        prices = cached_df[overlap]
                        break
                except Exception:
                    pass

    # If not loaded from local cache, attempt download
    if prices is None:
        import yfinance as yf
        logger.info(f"Downloading data for {len(config.tickers)} tickers: {config.tickers}")
        try:
            raw = yf.download(
                config.tickers,
                start=config.start_date,
                end=config.end_date,
                auto_adjust=True,
                progress=False,
            )
            if isinstance(raw.columns, pd.MultiIndex):
                prices = raw["Close"]
            else:
                prices = raw[["Close"]]
        except Exception as dl_err:
            logger.warning(f"Network download failed: {dl_err}. Checking fallback local data...")
            cand = os.path.join(_engine_root, "research", "regime_data_v1", "prices.csv")
            if os.path.exists(cand):
                cached_df = pd.read_csv(cand, index_col=0, parse_dates=True)
                overlap = [t for t in config.tickers if t in cached_df.columns]
                if not overlap:
                    overlap = list(cached_df.columns)
                logger.info(f"Fallback to local dataset ({cand}) with {overlap}")
                prices = cached_df[overlap]
            else:
                raise

    # Drop tickers with more than 20% missing
    missing_frac = prices.isna().mean()
    keep = missing_frac[missing_frac < 0.20].index.tolist()
    dropped = [t for t in prices.columns if t not in keep]
    if dropped:
        logger.warning(f"Dropped tickers (>20% missing): {dropped}")
    prices = prices[keep]

    # Filter dates if within bounds
    if config.start_date:
        prices = prices.loc[prices.index >= config.start_date]
    if config.end_date:
        prices = prices.loc[prices.index <= config.end_date]

    # Forward-fill then drop rows with any remaining NaN
    prices = prices.ffill().dropna()
    returns = prices.pct_change(fill_method=None).dropna()
    prices = prices.loc[returns.index]

    logger.info(f"Universe: {list(prices.columns)} | Period: {prices.index[0].date()} → {prices.index[-1].date()} | {len(prices)} days")
    return prices, returns

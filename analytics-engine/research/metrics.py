"""
metrics.py — Financial performance metrics for the research paper.

All metrics accept a pd.Series of daily equity values (starting at 1.0).
Example:
    equity = pd.Series([1.0, 1.01, 1.005, ...], index=date_index)
    m = compute_metrics(equity, rf_annual=0.06)
"""

import numpy as np
import pandas as pd
from typing import Dict


TRADING_DAYS = 252


def compute_metrics(
    equity: pd.Series,
    rf_annual: float = 0.06,
    name: str = "Strategy",
) -> Dict[str, float]:
    """
    Compute all paper metrics from a daily equity curve.

    Args:
        equity      : pd.Series of portfolio value (starts at 1.0), daily frequency.
        rf_annual   : Annual risk-free rate (default 6% for India).
        name        : Strategy label.

    Returns:
        Dict with all metrics rounded to 4 decimal places.
    """
    equity = equity.dropna()
    if len(equity) < 2:
        return _empty_metrics(name)

    daily_returns = equity.pct_change().dropna()

    # --- Core metrics ----------------------------------------------------------
    n_days = len(daily_returns)
    n_years = n_days / TRADING_DAYS

    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    cagr = float((equity.iloc[-1] / equity.iloc[0]) ** (1.0 / max(n_years, 1e-6)) - 1.0)

    ann_vol = float(daily_returns.std() * np.sqrt(TRADING_DAYS))
    rf_daily = (1.0 + rf_annual) ** (1.0 / TRADING_DAYS) - 1.0

    excess = daily_returns - rf_daily
    sharpe = float((excess.mean() / (daily_returns.std() + 1e-12)) * np.sqrt(TRADING_DAYS))

    # --- Sortino (downside deviation) ------------------------------------------
    downside = daily_returns[daily_returns < rf_daily]
    downside_std = float(downside.std() * np.sqrt(TRADING_DAYS)) if len(downside) > 1 else 1e-6
    sortino = float(((cagr - rf_annual) / (downside_std + 1e-12)))

    # --- Max Drawdown ----------------------------------------------------------
    rolling_max = equity.cummax()
    drawdown = (equity - rolling_max) / (rolling_max + 1e-12)
    max_dd = float(drawdown.min())

    # --- Calmar ----------------------------------------------------------------
    calmar = float(cagr / (abs(max_dd) + 1e-12))

    # --- Win rate (% of months with positive return) ---------------------------
    monthly = equity.resample("ME").last().pct_change().dropna()
    win_rate = float((monthly > 0).mean()) if len(monthly) > 0 else 0.0

    # --- Value at Risk (95%, parametric) --------------------------------------
    var_95 = float(daily_returns.mean() - 1.645 * daily_returns.std())

    # --- Conditional VaR (CVaR / Expected Shortfall) --------------------------
    threshold = daily_returns.quantile(0.05)
    cvar_95 = float(daily_returns[daily_returns <= threshold].mean())

    # --- Average daily turnover (if tracked; else NaN) ------------------------
    turnover = float("nan")  # filled by backtest engine per-strategy

    return {
        "name": name,
        "total_return": round(total_return, 4),
        "cagr": round(cagr, 4),
        "ann_vol": round(ann_vol, 4),
        "sharpe": round(sharpe, 4),
        "sortino": round(sortino, 4),
        "calmar": round(calmar, 4),
        "max_drawdown": round(max_dd, 4),
        "win_rate": round(win_rate, 4),
        "var_95": round(var_95, 4),
        "cvar_95": round(cvar_95, 4),
        "turnover": turnover,
        "n_days": n_days,
    }


def _empty_metrics(name: str) -> Dict[str, float]:
    return {
        "name": name,
        "total_return": float("nan"),
        "cagr": float("nan"),
        "ann_vol": float("nan"),
        "sharpe": float("nan"),
        "sortino": float("nan"),
        "calmar": float("nan"),
        "max_drawdown": float("nan"),
        "win_rate": float("nan"),
        "var_95": float("nan"),
        "cvar_95": float("nan"),
        "turnover": float("nan"),
        "n_days": 0,
    }


def metrics_table(results: list) -> pd.DataFrame:
    """
    Build a formatted metrics DataFrame from a list of compute_metrics() dicts.
    Suitable for direct use in a paper table (LaTeX export via df.to_latex()).
    """
    df = pd.DataFrame(results).set_index("name")
    # Format as percentages where appropriate
    pct_cols = ["total_return", "cagr", "ann_vol", "max_drawdown", "win_rate", "var_95", "cvar_95"]
    for col in pct_cols:
        if col in df.columns:
            df[col] = (df[col] * 100).round(2)
    ratio_cols = ["sharpe", "sortino", "calmar"]
    for col in ratio_cols:
        if col in df.columns:
            df[col] = df[col].round(3)
    return df


def rolling_sharpe(equity: pd.Series, window: int = 63, rf_annual: float = 0.06) -> pd.Series:
    """
    Compute rolling Sharpe ratio (63-day ≈ 1 quarter) for the equity curve.
    Used for Figure 2 in the paper.
    """
    daily_returns = equity.pct_change().dropna()
    rf_daily = (1.0 + rf_annual) ** (1.0 / TRADING_DAYS) - 1.0
    excess = daily_returns - rf_daily
    roll_mean = excess.rolling(window, min_periods=21).mean()
    roll_std = excess.rolling(window, min_periods=21).std()
    return (roll_mean / (roll_std + 1e-12)) * np.sqrt(TRADING_DAYS)


def drawdown_series(equity: pd.Series) -> pd.Series:
    """Return the drawdown series as a fraction (negative values)."""
    rolling_max = equity.cummax()
    return (equity - rolling_max) / (rolling_max + 1e-12)

"""
Risk metrics engine.

Computes both per-asset risk statistics and canonical portfolio-level risk metrics
using standardized financial formulas.
"""
from typing import Optional, Dict, Any, List
import numpy as np
import pandas as pd

from services.financial_metrics import (
    canonical_portfolio_returns,
    compute_annualized_volatility,
    compute_var_cvar,
    compute_wealth_index_drawdown,
    compute_sharpe_ratio,
    compute_sortino_ratio,
    compute_cumulative_return,
    compute_annualized_return,
    DEFAULT_RISK_FREE_RATE,
)


def compute_volatility(returns: pd.DataFrame) -> pd.Series:
    """
    Annualized sample volatility for each stock (ddof=1).
    Higher = riskier.
    """
    daily_vol = returns.std(ddof=1)
    annualized_vol = daily_vol * np.sqrt(252)
    return annualized_vol


def compute_var(returns: pd.DataFrame, confidence: float = 0.95) -> pd.Series:
    """
    Historical one-day return quantile at (1 - confidence).
    Returns a signed return (typically negative), not a positive loss amount.
    """
    return returns.quantile(1.0 - confidence)


def compute_cvar(returns: pd.DataFrame, confidence: float = 0.95) -> pd.Series:
    """
    Mean historical one-day return at or below the VaR quantile (signed).
    """
    var = compute_var(returns, confidence)
    cvar_dict = {}
    for col in returns.columns:
        col_var = var[col]
        tail = returns[col][returns[col] <= col_var]
        cvar_dict[col] = float(tail.mean()) if len(tail) > 0 else float(col_var)
    return pd.Series(cvar_dict)


def compute_drawdown(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Drawdown — how far each stock dropped from its peak.
    Guaranteed <= 0.0.
    """
    if prices.empty:
        return prices
    rolling_max = prices.cummax()
    drawdown = (prices - rolling_max) / rolling_max
    return drawdown.clip(upper=0.0)


def compute_max_drawdown(prices: pd.DataFrame) -> pd.Series:
    """
    Largest peak-to-trough decline within the supplied price window.
    """
    drawdown = compute_drawdown(prices)
    return drawdown.min().clip(upper=0.0)


def compute_portfolio_risk_metrics(
    returns: pd.DataFrame,
    weights: List[float] | np.ndarray,
    tickers: List[str],
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
    confidence: float = 0.95,
) -> Dict[str, Any]:
    """
    Compute canonical portfolio-level risk metrics using the single
    daily portfolio return series r_p,t = sum(w_i * r_i,t).
    """
    port_ret = canonical_portfolio_returns(returns, weights, tickers)
    if port_ret.empty or len(port_ret) < 2:
        return {
            "portfolio_volatility": None,
            "portfolio_var_95": None,
            "portfolio_cvar_95": None,
            "portfolio_max_drawdown": None,
            "portfolio_sharpe": None,
            "portfolio_sortino": None,
            "portfolio_cumulative_return": None,
            "portfolio_annualized_return": None,
            "drawdown_series": pd.Series(dtype=float),
            "portfolio_returns": pd.Series(dtype=float),
            "status": "UNAVAILABLE",
        }

    vol = compute_annualized_volatility(port_ret, ddof=1)
    var_val, cvar_val = compute_var_cvar(port_ret, confidence_level=confidence)
    max_dd, dd_series = compute_wealth_index_drawdown(port_ret)
    sharpe = compute_sharpe_ratio(port_ret, risk_free_rate_annual=risk_free_rate)
    sortino = compute_sortino_ratio(port_ret, risk_free_rate_annual=risk_free_rate)
    cum_ret = compute_cumulative_return(port_ret)
    ann_ret = compute_annualized_return(port_ret)

    return {
        "portfolio_volatility": round(vol, 4) if vol is not None else None,
        "portfolio_var_95": round(var_val, 4) if var_val is not None else None,
        "portfolio_cvar_95": round(cvar_val, 4) if cvar_val is not None else None,
        "portfolio_max_drawdown": round(max_dd, 4) if max_dd is not None else None,
        "portfolio_sharpe": round(sharpe, 4) if sharpe is not None else None,
        "portfolio_sortino": round(sortino, 4) if sortino is not None else None,
        "portfolio_cumulative_return": round(cum_ret, 4) if cum_ret is not None else None,
        "portfolio_annualized_return": round(ann_ret, 4) if ann_ret is not None else None,
        "drawdown_series": dd_series,
        "portfolio_returns": port_ret,
        "status": "SUCCESS",
    }


def get_risk_summary(
    prices: pd.DataFrame,
    returns: pd.DataFrame,
    weights: Optional[List[float]] = None,
    tickers: Optional[List[str]] = None,
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
) -> dict:
    """
    Master function — computes per-stock risk summary and, when weights/tickers
    are supplied, canonical portfolio-level risk metrics.
    """
    volatility = compute_volatility(returns)
    var_95 = compute_var(returns, confidence=0.95)
    cvar_95 = compute_cvar(returns, confidence=0.95)
    max_drawdown = compute_max_drawdown(prices)

    summary = pd.DataFrame({
        "Volatility (Annual)": volatility,
        "VaR (95%)":           var_95,
        "CVaR (95%)":          cvar_95,
        "Max Drawdown":        max_drawdown
    })

    port_risk = None
    drawdown_series = compute_drawdown(prices)

    if weights is not None and tickers is not None:
        try:
            port_risk = compute_portfolio_risk_metrics(
                returns=returns,
                weights=weights,
                tickers=tickers,
                risk_free_rate=risk_free_rate,
            )
            # Use portfolio drawdown series if available
            if "drawdown_series" in port_risk and not port_risk["drawdown_series"].empty:
                drawdown_series = port_risk["drawdown_series"]
        except Exception:
            port_risk = None

    return {
        "summary": summary,
        "drawdown_series": drawdown_series,
        "portfolio_risk": port_risk,
    }

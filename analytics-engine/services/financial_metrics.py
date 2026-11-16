"""
Canonical financial metrics engine.

Authoritative module for portfolio-level returns, volatility, Sharpe, Sortino,
Beta, Alpha, wealth-index drawdowns, and security return contributions.

Conventions:
- Daily return: Simple percentage return r_t = P_t / P_(t-1) - 1.
- Portfolio daily return: r_p,t = sum_i(w_i * r_i,t) using canonical market weights.
- Cumulative return: Geometric compounding prod(1 + r_t) - 1.
- Annualized return: Geometric CAGR (1 + r_cum)^(252 / N) - 1.
- Volatility: Sample standard deviation with ddof=1 annualized by sqrt(252).
- Sharpe ratio: Daily excess return over daily risk-free rate annualized:
    mean(r_p,t - r_f,daily) / std(r_p,t - r_f,daily, ddof=1) * sqrt(252).
- Sortino ratio: Downside deviation relative to MAR (daily risk-free rate):
    MAR = (1 + r_f_annual)^(1/252) - 1
    downside_dev = sqrt(mean(min(r_t - MAR, 0)^2)) * sqrt(252)
    Sortino = (mean(r_t - MAR) * 252) / downside_dev.
- Beta: Cov(r_p, r_b) / Var(r_b) using sample statistics with ddof=1 on aligned dates.
- Alpha: Annualized realized Jensen's Alpha:
    alpha = R_p,ann - [r_f_annual + beta * (R_b,ann - r_f_annual)].
- Drawdown: Wealth index initialized at wealth_0 = 1.0, tracking peak-to-trough.
- Security return contribution: daily c_i,t = w_i * r_i,t.
"""
from typing import Optional, Tuple, Dict, Any, List
import numpy as np
import pandas as pd

WEIGHT_SUM_TOLERANCE = 1e-5
TRADING_DAYS_PER_YEAR = 252
DEFAULT_RISK_FREE_RATE = 0.02


def canonical_portfolio_returns(
    returns: pd.DataFrame,
    weights: List[float] | np.ndarray,
    tickers: List[str],
) -> pd.Series:
    """
    Construct canonical daily portfolio return series from aligned asset returns and weights:
        r_p,t = sum(w_i * r_i,t)
    Weights must match the order and names of supplied tickers.
    """
    if returns is None or returns.empty:
        return pd.Series(dtype=float)

    weights_arr = np.asarray(weights, dtype=float)
    if len(weights_arr) != len(tickers):
        raise ValueError(f"Weight count ({len(weights_arr)}) does not match ticker count ({len(tickers)})")

    weight_sum = float(np.sum(weights_arr))
    if abs(weight_sum - 1.0) > WEIGHT_SUM_TOLERANCE:
        raise ValueError(f"Weights must sum to 1.0 within tolerance {WEIGHT_SUM_TOLERANCE} (current sum: {weight_sum})")

    # Safe normalization for tiny floating-point drift
    normalized_weights = weights_arr / weight_sum

    # Align columns by ticker (case-insensitive)
    col_map = {str(c).upper().strip(): c for c in returns.columns}
    aligned_cols = []
    aligned_weights = []

    for t, w in zip(tickers, normalized_weights):
        clean_t = str(t).upper().strip()
        if clean_t in col_map:
            aligned_cols.append(col_map[clean_t])
            aligned_weights.append(w)
        else:
            raise ValueError(f"Ticker '{t}' not found in returns DataFrame columns: {list(returns.columns)}")

    sub_returns = returns[aligned_cols].dropna()
    if sub_returns.empty:
        return pd.Series(dtype=float)

    w_vec = np.asarray(aligned_weights, dtype=float)
    port_ret = sub_returns.values @ w_vec
    return pd.Series(port_ret, index=sub_returns.index, name="portfolio_return")


def compute_cumulative_return(returns: pd.Series) -> Optional[float]:
    """
    Geometric cumulative return: prod(1 + r_t) - 1.
    """
    s = pd.Series(returns).dropna()
    if len(s) == 0:
        return None
    cum = float(np.prod(1.0 + s.values) - 1.0)
    return cum if np.isfinite(cum) else None


def compute_annualized_return(
    returns: pd.Series,
    trading_days: int = TRADING_DAYS_PER_YEAR,
) -> Optional[float]:
    """
    Geometric annualized return (CAGR):
        (1 + cum_return) ** (trading_days / N) - 1
    Requires at least 2 observations.
    """
    s = pd.Series(returns).dropna()
    n = len(s)
    if n < 2:
        return None

    cum = compute_cumulative_return(s)
    if cum is None:
        return None

    gross = 1.0 + cum
    if gross <= 0:
        return -1.0  # Complete loss

    ann = float(gross ** (trading_days / n) - 1.0)
    return ann if np.isfinite(ann) else None


def compute_annualized_volatility(
    returns: pd.Series,
    ddof: int = 1,
    trading_days: int = TRADING_DAYS_PER_YEAR,
) -> Optional[float]:
    """
    Annualized sample standard deviation:
        std(returns, ddof=1) * sqrt(trading_days)
    """
    s = pd.Series(returns).dropna()
    if len(s) < 2:
        return None

    daily_vol = float(np.std(s.values, ddof=ddof))
    ann_vol = daily_vol * np.sqrt(trading_days)
    return float(ann_vol) if np.isfinite(ann_vol) else None


def compute_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate_annual: float = DEFAULT_RISK_FREE_RATE,
    trading_days: int = TRADING_DAYS_PER_YEAR,
) -> Optional[float]:
    """
    Standardized daily excess-return Sharpe ratio:
        daily_rf = (1 + annual_rf) ** (1 / trading_days) - 1
        excess = returns - daily_rf
        Sharpe = mean(excess) / std(excess, ddof=1) * sqrt(trading_days)
    Returns None if volatility is zero or data is insufficient.
    """
    s = pd.Series(returns).dropna()
    if len(s) < 2:
        return None

    daily_rf = (1.0 + risk_free_rate_annual) ** (1.0 / trading_days) - 1.0
    excess = s.values - daily_rf

    vol = float(np.std(excess, ddof=1))
    if vol <= 1e-12 or not np.isfinite(vol):
        return None

    mean_excess = float(np.mean(excess))
    sharpe = (mean_excess / vol) * np.sqrt(trading_days)
    return float(sharpe) if np.isfinite(sharpe) else None


def compute_sortino_ratio(
    returns: pd.Series,
    risk_free_rate_annual: float = DEFAULT_RISK_FREE_RATE,
    trading_days: int = TRADING_DAYS_PER_YEAR,
) -> Optional[float]:
    """
    Standardized Sortino ratio relative to MAR (daily risk-free rate):
        daily_mar = (1 + annual_rf) ** (1 / trading_days) - 1
        excess = r_t - daily_mar
        downside_diff = min(r_t - daily_mar, 0)
        downside_dev = sqrt(mean(downside_diff ** 2)) * sqrt(trading_days)
        Sortino = (mean(excess) * trading_days) / downside_dev
    Returns None if downside deviation is zero or data is insufficient.
    """
    s = pd.Series(returns).dropna()
    if len(s) < 2:
        return None

    daily_mar = (1.0 + risk_free_rate_annual) ** (1.0 / trading_days) - 1.0
    excess = s.values - daily_mar

    downside = np.minimum(excess, 0.0)
    mean_sq_downside = float(np.mean(downside ** 2))
    if mean_sq_downside <= 1e-14:
        return None  # No negative excess returns / zero downside risk

    downside_dev = np.sqrt(mean_sq_downside) * np.sqrt(trading_days)
    if downside_dev <= 1e-12 or not np.isfinite(downside_dev):
        return None

    annualized_excess = float(np.mean(excess)) * trading_days
    sortino = annualized_excess / downside_dev
    return float(sortino) if np.isfinite(sortino) else None


def compute_wealth_index_drawdown(returns: pd.Series) -> Tuple[Optional[float], pd.Series]:
    """
    Wealth-index maximum drawdown with explicit baseline wealth_0 = 1.0:
        wealth_0 = 1.0
        wealth_t = wealth_(t-1) * (1 + r_t)
        running_peak_t = max(wealth_0, ..., wealth_t)
        drawdown_t = wealth_t / running_peak_t - 1.0
        max_drawdown = min(drawdown_t) <= 0.0
    Returns:
        (max_drawdown, drawdown_series)
    """
    s = pd.Series(returns).dropna()
    if len(s) == 0:
        return None, pd.Series(dtype=float)

    # Reconstruct wealth index starting with baseline 1.0
    r_vals = s.values
    wealth = np.empty(len(r_vals) + 1, dtype=float)
    wealth[0] = 1.0
    np.multiply.accumulate(1.0 + r_vals, out=wealth[1:])

    # Running peak includes wealth_0 = 1.0
    running_peak = np.maximum.accumulate(wealth)
    drawdowns_full = (wealth / running_peak) - 1.0

    # Drawdown series for the observation dates (t=1..T)
    drawdown_series = pd.Series(drawdowns_full[1:], index=s.index, name="drawdown")
    max_dd = float(np.min(drawdown_series.values))

    # Drawdown must be <= 0.0
    max_dd = min(0.0, max_dd)
    return (max_dd if np.isfinite(max_dd) else None), drawdown_series


def compute_beta_and_alpha(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
    risk_free_rate_annual: float = DEFAULT_RISK_FREE_RATE,
    trading_days: int = TRADING_DAYS_PER_YEAR,
) -> Dict[str, Any]:
    """
    Calculate Beta and realized Jensen's Alpha on aligned dates:
        common_dates = intersection(dates(p), dates(b))
        Beta = Cov(r_p, r_b, ddof=1) / Var(r_b, ddof=1)
        Alpha = R_p,ann - [r_f + Beta * (R_b,ann - r_f)]
    Uses identical sample degrees of freedom (ddof=1) for covariance and variance.
    """
    p = pd.Series(portfolio_returns).dropna()
    b = pd.Series(benchmark_returns).dropna()

    common_idx = p.index.intersection(b.index)
    if len(common_idx) < 2:
        return {
            "beta": None,
            "alpha": None,
            "aligned_start": None,
            "aligned_end": None,
            "observation_count": len(common_idx),
            "status": "UNAVAILABLE",
            "reason": "Insufficient overlapping observations between portfolio and benchmark",
        }

    p_aligned = p.loc[common_idx]
    b_aligned = b.loc[common_idx]

    var_b = float(np.var(b_aligned.values, ddof=1))
    if var_b <= 1e-12 or not np.isfinite(var_b):
        return {
            "beta": None,
            "alpha": None,
            "aligned_start": str(common_idx[0].date()) if hasattr(common_idx[0], "date") else str(common_idx[0]),
            "aligned_end": str(common_idx[-1].date()) if hasattr(common_idx[-1], "date") else str(common_idx[-1]),
            "observation_count": len(common_idx),
            "status": "UNAVAILABLE",
            "reason": "Benchmark variance is effectively zero",
        }

    cov_matrix = np.cov(p_aligned.values, b_aligned.values, ddof=1)
    cov_pb = float(cov_matrix[0, 1])
    beta = cov_pb / var_b

    p_ann = compute_annualized_return(p_aligned, trading_days=trading_days)
    b_ann = compute_annualized_return(b_aligned, trading_days=trading_days)

    if p_ann is None or b_ann is None or not np.isfinite(beta):
        alpha = None
    else:
        # Annualized realized Jensen's Alpha
        alpha = float(p_ann - (risk_free_rate_annual + beta * (b_ann - risk_free_rate_annual)))

    aligned_start = str(common_idx[0].date()) if hasattr(common_idx[0], "date") else str(common_idx[0])
    aligned_end = str(common_idx[-1].date()) if hasattr(common_idx[-1], "date") else str(common_idx[-1])

    return {
        "beta": float(beta) if np.isfinite(beta) else None,
        "alpha": float(alpha) if alpha is not None and np.isfinite(alpha) else None,
        "aligned_start": aligned_start,
        "aligned_end": aligned_end,
        "observation_count": len(common_idx),
        "status": "SUCCESS",
        "reason": None,
    }


def compute_var_cvar(
    returns: pd.Series,
    confidence_level: float = 0.95,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Historical 1-day portfolio return VaR and CVaR at specified confidence level:
        VaR = quantile(1 - confidence_level) (signed return, typically negative)
        CVaR = mean(returns[returns <= VaR]) (signed return, typically negative)
    """
    s = pd.Series(returns).dropna()
    if len(s) < 2:
        return None, None

    q = (1.0 - confidence_level) * 100.0
    var = float(np.percentile(s.values, q))
    tail = s.values[s.values <= var]
    cvar = float(np.mean(tail)) if len(tail) > 0 else var

    return (var if np.isfinite(var) else None), (cvar if np.isfinite(cvar) else None)


def compute_security_contributions(
    returns: pd.DataFrame,
    weights: List[float] | np.ndarray,
    tickers: List[str],
) -> Dict[str, Any]:
    """
    Compute daily security return contributions:
        daily_contribution_i,t = weight_i * asset_return_i,t
    Accumulated arithmetic contribution:
        total_contribution_i = sum_t(weight_i * asset_return_i,t)
    Reconciliation:
        sum_i(total_contribution_i) = sum_t(r_p,t) (arithmetic sum of portfolio daily returns)
    Also reports geometric portfolio cumulative return and the compounding residual:
        compounding_residual = cumulative_geometric_return - sum(total_contributions)
    """
    weights_arr = np.asarray(weights, dtype=float)
    weight_sum = float(np.sum(weights_arr))
    if abs(weight_sum - 1.0) > WEIGHT_SUM_TOLERANCE:
        raise ValueError(f"Weights must sum to 1.0 within tolerance {WEIGHT_SUM_TOLERANCE}")

    weights_arr = weights_arr / weight_sum
    col_map = {str(c).upper().strip(): c for c in returns.columns}

    matched_tickers = []
    matched_weights = []
    matched_cols = []
    for t, w in zip(tickers, weights_arr):
        clean_t = str(t).upper().strip()
        if clean_t in col_map:
            matched_tickers.append(clean_t)
            matched_weights.append(w)
            matched_cols.append(col_map[clean_t])

    if not matched_cols:
        return {"error": "No matching tickers found in returns"}

    sub_returns = returns[matched_cols].dropna()
    if sub_returns.empty:
        return {"error": "No overlapping return observations"}

    w_vec = np.asarray(matched_weights, dtype=float)
    daily_contribs = sub_returns.values * w_vec  # shape: (T, N)
    daily_port_return = daily_contribs.sum(axis=1)

    cum_geometric = float(np.prod(1.0 + daily_port_return) - 1.0)
    sum_arithmetic_port_return = float(np.sum(daily_port_return))

    total_contributions = daily_contribs.sum(axis=0)  # shape: (N,)

    security_results = []
    for i, t in enumerate(matched_tickers):
        c_i = float(total_contributions[i])
        w_i = float(matched_weights[i])
        asset_ret_arithmetic = float(sub_returns.iloc[:, i].sum())
        asset_ret_compound = float(np.prod(1.0 + sub_returns.iloc[:, i].values) - 1.0)
        security_results.append({
            "ticker": t,
            "weight": round(w_i, 6),
            "compound_return": round(asset_ret_compound, 4),
            "arithmetic_return": round(asset_ret_arithmetic, 4),
            "return_contribution": round(c_i, 6),
            "contribution_pct_of_sum": round((c_i / sum_arithmetic_port_return * 100.0), 2) if sum_arithmetic_port_return != 0 else 0.0,
        })

    sum_contributions = float(np.sum(total_contributions))
    compounding_residual = cum_geometric - sum_contributions

    return {
        "model": "daily_constant_weight_contribution",
        "methodology": "return_contribution",
        "observation_count": len(sub_returns),
        "cumulative_portfolio_return": round(cum_geometric, 6),
        "sum_of_daily_portfolio_returns": round(sum_arithmetic_port_return, 6),
        "sum_of_security_contributions": round(sum_contributions, 6),
        "compounding_residual": round(compounding_residual, 6),
        "reconciled": bool(abs(sum_contributions - sum_arithmetic_port_return) < 1e-9),
        "security_contributions": security_results,
    }

"""
Risk budgeting engine — decomposes portfolio-level risk into per-asset contributions.

Calculates marginal contribution to risk (MCR), component contribution to risk (CCR),
and percentage contribution to total portfolio risk (PCR).

All values are mathematically derived from the portfolio's return covariance matrix
and weight vector:
    σ_p = √(wᵀ Σ w)
    MCR_i = (Σ w)_i / σ_p
    CCR_i = w_i * MCR_i
    PCR_i = CCR_i / σ_p
    sum(CCR) = σ_p
    sum(PCR) = 1.0 (100%)
"""
from typing import List, Dict, Any
import numpy as np
import pandas as pd

from services.financial_metrics import WEIGHT_SUM_TOLERANCE, TRADING_DAYS_PER_YEAR


def compute_risk_budget(
    tickers: List[str],
    weights: List[float],
    returns: pd.DataFrame,
    portfolio_value: float = 100000,
    confidence_level: float = 0.95,
) -> dict:
    """
    Compute risk contribution analysis for the portfolio.
    """
    weights_arr = np.asarray(weights, dtype=float)
    if len(weights_arr) != len(tickers):
        return {"error": "Length of tickers and weights must match"}

    w_sum = float(np.sum(weights_arr))
    if abs(w_sum - 1.0) > WEIGHT_SUM_TOLERANCE:
        return {"error": f"Weights must sum to 1.0 within tolerance {WEIGHT_SUM_TOLERANCE} (current sum: {w_sum})"}

    normalized_weights = weights_arr / w_sum
    tickers_clean = [str(t).upper().strip() for t in tickers]

    # Align returns with tickers by name
    col_map = {str(c).upper().strip(): c for c in returns.columns}
    usable_cols = []
    usable_tickers = []
    usable_weights = []

    for t, w in zip(tickers_clean, normalized_weights):
        if t in col_map:
            usable_cols.append(col_map[t])
            usable_tickers.append(t)
            usable_weights.append(w)

    if len(usable_cols) == 0 or len(returns) < 2:
        return {"error": "Insufficient data or no matching tickers in returns"}

    usable_weights = np.asarray(usable_weights, dtype=float)
    # Re-normalize if any ticker was missing
    if len(usable_weights) != len(normalized_weights):
        usable_weights = usable_weights / np.sum(usable_weights)

    ret_aligned = returns[usable_cols].dropna()
    if len(ret_aligned) < 2:
        return {"error": "Insufficient overlapping returns after alignment"}

    # Covariance matrix (annualized, sample ddof=1)
    cov_matrix = ret_aligned.cov().values * TRADING_DAYS_PER_YEAR

    # Portfolio volatility (annualized)
    port_var = float(usable_weights @ cov_matrix @ usable_weights)
    port_vol = float(np.sqrt(port_var)) if port_var > 0 else 0.0

    if port_vol <= 1e-12:
        return {"error": "Portfolio volatility is effectively zero — cannot compute risk contributions"}

    # Marginal contribution to risk: d(σ_p)/d(w_i) = (Σw)_i / σ_p
    marginal = (cov_matrix @ usable_weights) / port_vol

    # Component contribution to risk: w_i * MCR_i
    component = usable_weights * marginal

    # Percentage contribution to risk: CCR_i / σ_p
    percentage = component / port_vol

    # Portfolio daily returns using aligned weights
    port_daily_returns = ret_aligned.values @ usable_weights
    var_threshold = float(np.percentile(port_daily_returns, (1.0 - confidence_level) * 100.0))
    tail_returns = port_daily_returns[port_daily_returns <= var_threshold]
    cvar = float(np.mean(tail_returns)) if len(tail_returns) > 0 else var_threshold

    risk_contributions = []
    for i, ticker in enumerate(usable_tickers):
        risk_contributions.append({
            "ticker": ticker,
            "weight": round(float(usable_weights[i]), 4),
            "marginal_contribution_to_risk": round(float(marginal[i]), 6),
            "component_contribution_to_risk": round(float(component[i]), 6),
            "percentage_contribution_to_risk": round(float(percentage[i] * 100.0), 2),
            "volatility": round(float(np.sqrt(cov_matrix[i, i])), 4),
            "value_at_risk": round(var_threshold, 4),
        })

    # Sort by risk contribution descending
    risk_contributions.sort(key=lambda x: -x["percentage_contribution_to_risk"])

    # Diversification ratio
    weighted_avg_vol = float(np.average(
        [np.sqrt(cov_matrix[i, i]) for i in range(len(usable_cols))],
        weights=usable_weights
    ))
    diversification_ratio = weighted_avg_vol / port_vol if port_vol > 0 else 0.0

    # Herfindahl-Hirschman Index for risk concentration
    pcr_values = percentage
    hhi = float(np.sum(pcr_values ** 2))

    sum_pcr = float(np.sum(percentage))
    sum_ccr = float(np.sum(component))

    return {
        "portfolio_volatility": round(port_vol, 4),
        "portfolio_variance": round(port_var, 6),
        "sum_of_component_risk": round(sum_ccr, 4),
        "sum_of_percentage_risk": round(sum_pcr * 100.0, 2),
        "risk_budget_reconciled": bool(abs(sum_pcr - 1.0) < 1e-4 and abs(sum_ccr - port_vol) < 1e-4),
        "portfolio_value": float(portfolio_value),
        "currency": None,  # Set by caller
        "confidence_level": confidence_level,
        "var_95": round(var_threshold, 4),
        "cvar_95": round(cvar, 4),
        "risk_horizon": "1 trading day",
        "diversification_ratio": round(diversification_ratio, 4),
        "herfindahl_index": round(hhi, 4),
        "risk_concentration": _interpret_hhi(hhi),
        "risk_contributions": risk_contributions,
    }


def _interpret_hhi(hhi: float) -> str:
    """Classify risk concentration level based on HHI."""
    if hhi > 0.25:
        return "highly_concentrated"
    elif hhi > 0.15:
        return "moderately_concentrated"
    elif hhi > 0.08:
        return "moderately_diversified"
    else:
        return "well_diversified"


def compute_correlation_matrix(tickers: List[str], returns: pd.DataFrame) -> dict:
    """Return the pairwise correlation matrix for the portfolio's tickers."""
    tickers_clean = [str(t).upper().strip() for t in tickers]
    col_map = {str(c).upper().strip(): c for c in returns.columns}
    usable_cols = [col_map[t] for t in tickers_clean if t in col_map]
    usable_tickers = [t for t in tickers_clean if t in col_map]

    if not usable_cols:
        return {"error": "No matching tickers in returns data"}

    corr = returns[usable_cols].dropna().corr()
    matrix = []
    for i, _ in enumerate(usable_tickers):
        row = []
        for j, _ in enumerate(usable_tickers):
            row.append(round(float(corr.iloc[i, j]), 4))
        matrix.append(row)

    return {
        "tickers": usable_tickers,
        "matrix": matrix,
    }

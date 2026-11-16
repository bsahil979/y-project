"""
Portfolio return attribution engine.

Computes security-level, sector-level, and asset-class-level return contribution
to portfolio performance using canonical daily constant-weight returns.

Methodology:
- Daily security contribution: c_i,t = weight_i * asset_return_i,t
- Cumulative security contribution: C_i = sum_t(c_i,t)
- Sum of contributions: sum_i(C_i) = sum_t(r_p,t)
- Geometric compounded portfolio return: R_p = prod(1 + r_p,t) - 1
- Compounding residual: R_p - sum_i(C_i)
"""
from typing import Optional, List, Dict, Any
import numpy as np
import pandas as pd
from services.portfolio_score import get_asset_category
from services.financial_metrics import WEIGHT_SUM_TOLERANCE, compute_cumulative_return


def compute_attribution(
    tickers: List[str],
    weights: List[float],
    prices: pd.DataFrame,
    portfolio_value: float = 100000,
    currency_symbol: str = "$",
) -> dict:
    """
    Compute portfolio return attribution across multiple dimensions using
    daily constant-weight security return contributions.
    """
    weights_arr = np.asarray(weights, dtype=float)
    if len(weights_arr) != len(tickers):
        return {"error": "Length of tickers and weights must match"}

    w_sum = float(np.sum(weights_arr))
    if abs(w_sum - 1.0) > WEIGHT_SUM_TOLERANCE:
        return {"error": f"Weights must sum to 1.0 (current sum: {w_sum})"}

    normalized_weights = weights_arr / w_sum
    tickers_clean = [str(t).upper().strip() for t in tickers]

    # Align prices with tickers
    col_map = {str(c).upper().strip(): c for c in prices.columns}
    usable_tickers = []
    usable_weights = []
    usable_cols = []

    for t, w in zip(tickers_clean, normalized_weights):
        if t in col_map:
            usable_tickers.append(t)
            usable_weights.append(w)
            usable_cols.append(col_map[t])

    if not usable_cols:
        return {"error": "No usable price data for any tickers"}

    usable_prices = prices[usable_cols].dropna()
    if len(usable_prices) < 2:
        return {"error": "Insufficient price history for return attribution"}

    # Daily returns
    daily_returns = usable_prices.pct_change().dropna()
    if daily_returns.empty:
        return {"error": "Insufficient return observations for return attribution"}

    w_vec = np.asarray(usable_weights, dtype=float)

    # Daily security contributions: c_i,t = w_i * r_i,t
    daily_contribs = daily_returns.values * w_vec  # (T, N)
    daily_port_return = daily_contribs.sum(axis=1)

    port_cum_return = compute_cumulative_return(pd.Series(daily_port_return, index=daily_returns.index))
    if port_cum_return is None:
        port_cum_return = 0.0

    sum_arithmetic_port_return = float(np.sum(daily_port_return))
    sec_contributions = daily_contribs.sum(axis=0)  # (N,)
    sum_contributions = float(np.sum(sec_contributions))
    compounding_residual = port_cum_return - sum_contributions

    # Asset compounded and arithmetic returns
    asset_compounded = (np.prod(1.0 + daily_returns.values, axis=0) - 1.0)
    asset_arithmetic = daily_returns.values.sum(axis=0)

    # Position values
    position_values = portfolio_value * w_vec
    position_returns = portfolio_value * sec_contributions

    # --- Security Contribution ---
    security_contrib = []
    for i, ticker in enumerate(usable_tickers):
        w = float(usable_weights[i])
        r_comp = float(asset_compounded[i])
        r_arith = float(asset_arithmetic[i])
        contrib = float(sec_contributions[i])
        security_contrib.append({
            "ticker": ticker,
            "weight": round(w, 4),
            "return": round(r_comp, 4),
            "arithmetic_return": round(r_arith, 4),
            "contribution": round(contrib, 4),
            "contribution_pct": round(contrib / sum_contributions * 100.0, 2) if sum_contributions != 0 else 0.0,
            "position_value": round(float(position_values[i]), 2),
            "dollar_pnl": round(float(position_returns[i]), 2),
            "category": get_asset_category(ticker),
        })

    # --- Sector Contribution ---
    sector_data = {}
    for i, ticker in enumerate(usable_tickers):
        cat = get_asset_category(ticker)
        if cat not in sector_data:
            sector_data[cat] = {"weight": 0.0, "return_weighted_sum": 0.0, "contrib": 0.0, "tickers": []}
        w = float(usable_weights[i])
        contrib = float(sec_contributions[i])
        sector_data[cat]["weight"] += w
        sector_data[cat]["contrib"] += contrib
        sector_data[cat]["return_weighted_sum"] += w * float(asset_compounded[i])
        sector_data[cat]["tickers"].append(ticker)

    sector_contrib = []
    for cat, data in sorted(sector_data.items(), key=lambda x: -x[1]["contrib"]):
        cat_weight = data["weight"]
        cat_contrib = data["contrib"]
        sector_contrib.append({
            "category": cat,
            "weight": round(cat_weight, 4),
            "return": round(data["return_weighted_sum"] / cat_weight, 4) if cat_weight > 0 else 0.0,
            "contribution": round(cat_contrib, 4),
            "contribution_pct": round(cat_contrib / sum_contributions * 100.0, 2) if sum_contributions != 0 else 0.0,
            "tickers": data["tickers"],
        })

    # --- Asset Class Contribution ---
    def _asset_class(cat: str) -> str:
        if "ETF" in cat or cat in ("Equity", "Technology", "Communication", "Consumer", "Financial", "Healthcare", "Energy", "Utilities", "Industrials", "Basic Materials"):
            if "Cash" in cat or cat == "Other":
                return "Cash"
            if "Financial" in cat:
                return "Financials"
            if "Technology" in cat:
                return "Technology"
            if "Health" in cat:
                return "Healthcare"
            if "Consumer" in cat:
                return "Consumer"
            if "Energy" in cat or "Utilities" in cat:
                return "Energy/Utilities"
            if "Industries" in cat:
                return "Industrials"
            if "Materials" in cat:
                return "Materials"
            return cat
        return cat

    asset_class_data = {}
    for i, ticker in enumerate(usable_tickers):
        cat = get_asset_category(ticker)
        ac = _asset_class(cat)
        if ac not in asset_class_data:
            asset_class_data[ac] = {"weight": 0.0, "contrib": 0.0, "tickers": []}
        asset_class_data[ac]["weight"] += float(usable_weights[i])
        asset_class_data[ac]["contrib"] += float(sec_contributions[i])
        asset_class_data[ac]["tickers"].append(ticker)

    asset_class_contrib = []
    for ac, data in sorted(asset_class_data.items(), key=lambda x: -x[1]["contrib"]):
        ac_contrib = data["contrib"]
        asset_class_contrib.append({
            "asset_class": ac,
            "weight": round(data["weight"], 4),
            "contribution": round(ac_contrib, 4),
            "contribution_pct": round(ac_contrib / sum_contributions * 100.0, 2) if sum_contributions != 0 else 0.0,
            "tickers": data["tickers"],
        })

    first_date = usable_prices.index[0]
    last_date = usable_prices.index[-1]

    return {
        "period": {
            "start": first_date.strftime('%Y-%m-%d') if hasattr(first_date, 'strftime') else str(first_date),
            "end": last_date.strftime('%Y-%m-%d') if hasattr(last_date, 'strftime') else str(last_date),
        },
        "model": "daily_constant_weight_contribution",
        "methodology": "return_contribution",
        "portfolio_total_return": round(port_cum_return, 4),
        "sum_of_security_contributions": round(sum_contributions, 4),
        "compounding_residual": round(compounding_residual, 4),
        "reconciled": bool(abs(sum_contributions - sum_arithmetic_port_return) < 1e-9),
        "portfolio_value": float(portfolio_value),
        "currency": currency_symbol,
        "security_contribution": security_contrib,
        "sector_contribution": sector_contrib,
        "asset_class_contribution": asset_class_contrib,
    }

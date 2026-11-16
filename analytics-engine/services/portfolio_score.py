"""
Portfolio score engine.

Evaluates overall portfolio health (0 to 1000 points) across 4 dimensions:
1. Downside Protection (max 400) - PORTFOLIO-LEVEL max drawdown & VaR
2. Risk-Adjusted Return (max 300) - PORTFOLIO-LEVEL Sharpe ratio
3. Allocation Quality (max 200) - ASSET-LEVEL concentration & diversification
4. Stress Resilience (max 100) - PORTFOLIO-LEVEL drawdown resilience

All risk and return inputs are evaluated at the true portfolio level rather than
averaging individual asset statistics.
"""
from typing import Optional, List, Dict, Any
import numpy as np
import pandas as pd

from services.financial_metrics import (
    canonical_portfolio_returns,
    compute_annualized_volatility,
    compute_annualized_return,
    compute_sharpe_ratio,
    compute_wealth_index_drawdown,
    compute_var_cvar,
    DEFAULT_RISK_FREE_RATE,
)


def get_currency_symbol(currency_map: dict) -> str:
    """Determine dominant currency symbol. Favors INR if present."""
    if "INR" in currency_map.values():
        return "\u20b9"
    counts = pd.Series(list(currency_map.values())).value_counts()
    dominant = counts.index[0] if not counts.empty else "USD"
    symbols = {"USD": "$", "INR": "\u20b9", "EUR": "\u20ac", "GBP": "\u00a3"}
    return symbols.get(dominant, "$")


RISK_TOLERANCE_THRESHOLDS = {
    'HIGH_RISK_THRESHOLD': 0.35,
    'MEDIUM_RISK_THRESHOLD': 0.20,
    'HIGH_DRAWDOWN_THRESHOLD': -0.30,
    'HIGH_VAR_THRESHOLD': -0.03,
}

ASSET_CATEGORIES = {
    'AAPL': 'Technology',
    'MSFT': 'Technology',
    'GOOGL': 'Communication',
    'AMZN': 'Consumer Cyclical',
    'NVDA': 'Technology',
    'GOOG': 'Communication',
    'JPM': 'Financial',
    'JNJ': 'Healthcare',
    'V': 'Financial',
    'WMT': 'Consumer Defensive',
    'SPY': 'ETF',
    'QQQ': 'ETF',
    'IWM': 'ETF',
    'DIA': 'ETF',
    'XLF': 'ETF',
    'EFA': 'ETF',
    'EEM': 'ETF',
    'VNQ': 'ETF',
    'BND': 'ETF',
    'HYG': 'ETF',
    'TLT': 'ETF',
    'GLD': 'ETF',
    'SLV': 'ETF',
    'USO': 'ETF',
    'UNG': 'ETF',
    'FXI': 'ETF',
    'EWJ': 'ETF',
    'INDA': 'ETF',
    'EWT': 'ETF',
    'RSX': 'ETF',
    'EWZ': 'ETF',
    'EPI': 'ETF',
}

INDIA_TICKERS = {
    'TCS.NS': 'Technology',
    'RELIANCE.NS': 'Energy',
    'HDFCBANK.NS': 'Financial',
    'INFY.NS': 'Technology',
    'ICICIBANK.NS': 'Financial',
    'SBIN.NS': 'Financial',
    'BHARTIARTL.NS': 'Communication',
    'AXISBANK.NS': 'Financial',
    'KOTAKBANK.NS': 'Financial',
    'LT.NS': 'Industrials',
    'HCLTECH.NS': 'Technology',
    'WIPRO.NS': 'Technology',
    'ITC.NS': 'Consumer Defensive',
    'BAJFINANCE.NS': 'Financial',
    'BAJAJ-AUTO.NS': 'Consumer Cyclical',
    'HINDUNILVR.NS': 'Consumer Defensive',
    'ASIANPAINT.NS': 'Basic Materials',
    'NESTEIND.NS': 'Consumer Defensive',
    'DRREDDY.NS': 'Healthcare',
    'SUNPHARMA.NS': 'Healthcare',
    'DIVIOLABS.NS': 'Healthcare',
    'APOLLOHOSP.NS': 'Healthcare',
    'POWERGRID.NS': 'Utilities',
    'SBILIFE.NS': 'Financial',
    'HDFCLIFE.NS': 'Financial',
    'SHRIRAMFIN.NS': 'Financial',
    'TRENT.NS': 'Consumer Cyclical',
    'ADANIGREEN.NS': 'Energy',
    'ADANIPORTS.NS': 'Industrials',
    'TATAMOTORS.NS': 'Consumer Cyclical',
    'LTIM.NS': 'Technology',
    'HINDALIBAR.NS': 'Consumer Defensive',
    'MOTHERSLJS.NS': 'Financial',
    'PERSISTENT.NS': 'Technology',
    'COPPER.NS': 'Basic Materials',
    'NMDC.NS': 'Basic Materials',
    'COALINDIA.NS': 'Energy',
    'IOC.NS': 'Energy',
    'RIL.NS': 'Energy',
}


def get_asset_category(ticker: str) -> str:
    t = ticker.upper().strip()
    if t in ASSET_CATEGORIES:
        return ASSET_CATEGORIES[t]
    if t in INDIA_TICKERS:
        return INDIA_TICKERS[t]
    return 'Other'


def compute_asset_allocation(tickers: list, weights: list) -> list:
    """Group weights by asset category."""
    cats = {}
    for t, w in zip(tickers, weights):
        c = get_asset_category(t)
        cats[c] = cats.get(c, 0.0) + float(w)
    return [{"category": k, "weight": round(v, 4)} for k, v in cats.items()]


def compute_portfolio_score(
    tickers: list,
    weights: list,
    risk_summary: Optional[pd.DataFrame] = None,
    returns: Optional[pd.DataFrame] = None,
    portfolio_value: float = 100000,
    portfolio_metrics: Optional[dict] = None,
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
) -> dict:
    """
    Score the portfolio (0-1000) using true portfolio-level risk and performance metrics.
    """
    if not tickers or not weights:
        return {
            'score': 0,
            'max_score': 1000,
            'grading': 'N/A',
            'components': {},
            'risks_identified': [],
            'metric_provenance': {},
        }

    # Step 1: Extract or calculate PORTFOLIO-LEVEL metrics
    port_vol: Optional[float] = None
    port_var: Optional[float] = None
    port_drawdown: Optional[float] = None
    port_sharpe: Optional[float] = None
    port_ann_return: Optional[float] = None

    if portfolio_metrics and isinstance(portfolio_metrics, dict):
        port_vol = portfolio_metrics.get("portfolio_volatility")
        port_var = portfolio_metrics.get("portfolio_var_95")
        port_drawdown = portfolio_metrics.get("portfolio_max_drawdown")
        port_sharpe = portfolio_metrics.get("portfolio_sharpe")
        port_ann_return = portfolio_metrics.get("portfolio_annualized_return")

    # If portfolio metrics are not provided or incomplete, compute from canonical portfolio returns
    if (port_vol is None or port_drawdown is None or port_sharpe is None) and returns is not None and not returns.empty:
        try:
            port_ret = canonical_portfolio_returns(returns, weights, tickers)
            if not port_ret.empty and len(port_ret) >= 2:
                if port_vol is None:
                    port_vol = compute_annualized_volatility(port_ret, ddof=1)
                if port_var is None:
                    port_var, _ = compute_var_cvar(port_ret, confidence_level=0.95)
                if port_drawdown is None:
                    port_drawdown, _ = compute_wealth_index_drawdown(port_ret)
                if port_sharpe is None:
                    port_sharpe = compute_sharpe_ratio(port_ret, risk_free_rate_annual=risk_free_rate)
                if port_ann_return is None:
                    port_ann_return = compute_annualized_return(port_ret)
        except Exception:
            pass

    # Safe defaults if data is missing
    vol_val = port_vol if port_vol is not None else 0.0
    var_val = port_var if port_var is not None else 0.0
    dd_val = port_drawdown if port_drawdown is not None else 0.0
    sharpe_val = port_sharpe if port_sharpe is not None else 0.0
    return_val = port_ann_return if port_ann_return is not None else 0.0

    components = {}

    # 1. Downside Protection (max 400 points) — PORTFOLIO-LEVEL
    # Lower portfolio drawdown and portfolio VaR = higher score
    drawdown_abs = abs(dd_val)
    var_abs = abs(var_val)
    downside_score = min(400, max(0, 400 * (1.0 - drawdown_abs / 0.5) * (1.0 - var_abs / 0.1)))
    components['downside_protection'] = {
        'score': round(downside_score, 1),
        'max': 400,
        'label': 'Downside Protection',
        'provenance': 'PORTFOLIO-LEVEL',
        'detail': f'Portfolio Max Drawdown: {dd_val*100:.1f}%, Portfolio VaR(95%): {var_val*100:.2f}%',
    }

    # 2. Risk-Adjusted Return (max 300 points) — PORTFOLIO-LEVEL
    # Uses canonical daily-excess annualized portfolio Sharpe
    sharpe_score = min(300, max(0, 150 + sharpe_val * 50))
    components['risk_adjusted_return'] = {
        'score': round(sharpe_score, 1),
        'max': 300,
        'label': 'Risk-Adjusted Return',
        'provenance': 'PORTFOLIO-LEVEL',
        'detail': f'Portfolio Sharpe: {sharpe_val:.2f} (ann return: {return_val*100:.1f}%, vol: {vol_val*100:.1f}%)',
    }

    # 3. Allocation Quality (max 200 points) — ASSET-LEVEL & HEURISTIC
    # Rewards diversification across unique holdings and penalizes heavy concentration
    max_weight = max(weights) if weights else 1.0
    unique_holdings = len(tickers)
    allocation_score = min(200, unique_holdings * 25 + (1.0 - max_weight) * 50)
    components['allocation_quality'] = {
        'score': round(allocation_score, 1),
        'max': 200,
        'label': 'Allocation Quality',
        'provenance': 'ASSET-LEVEL',
        'detail': f'{unique_holdings} holdings, max position: {max_weight*100:.0f}%',
    }

    # 4. Stress Resilience (max 100 points) — PORTFOLIO-LEVEL
    # Evaluates how well the true portfolio bounded historical drawdown
    stress_score = min(100, max(0, 100 * (1.0 - drawdown_abs / 0.5)))
    components['stress_resilience'] = {
        'score': round(stress_score, 1),
        'max': 100,
        'label': 'Stress Resilience',
        'provenance': 'PORTFOLIO-LEVEL',
        'detail': 'Based on canonical portfolio historical drawdown & VaR',
    }

    total_score = round(
        components['downside_protection']['score']
        + components['risk_adjusted_return']['score']
        + components['allocation_quality']['score']
        + components['stress_resilience']['score']
    )

    # Grading
    pct = total_score / 1000.0
    if pct >= 0.9:
        grade = 'A+'
    elif pct >= 0.8:
        grade = 'A'
    elif pct >= 0.7:
        grade = 'B'
    elif pct >= 0.6:
        grade = 'C'
    elif pct >= 0.5:
        grade = 'D'
    else:
        grade = 'F'

    # Risk identification using portfolio-level metrics
    risks = identify_portfolio_risks(tickers, weights, vol_val, dd_val)

    metric_provenance = {
        "portfolio_volatility": "PORTFOLIO-LEVEL",
        "portfolio_drawdown": "PORTFOLIO-LEVEL",
        "portfolio_var": "PORTFOLIO-LEVEL",
        "portfolio_sharpe": "PORTFOLIO-LEVEL",
        "allocation_concentration": "ASSET-LEVEL",
        "diversification_count": "HEURISTIC",
    }

    return {
        'score': total_score,
        'max_score': 1000,
        'grade': grade,
        'grading': grade,
        'pct': round(pct * 100.0, 1),
        'components': components,
        'risks_identified': risks,
        'metric_provenance': metric_provenance,
    }


def identify_portfolio_risks(
    tickers: list,
    weights: list,
    port_volatility: float,
    port_drawdown: float,
) -> list:
    """Identify key risks using portfolio-level metrics and concentration thresholds."""
    risks = []

    # Concentration risk (ASSET-LEVEL)
    max_weight = max(weights) if weights else 0
    if max_weight > 0.5:
        risks.append({
            'type': 'concentration',
            'severity': 'high',
            'label': 'Concentration Risk',
            'description': f"Single position represents {max_weight*100:.0f}% of portfolio. A single stock's decline heavily impacts total value.",
        })
    elif max_weight > 0.3:
        risks.append({
            'type': 'concentration',
            'severity': 'medium',
            'label': 'Moderate Concentration',
            'description': f"Largest position is {max_weight*100:.0f}% of portfolio.",
        })

    # Portfolio Volatility risk (PORTFOLIO-LEVEL)
    if port_volatility > RISK_TOLERANCE_THRESHOLDS['HIGH_RISK_THRESHOLD']:
        risks.append({
            'type': 'volatility',
            'severity': 'high',
            'label': 'High Portfolio Volatility',
            'description': f"Annualized portfolio volatility is {port_volatility*100:.1f}%, exceeding the 35% high-risk threshold.",
        })
    elif port_volatility > RISK_TOLERANCE_THRESHOLDS['MEDIUM_RISK_THRESHOLD']:
        risks.append({
            'type': 'volatility',
            'severity': 'medium',
            'label': 'Moderate Portfolio Volatility',
            'description': f"Annualized portfolio volatility is {port_volatility*100:.1f}%.",
        })

    # Portfolio Drawdown risk (PORTFOLIO-LEVEL)
    if port_drawdown < RISK_TOLERANCE_THRESHOLDS['HIGH_DRAWDOWN_THRESHOLD']:
        risks.append({
            'type': 'drawdown',
            'severity': 'high',
            'label': 'High Portfolio Historical Drawdown',
            'description': f"Portfolio suffered a historical peak-to-trough decline of {abs(port_drawdown)*100:.1f}%.",
        })

    return risks

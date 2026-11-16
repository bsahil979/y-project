"""
Benchmark engine — compares portfolio performance against benchmarks.

Supports configurable benchmarks (S&P 500, NIFTY 50, NASDAQ-100, custom tickers).
Calculates total return, annualized return, volatility, Sharpe, Sortino,
max drawdown, beta, alpha, tracking error, and information ratio using
canonical financial formulas.
"""
from typing import Optional, List, Dict, Any
import numpy as np
import pandas as pd

from services.financial_metrics import (
    canonical_portfolio_returns,
    compute_cumulative_return,
    compute_annualized_return,
    compute_annualized_volatility,
    compute_sharpe_ratio,
    compute_sortino_ratio,
    compute_wealth_index_drawdown,
    compute_beta_and_alpha,
    DEFAULT_RISK_FREE_RATE,
)

BENCHMARKS = {
    "S&P 500": "SPY",
    "NASDAQ-100": "QQQ",
    "NIFTY 50": "^NSEI",
    "Russell 2000": "IWM",
    "Dow Jones": "DIA",
    "MSCI Emerging Markets": "EEM",
    "US Aggregate Bonds": "BND",
}


def _safe_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Normalize price data to a DataFrame of daily returns."""
    returns = prices.pct_change().dropna()
    if isinstance(returns, pd.Series):
        returns = returns.to_frame()
    return returns


def compute_benchmark_comparison(
    prices: pd.DataFrame,
    weights: List[float],
    portfolio_value: float = 100000,
    benchmark_ticker: str = "SPY",
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
    tickers: Optional[List[str]] = None,
    portfolio_returns: Optional[pd.Series] = None,
    base_currency: Optional[str] = None,
) -> dict:
    """
    Compare portfolio against a benchmark using canonical financial metrics.

    Returns a dict of portfolio_vs_benchmark metrics and aligned return series.
    """
    bench_clean = benchmark_ticker.strip().upper()

    # Step 1: Obtain canonical daily portfolio returns
    if portfolio_returns is not None and isinstance(portfolio_returns, pd.Series) and not portfolio_returns.empty:
        port_daily = portfolio_returns.dropna()
    else:
        port_prices = prices.ffill().bfill()
        port_returns_df = _safe_returns(port_prices)
        if tickers is None:
            # If tickers not passed, try matching columns excluding the benchmark if possible
            cand_cols = [c for c in port_returns_df.columns if str(c).upper().strip() != bench_clean]
            if len(cand_cols) == len(weights):
                tickers = cand_cols
            else:
                tickers = list(port_returns_df.columns[:len(weights)])
        port_daily = canonical_portfolio_returns(port_returns_df, weights, tickers)

    # Step 2: Obtain benchmark daily returns
    bench_col = None
    if isinstance(prices, pd.DataFrame):
        col_lookup = {str(c).upper().strip(): c for c in prices.columns}
        if bench_clean in col_lookup:
            bench_col = col_lookup[bench_clean]

    if bench_col is not None:
        bench_prices = prices[bench_col].dropna()
        bench_daily = bench_prices.pct_change().dropna()
    else:
        # Fetch benchmark separately
        try:
            from services.data_fetcher import fetch_price_data
            start_date = prices.index[0].strftime('%Y-%m-%d') if hasattr(prices.index[0], 'strftime') else str(prices.index[0])
            end_date = (prices.index[-1] + pd.Timedelta(days=1)).strftime('%Y-%m-%d') if hasattr(prices.index[-1], 'strftime') else str(prices.index[-1])
            bench_data = fetch_price_data([benchmark_ticker], start_date, end_date)
            if base_currency:
                from services.data_fetcher import get_currency_metadata, normalize_currency_prices
                if bench_clean == '^NSEI' or bench_clean.endswith(('.NS', '.BO')):
                    original = 'INR'
                elif bench_clean in BENCHMARKS.values():
                    original = 'USD'
                else:
                    original = get_currency_metadata([bench_clean])[bench_clean]
                bench_data, _, _ = normalize_currency_prices(bench_data, {benchmark_ticker: original},
                    base_currency, start_date, end_date)
                bench_data = bench_data.reindex(prices.index)
            if isinstance(bench_data, pd.DataFrame):
                bench_prices = bench_data.iloc[:, 0]
            else:
                bench_prices = bench_data.dropna()
            bench_daily = bench_prices.pct_change(fill_method=None).dropna()
        except Exception as exc:
            return {
                "error": f"Failed to fetch benchmark data for '{benchmark_ticker}': {exc}",
                "benchmark_ticker": benchmark_ticker,
            }

    # Step 3: Strictly align on common dates
    common_idx = port_daily.dropna().index.intersection(bench_daily.dropna().index)
    if len(common_idx) < 2:
        return {
            "error": "Insufficient overlapping data for benchmark comparison",
            "benchmark_ticker": benchmark_ticker,
            "observation_count": len(common_idx),
        }

    port_aligned = port_daily.loc[common_idx]
    bench_aligned = bench_daily.loc[common_idx]

    # Step 4: Compute canonical metrics using standardized formulas
    port_total = compute_cumulative_return(port_aligned)
    bench_total = compute_cumulative_return(bench_aligned)

    port_annualized = compute_annualized_return(port_aligned)
    bench_annualized = compute_annualized_return(bench_aligned)

    port_vol = compute_annualized_volatility(port_aligned, ddof=1)
    bench_vol = compute_annualized_volatility(bench_aligned, ddof=1)

    port_sharpe = compute_sharpe_ratio(port_aligned, risk_free_rate_annual=risk_free_rate)
    bench_sharpe = compute_sharpe_ratio(bench_aligned, risk_free_rate_annual=risk_free_rate)

    port_sortino = compute_sortino_ratio(port_aligned, risk_free_rate_annual=risk_free_rate)
    bench_sortino = compute_sortino_ratio(bench_aligned, risk_free_rate_annual=risk_free_rate)

    port_dd, _ = compute_wealth_index_drawdown(port_aligned)
    bench_dd, _ = compute_wealth_index_drawdown(bench_aligned)

    beta_alpha = compute_beta_and_alpha(port_aligned, bench_aligned, risk_free_rate_annual=risk_free_rate)
    beta = beta_alpha["beta"]
    alpha = beta_alpha["alpha"]

    # Tracking error & Information ratio
    excess = port_aligned - bench_aligned
    tracking_error = compute_annualized_volatility(excess, ddof=1)
    if tracking_error is not None and tracking_error > 1e-12:
        ir = float(excess.mean() * 252 / tracking_error)
    else:
        ir = None

    outperf = (port_total - bench_total) if (port_total is not None and bench_total is not None) else None
    outperf_pct = (outperf * 100.0) if outperf is not None else None

    aligned_start = str(common_idx[0].date()) if hasattr(common_idx[0], 'date') else str(common_idx[0])
    aligned_end = str(common_idx[-1].date()) if hasattr(common_idx[-1], 'date') else str(common_idx[-1])

    return {
        "benchmark_ticker": benchmark_ticker,
        "benchmark_display": BENCHMARKS.get(benchmark_ticker, benchmark_ticker),
        "period_days": len(common_idx),
        "aligned_start": aligned_start,
        "aligned_end": aligned_end,
        "observation_count": len(common_idx),
        "portfolio": {
            "total_return": round(port_total, 4) if port_total is not None else None,
            "annualized_return": round(port_annualized, 4) if port_annualized is not None else None,
            "volatility": round(port_vol, 4) if port_vol is not None else None,
            "sharpe_ratio": round(port_sharpe, 4) if port_sharpe is not None else None,
            "sortino_ratio": round(port_sortino, 4) if port_sortino is not None else None,
            "max_drawdown": round(port_dd, 4) if port_dd is not None else None,
        },
        "benchmark": {
            "total_return": round(bench_total, 4) if bench_total is not None else None,
            "annualized_return": round(bench_annualized, 4) if bench_annualized is not None else None,
            "volatility": round(bench_vol, 4) if bench_vol is not None else None,
            "sharpe_ratio": round(bench_sharpe, 4) if bench_sharpe is not None else None,
            "sortino_ratio": round(bench_sortino, 4) if bench_sortino is not None else None,
            "max_drawdown": round(bench_dd, 4) if bench_dd is not None else None,
        },
        "comparison": {
            "alpha": round(alpha, 4) if alpha is not None else None,
            "beta": round(beta, 4) if beta is not None else None,
            "tracking_error": round(tracking_error, 4) if tracking_error is not None else None,
            "information_ratio": round(ir, 4) if ir is not None else None,
            "outperformance": round(outperf, 4) if outperf is not None else None,
            "outperformance_pct": round(outperf_pct, 2) if outperf_pct is not None else None,
        },
        "return_series": {
            "portfolio_daily": _clean_series(port_aligned),
            "benchmark_daily": _clean_series(bench_aligned),
        },
    }


def _clean_series(s: pd.Series) -> list:
    """Convert pandas Series to JSON-friendly list for API response."""
    return [
        {"date": idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx), "return": float(v)}
        for idx, v in s.items()
    ]


def list_available_benchmarks() -> list[dict]:
    """Return all supported benchmark options."""
    return [{"name": k, "ticker": v} for k, v in BENCHMARKS.items()]

"""
Benchmark Engine - Comprehensive benchmark comparison for portfolio analysis.

This module provides:
- Configurable benchmark selection (NIFTY 50, S&P 500, NASDAQ-100, custom)
- Relative performance metrics calculation
- Portfolio vs benchmark comparison
- Tracking error and information ratio
- Alpha and beta calculation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkConfig:
    """Benchmark configuration."""
    ticker: str
    name: str
    description: str
    asset_class: str


# Predefined benchmarks
STANDARD_BENCHMARKS = {
    'SPY': BenchmarkConfig(
        ticker='SPY',
        name='S&P 500',
        description='SPDR S&P 500 ETF Trust',
        asset_class='US Equity'
    ),
    'QQQ': BenchmarkConfig(
        ticker='QQQ',
        name='NASDAQ-100',
        description='Invesco QQQ Trust',
        asset_class='US Equity'
    ),
    'IWM': BenchmarkConfig(
        ticker='IWM',
        name='Russell 2000',
        description='iShares Russell 2000 ETF',
        asset_class='US Equity'
    ),
    'VTI': BenchmarkConfig(
        ticker='VTI',
        name='Total US Market',
        description='Vanguard Total Stock Market ETF',
        asset_class='US Equity'
    ),
    'VNQ': BenchmarkConfig(
        ticker='VNQ',
        name='Real Estate',
        description='Vanguard Real Estate ETF',
        asset_class='US Real Estate'
    ),
    'GLD': BenchmarkConfig(
        ticker='GLD',
        name='Gold',
        description='SPDR Gold Shares',
        asset_class='Commodity'
    ),
    'EFA': BenchmarkConfig(
        ticker='EFA',
        name='MSCI EAFE',
        description='iShares MSCI EAFE ETF',
        asset_class='International Equity'
    ),
    'EEM': BenchmarkConfig(
        ticker='EEM',
        name='Emerging Markets',
        description='iShares MSCI Emerging Markets ETF',
        asset_class='Emerging Markets'
    ),
    'BND': BenchmarkConfig(
        ticker='BND',
        name='Aggregate Bond',
        description='Vanguard Total Bond Market ETF',
        asset_class='US Fixed Income'
    ),
    # Indian benchmarks
    'NIFTY50': BenchmarkConfig(
        ticker='^NSEI',
        name='NIFTY 50',
        description='NIFTY 50 Index',
        asset_class='Indian Equity'
    ),
    'NIFTYBANK': BenchmarkConfig(
        ticker='^NSEBANK',
        name='NIFTY Bank',
        description='NIFTY Bank Index',
        asset_class='Indian Equity'
    ),
    'SENSEX': BenchmarkConfig(
        ticker='^BSESN',
        name='SENSEX',
        description='BSE SENSEX Index',
        asset_class='Indian Equity'
    )
}


class BenchmarkEngine:
    """
    Benchmark comparison engine for portfolio analysis.
    """
    
    def __init__(self):
        """Initialize the benchmark engine."""
        self.benchmarks = STANDARD_BENCHMARKS
        logger.info("Benchmark Engine initialized")
    
    def get_available_benchmarks(self) -> Dict[str, BenchmarkConfig]:
        """Get all available benchmarks."""
        return self.benchmarks
    
    def compare_portfolio_to_benchmark(
        self,
        portfolio_returns: pd.Series,
        benchmark_ticker: str,
        benchmark_returns: Optional[pd.Series] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare portfolio performance to a benchmark.
        
        Args:
            portfolio_returns: Portfolio return series
            benchmark_ticker: Benchmark ticker symbol
            benchmark_returns: Optional pre-fetched benchmark returns
            start_date: Start date for comparison
            end_date: End date for comparison
            
        Returns:
            Comprehensive benchmark comparison metrics
        """
        logger.info(f"Comparing portfolio to benchmark: {benchmark_ticker}")
        
        # Fetch benchmark data if not provided
        if benchmark_returns is None:
            benchmark_returns = self._fetch_benchmark_data(
                benchmark_ticker,
                start_date,
                end_date
            )
        
        if benchmark_returns is None or benchmark_returns.empty:
            return {
                'status': 'failed',
                'error': f'Could not fetch benchmark data for {benchmark_ticker}'
            }
        
        # Align dates
        common_dates = portfolio_returns.index.intersection(benchmark_returns.index)
        if len(common_dates) < 30:
            return {
                'status': 'failed',
                'error': f'Insufficient overlapping data points: {len(common_dates)}'
            }
        
        portfolio_aligned = portfolio_returns.loc[common_dates]
        benchmark_aligned = benchmark_returns.loc[common_dates]
        
        # Calculate performance metrics
        n_days = len(portfolio_aligned)
        
        # Portfolio metrics
        portfolio_cumulative = (1 + portfolio_aligned).cumprod()
        portfolio_total_return = portfolio_cumulative.iloc[-1] - 1
        portfolio_annual_return = (1 + portfolio_total_return) ** (252 / n_days) - 1
        portfolio_volatility = portfolio_aligned.std() * np.sqrt(252)
        
        # Benchmark metrics
        benchmark_cumulative = (1 + benchmark_aligned).cumprod()
        benchmark_total_return = benchmark_cumulative.iloc[-1] - 1
        benchmark_annual_return = (1 + benchmark_total_return) ** (252 / n_days) - 1
        benchmark_volatility = benchmark_aligned.std() * np.sqrt(252)
        
        # Risk-free rate (simplified - using 2%)
        risk_free_rate = 0.02
        
        # Sharpe ratios
        portfolio_sharpe = (portfolio_annual_return - risk_free_rate) / portfolio_volatility if portfolio_volatility > 0 else 0
        benchmark_sharpe = (benchmark_annual_return - risk_free_rate) / benchmark_volatility if benchmark_volatility > 0 else 0
        
        # Max drawdown
        portfolio_drawdown = self._calculate_max_drawdown(portfolio_cumulative)
        benchmark_drawdown = self._calculate_max_drawdown(benchmark_cumulative)
        
        # Relative metrics
        excess_returns = portfolio_aligned - benchmark_aligned
        excess_annual_return = excess_returns.mean() * 252
        tracking_error = excess_returns.std() * np.sqrt(252)
        
        # Beta calculation
        covariance = np.cov(portfolio_aligned, benchmark_aligned)[0, 1]
        benchmark_variance = np.var(benchmark_aligned)
        beta = covariance / benchmark_variance if benchmark_variance > 0 else 1.0
        
        # Alpha calculation (Jensen's alpha)
        alpha = portfolio_annual_return - (risk_free_rate + beta * (benchmark_annual_return - risk_free_rate))
        
        # Information ratio
        information_ratio = excess_annual_return / tracking_error if tracking_error > 0 else 0
        
        # Upside/Downside capture
        portfolio_up = portfolio_aligned[portfolio_aligned > 0].mean()
        benchmark_up = benchmark_aligned[benchmark_aligned > 0].mean()
        portfolio_down = portfolio_aligned[portfolio_aligned < 0].mean()
        benchmark_down = benchmark_aligned[benchmark_aligned < 0].mean()
        
        upside_capture = portfolio_up / benchmark_up if benchmark_up > 0 else 0
        downside_capture = portfolio_down / benchmark_down if benchmark_down < 0 else 0
        
        # Rolling performance (63-day window)
        window = min(63, n_days)
        rolling_excess = excess_returns.rolling(window).mean() * 252
        rolling_tracking_error = excess_returns.rolling(window).std() * np.sqrt(252)
        
        # Hit rate (days portfolio outperforms benchmark)
        hit_rate = (portfolio_aligned > benchmark_aligned).sum() / len(portfolio_aligned)
        
        return {
            'status': 'success',
            'benchmark_ticker': benchmark_ticker,
            'benchmark_info': self.benchmarks.get(benchmark_ticker.upper(), benchmark_ticker),
            'comparison_period': {
                'start_date': str(common_dates.min()),
                'end_date': str(common_dates.max()),
                'n_days': n_days
            },
            'portfolio_metrics': {
                'total_return': portfolio_total_return,
                'annual_return': portfolio_annual_return,
                'volatility': portfolio_volatility,
                'sharpe_ratio': portfolio_sharpe,
                'max_drawdown': portfolio_drawdown
            },
            'benchmark_metrics': {
                'total_return': benchmark_total_return,
                'annual_return': benchmark_annual_return,
                'volatility': benchmark_volatility,
                'sharpe_ratio': benchmark_sharpe,
                'max_drawdown': benchmark_drawdown
            },
            'relative_metrics': {
                'excess_return': excess_annual_return,
                'tracking_error': tracking_error,
                'beta': beta,
                'alpha': alpha,
                'information_ratio': information_ratio,
                'upside_capture': upside_capture,
                'downside_capture': downside_capture,
                'hit_rate': hit_rate
            },
            'rolling_metrics': {
                'rolling_excess_return': rolling_excess.iloc[-1] if len(rolling_excess) > 0 else 0,
                'rolling_tracking_error': rolling_tracking_error.iloc[-1] if len(rolling_tracking_error) > 0 else 0
            },
            'outperformance_summary': {
                'total_return_diff': portfolio_total_return - benchmark_total_return,
                'annual_return_diff': portfolio_annual_return - benchmark_annual_return,
                'volatility_diff': portfolio_volatility - benchmark_volatility,
                'sharpe_diff': portfolio_sharpe - benchmark_sharpe,
                'outperformed': portfolio_total_return > benchmark_total_return
            }
        }
    
    def _fetch_benchmark_data(
        self,
        benchmark_ticker: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.Series]:
        """Fetch benchmark data from Yahoo Finance."""
        try:
            import yfinance as yf
            
            ticker_obj = yf.Ticker(benchmark_ticker)
            data = ticker_obj.history(start=start_date, end=end_date)
            
            if data is None or data.empty:
                return None
            
            # Use 'Close' prices
            returns = data['Close'].pct_change().dropna()
            
            return returns
            
        except Exception as e:
            logger.error(f"Failed to fetch benchmark data for {benchmark_ticker}: {e}")
            return None
    
    def _calculate_max_drawdown(self, cumulative_returns: pd.Series) -> float:
        """Calculate maximum drawdown from cumulative returns."""
        cummax = cumulative_returns.cummax()
        drawdown = (cumulative_returns - cummax) / cummax
        return drawdown.min()
    
    def compare_multiple_benchmarks(
        self,
        portfolio_returns: pd.Series,
        benchmark_tickers: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compare portfolio to multiple benchmarks.
        
        Args:
            portfolio_returns: Portfolio return series
            benchmark_tickers: List of benchmark tickers
            start_date: Start date for comparison
            end_date: End date for comparison
            
        Returns:
            Dictionary of comparison results for each benchmark
        """
        results = {}
        
        for ticker in benchmark_tickers:
            comparison = self.compare_portfolio_to_benchmark(
                portfolio_returns,
                ticker,
                start_date=start_date,
                end_date=end_date
            )
            results[ticker] = comparison
        
        return results
    
    def get_best_benchmark(
        self,
        portfolio_returns: pd.Series,
        candidate_benchmarks: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Find the best benchmark for comparison based on criteria.
        
        Args:
            portfolio_returns: Portfolio return series
            candidate_benchmarks: List of benchmark tickers to consider
            start_date: Start date for comparison
            end_date: End date for comparison
            
        Returns:
            Best benchmark comparison result
        """
        comparisons = self.compare_multiple_benchmarks(
            portfolio_returns,
            candidate_benchmarks,
            start_date,
            end_date
        )
        
        # Filter successful comparisons
        successful = {k: v for k, v in comparisons.items() if v.get('status') == 'success'}
        
        if not successful:
            return {
                'status': 'failed',
                'error': 'No benchmark comparisons succeeded'
            }
        
        # Select best based on information ratio (higher is better)
        best_ticker = max(
            successful.keys(),
            key=lambda k: successful[k]['relative_metrics']['information_ratio']
        )
        
        return {
            'status': 'success',
            'best_benchmark': best_ticker,
            'comparison': successful[best_ticker],
            'all_comparisons': successful
        }


def create_benchmark_engine() -> BenchmarkEngine:
    """Convenience function to create a benchmark engine."""
    return BenchmarkEngine()


if __name__ == "__main__":
    # Example usage
    engine = create_benchmark_engine()
    
    # Get available benchmarks
    benchmarks = engine.get_available_benchmarks()
    print("Available benchmarks:")
    for ticker, config in benchmarks.items():
        print(f"  {ticker}: {config.name} - {config.description}")
    
    # Example comparison (would need real data)
    print("\nBenchmark engine ready for integration")
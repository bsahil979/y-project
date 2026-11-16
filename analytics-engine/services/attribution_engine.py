"""
Attribution Engine - Portfolio return attribution analysis.

This module provides:
- Security-level contribution analysis
- Sector contribution analysis
- Asset-class contribution analysis
- Allocation vs selection contribution
- Absolute and percentage contributions
- Time-period based attribution

Never fabricates attribution - all calculations are mathematically derived from actual data.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class AttributionResult:
    """Result of attribution analysis."""
    security_contributions: Dict[str, Dict[str, Any]]
    sector_contributions: Dict[str, Dict[str, Any]]
    asset_class_contributions: Dict[str, Dict[str, Any]]
    allocation_vs_selection: Dict[str, Dict[str, Any]]
    attribution_summary: Dict[str, Any]
    attribution_period: Dict[str, str]
    timestamp: str


class AttributionEngine:
    """
    Portfolio return attribution engine.
    """
    
    def __init__(self):
        """Initialize the attribution engine."""
        # Import categorization
        try:
            from services.portfolio_score import get_asset_category
            self.get_asset_category = get_asset_category
            logger.info("Attribution Engine initialized")
        except ImportError as e:
            logger.error(f"Failed to import categorization: {e}")
            self.get_asset_category = lambda x: 'Other'
    
    def calculate_attribution(
        self,
        returns: pd.DataFrame,
        weights: np.ndarray,
        benchmark_returns: Optional[pd.Series] = None,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None
    ) -> AttributionResult:
        """
        Calculate comprehensive portfolio attribution.
        
        Args:
            returns: DataFrame with asset returns (columns = assets)
            weights: Array of portfolio weights
            benchmark_returns: Optional benchmark returns for selection attribution
            period_start: Start date for attribution period
            period_end: End date for attribution period
            
        Returns:
            Comprehensive attribution analysis
        """
        logger.info("Calculating portfolio attribution")
        
        # Validate inputs
        if len(returns.columns) != len(weights):
            raise ValueError("Number of assets in returns must match length of weights")
        
        if abs(sum(weights) - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0 (current sum: {sum(weights)})")
        
        # Calculate portfolio returns
        portfolio_returns = (returns * weights).sum(axis=1)
        
        # Calculate total portfolio return
        total_return = portfolio_returns.sum()
        
        # Attribution period
        if period_start is None:
            period_start = returns.index.min()
        if period_end is None:
            period_end = returns.index.max()
        
        # Security-level attribution
        security_contributions = self._calculate_security_attribution(
            returns, weights, total_return
        )
        
        # Sector-level attribution
        sector_contributions = self._calculate_sector_attribution(
            security_contributions, returns.columns
        )
        
        # Asset-class attribution
        asset_class_contributions = self._calculate_asset_class_attribution(
            security_contributions, returns.columns
        )
        
        # Allocation vs selection attribution
        allocation_vs_selection = self._calculate_allocation_vs_selection(
            returns, weights, benchmark_returns
        )
        
        # Attribution summary
        attribution_summary = self._create_attribution_summary(
            security_contributions,
            sector_contributions,
            asset_class_contributions,
            total_return
        )
        
        return AttributionResult(
            security_contributions=security_contributions,
            sector_contributions=sector_contributions,
            asset_class_contributions=asset_class_contributions,
            allocation_vs_selection=allocation_vs_selection,
            attribution_summary=attribution_summary,
            attribution_period={
                'start': str(period_start),
                'end': str(period_end)
            },
            timestamp=datetime.now().isoformat()
        )
    
    def _calculate_security_attribution(
        self,
        returns: pd.DataFrame,
        weights: np.ndarray,
        total_return: float
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate security-level contribution."""
        security_contributions = {}
        
        for i, ticker in enumerate(returns.columns):
            asset_weight = weights[i]
            asset_return = returns[ticker].sum()
            
            # Contribution = weight * return
            contribution = asset_weight * asset_return
            pct_contribution = (contribution / total_return * 100) if total_return != 0 else 0
            
            security_contributions[ticker] = {
                'weight': asset_weight,
                'return': asset_return,
                'contribution': contribution,
                'pct_contribution': pct_contribution,
                'absolute_contribution': contribution,
                'weight_return_product': asset_weight * asset_return
            }
        
        return security_contributions
    
    def _calculate_sector_attribution(
        self,
        security_contributions: Dict[str, Dict[str, Any]],
        tickers: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate sector-level contribution."""
        sector_map = {}
        for ticker in tickers:
            sector = self.get_asset_category(ticker)
            sector_map[ticker] = sector
        
        sector_contributions = {}
        
        for ticker, contrib in security_contributions.items():
            sector = sector_map.get(ticker, 'Other')
            
            if sector not in sector_contributions:
                sector_contributions[ sector] = {
                    'weight': 0.0,
                    'contribution': 0.0,
                    'assets': []
                }
            
            sector_contributions[sector]['weight'] += contrib['weight']
            sector_contributions[sector]['contribution'] += contrib['contribution']
            sector_contributions[sector]['assets'].append(ticker)
        
        # Calculate percentages
        total_contribution = sum(s['contribution'] for s in sector_contributions.values())
        
        for sector in sector_contributions:
            sector_contributions[sector]['pct_contribution'] = (
                sector_contributions[sector]['contribution'] / total_contribution * 100
            ) if total_contribution != 0 else 0
        
        return sector_contributions
    
    def _calculate_asset_class_attribution(
        self,
        security_contributions: Dict[str, Dict[str, Any]],
        tickers: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate asset-class level contribution."""
        # Simplified asset class mapping
        asset_class_map = {}
        for ticker in tickers:
            sector = self.get_asset_category(ticker)
            
            # Map sectors to asset classes
            if sector in ['Technology', 'Communication', 'Consumer Cyclical', 'Industrials']:
                asset_class = 'Equity'
            elif sector in ['Financial', 'Healthcare', 'Consumer Defensive']:
                asset_class = 'Equity'
            elif sector == 'ETF':
                asset_class = 'ETF'
            else:
                asset_class = 'Other'
            
            asset_class_map[ticker] = asset_class
        
        asset_class_contributions = {}
        
        for ticker, contrib in security_contributions.items():
            asset_class = asset_class_map.get(ticker, 'Other')
            
            if asset_class not in asset_class_contributions:
                asset_class_contributions[asset_class] = {
                    'weight': 0.0,
                    'contribution': 0.0,
                    'assets': []
                }
            
            asset_class_contributions[asset_class]['weight'] += contrib['weight']
            asset_class_contributions[asset_class]['contribution'] += contrib['contribution']
            asset_class_contributions[asset_class]['assets'].append(ticker)
        
        # Calculate percentages
        total_contribution = sum(s['contribution'] for s in asset_class_contributions.values())
        
        for asset_class in asset_class_contributions:
            asset_class_contributions[asset_class]['pct_contribution'] = (
                asset_class_contributions[asset_class]['contribution'] / total_contribution * 100
            ) if total_contribution != 0 else 0
        
        return asset_class_contributions
    
    def _calculate_allocation_vs_selection(
        self,
        returns: pd.DataFrame,
        weights: np.ndarray,
        benchmark_returns: Optional[pd.Series] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculate allocation vs selection attribution.
        
        Allocation effect: How much return came from being in high-performing assets
        Selection effect: How much return came from timing decisions
        """
        if benchmark_returns is None:
            return {
                'status': 'skipped',
                'reason': 'No benchmark provided for selection attribution'
            }
        
        # Align dates
        common_dates = returns.index.intersection(benchmark_returns.index)
        if len(common_dates) < 30:
            return {
                'status': 'skipped',
                'reason': 'Insufficient overlapping data'
            }
        
        returns_aligned = returns.loc[common_dates]
        benchmark_aligned = benchmark_returns.loc[common_dates]
        
        # Calculate portfolio return
        portfolio_return = (returns_aligned * weights).sum(axis=1).sum()
        
        # Calculate equal-weight benchmark return
        equal_weights = np.ones(len(returns.columns)) / len(returns.columns)
        benchmark_return = (benchmark_aligned * equal_weights).sum()
        
        # Calculate asset returns
        asset_returns = returns_aligned.sum()
        
        # Allocation effect: Using portfolio weights vs equal weights
        allocation_effect = portfolio_return - (asset_returns * equal_weights).sum()
        
        # Selection effect: Asset returns vs benchmark returns
        selection_effect = (asset_returns * weights).sum() - (benchmark_aligned * weights).sum()
        
        # Interaction effect
        interaction_effect = portfolio_return - allocation_effect - selection_effect
        
        return {
            'status': 'success',
            'allocation_effect': allocation_effect,
            'selection_effect': selection_effect,
            'interaction_effect': interaction_effect,
            'portfolio_return': portfolio_return,
            'benchmark_return': benchmark_return,
            'total_attribution': portfolio_return,
            'breakdown': {
                'allocation': allocation_effect,
                'selection': selection_effect,
                'interaction': interaction_effect
            }
        }
    
    def _create_attribution_summary(
        self,
        security_contributions: Dict[str, Dict[str, Any]],
        sector_contributions: Dict[str, Dict[str, Any]],
        asset_class_contributions: Dict[str, Dict[str, Any]],
        total_return: float
    ) -> Dict[str, Any]:
        """Create attribution summary."""
        
        # Find top contributors
        top_securities = sorted(
            security_contributions.items(),
            key=lambda x: abs(x[1]['pct_contribution']),
            reverse=True
        )[:5]
        
        # Find top sectors
        top_sectors = sorted(
            sector_contributions.items(),
            key=lambda x: abs(x[1]['pct_contribution']),
            reverse=True
        )[:3]
        
        return {
            'total_return': total_return,
            'top_security_contributors': [
                {
                    'ticker': ticker,
                    'contribution': contrib['contribution'],
                    'pct_contribution': contrib['pct_contribution']
                }
                for ticker, contrib in top_securities
            ],
            'top_sector_contributors': [
                {
                    'sector': sector,
                    'contribution': contrib['contribution'],
                    'pct_contribution': contrib['pct_contribution']
                }
                for sector, contrib in top_sectors
            ],
            'diversification_score': self._calculate_diversification_score(security_contributions),
            'concentration_risk': self._assess_concentration_risk(security_contributions)
        }
    
    def _calculate_diversification_score(self, security_contributions: Dict[str, Dict[str, Any]]) -> float:
        """Calculate diversification score based on concentration."""
        contributions = [abs(c['pct_contribution']) for c in security_contributions.values()]
        
        # Herfindahl-Hirschman Index (concentration measure)
        hhi = sum(c ** 2 for c in contributions) / 10000
        
        # Convert to diversification score (inverse of HHI)
        if hhi == 0:
            return 100.0
        
        div_score = (1 - hhi) * 100
        return round(div_score, 2)
    
    def _assess_concentration_risk(self, security_contributions: Dict[str, Dict[str, Any]]) -> str:
        """Assess concentration risk level."""
        max_contribution = max(abs(c['pct_contribution']) for c in security_contributions.values())
        
        if max_contribution > 50:
            return 'high'
        elif max_contribution > 30:
            return 'medium'
        else:
            return 'low'


def create_attribution_engine() -> AttributionEngine:
    """Convenience function to create an attribution engine."""
    return AttributionEngine()


if __name__ == "__main__":
    # Example usage
    engine = create_attribution_engine()
    
    # Create sample data
    np.random.seed(42)
    tickers = ['AAPL', 'MSFT', 'GOOGL']
    n_days = 252
    returns = pd.DataFrame(
        np.random.randn(n_days, len(tickers)) * 0.01,
        index=pd.date_range('2020-01-01', periods=n_days),
        columns=tickers
    )
    weights = np.array([0.4, 0.3, 0.3])
    
    result = engine.calculate_attribution(returns, weights)
    print("Attribution analysis completed")
    print(f"Top security contributors: {result.attribution_summary['top_security_contributors']}")
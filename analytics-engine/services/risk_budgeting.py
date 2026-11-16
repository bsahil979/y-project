"""
Risk Budgeting Engine - Portfolio risk contribution analysis.

This module provides:
- Marginal contribution to risk (Marginal VaR)
- Component contribution to risk (Component VaR)
- Percentage contribution to total portfolio risk
- Risk budget allocation
- Risk limit enforcement

All calculations are mathematically derived from portfolio covariance and weights.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class RiskBudgetResult:
    """Result of risk budgeting analysis."""
    portfolio_volatility: float
    portfolio_variance: float
    marginal_contributions: Dict[str, Dict[str, Any]]
    component_contributions: Dict[str, Dict[str, Any]]
    percentage_contributions: Dict[str, float]
    risk_budget_analysis: Dict[str, Any]
    risk_limit_analysis: Dict[str, Any]
    diversification_ratio: float
    timestamp: str


class RiskBudgetingEngine:
    """
    Portfolio risk budgeting engine.
    """
    
    def __init__(self):
        """Initialize the risk budgeting engine."""
        logger.info("Risk Budgeting Engine initialized")
    
    def calculate_risk_budget(
        self,
        returns: pd.DataFrame,
        weights: np.ndarray,
        confidence_level: float = 0.95,
        risk_limits: Optional[Dict[str, float]] = None
    ) -> RiskBudgetResult:
        """
        Calculate comprehensive risk budget analysis.
        
        Args:
            returns: DataFrame with asset returns (columns = assets)
            weights: Array of portfolio weights
            confidence_level: Confidence level for VaR calculations
            risk_limits: Optional risk limits for each asset
            
        Returns:
            Comprehensive risk budget analysis
        """
        logger.info("Calculating risk budget")
        
        # Validate inputs
        if len(returns.columns) != len(weights):
            raise ValueError("Number of assets in returns must match length of weights")
        
        if abs(sum(weights) - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0 (current sum: {sum(weights)})")
        
        # Calculate covariance matrix (annualized)
        cov_matrix = returns.cov() * 252
        
        # Calculate portfolio variance and volatility
        portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
        portfolio_volatility = np.sqrt(portfolio_variance)
        
        # Calculate marginal VaR (Marginal Contribution to Risk)
        marginal_var = np.dot(cov_matrix, weights)
        
        # Calculate component VaR (Component Contribution to Risk)
        component_var = weights * marginal_var
        
        # Calculate percentage contributions
        percentage_contributions = {}
        for i, ticker in enumerate(returns.columns):
            pct_contrib = (component_var[i] / portfolio_variance * 100) if portfolio_variance > 0 else 0
            percentage_contributions[ticker] = pct_contrib
        
        # Build detailed marginal contributions
        marginal_contributions = {}
        for i, ticker in enumerate(returns.columns):
            marginal_contributions[ticker] = {
                'marginal_var': marginal_var[i],
                'weight': weights[i],
                'asset_volatility': np.sqrt(cov_matrix.iloc[i, i]),
                'correlation_with_portfolio': (
                    marginal_var[i] / (weights[i] * portfolio_variance) 
                    if weights[i] > 0 and portfolio_variance > 0 else 0
                )
            }
        
        # Build detailed component contributions
        component_contributions = {}
        for i, ticker in enumerate(returns.columns):
            component_contributions[ticker] = {
                'component_var': component_var[i],
                'weight': weights[i],
                'pct_contribution': percentage_contributions[ticker],
                'risk_adjusted_weight': component_var[i] / portfolio_variance if portfolio_variance > 0 else 0
            }
        
        # Risk budget analysis
        risk_budget_analysis = self._analyze_risk_budget(
            weights,
            component_var,
            portfolio_variance
        )
        
        # Risk limit analysis
        risk_limit_analysis = self._analyze_risk_limits(
            weights,
            component_var,
            portfolio_variance,
            risk_limits
        )
        
        # Diversification ratio
        diversification_ratio = self._calculate_diversification_ratio(
            weights,
            cov_matrix,
            portfolio_volatility
        )
        
        return RiskBudgetResult(
            portfolio_volatility=portfolio_volatility,
            portfolio_variance=portfolio_variance,
            marginal_contributions=marginal_contributions,
            component_contributions=component_contributions,
            percentage_contributions=percentage_contributions,
            risk_budget_analysis=risk_budget_analysis,
            risk_limit_analysis=risk_limit_analysis,
            diversification_ratio=diversification_ratio,
            timestamp=datetime.now().isoformat()
        )
    
    def _analyze_risk_budget(
        self,
        weights: np.ndarray,
        component_var: np.ndarray,
        portfolio_variance: float
    ) -> Dict[str, Any]:
        """Analyze risk budget allocation."""
        
        # Calculate risk contribution vs weight deviation
        risk_weight_deviation = {}
        for i, weight in enumerate(weights):
            risk_contrib = component_var[i] / portfolio_variance if portfolio_variance > 0 else 0
            deviation = risk_contrib - weight
            risk_weight_deviation[i] = {
                'weight': weight,
                'risk_contribution': risk_contrib,
                'deviation': deviation,
                'over_weighted_risk': deviation > 0.05,
                'under_weighted_risk': deviation < -0.05
            }
        
        # Identify risk concentration
        max_risk_contrib = max(component_var) / portfolio_variance if portfolio_variance > 0 else 0
        risk_concentration = 'high' if max_risk_contrib > 0.4 else 'medium' if max_risk_contrib > 0.25 else 'low'
        
        # Risk parity score (how close to equal risk contribution)
        ideal_risk_contrib = 1.0 / len(weights)
        risk_parity_score = 1.0 - np.std([c / portfolio_variance for c in component_var]) if portfolio_variance > 0 else 0
        
        return {
            'risk_weight_deviation': risk_weight_deviation,
            'max_risk_contribution': max_risk_contrib,
            'risk_concentration': risk_concentration,
            'risk_parity_score': risk_parity_score,
            'ideal_risk_contribution': ideal_risk_contrib
        }
    
    def _analyze_risk_limits(
        self,
        weights: np.ndarray,
        component_var: np.ndarray,
        portfolio_variance: float,
        risk_limits: Optional[Dict[str, float]]
    ) -> Dict[str, Any]:
        """Analyze risk limit compliance."""
        
        if risk_limits is None:
            return {
                'status': 'skipped',
                'reason': 'No risk limits provided'
            }
        
        # Check each asset's risk contribution against limits
        limit_compliance = {}
        for i, (ticker, weight) in enumerate(zip(range(len(weights)), weights)):
            risk_contrib = component_var[i] / portfolio_variance if portfolio_variance > 0 else 0
            limit = risk_limits.get(ticker, risk_limits.get('default', 0.3))
            
            limit_compliance[ticker] = {
                'risk_contribution': risk_contrib,
                'limit': limit,
                'compliant': risk_contrib <= limit,
                'excess': max(0, risk_contrib - limit)
            }
        
        # Overall compliance
        all_compliant = all(c['compliant'] for c in limit_compliance.values())
        
        return {
            'status': 'success',
            'all_compliant': all_compliant,
            'limit_compliance': limit_compliance,
            'violations': [k for k, v in limit_compliance.items() if not v['compliant']]
        }
    
    def _calculate_diversification_ratio(
        self,
        weights: np.ndarray,
        cov_matrix: pd.DataFrame,
        portfolio_volatility: float
    ) -> float:
        """
        Calculate diversification ratio.
        
        DR = (Sum of weighted volatilities) / Portfolio volatility
        DR > 1 indicates diversification benefit
        """
        if portfolio_volatility == 0:
            return 1.0
        
        # Calculate weighted sum of individual volatilities
        weighted_volatilities = 0
        for i, weight in enumerate(weights):
            asset_volatility = np.sqrt(cov_matrix.iloc[i, i])
            weighted_volatilities += weight * asset_volatility
        
        diversification_ratio = weighted_volatilities / portfolio_volatility
        
        return round(diversification_ratio, 4)
    
    def suggest_risk_parity_weights(
        self,
        returns: pd.DataFrame,
        max_iterations: int = 1000,
        tolerance: float = 1e-6
    ) -> Dict[str, Any]:
        """
        Suggest risk parity weights using iterative optimization.
        
        Risk parity aims to equalize risk contributions across all assets.
        
        Args:
            returns: DataFrame with asset returns
            max_iterations: Maximum iterations for optimization
            tolerance: Convergence tolerance
            
        Returns:
            Risk parity weights and analysis
        """
        logger.info("Calculating risk parity weights")
        
        n_assets = len(returns.columns)
        cov_matrix = returns.cov() * 252
        
        # Initialize equal weights
        weights = np.ones(n_assets) / n_assets
        
        # Iterative optimization
        for iteration in range(max_iterations):
            # Calculate risk contributions
            portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
            marginal_var = np.dot(cov_matrix, weights)
            component_var = weights * marginal_var
            
            # Calculate target risk contribution
            target_risk = portfolio_variance / n_assets
            
            # Adjust weights inversely proportional to risk contribution
            new_weights = weights * (target_risk / component_var)
            
            # Normalize weights
            new_weights = new_weights / new_weights.sum()
            
            # Check convergence
            if np.linalg.norm(new_weights - weights) < tolerance:
                logger.info(f"Converged in {iteration} iterations")
                break
            
            weights = new_weights
        
        # Calculate final risk contributions
        portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
        portfolio_volatility = np.sqrt(portfolio_variance)
        marginal_var = np.dot(cov_matrix, weights)
        component_var = weights * marginal_var
        
        # Calculate percentage contributions
        pct_contributions = {}
        for i, ticker in enumerate(returns.columns):
            pct_contributions[ticker] = (
                component_var[i] / portfolio_variance * 100
            ) if portfolio_variance > 0 else 0
        
        return {
            'weights': dict(zip(returns.columns, weights)),
            'portfolio_volatility': portfolio_volatility,
            'risk_contributions': pct_contributions,
            'iterations': iteration + 1,
            'converged': True
        }
    
    def calculate_ewma_covariance(
        self,
        returns: pd.DataFrame,
        lambda_param: float = 0.94
    ) -> pd.DataFrame:
        """
        Calculate EWMA (Exponentially Weighted Moving Average) covariance matrix.
        
        EWMA gives more weight to recent observations, useful for dynamic risk modeling.
        
        Args:
            returns: DataFrame with asset returns
            lambda_param: Decay factor (0.94 is standard)
            
        Returns:
            EWMA covariance matrix
        """
        n_assets = len(returns.columns)
        n_obs = len(returns)
        
        # Initialize covariance matrix
        ewma_cov = returns.cov()
        
        # Apply EWMA decay
        for t in range(1, n_obs):
            decay = lambda_param ** t
            recent_cov = returns.iloc[-t-1:].cov()
            ewma_cov = decay * ewma_cov + (1 - decay) * recent_cov
        
        return ewma_cov


def create_risk_budgeting_engine() -> RiskBudgetingEngine:
    """Convenience function to create a risk budgeting engine."""
    return RiskBudgetingEngine()


if __name__ == "__main__":
    # Example usage
    engine = create_risk_budgeting_engine()
    
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
    
    result = engine.calculate_risk_budget(returns, weights)
    print("Risk budgeting analysis completed")
    print(f"Portfolio volatility: {result.portfolio_volatility*100:.2f}%")
    print(f"Risk contributions: {result.percentage_contributions}")
    print(f"Diversification ratio: {result.diversification_ratio:.2f}")
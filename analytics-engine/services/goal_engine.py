"""
Goal Engine - Goal-based portfolio analysis with Monte Carlo simulation.

This module provides:
- Goal probability analysis
- Required return calculations
- Monte Carlo distribution simulation
- Shortfall probability
- Required contribution analysis
- Interactive assumption adjustment
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class GoalInput:
    """Input for goal analysis."""
    current_capital: float
    monthly_contribution: float
    target_amount: float
    time_horizon_years: int
    risk_tolerance: str  # 'conservative', 'moderate', 'aggressive'
    goal_name: str = "Financial Goal"


@dataclass
class GoalResult:
    """Result of goal analysis."""
    goal_input: GoalInput
    required_annual_return: float
    expected_annual_return: float
    probability_of_success: float
    shortfall_probability: float
    expected_future_value: float
    required_monthly_contribution: float
    monte_carlo_distribution: Dict[str, Any]
    sensitivity_analysis: Dict[str, Any]
    goal_feasibility: str
    recommendations: List[str]
    timestamp: str


class GoalEngine:
    """
    Goal-based portfolio analysis engine with Monte Carlo simulation.
    """
    
    def __init__(self):
        """Initialize the goal engine."""
        logger.info("Goal Engine initialized")
    
    def analyze_goal(
        self,
        goal_input: GoalInput,
        portfolio_returns: pd.Series,
        n_simulations: int = 10000,
        confidence_level: float = 0.95
    ) -> GoalResult:
        """
        Analyze goal feasibility with Monte Carlo simulation.
        
        Args:
            goal_input: Goal parameters
            portfolio_returns: Historical portfolio returns
            n_simulations: Number of Monte Carlo simulations
            confidence_level: Confidence level for intervals
            
        Returns:
            Comprehensive goal analysis
        """
        logger.info(f"Analyzing goal: {goal_input.goal_name}")
        
        # Calculate historical return statistics
        annual_return = portfolio_returns.mean() * 252
        annual_volatility = portfolio_returns.std() * np.sqrt(252)
        
        # Adjust expected return based on risk tolerance
        expected_return = self._adjust_return_for_risk_tolerance(
            annual_return,
            goal_input.risk_tolerance
        )
        
        # Calculate required return to achieve goal
        required_return = self._calculate_required_return(
            goal_input.current_capital,
            goal_input.monthly_contribution,
            goal_input.target_amount,
            goal_input.time_horizon_years
        )
        
        # Run Monte Carlo simulation
        monte_carlo_results = self._run_monte_carlo_simulation(
            goal_input,
            expected_return,
            annual_volatility,
            n_simulations
        )
        
        # Calculate probability of success
        probability_of_success = monte_carlo_results['success_rate']
        shortfall_probability = 1 - probability_of_success
        
        # Calculate expected future value
        expected_future_value = monte_carlo_results['expected_value']
        
        # Calculate required monthly contribution
        required_contribution = self._calculate_required_contribution(
            goal_input.current_capital,
            goal_input.target_amount,
            goal_input.time_horizon_years,
            expected_return
        )
        
        # Sensitivity analysis
        sensitivity_analysis = self._perform_sensitivity_analysis(
            goal_input,
            expected_return,
            annual_volatility
        )
        
        # Assess goal feasibility
        goal_feasibility = self._assess_feasibility(
            probability_of_success,
            required_return,
            expected_return
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            goal_input,
            probability_of_success,
            required_return,
            expected_return,
            required_contribution
        )
        
        return GoalResult(
            goal_input=goal_input,
            required_annual_return=required_return,
            expected_annual_return=expected_return,
            probability_of_success=probability_of_success,
            shortfall_probability=shortfall_probability,
            expected_future_value=expected_future_value,
            required_monthly_contribution=required_contribution,
            monte_carlo_distribution=monte_carlo_results,
            sensitivity_analysis=sensitivity_analysis,
            goal_feasibility=goal_feasibility,
            recommendations=recommendations,
            timestamp=datetime.now().isoformat()
        )
    
    def _adjust_return_for_risk_tolerance(
        self,
        historical_return: float,
        risk_tolerance: str
    ) -> float:
        """Adjust expected return based on risk tolerance."""
        risk_adjustments = {
            'conservative': -0.02,  # Conservative: reduce return by 2%
            'moderate': 0.0,       # Moderate: use historical return
            'aggressive': 0.02     # Aggressive: increase return by 2%
        }
        
        adjustment = risk_adjustments.get(risk_tolerance, 0.0)
        adjusted_return = historical_return + adjustment
        
        # Ensure return is reasonable
        return max(min(adjusted_return, 0.25), -0.10)
    
    def _calculate_required_return(
        self,
        current_capital: float,
        monthly_contribution: float,
        target_amount: float,
        time_horizon_years: int
    ) -> float:
        """
        Calculate required annual return to achieve goal.
        
        Solves for r in:
        target = current * (1+r)^n + contribution * [(1+r)^n - 1] / r
        
        Using numerical approximation.
        """
        n_months = time_horizon_years * 12
        annual_contribution = monthly_contribution * 12
        
        # Binary search for required return
        low, high = -0.5, 0.5
        for _ in range(100):
            mid = (low + high) / 2
            future_value = (
                current_capital * (1 + mid) ** time_horizon_years +
                annual_contribution * ((1 + mid) ** time_horizon_years - 1) / mid
                if mid != 0 else
                current_capital + annual_contribution * time_horizon_years
            )
            
            if future_value < target_amount:
                low = mid
            else:
                high = mid
            
            if abs(high - low) < 1e-6:
                break
        
        return (low + high) / 2
    
    def _run_monte_carlo_simulation(
        self,
        goal_input: GoalInput,
        expected_return: float,
        volatility: float,
        n_simulations: int
    ) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation for goal achievement.
        
        Simulates n_simulations possible future paths and calculates
        the probability of achieving the goal.
        """
        n_months = goal_input.time_horizon_years * 12
        monthly_return = expected_return / 12
        monthly_volatility = volatility / np.sqrt(12)
        
        # Generate random returns for each simulation
        random_returns = np.random.normal(
            monthly_return,
            monthly_volatility,
            (n_simulations, n_months)
        )
        
        # Simulate portfolio growth for each path
        final_values = np.zeros(n_simulations)
        
        for i in range(n_simulations):
            value = goal_input.current_capital
            for month in range(n_months):
                value = value * (1 + random_returns[i, month]) + goal_input.monthly_contribution
            final_values[i] = value
        
        # Calculate statistics
        success_rate = np.mean(final_values >= goal_input.target_amount)
        expected_value = np.mean(final_values)
        median_value = np.median(final_values)
        
        # Calculate percentiles
        percentiles = {
            'p5': np.percentile(final_values, 5),
            'p10': np.percentile(final_values, 10),
            'p25': np.percentile(final_values, 25),
            'p50': np.percentile(final_values, 50),
            'p75': np.percentile(final_values, 75),
            'p90': np.percentile(final_values, 90),
            'p95': np.percentile(final_values, 95)
        }
        
        return {
            'success_rate': success_rate,
            'expected_value': expected_value,
            'median_value': median_value,
            'percentiles': percentiles,
            'n_simulations': n_simulations,
            'distribution': final_values.tolist()
        }
    
    def _calculate_required_contribution(
        self,
        current_capital: float,
        target_amount: float,
        time_horizon_years: int,
        expected_return: float
    ) -> float:
        """
        Calculate required monthly contribution to achieve goal.
        
        Solves for PMT in:
        target = current * (1+r)^n + PMT * n * 12
        """
        future_capital = current_capital * (1 + expected_return) ** time_horizon_years
        shortfall = target_amount - future_capital
        
        if shortfall <= 0:
            return 0.0
        
        n_months = time_horizon_years * 12
        
        # Simplified calculation (ignoring time value of contributions)
        required_monthly = shortfall / n_months
        
        # More accurate calculation with time value
        if expected_return != 0:
            monthly_return = expected_return / 12
            required_monthly = (
                shortfall * monthly_return /
                ((1 + monthly_return) ** n_months - 1)
            )
        
        return max(required_monthly, 0.0)
    
    def _perform_sensitivity_analysis(
        self,
        goal_input: GoalInput,
        expected_return: float,
        volatility: float
    ) -> Dict[str, Any]:
        """Perform sensitivity analysis on key parameters."""
        
        # Test different time horizons
        time_horizon_scenarios = {}
        for years in [5, 10, 15, 20, 25, 30]:
            if years <= goal_input.time_horizon_years:
                required_return = self._calculate_required_return(
                    goal_input.current_capital,
                    goal_input.monthly_contribution,
                    goal_input.target_amount,
                    years
                )
                time_horizon_scenarios[f'{years}_years'] = {
                    'required_return': required_return,
                    'feasible': required_return <= expected_return + 0.05
                }
        
        # Test different contribution levels
        contribution_scenarios = {}
        for multiplier in [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]:
            contribution = goal_input.monthly_contribution * multiplier
            required_return = self._calculate_required_return(
                goal_input.current_capital,
                contribution,
                goal_input.target_amount,
                goal_input.time_horizon_years
            )
            contribution_scenarios[f'{multiplier}x'] = {
                'monthly_contribution': contribution,
                'required_return': required_return,
                'feasible': required_return <= expected_return + 0.05
            }
        
        # Test different target amounts
        target_scenarios = {}
        for multiplier in [0.75, 0.9, 1.0, 1.1, 1.25, 1.5]:
            target = goal_input.target_amount * multiplier
            required_return = self._calculate_required_return(
                goal_input.current_capital,
                goal_input.monthly_contribution,
                target,
                goal_input.time_horizon_years
            )
            target_scenarios[f'{multiplier}x'] = {
                'target_amount': target,
                'required_return': required_return,
                'feasible': required_return <= expected_return + 0.05
            }
        
        return {
            'time_horizon_scenarios': time_horizon_scenarios,
            'contribution_scenarios': contribution_scenarios,
            'target_scenarios': target_scenarios
        }
    
    def _assess_feasibility(
        self,
        probability_of_success: float,
        required_return: float,
        expected_return: float
    ) -> str:
        """Assess overall goal feasibility."""
        
        if probability_of_success >= 0.8:
            return 'highly_likely'
        elif probability_of_success >= 0.6:
            return 'likely'
        elif probability_of_success >= 0.4:
            return 'moderate'
        elif probability_of_success >= 0.2:
            return 'unlikely'
        else:
            return 'highly_unlikely'
    
    def _generate_recommendations(
        self,
        goal_input: GoalInput,
        probability_of_success: float,
        required_return: float,
        expected_return: float,
        required_contribution: float
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if probability_of_success < 0.5:
            recommendations.append(
                f"Goal has {probability_of_success*100:.1f}% probability of success. "
                "Consider extending time horizon or increasing contributions."
            )
        
        if required_return > expected_return + 0.05:
            recommendations.append(
                f"Required return ({required_return*100:.1f}%) exceeds expected return "
                f"({expected_return*100:.1f}%). Consider higher-risk allocation."
            )
        
        if required_contribution > goal_input.monthly_contribution * 1.5:
            recommendations.append(
                f"Required monthly contribution (${required_contribution:.0f}) is significantly "
                f"higher than current (${goal_input.monthly_contribution:.0f}). "
                "Consider increasing savings rate."
            )
        
        if probability_of_success >= 0.7:
            recommendations.append(
                f"Goal is on track with {probability_of_success*100:.1f}% probability of success. "
                "Maintain current strategy."
            )
        
        if goal_input.risk_tolerance == 'conservative' and required_return > 0.06:
            recommendations.append(
                "Conservative risk tolerance may not support required return. "
                "Consider increasing time horizon or target amount."
            )
        
        return recommendations


def create_goal_engine() -> GoalEngine:
    """Convenience function to create a goal engine."""
    return GoalEngine()


if __name__ == "__main__":
    # Example usage
    engine = create_goal_engine()
    
    # Create sample goal
    goal_input = GoalInput(
        current_capital=100000,
        monthly_contribution=1000,
        target_amount=500000,
        time_horizon_years=10,
        risk_tolerance='moderate',
        goal_name='Retirement'
    )
    
    # Create sample returns
    np.random.seed(42)
    n_days = 252
    portfolio_returns = pd.Series(
        np.random.randn(n_days) * 0.01 + 0.0003,
        index=pd.date_range('2020-01-01', periods=n_days)
    )
    
    result = engine.analyze_goal(goal_input, portfolio_returns)
    print("Goal analysis completed")
    print(f"Probability of success: {result.probability_of_success*100:.1f}%")
    print(f"Required annual return: {result.required_annual_return*100:.2f}%")
    print(f"Expected annual return: {result.expected_annual_return*100:.2f}%")
    print(f"Goal feasibility: {result.goal_feasibility}")
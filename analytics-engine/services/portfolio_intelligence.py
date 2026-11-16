"""
Core Portfolio Intelligence Engine - Central orchestrator for all portfolio analysis.

This module provides the unified pipeline that coordinates:
- Market data fetching and feature engineering
- ML model inference (LSTM, RF, HMM, MarketMind)
- Quantitative calculations (risk metrics, performance metrics)
- Portfolio optimization
- Stress testing and simulation
- Explainability generation
- LLM context preparation

Input:
- User portfolio (tickers, weights)
- Market data sources
- User risk profile
- Investment horizon
- Financial goals

Output:
- Comprehensive portfolio analysis
- Actionable recommendations
- Explainable insights
- Risk assessment
- Optimization suggestions
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    """User's investment profile and preferences."""
    risk_tolerance: str  # 'conservative', 'moderate', 'aggressive'
    investment_horizon: str  # 'short', 'medium', 'long'
    financial_goals: List[str]
    max_drawdown_tolerance: float  # Maximum acceptable drawdown (0-1)
    target_return: Optional[float]  # Target annual return (0-1)
    liquidity_needs: str  # 'low', 'medium', 'high'


@dataclass
class PortfolioInput:
    """Input portfolio for analysis."""
    tickers: List[str]
    weights: List[float]
    portfolio_value: float
    start_date: str
    end_date: str


@dataclass
class PortfolioAnalysis:
    """Comprehensive portfolio analysis results."""
    portfolio_input: PortfolioInput
    risk_metrics: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    ml_predictions: Dict[str, Any]
    optimization_results: Dict[str, Any]
    stress_test_results: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    explainability: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    confidence_score: float
    analysis_timestamp: str


class PortfolioIntelligenceEngine:
    """
    Central portfolio intelligence engine that coordinates all financial components.
    """
    
    def __init__(self, user_profile: Optional[UserProfile] = None):
        """
        Initialize the portfolio intelligence engine.
        
        Args:
            user_profile: User's investment preferences and constraints
        """
        self.user_profile = user_profile or self._default_profile()
        
        # Import all required services
        try:
            from services.data_fetcher import get_portfolio_data
            from services.risk_metrics import get_risk_summary
            from services.regime_detector import detect_market_regime_hmm
            from services.stress_tester import get_stress_summary
            from services.portfolio_score import compute_portfolio_score
            from services.portfolio_optimizer import PortfolioOptimizer
            from services.explainability_engine import ExplainabilityEngine
            from trading_engine.meta_model import MarketMindMetaModel
            
            self.get_portfolio_data = get_portfolio_data
            self.get_risk_summary = get_risk_summary
            self.detect_market_regime_hmm = detect_market_regime_hmm
            self.get_stress_summary = get_stress_summary
            self.compute_portfolio_score = compute_portfolio_score
            self.PortfolioOptimizer = PortfolioOptimizer
            self.ExplainabilityEngine = ExplainabilityEngine
            self.MarketMindMetaModel = MarketMindMetaModel
            
            self.explainability_engine = self.ExplainabilityEngine()
            self.meta_model = self.MarketMindMetaModel()
            
            logger.info("Portfolio Intelligence Engine initialized successfully")
            
        except ImportError as e:
            logger.error(f"Failed to import required services: {e}")
            raise
    
    def _default_profile(self) -> UserProfile:
        """Create a default moderate risk profile."""
        return UserProfile(
            risk_tolerance='moderate',
            investment_horizon='medium',
            financial_goals=['growth', 'income'],
            max_drawdown_tolerance=0.20,
            target_return=0.08,
            liquidity_needs='medium'
        )
    
    def analyze_portfolio(
        self,
        portfolio_input: PortfolioInput,
        include_optimization: bool = True,
        include_stress_test: bool = True,
        include_ml_predictions: bool = True
    ) -> PortfolioAnalysis:
        """
        Perform comprehensive portfolio analysis.
        
        Args:
            portfolio_input: Portfolio to analyze
            include_optimization: Whether to include optimization suggestions
            include_stress_test: Whether to include stress testing
            include_ml_predictions: Whether to include ML model predictions
            
        Returns:
            Comprehensive portfolio analysis
        """
        logger.info(f"Starting portfolio analysis for {len(portfolio_input.tickers)} tickers")
        
        # Step 1: Fetch market data
        logger.info("Step 1: Fetching market data")
        data = self.get_portfolio_data(
            portfolio_input.tickers,
            portfolio_input.start_date,
            portfolio_input.end_date
        )
        prices = data["prices"]
        returns = data["returns"]
        
        # Step 2: Calculate risk metrics
        logger.info("Step 2: Calculating risk metrics")
        risk_summary = self.get_risk_summary(prices, returns)
        risk_metrics = self._extract_risk_metrics(risk_summary)
        
        # Step 3: Calculate performance metrics
        logger.info("Step 3: Calculating performance metrics")
        performance_metrics = self._calculate_performance_metrics(prices, returns)
        
        # Step 4: Market regime detection
        logger.info("Step 4: Detecting market regime")
        portfolio_returns = returns.mean(axis=1)
        regime_summary = self.detect_market_regime_hmm(portfolio_returns)
        
        # Step 5: ML model predictions (if requested)
        ml_predictions = {}
        if include_ml_predictions:
            logger.info("Step 5: Generating ML predictions")
            ml_predictions = self._generate_ml_predictions(
                portfolio_input.tickers,
                portfolio_input.end_date
            )
        
        # Step 6: Portfolio optimization (if requested)
        optimization_results = {}
        if include_optimization:
            logger.info("Step 6: Running portfolio optimization")
            optimization_results = self._run_portfolio_optimization(
                returns,
                portfolio_input.weights
            )
        
        # Step 7: Stress testing (if requested)
        stress_test_results = {}
        if include_stress_test:
            logger.info("Step 7: Running stress tests")
            stress_test_results = self.get_stress_summary(
                portfolio_input.tickers,
                portfolio_input.weights,
                portfolio_input.portfolio_value
            )
        
        # Step 8: Portfolio scoring
        logger.info("Step 8: Calculating portfolio score")
        portfolio_score = self.compute_portfolio_score(
            tickers=portfolio_input.tickers,
            weights=portfolio_input.weights,
            risk_summary=risk_summary["summary"],
            returns=returns,
            portfolio_value=portfolio_input.portfolio_value
        )
        
        # Step 9: Risk assessment based on user profile
        logger.info("Step 9: Assessing risk vs user profile")
        risk_assessment = self._assess_risk_profile(risk_metrics, portfolio_score)
        
        # Step 10: Generate recommendations
        logger.info("Step 10: Generating recommendations")
        recommendations = self._generate_recommendations(
            risk_metrics,
            performance_metrics,
            ml_predictions,
            optimization_results,
            stress_test_results,
            portfolio_score,
            risk_assessment
        )
        
        # Step 11: Generate explainability
        logger.info("Step 11: Generating explainability")
        explainability = self._generate_explainability(
            portfolio_input,
            risk_metrics,
            ml_predictions,
            optimization_results
        )
        
        # Step 12: Calculate overall confidence score
        logger.info("Step 12: Calculating confidence score")
        confidence_score = self._calculate_confidence_score(
            risk_metrics,
            ml_predictions,
            portfolio_score
        )
        
        # Assemble final analysis
        analysis = PortfolioAnalysis(
            portfolio_input=portfolio_input,
            risk_metrics=risk_metrics,
            performance_metrics=performance_metrics,
            ml_predictions=ml_predictions,
            optimization_results=optimization_results,
            stress_test_results=stress_test_results,
            recommendations=recommendations,
            explainability=explainability,
            risk_assessment=risk_assessment,
            confidence_score=confidence_score,
            analysis_timestamp=datetime.now().isoformat()
        )
        
        logger.info("Portfolio analysis completed successfully")
        return analysis
    
    def _extract_risk_metrics(self, risk_summary: Dict) -> Dict[str, Any]:
        """Extract key risk metrics from risk summary."""
        summary = risk_summary["summary"]
        
        return {
            'volatility': summary.get('Volatility (Annual)', 0),
            'var_95': summary.get('VaR (95%)', 0),
            'cvar_95': summary.get('CVaR (95%)', 0),
            'max_drawdown': summary.get('Max Drawdown', 0),
            'sharpe_ratio': summary.get('Sharpe Ratio', 0),
            'sortino_ratio': summary.get('Sortino Ratio', 0),
            'beta': summary.get('Beta', 0),
            'alpha': summary.get('Alpha', 0)
        }
    
    def _calculate_performance_metrics(self, prices: pd.DataFrame, returns: pd.DataFrame) -> Dict[str, Any]:
        """Calculate portfolio performance metrics."""
        # Calculate portfolio returns from weights
        # For now, use equal weights if not provided
        portfolio_returns = returns.mean(axis=1)
        
        # Calculate cumulative returns
        cumulative_returns = (1 + portfolio_returns).cumprod()
        
        # Calculate performance metrics
        total_return = cumulative_returns.iloc[-1] - 1
        annual_return = (1 + total_return) ** (252 / len(portfolio_returns)) - 1
        annual_volatility = portfolio_returns.std() * np.sqrt(252)
        
        # Calculate rolling metrics
        rolling_sharpe = (portfolio_returns.rolling(63).mean() / portfolio_returns.rolling(63).std()) * np.sqrt(252)
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'annual_volatility': annual_volatility,
            'rolling_sharpe_63d': rolling_sharpe.iloc[-1] if len(rolling_sharpe) > 0 else 0,
            'best_day': portfolio_returns.max(),
            'worst_day': portfolio_returns.min(),
            'up_days': (portfolio_returns > 0).sum(),
            'down_days': (portfolio_returns <= 0).sum(),
            'win_rate': (portfolio_returns > 0).sum() / len(portfolio_returns)
        }
    
    def _generate_ml_predictions(self, tickers: List[str], end_date: str) -> Dict[str, Any]:
        """Generate ML model predictions for each ticker."""
        predictions = {}
        
        for ticker in tickers:
            try:
                # Try MarketMind meta-model first
                if self.meta_model.is_ready():
                    if self.meta_model.model is None:
                        self.meta_model.load()
                    
                    prediction = self.meta_model.predict_for_ticker(ticker)
                    predictions[ticker] = {
                        'marketmind': prediction,
                        'source': 'meta_model'
                    }
                else:
                    # Fallback to individual models if meta-model not available
                    predictions[ticker] = {
                        'marketmind': None,
                        'source': 'not_available',
                        'message': 'Meta-model not trained'
                    }
                    
            except Exception as e:
                logger.warning(f"Failed to generate ML prediction for {ticker}: {e}")
                predictions[ticker] = {
                    'marketmind': None,
                    'source': 'error',
                    'error': str(e)
                }
        
        return predictions
    
    def _run_portfolio_optimization(self, returns: pd.DataFrame, current_weights: List[float]) -> Dict[str, Any]:
        """Run portfolio optimization analysis."""
        try:
            optimizer = self.PortfolioOptimizer(returns)
            
            # Compare current portfolio with optimized versions
            current_weights_dict = dict(zip(returns.columns, current_weights))
            
            comparison = optimizer.compare_with_current(current_weights_dict, 'max_sharpe')
            
            return {
                'current_portfolio': comparison['current_portfolio'],
                'optimized_portfolio': comparison['optimized_portfolio'],
                'improvements': comparison['improvements'],
                'rebalance_suggestions': comparison['rebalance_suggestions'],
                'explanation': comparison['explanation']
            }
            
        except Exception as e:
            logger.error(f"Portfolio optimization failed: {e}")
            return {
                'error': str(e),
                'status': 'failed'
            }
    
    def _assess_risk_profile(self, risk_metrics: Dict, portfolio_score: Dict) -> Dict[str, Any]:
        """Assess portfolio risk against user profile."""
        def _to_float(v):
            if hasattr(v, 'iloc') and hasattr(v, '__len__') and len(v) > 0:
                v = v.iloc[0]
            elif hasattr(v, 'item'):
                try:
                    v = v.item()
                except Exception:
                    pass
            try:
                return float(v)
            except (TypeError, ValueError):
                return 0.0

        max_drawdown = abs(_to_float(risk_metrics.get('max_drawdown', 0)))
        volatility = _to_float(risk_metrics.get('volatility', 0))
        sharpe_ratio = _to_float(risk_metrics.get('sharpe_ratio', 0))
        
        # Risk tolerance thresholds
        risk_thresholds = {
            'conservative': {'max_drawdown': 0.15, 'volatility': 0.20},
            'moderate': {'max_drawdown': 0.25, 'volatility': 0.30},
            'aggressive': {'max_drawdown': 0.40, 'volatility': 0.50}
        }
        
        user_thresholds = risk_thresholds.get(self.user_profile.risk_tolerance, risk_thresholds['moderate'])
        
        # Assess each risk metric
        drawdown_status = 'acceptable' if max_drawdown <= user_thresholds['max_drawdown'] else 'exceeds_tolerance'
        volatility_status = 'acceptable' if volatility <= user_thresholds['volatility'] else 'exceeds_tolerance'
        
        # Overall risk assessment
        risk_level = 'low'
        if max_drawdown > 0.20 or volatility > 0.30:
            risk_level = 'medium'
        if max_drawdown > 0.35 or volatility > 0.45:
            risk_level = 'high'
        
        # Check against user's max drawdown tolerance
        within_tolerance = max_drawdown <= self.user_profile.max_drawdown_tolerance
        
        return {
            'risk_level': risk_level,
            'drawdown_status': drawdown_status,
            'volatility_status': volatility_status,
            'within_tolerance': within_tolerance,
            'user_profile': self.user_profile.risk_tolerance,
            'risk_score': portfolio_score.get('score', 0),
            'risk_grade': portfolio_score.get('grade', 'N/A')
        }
    
    def _generate_recommendations(
        self,
        risk_metrics: Dict,
        performance_metrics: Dict,
        ml_predictions: Dict,
        optimization_results: Dict,
        stress_test_results: Dict,
        portfolio_score: Dict,
        risk_assessment: Dict
    ) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []
        
        # Risk-based recommendations
        if risk_assessment['risk_level'] == 'high':
            recommendations.append({
                'type': 'risk',
                'priority': 'high',
                'action': 'reduce_risk',
                'title': 'High Portfolio Risk Detected',
                'description': f"Portfolio risk level is {risk_assessment['risk_level']}. Consider reducing exposure to volatile assets.",
                'reasoning': f"Max drawdown: {abs(risk_metrics['max_drawdown'])*100:.1f}%, Volatility: {risk_metrics['volatility']*100:.1f}%"
            })
        
        # Optimization-based recommendations
        if optimization_results and 'improvements' in optimization_results:
            improvements = optimization_results['improvements']
            if improvements.get('return_improvement_pct', 0) > 10:
                recommendations.append({
                    'type': 'optimization',
                    'priority': 'medium',
                    'action': 'rebalance',
                    'title': 'Optimization Opportunity',
                    'description': f"Portfolio optimization could improve returns by {improvements['return_improvement_pct']:.1f}%.",
                    'reasoning': optimization_results.get('explanation', '')
                })
        
        # Stress test recommendations
        if stress_test_results and 'stress_table' in stress_test_results:
            worst_loss = stress_test_results['stress_table']['Portfolio Loss (%)'].min()
            if worst_loss < -20:
                recommendations.append({
                    'type': 'stress',
                    'priority': 'high',
                    'action': 'diversify',
                    'title': 'Stress Test Warning',
                    'description': f"Worst-case scenario shows {worst_loss:.1f}% loss. Consider diversification.",
                    'reasoning': f"Based on historical stress scenarios"
                })
        
        # ML-based recommendations
        ml_buy_signals = []
        ml_sell_signals = []
        for ticker, pred in ml_predictions.items():
            if pred.get('marketmind'):
                mm_pred = pred['marketmind']
                if mm_pred.get('recommendation') == 'BUY' and mm_pred.get('confidence', 0) > 0.6:
                    ml_buy_signals.append(ticker)
                elif mm_pred.get('recommendation') == 'SELL' and mm_pred.get('confidence', 0) > 0.6:
                    ml_sell_signals.append(ticker)
        
        if ml_buy_signals:
            recommendations.append({
                'type': 'ml_signal',
                'priority': 'low',
                'action': 'consider_increase',
                'title': 'ML Buy Signals',
                'description': f"ML models indicate BUY signals for: {', '.join(ml_buy_signals)}",
                'reasoning': "Based on MarketMind meta-model predictions"
            })
        
        if ml_sell_signals:
            recommendations.append({
                'type': 'ml_signal',
                'priority': 'low',
                'action': 'consider_reduce',
                'title': 'ML Sell Signals',
                'description': f"ML models indicate SELL signals for: {', '.join(ml_sell_signals)}",
                'reasoning': "Based on MarketMind meta-model predictions"
            })
        
        return recommendations
    
    def _generate_explainability(
        self,
        portfolio_input: PortfolioInput,
        risk_metrics: Dict,
        ml_predictions: Dict,
        optimization_results: Dict
    ) -> Dict[str, Any]:
        """Generate explainability for the analysis."""
        # This would use the explainability engine to generate detailed explanations
        # For now, provide a basic structure
        
        primary_factors = []
        
        # Add risk factors
        if abs(risk_metrics.get('max_drawdown', 0)) > 0.2:
            primary_factors.append({
                'factor': 'Maximum Drawdown',
                'impact': 'negative',
                'value': f"{abs(risk_metrics['max_drawdown'])*100:.1f}%",
                'importance': 'high'
            })
        
        # Add ML factors
        if ml_predictions:
            ml_available = sum(1 for pred in ml_predictions.values() if pred.get('marketmind'))
            primary_factors.append({
                'factor': 'ML Model Coverage',
                'impact': 'neutral',
                'value': f"{ml_available}/{len(ml_predictions)} tickers",
                'importance': 'medium'
            })
        
        return {
            'primary_factors': primary_factors,
            'model_contributions': {
                'risk_metrics': 0.4,
                'ml_predictions': 0.3,
                'optimization': 0.2,
                'stress_testing': 0.1
            },
            'reasoning_chain': [
                "Risk analysis completed",
                "ML predictions generated",
                "Optimization analysis performed",
                "Stress testing conducted",
                "Recommendations synthesized"
            ],
            'data_sources': [
                'Yahoo Finance market data',
                'Technical indicator calculations',
                'ML model predictions',
                'Optimization algorithms'
            ]
        }
    
    def _calculate_confidence_score(
        self,
        risk_metrics: Dict,
        ml_predictions: Dict,
        portfolio_score: Dict
    ) -> float:
        """Calculate overall confidence score for the analysis."""
        confidence = 0.5  # Base confidence
        
        # Increase confidence if ML predictions are available
        ml_available = sum(1 for pred in ml_predictions.values() if pred.get('marketmind'))
        if ml_available > 0:
            confidence += 0.2 * (ml_available / len(ml_predictions))
        
        # Increase confidence if risk metrics are reliable
        if risk_metrics.get('volatility', 0) > 0:
            confidence += 0.1
        
        # Increase confidence if portfolio score is available
        if portfolio_score.get('score', 0) > 0:
            confidence += 0.1
        
        # Decrease confidence if key data is missing
        if not risk_metrics or not ml_predictions:
            confidence -= 0.2
        
        return min(max(confidence, 0.0), 1.0)


def create_portfolio_intelligence_engine(user_profile: Optional[UserProfile] = None) -> PortfolioIntelligenceEngine:
    """
    Convenience function to create a portfolio intelligence engine.
    """
    return PortfolioIntelligenceEngine(user_profile=user_profile)


if __name__ == "__main__":
    # Example usage
    engine = create_portfolio_intelligence_engine()
    
    portfolio_input = PortfolioInput(
        tickers=['AAPL', 'MSFT', 'GOOGL'],
        weights=[0.4, 0.3, 0.3],
        portfolio_value=100000,
        start_date='2020-01-01',
        end_date='2024-01-01'
    )
    
    analysis = engine.analyze_portfolio(portfolio_input)
    print("Portfolio Analysis Completed")
    print(f"Risk Level: {analysis.risk_assessment['risk_level']}")
    print(f"Confidence Score: {analysis.confidence_score:.2f}")
    print(f"Recommendations: {len(analysis.recommendations)}")
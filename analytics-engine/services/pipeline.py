"""
Canonical Portfolio Analysis Pipeline - Central orchestrator for all portfolio analysis.

This module provides the unified pipeline that coordinates:
- Data validation and feature engineering
- Portfolio analytics
- ML model inference
- Risk engine
- Stress engine
- Optimization
- Recommendation engine
- Explainability
- LLM advisor preparation

Every component consumes and produces structured data.
No calculations are duplicated between services.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class PipelineInput:
    """Standardized input for the portfolio analysis pipeline."""
    tickers: List[str]
    weights: List[float]
    portfolio_value: float
    start_date: str
    end_date: str
    benchmark_ticker: Optional[str] = None
    user_profile: Optional[Dict[str, Any]] = None


@dataclass
class PipelineOutput:
    """Standardized output from the portfolio analysis pipeline."""
    input: PipelineInput
    portfolio_analytics: Dict[str, Any]
    ml_predictions: Dict[str, Any]
    risk_analysis: Dict[str, Any]
    benchmark_comparison: Optional[Dict[str, Any]]
    attribution_analysis: Optional[Dict[str, Any]]
    risk_budget: Optional[Dict[str, Any]]
    stress_test: Dict[str, Any]
    optimization: Optional[Dict[str, Any]]
    goal_analysis: Optional[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    explainability: Dict[str, Any]
    llm_context: Dict[str, Any]
    pipeline_metadata: Dict[str, Any]
    timestamp: str


class PortfolioAnalysisPipeline:
    """
    Canonical portfolio analysis pipeline that coordinates all financial engines.
    """
    
    def __init__(self):
        """Initialize the pipeline with all required engines."""
        self._initialize_engines()
        logger.info("Portfolio Analysis Pipeline initialized")
    
    def _initialize_engines(self):
        """Initialize all required financial engines."""
        try:
            # Import engines
            from services.data_fetcher import get_portfolio_data
            from services.risk_metrics import get_risk_summary
            from services.regime_detector import detect_market_regime_hmm
            from services.stress_tester import get_stress_summary
            from services.portfolio_score import compute_portfolio_score
            from services.portfolio_optimizer import PortfolioOptimizer
            from services.explainability_engine import ExplainabilityEngine
            from services.benchmark_engine import BenchmarkEngine
            from services.attribution_engine import AttributionEngine
            from services.risk_budgeting import RiskBudgetingEngine
            from services.goal_engine import GoalEngine
            from services.recommendation_engine import CentralRecommendationEngine
            from trading_engine.meta_model import MarketMindMetaModel
            
            # Store engine references
            self.get_portfolio_data = get_portfolio_data
            self.get_risk_summary = get_risk_summary
            self.detect_market_regime_hmm = detect_market_regime_hmm
            self.get_stress_summary = get_stress_summary
            self.compute_portfolio_score = compute_portfolio_score
            self.PortfolioOptimizer = PortfolioOptimizer
            self.ExplainabilityEngine = ExplainabilityEngine
            self.MarketMindMetaModel = MarketMindMetaModel
            
            # Initialize stateful engines
            self.explainability_engine = self.ExplainabilityEngine()
            self.meta_model = self.MarketMindMetaModel()
            self.benchmark_engine = BenchmarkEngine()
            self.attribution_engine = AttributionEngine()
            self.risk_budgeting_engine = RiskBudgetingEngine()
            self.goal_engine = GoalEngine()
            self.recommendation_engine = CentralRecommendationEngine()
            
            logger.info("All engines initialized successfully")
            
        except ImportError as e:
            logger.error(f"Failed to import required engines: {e}")
            raise
    
    def run_pipeline(self, pipeline_input: PipelineInput) -> PipelineOutput:
        """
        Run the complete portfolio analysis pipeline.
        
        Args:
            pipeline_input: Standardized pipeline input
            
        Returns:
            Complete pipeline output with all analysis results
        """
        logger.info("=" * 70)
        logger.info("STARTING PORTFOLIO ANALYSIS PIPELINE")
        logger.info("=" * 70)
        
        pipeline_metadata = {
            'start_time': datetime.now().isoformat(),
            'tickers': pipeline_input.tickers,
            'period': f"{pipeline_input.start_date} to {pipeline_input.end_date}",
            'pipeline_version': '1.0'
        }
        
        # Step 1: Data Validation and Fetching
        logger.info("Step 1: Data Validation and Fetching")
        data_validation_result = self._step_data_validation(pipeline_input)
        if not data_validation_result['valid']:
            raise ValueError(f"Data validation failed: {data_validation_result['error']}")
        
        # Step 2: Feature Engineering
        logger.info("Step 2: Feature Engineering")
        feature_engineering_result = self._step_feature_engineering(
            data_validation_result['data']
        )
        
        # Step 3: Portfolio Analytics
        logger.info("Step 3: Portfolio Analytics")
        portfolio_analytics = self._step_portfolio_analytics(
            data_validation_result['data'],
            pipeline_input.weights
        )
        
        # Step 4: ML Model Inference
        logger.info("Step 4: ML Model Inference")
        ml_predictions = self._step_ml_inference(
            pipeline_input.tickers,
            feature_engineering_result['features']
        )
        
        # Step 5: Risk Engine
        logger.info("Step 5: Risk Engine")
        risk_analysis = self._step_risk_analysis(
            data_validation_result['data'],
            portfolio_analytics
        )
        
        # Step 6: Benchmark Comparison (if benchmark provided)
        benchmark_comparison = None
        if pipeline_input.benchmark_ticker:
            logger.info("Step 6: Benchmark Comparison")
            benchmark_comparison = self._step_benchmark_comparison(
                data_validation_result['data'],
                pipeline_input.benchmark_ticker,
                portfolio_analytics
            )
        
        # Step 7: Attribution Analysis
        logger.info("Step 7: Attribution Analysis")
        attribution_analysis = self._step_attribution_analysis(
            data_validation_result['data'],
            pipeline_input.weights
        )
        
        # Step 8: Risk Budgeting
        logger.info("Step 8: Risk Budgeting")
        risk_budget = self._step_risk_budgeting(
            data_validation_result['data'],
            pipeline_input.weights
        )
        
        # Step 9: Stress Testing
        logger.info("Step 9: Stress Testing")
        stress_test = self._step_stress_testing(
            pipeline_input.tickers,
            pipeline_input.weights,
            pipeline_input.portfolio_value
        )
        
        # Step 10: Optimization
        logger.info("Step 10: Portfolio Optimization")
        optimization = self._step_optimization(
            data_validation_result['data'],
            pipeline_input.weights
        )
        
        # Step 11: Goal Analysis (if user profile provided)
        goal_analysis = None
        if pipeline_input.user_profile:
            logger.info("Step 11: Goal Analysis")
            goal_analysis = self._step_goal_analysis(
                data_validation_result['data'],
                pipeline_input.user_profile
            )
        
        # Step 12: Recommendation Engine
        logger.info("Step 12: Recommendation Engine")
        recommendations = self._step_recommendation_engine(
            portfolio_analytics,
            ml_predictions,
            risk_analysis,
            benchmark_comparison,
            attribution_analysis,
            risk_budget,
            stress_test,
            optimization,
            goal_analysis
        )
        
        # Step 13: Explainability
        logger.info("Step 13: Explainability")
        explainability = self._step_explainability(
            pipeline_input,
            portfolio_analytics,
            ml_predictions,
            risk_analysis,
            recommendations
        )
        
        # Step 14: LLM Context Preparation
        logger.info("Step 14: LLM Context Preparation")
        llm_context = self._step_llm_context_preparation(
            pipeline_input,
            portfolio_analytics,
            ml_predictions,
            risk_analysis,
            benchmark_comparison,
            attribution_analysis,
            risk_budget,
            stress_test,
            optimization,
            recommendations,
            explainability
        )
        
        # Update pipeline metadata
        pipeline_metadata['end_time'] = datetime.now().isoformat()
        pipeline_metadata['duration_seconds'] = (
            datetime.fromisoformat(pipeline_metadata['end_time']) - 
            datetime.fromisoformat(pipeline_metadata['start_time'])
        ).total_seconds()
        
        # Assemble final output
        pipeline_output = PipelineOutput(
            input=pipeline_input,
            portfolio_analytics=portfolio_analytics,
            ml_predictions=ml_predictions,
            risk_analysis=risk_analysis,
            benchmark_comparison=benchmark_comparison,
            attribution_analysis=attribution_analysis,
            risk_budget=risk_budget,
            stress_test=stress_test,
            optimization=optimization,
            goal_analysis=goal_analysis,
            recommendations=recommendations,
            explainability=explainability,
            llm_context=llm_context,
            pipeline_metadata=pipeline_metadata,
            timestamp=datetime.now().isoformat()
        )
        
        logger.info("=" * 70)
        logger.info("PORTFOLIO ANALYSIS PIPELINE COMPLETED")
        logger.info(f"Duration: {pipeline_metadata['duration_seconds']:.2f} seconds")
        logger.info("=" * 70)
        
        return pipeline_output
    
    def _step_data_validation(self, pipeline_input: PipelineInput) -> Dict[str, Any]:
        """Step 1: Data validation and fetching."""
        try:
            # Input validation
            if len(pipeline_input.tickers) != len(pipeline_input.weights):
                return {
                    'valid': False,
                    'error': 'Number of tickers and weights must match'
                }
            
            if abs(sum(pipeline_input.weights) - 1.0) > 0.01:
                return {
                    'valid': False,
                    'error': f'Weights must sum to 1.0 (current sum: {sum(pipeline_input.weights)})'
                }
            
            # Fetch data
            data = self.get_portfolio_data(
                pipeline_input.tickers,
                pipeline_input.start_date,
                pipeline_input.end_date
            )
            
            # Data quality validation
            if data is None or data['prices'].empty:
                return {
                    'valid': False,
                    'error': 'No data returned for provided tickers and date range'
                }
            
            # Check for missing data
            missing_pct = data['prices'].isna().sum() / data['prices'].size * 100
            if missing_pct > 10:
                logger.warning(f"High missing data percentage: {missing_pct:.1f}%")
            
            return {
                'valid': True,
                'data': data,
                'missing_data_pct': missing_pct,
                'data_points': len(data['prices'])
            }
            
        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            return {
                'valid': False,
                'error': str(e)
            }
    
    def _step_feature_engineering(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Step 2: Feature engineering (data is already processed)."""
        # The data from get_portfolio_data already includes technical indicators
        # This step validates and catalogs the features
        
        prices = data['prices']
        returns = data['returns']
        
        features = {
            'prices': prices,
            'returns': returns,
            'n_observations': len(prices),
            'n_assets': len(prices.columns),
            'date_range': {
                'start': str(prices.index.min()),
                'end': str(prices.index.max())
            },
            'data_frequency': 'daily',
            'asset_columns': prices.columns.tolist()
        }
        
        return features
    
    def _step_portfolio_analytics(self, data: Dict[str, Any], weights: List[float]) -> Dict[str, Any]:
        """Step 3: Portfolio analytics calculation."""
        prices = data['prices']
        returns = data['returns']
        
        # Calculate portfolio returns
        weights_array = np.array(weights)
        portfolio_returns = (returns * weights_array).sum(axis=1)
        
        # Calculate portfolio metrics
        cumulative_returns = (1 + portfolio_returns).cumprod()
        total_return = cumulative_returns.iloc[-1] - 1
        
        # Annualized metrics
        n_days = len(portfolio_returns)
        annual_return = (1 + total_return) ** (252 / n_days) - 1
        annual_volatility = portfolio_returns.std() * np.sqrt(252)
        
        # Risk-adjusted metrics
        risk_free_rate = 0.02
        sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility if annual_volatility > 0 else 0
        
        # Drawdown
        cummax = cumulative_returns.cummax()
        drawdown = (cumulative_returns - cummax) / cummax
        max_drawdown = drawdown.min()
        
        return {
            'portfolio_returns': portfolio_returns,
            'cumulative_returns': cumulative_returns,
            'total_return': total_return,
            'annual_return': annual_return,
            'annual_volatility': annual_volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'final_value': cumulative_returns.iloc[-1],
            'n_observations': n_days
        }
    
    def _step_ml_inference(self, tickers: List[str], features: Dict[str, Any]) -> Dict[str, Any]:
        """Step 4: ML model inference."""
        ml_predictions = {}
        
        for ticker in tickers:
            try:
                # Try MarketMind meta-model
                if self.meta_model.is_ready():
                    if self.meta_model.model is None:
                        self.meta_model.load()
                    
                    prediction = self.meta_model.predict_for_ticker(ticker)
                    ml_predictions[ticker] = {
                        'marketmind': prediction,
                        'source': 'meta_model',
                        'status': 'success'
                    }
                else:
                    ml_predictions[ticker] = {
                        'marketmind': None,
                        'source': 'not_available',
                        'status': 'meta_model_not_trained'
                    }
                    
            except Exception as e:
                logger.warning(f"ML inference failed for {ticker}: {e}")
                ml_predictions[ticker] = {
                    'marketmind': None,
                    'source': 'error',
                    'status': 'error',
                    'error': str(e)
                }
        
        return ml_predictions
    
    def _step_risk_analysis(self, data: Dict[str, Any], portfolio_analytics: Dict[str, Any]) -> Dict[str, Any]:
        """Step 5: Risk analysis."""
        prices = data['prices']
        returns = data['returns']
        
        # Use existing risk metrics engine
        risk_summary = self.get_risk_summary(prices, returns)
        
        # Extract key metrics
        risk_analysis = {
            'risk_summary': risk_summary['summary'].to_dict(),
            'portfolio_volatility': portfolio_analytics['annual_volatility'],
            'portfolio_sharpe': portfolio_analytics['sharpe_ratio'],
            'portfolio_max_drawdown': portfolio_analytics['max_drawdown'],
            'risk_assessment': self._assess_risk_level(portfolio_analytics)
        }
        
        return risk_analysis
    
    def _assess_risk_level(self, portfolio_analytics: Dict[str, Any]) -> str:
        """Assess overall risk level."""
        volatility = portfolio_analytics['annual_volatility']
        drawdown = abs(portfolio_analytics['max_drawdown'])
        
        if volatility < 0.15 and drawdown < 0.15:
            return 'low'
        elif volatility < 0.25 and drawdown < 0.25:
            return 'medium'
        else:
            return 'high'
    
    def _step_benchmark_comparison(self, data: Dict[str, Any], benchmark_ticker: str, portfolio_analytics: Dict[str, Any]) -> Dict[str, Any]:
        """Step 6: Benchmark comparison using benchmark engine."""
        try:
            portfolio_returns = portfolio_analytics['portfolio_returns']
            
            comparison = self.benchmark_engine.compare_portfolio_to_benchmark(
                portfolio_returns,
                benchmark_ticker,
                start_date=str(data['prices'].index.min()),
                end_date=str(data['prices'].index.max())
            )
            
            return comparison
            
        except Exception as e:
            logger.error(f"Benchmark comparison failed: {e}")
            return {
                'error': str(e),
                'status': 'failed'
            }
    
    def _step_attribution_analysis(self, data: Dict[str, Any], weights: List[float]) -> Dict[str, Any]:
        """Step 7: Attribution analysis using attribution engine."""
        try:
            returns = data['returns']
            weights_array = np.array(weights)
            
            attribution_result = self.attribution_engine.calculate_attribution(
                returns,
                weights_array,
                period_start=str(returns.index.min()),
                period_end=str(returns.index.max())
            )
            
            return asdict(attribution_result)
            
        except Exception as e:
            logger.error(f"Attribution analysis failed: {e}")
            return {
                'error': str(e),
                'status': 'failed'
            }
    
    def _step_risk_budgeting(self, data: Dict[str, Any], weights: List[float]) -> Dict[str, Any]:
        """Step 8: Risk budgeting analysis using risk budgeting engine."""
        try:
            returns = data['returns']
            weights_array = np.array(weights)
            
            risk_budget_result = self.risk_budgeting_engine.calculate_risk_budget(
                returns,
                weights_array
            )
            
            return asdict(risk_budget_result)
            
        except Exception as e:
            logger.error(f"Risk budgeting failed: {e}")
            return {
                'error': str(e),
                'status': 'failed'
            }
    
    def _step_stress_testing(self, tickers: List[str], weights: List[float], portfolio_value: float) -> Dict[str, Any]:
        """Step 9: Stress testing."""
        stress_results = self.get_stress_summary(tickers, weights, portfolio_value)
        
        return {
            'stress_table': stress_results['stress_table'].to_dict(),
            'worst_scenario': stress_results['worst_scenario'],
            'worst_loss': stress_results['worst_loss'],
            'worst_loss_pct': stress_results['worst_loss_pct']
        }
    
    def _step_optimization(self, data: Dict[str, Any], weights: List[float]) -> Dict[str, Any]:
        """Step 10: Portfolio optimization."""
        returns = data['returns']
        
        try:
            optimizer = self.PortfolioOptimizer(returns)
            current_weights_dict = dict(zip(returns.columns, weights))
            
            comparison = optimizer.compare_with_current(current_weights_dict, 'max_sharpe')
            
            return {
                'current_portfolio': comparison['current_portfolio'],
                'optimized_portfolio': comparison['optimized_portfolio'],
                'improvements': comparison['improvements'],
                'rebalance_suggestions': comparison['rebalance_suggestions'],
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return {
                'error': str(e),
                'status': 'failed'
            }
    
    def _step_goal_analysis(self, data: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Step 11: Goal analysis using goal engine."""
        try:
            returns = data['returns']
            portfolio_returns = returns.mean(axis=1)
            
            # Create goal input
            from services.goal_engine import GoalInput
            goal_input = GoalInput(
                current_capital=user_profile.get('current_capital', 100000),
                monthly_contribution=user_profile.get('monthly_contribution', 1000),
                target_amount=user_profile.get('target_amount', 500000),
                time_horizon_years=user_profile.get('time_horizon_years', 10),
                risk_tolerance=user_profile.get('risk_tolerance', 'moderate'),
                goal_name=user_profile.get('goal_name', 'Financial Goal')
            )
            
            goal_result = self.goal_engine.analyze_goal(
                goal_input,
                portfolio_returns
            )
            
            return asdict(goal_result)
            
        except Exception as e:
            logger.error(f"Goal analysis failed: {e}")
            return {
                'error': str(e),
                'status': 'failed'
            }
    
    def _step_recommendation_engine(
        self,
        portfolio_analytics: Dict[str, Any],
        ml_predictions: Dict[str, Any],
        risk_analysis: Dict[str, Any],
        benchmark_comparison: Optional[Dict[str, Any]],
        attribution_analysis: Dict[str, Any],
        risk_budget: Optional[Dict[str, Any]],
        stress_test: Dict[str, Any],
        optimization: Optional[Dict[str, Any]],
        goal_analysis: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Step 12: Recommendation engine - central decision layer."""
        recommendations = []
        
        # Risk-based recommendations
        if risk_analysis['risk_assessment'] == 'high':
            recommendations.append({
                'type': 'risk',
                'priority': 'high',
                'action': 'reduce_exposure',
                'title': 'High Portfolio Risk Detected',
                'description': f"Portfolio risk level is {risk_analysis['risk_assessment']}. Consider reducing exposure to volatile assets.",
                'reasoning': f"Volatility: {risk_analysis['portfolio_volatility']*100:.1f}%, Max Drawdown: {abs(risk_analysis['portfolio_max_drawdown'])*100:.1f}%",
                'supporting_metrics': {
                    'volatility': risk_analysis['portfolio_volatility'],
                    'max_drawdown': risk_analysis['portfolio_max_drawdown'],
                    'sharpe_ratio': risk_analysis['portfolio_sharpe']
                },
                'confidence': 0.75,
                'timestamp': datetime.now().isoformat()
            })
        
        # Optimization-based recommendations
        if optimization and optimization.get('status') == 'success':
            improvements = optimization['improvements']
            if improvements.get('return_improvement_pct', 0) > 5:
                recommendations.append({
                    'type': 'optimization',
                    'priority': 'medium',
                    'action': 'rebalance',
                    'title': 'Optimization Opportunity',
                    'description': f"Portfolio optimization could improve returns by {improvements['return_improvement_pct']:.1f}%.",
                    'reasoning': optimization.get('explanation', ''),
                    'supporting_metrics': improvements,
                    'confidence': 0.65,
                    'timestamp': datetime.now().isoformat()
                })
        
        # Stress test recommendations
        worst_loss_pct = stress_test.get('worst_loss_pct', 0)
        if worst_loss_pct < -20:
            recommendations.append({
                'type': 'stress',
                'priority': 'high',
                'action': 'diversify',
                'title': 'Stress Test Warning',
                'description': f"Worst-case scenario shows {worst_loss_pct:.1f}% loss. Consider diversification.",
                'reasoning': f"Based on historical stress scenario: {stress_test.get('worst_scenario', 'Unknown')}",
                'supporting_metrics': {
                    'worst_loss_pct': worst_loss_pct,
                    'worst_scenario': stress_test.get('worst_scenario')
                },
                'confidence': 0.70,
                'timestamp': datetime.now().isoformat()
            })
        
        # ML-based recommendations
        buy_signals = []
        sell_signals = []
        for ticker, pred in ml_predictions.items():
            if pred.get('status') == 'success' and pred.get('marketmind'):
                mm_pred = pred['marketmind']
                if mm_pred.get('recommendation') == 'BUY' and mm_pred.get('confidence', 0) > 0.6:
                    buy_signals.append(ticker)
                elif mm_pred.get('recommendation') == 'SELL' and mm_pred.get('confidence', 0) > 0.6:
                    sell_signals.append(ticker)
        
        if buy_signals:
            recommendations.append({
                'type': 'ml_signal',
                'priority': 'low',
                'action': 'consider_increase',
                'title': 'ML Buy Signals',
                'description': f"ML models indicate BUY signals for: {', '.join(buy_signals)}",
                'reasoning': "Based on MarketMind meta-model predictions",
                'supporting_metrics': {'buy_signals': buy_signals},
                'confidence': 0.55,
                'timestamp': datetime.now().isoformat()
            })
        
        if sell_signals:
            recommendations.append({
                'type': 'ml_signal',
                'priority': 'low',
                'action': 'consider_reduce',
                'title': 'ML Sell Signals',
                'description': f"ML models indicate SELL signals for: {', '.join(sell_signals)}",
                'reasoning': "Based on MarketMind meta-model predictions",
                'supporting_metrics': {'sell_signals': sell_signals},
                'confidence': 0.55,
                'timestamp': datetime.now().isoformat()
            })
        
        return recommendations
    
    def _step_explainability(
        self,
        pipeline_input: PipelineInput,
        portfolio_analytics: Dict[str, Any],
        ml_predictions: Dict[str, Any],
        risk_analysis: Dict[str, Any],
        recommendations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Step 13: Explainability."""
        # Generate primary factors
        primary_factors = []
        
        # Risk factors
        if abs(risk_analysis['portfolio_max_drawdown']) > 0.15:
            primary_factors.append({
                'factor': 'Maximum Drawdown',
                'impact': 'negative',
                'value': f"{abs(risk_analysis['portfolio_max_drawdown'])*100:.1f}%",
                'importance': 'high'
            })
        
        # ML factor
        ml_available = sum(1 for pred in ml_predictions.values() if pred.get('status') == 'success')
        if ml_available > 0:
            primary_factors.append({
                'factor': 'ML Model Coverage',
                'impact': 'neutral',
                'value': f"{ml_available}/{len(ml_predictions)} tickers",
                'importance': 'medium'
            })
        
        # Model contributions
        model_contributions = {
            'risk_metrics': 0.35,
            'ml_predictions': 0.25,
            'optimization': 0.20,
            'stress_testing': 0.15,
            'attribution': 0.05
        }
        
        # Reasoning chain
        reasoning_chain = [
            "1. Data validation and fetching completed",
            "2. Feature engineering applied",
            "3. Portfolio analytics calculated",
            "4. ML model inference performed",
            "5. Risk analysis completed",
            "6. Stress testing conducted",
            "7. Optimization analysis performed",
            "8. Recommendations synthesized"
        ]
        
        return {
            'primary_factors': primary_factors,
            'model_contributions': model_contributions,
            'reasoning_chain': reasoning_chain,
            'data_sources': [
                'Yahoo Finance market data',
                'Technical indicator calculations',
                'ML model predictions',
                'Optimization algorithms',
                'Historical stress scenarios'
            ]
        }
    
    def _step_llm_context_preparation(
        self,
        pipeline_input: PipelineInput,
        portfolio_analytics: Dict[str, Any],
        ml_predictions: Dict[str, Any],
        risk_analysis: Dict[str, Any],
        benchmark_comparison: Optional[Dict[str, Any]],
        attribution_analysis: Optional[Dict[str, Any]],
        risk_budget: Optional[Dict[str, Any]],
        stress_test: Dict[str, Any],
        optimization: Optional[Dict[str, Any]],
        recommendations: List[Dict[str, Any]],
        explainability: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Step 14: LLM context preparation."""
        
        # This provides structured context for the LLM to prevent hallucination
        llm_context = {
            'portfolio_summary': {
                'tickers': pipeline_input.tickers,
                'total_value': pipeline_input.portfolio_value,
                'annual_return': portfolio_analytics['annual_return'],
                'volatility': portfolio_analytics['annual_volatility'],
                'sharpe_ratio': portfolio_analytics['sharpe_ratio'],
                'max_drawdown': portfolio_analytics['max_drawdown']
            },
            'risk_assessment': {
                'risk_level': risk_analysis['risk_assessment'],
                'key_risks': [
                    f"Volatility: {risk_analysis['portfolio_volatility']*100:.1f}%",
                    f"Max Drawdown: {abs(risk_analysis['portfolio_max_drawdown'])*100:.1f}%"
                ]
            },
            'ml_insights': {
                'predictions': ml_predictions,
                'coverage': f"{sum(1 for p in ml_predictions.values() if p.get('status') == 'success')}/{len(ml_predictions)} tickers"
            },
            'stress_test_summary': {
                'worst_scenario': stress_test.get('worst_scenario'),
                'worst_loss_pct': stress_test.get('worst_loss_pct')
            },
            'recommendations': recommendations,
            'explainability': explainability
        }
        
        # Add benchmark if available
        if benchmark_comparison and benchmark_comparison.get('status') == 'success':
            llm_context['benchmark_comparison'] = {
                'benchmark': benchmark_comparison['benchmark_ticker'],
                'alpha': benchmark_comparison['alpha'],
                'beta': benchmark_comparison['beta'],
                'information_ratio': benchmark_comparison['information_ratio']
            }
        
        # Add optimization if available
        if optimization and optimization.get('status') == 'success':
            llm_context['optimization'] = {
                'current_portfolio': optimization['current_portfolio'],
                'optimized_portfolio': optimization['optimized_portfolio'],
                'improvements': optimization['improvements']
            }
        
        return llm_context


def create_pipeline() -> PortfolioAnalysisPipeline:
    """Convenience function to create the portfolio analysis pipeline."""
    return PortfolioAnalysisPipeline()


if __name__ == "__main__":
    # Example usage
    pipeline = create_pipeline()
    
    input_data = PipelineInput(
        tickers=['AAPL', 'MSFT', 'GOOGL'],
        weights=[0.4, 0.3, 0.3],
        portfolio_value=100000,
        start_date='2020-01-01',
        end_date='2024-01-01',
        benchmark_ticker='SPY'
    )
    
    output = pipeline.run_pipeline(input_data)
    print("Pipeline executed successfully")
    print(f"Portfolio return: {output.portfolio_analytics['annual_return']*100:.2f}%")
    print(f"Recommendations: {len(output.recommendations)}")
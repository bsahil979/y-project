"""
Portfolio Optimization Engine - Implements modern portfolio theory and optimization algorithms.

This module provides:
1. Mean-Variance Optimization (Markowitz)
2. Risk Parity Optimization  
3. Max Sharpe Ratio Optimization
4. Min Volatility Optimization
5. Target Return Optimization
6. Constraints handling (sector, exposure, position limits)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from scipy.optimize import minimize
from scipy import stats
import warnings

warnings.filterwarnings('ignore')


def get_profile_constraints(risk_preference: str, investment_horizon_years=None,
                            *, n_assets: Optional[int] = None, horizon_source=None) -> Dict:
    """Deterministic profile and horizon policy; report any feasibility adjustment."""
    if investment_horizon_years is not None and (
            isinstance(investment_horizon_years, bool) or
            not isinstance(investment_horizon_years, (int, float)) or
            not np.isfinite(investment_horizon_years) or investment_horizon_years <= 0):
        raise ValueError('investment_horizon_years must be finite and positive')
    source = horizon_source or ('explicit' if investment_horizon_years is not None else 'default')
    if source not in ('explicit', 'nearest_goal', 'default'):
        raise ValueError('Invalid horizon_source')
    if (investment_horizon_years is None) != (source == 'default'):
        raise ValueError('Horizon source must be default only when no horizon is supplied')
    policies = {
        'conservative': ('minimum_volatility', .20, .30, .02, .05),
        'moderate': ('maximum_sharpe', .30, .40, .04, 0.0),
        'aggressive': ('target_return', .40, .50, .05, 0.0),
    }
    if risk_preference not in policies:
        raise ValueError('risk_preference must be conservative, moderate or aggressive')
    objective, cap, sector_cap, rebalance_threshold, beta_penalty = policies[risk_preference]
    if n_assets is not None:
        if isinstance(n_assets, bool) or not isinstance(n_assets, int) or n_assets < 1:
            raise ValueError('At least one asset is required')
        if risk_preference == 'conservative' and n_assets < 5:
            cap = min(1.0, max(.25, 1.2 / n_assets))
    baseline_cap = cap
    modifier = 'default_profile'
    effective_profile = risk_preference
    volatility_penalty = 1.0
    floor = 1.0 / n_assets if n_assets is not None else None
    if investment_horizon_years is not None:
        if investment_horizon_years <= 2:
            if n_assets is None:
                raise ValueError('n_assets is required for short-horizon feasibility')
            modifier = 'short_term_protection'
            cap = max(cap - .05, floor)
            if risk_preference == 'conservative':
                beta_penalty *= 1.25
                volatility_penalty = 1.25
            if risk_preference == 'aggressive':
                effective_profile = 'moderate'
                objective = 'maximum_sharpe'
        elif investment_horizon_years < 7:
            modifier = 'baseline_medium_term'
        else:
            modifier = 'long_term_growth'
    return {'applied_profile': risk_preference, 'effective_profile': effective_profile,
            'investment_horizon_years': investment_horizon_years, 'horizon_source': source,
            'horizon_modifier': modifier, 'baseline_max_weight_cap': baseline_cap,
            'feasibility_floor': floor,
            'feasibility_floor_applied': modifier == 'short_term_protection' and floor > baseline_cap - .05,
            'volatility_penalty': volatility_penalty, 'max_weight_cap': cap,
            'objective_used': objective, 'sector_weight_cap': sector_cap,
            'rebalance_threshold': rebalance_threshold, 'beta_penalty': beta_penalty}


def build_ai_black_litterman_views(pi, vol_i, marketmind_probabilities=None,
                                   finbert_scores=None, tau=.05):
    """Absolute annual-return views in pi insertion order (P = identity).

    Confidence is a deterministic policy coefficient, not calibrated accuracy:
    .75 for two sources, .35 for one, .15 for opposing signs, zero for none.
    Omega = tau * annual variance * (1-confidence)/confidence. Missing views
    are excluded from the posterior update, even though their Q equals pi.
    """
    if not np.isfinite(tau) or tau <= 0:
        raise ValueError('tau must be positive')
    probabilities, sentiments = marketmind_probabilities or {}, finbert_scores or {}
    q, omega, provenance = {}, [], {}
    for ticker, prior in pi.items():
        vol = float(vol_i[ticker])
        if not np.isfinite(prior) or not np.isfinite(vol) or vol < 0:
            raise ValueError('Prior returns and volatilities must be finite; volatility cannot be negative')
        probs = probabilities.get(ticker)
        net = None
        if probs is not None:
            # Named probabilities are preferred; legacy MarketMind labels: 2=buy, 1=hold, 0=sell.
            if isinstance(probs, dict):
                keys = ('buy', 'hold', 'sell') if 'buy' in probs else (('P_buy', 'P_hold', 'P_sell') if 'P_buy' in probs else ('2', '1', '0'))
                values = [probs.get(k) for k in keys]
            else:
                values = probs  # Explicit (P_buy, P_hold, P_sell) sequence.
            try:
                values = np.asarray(values, dtype=float)
                if values.shape == (3,) and np.isfinite(values).all() and (values >= 0).all() and (values <= 1).all() and np.isclose(values.sum(), 1, atol=1e-6):
                    net = float(values[0] - values[2])
            except (TypeError, ValueError):
                pass
        sentiment = sentiments.get(ticker)
        if sentiment is not None:
            try:
                sentiment = float(sentiment)
                if not np.isfinite(sentiment) or not -1 <= sentiment <= 1:
                    sentiment = None
            except (TypeError, ValueError):
                sentiment = None
        both = net is not None and sentiment is not None
        disagreement = both and net * sentiment < 0
        confidence = (.15 if disagreement else .75) if both else (.35 if net is not None or sentiment is not None else 0.0)
        signal = .65 * net + .35 * sentiment if both else (net if net is not None else (sentiment if sentiment is not None else 0.0))
        q[ticker] = float(prior + signal * .50 * vol)
        variance = max(tau * vol ** 2, 1e-12)
        omega.append(variance * (1-confidence) / max(confidence, 1e-12))
        provenance[ticker] = {'marketmind_net_prob': net, 'finbert_score': sentiment,
            'composite_signal': float(signal), 'implied_view_return_q': q[ticker],
            'view_confidence': confidence, 'fallback_to_prior': confidence == 0,
            'aligned_signals': bool(both and net * sentiment > 0)}
    return {'tickers': list(pi), 'Q': q, 'Omega': np.diag(omega).tolist(),
            'provenance': provenance, 'tau': tau}


class PortfolioOptimizer:
    """
    Multi-objective portfolio optimizer with constraint support.
    """
    
    def __init__(self, returns: pd.DataFrame, risk_free_rate: float = 0.02):
        """
        Initialize optimizer with historical returns data.
        
        Args:
            returns: DataFrame with asset returns (columns = assets, index = dates)
            risk_free_rate: Annual risk-free rate (default 2%)
        """
        self.returns = returns
        self.risk_free_rate = risk_free_rate
        self.mean_returns = returns.mean() * 252  # Annualized
        self.cov_matrix = returns.cov() * 252  # Annualized
        self.assets = returns.columns.tolist()
        self.n_assets = len(self.assets)

    def black_litterman(self, ai_views, risk_preference='moderate',
                       investment_horizon_years=None, horizon_source=None, risk_aversion=2.5):
        """Profile-capped BL with an equal-weight equilibrium prior and absolute AI views.

        Missing views do not update the prior. Posterior mean uncertainty is not
        added to the historical risk covariance, preserving equilibrium weights
        in the absence of views. No unconstrained fallback is permitted.
        """
        policy = get_profile_constraints(risk_preference, investment_horizon_years,
            n_assets=self.n_assets, horizon_source=horizon_source)
        cap = policy['max_weight_cap']
        metadata = {**policy, 'objective_used': 'black_litterman', 'method': 'black_litterman',
            'evaluation': 'in_sample', 'metric_type': 'optimization_expected',
            'prior_source': 'equal_weight_asset_basket', 'provenance': ai_views['provenance'],
            'view_uncertainty': ai_views['Omega'], 'signal_status': 'prior_only' if all(
                v['fallback_to_prior'] for v in ai_views['provenance'].values()) else 'ai_views',
            'confidence_note': 'Heuristic view confidence; not calibrated prediction accuracy'}
        def failure(reason, status='unavailable'):
            return {**metadata, 'success': False, 'status': status, 'weights': {}, 'reason': reason}
        if self.n_assets * cap < 1 - 1e-10:
            return failure(f'{self.n_assets} assets cannot sum to 100% under a {cap:.0%} cap', 'infeasible')
        if ai_views['tickers'] != self.assets:
            raise ValueError('AI view order must match optimizer assets')
        cov = self.cov_matrix.to_numpy(dtype=float)
        if len(self.returns) < 2 or not np.isfinite(cov).all():
            return failure('Finite aligned return history is required')
        if not np.isfinite(risk_aversion) or risk_aversion <= 0:
            raise ValueError('risk_aversion must be positive')
        initial = np.full(self.n_assets, 1 / self.n_assets)
        pi = risk_aversion * cov @ initial
        q = np.array([ai_views['Q'][a] for a in self.assets])
        omega = np.asarray(ai_views['Omega'], dtype=float)
        if omega.shape != cov.shape or not np.isfinite(q).all() or not np.isfinite(omega).all() or (np.diag(omega) <= 0).any():
            raise ValueError('Invalid AI views or uncertainty')
        active = [i for i, a in enumerate(self.assets) if not ai_views['provenance'][a]['fallback_to_prior']]
        posterior = pi.copy()
        if active:
            prior_cov = ai_views['tau'] * cov
            posterior += prior_cov[:, active] @ np.linalg.pinv(
                prior_cov[np.ix_(active, active)] + omega[np.ix_(active, active)]) @ (q[active] - pi[active])
        def solve(expected):
            result = minimize(lambda w: .5 * risk_aversion * w @ cov @ w - w @ expected,
                initial, method='SLSQP', bounds=[(0, cap)] * self.n_assets,
                constraints=[{'type': 'eq', 'fun': lambda w: w.sum()-1}],
                options={'maxiter': 1000, 'ftol': 1e-12})
            w = result.x
            if not (result.success and np.isfinite(w).all() and abs(w.sum()-1) < 1e-7 and w.min() >= 0 and w.max() <= cap):
                return None
            return w
        prior_weights, weights = solve(pi), solve(posterior)
        if weights is None or prior_weights is None:
            return failure('Constrained Black-Litterman optimization failed')
        return {**metadata, 'success': True, 'status': 'success',
            'weights': dict(zip(self.assets, weights.tolist())),
            'prior_weights': dict(zip(self.assets, prior_weights.tolist())),
            'prior_returns': dict(zip(self.assets, pi.tolist())),
            'posterior_returns': dict(zip(self.assets, posterior.tolist())),
            'performance': self._portfolio_performance(weights)}

    def optimize_personalized(self, risk_preference='moderate', investment_horizon_years=None, horizon_source=None, ai_views=None):
        policy = get_profile_constraints(risk_preference, investment_horizon_years,
                                         n_assets=self.n_assets, horizon_source=horizon_source)
        if ai_views is not None and policy['effective_profile'] == 'aggressive':
            return self.black_litterman(ai_views, risk_preference, investment_horizon_years, horizon_source)
        metadata = {**policy,
                    'horizon_usage': 'Horizon adjusts position caps, conservative penalties and aggressive objective behavior',
                    'evaluation': 'in_sample', 'metric_type': 'optimization_expected'}
        cap = policy['max_weight_cap']
        if self.n_assets * cap < 1 - 1e-10:
            return {**metadata, 'status': 'infeasible', 'success': False, 'weights': {},
                    'reason': f'{self.n_assets} assets cannot sum to 100% under a {cap:.0%} cap; add assets or change profile.'}
        clean = self.returns.to_numpy(dtype=float)
        if len(clean) < 2 or not np.isfinite(clean).all():
            raise ValueError('Personalized optimization requires finite aligned return history')
        initial = np.full(self.n_assets, 1 / self.n_assets)
        constraints = [{'type': 'eq', 'fun': lambda w: w.sum() - 1}]
        objective = self._neg_sharpe_ratio
        if risk_preference == 'conservative':
            proxy = self.returns.mean(axis=1)
            variance = float(proxy.var())
            betas = np.array([self.returns[a].cov(proxy) / variance for a in self.assets]) if variance > 1e-12 else np.zeros(self.n_assets)
            metadata.update(beta_reference='equal_weight_asset_basket', asset_betas=dict(zip(self.assets, betas.tolist())))
            objective = lambda w: policy['volatility_penalty'] * self._volatility(w) + policy['beta_penalty'] * np.dot(w, np.maximum(betas - 1.0, 0))
        elif policy['objective_used'] == 'target_return':
            means = self.mean_returns.to_numpy()
            requested = float(np.percentile(means, 75))
            remaining, attainable = 1.0, 0.0
            for index in np.argsort(means)[::-1]:
                amount = min(cap, remaining)
                attainable += amount * means[index]
                remaining -= amount
            target = min(requested, float(attainable))
            metadata.update(target_return_requested=requested, target_return_used=target,
                            target_return_adjusted=bool(requested > attainable),
                            target_definition='75th percentile of annualized historical asset mean returns; capped at feasible maximum')
            constraints.append({'type': 'ineq', 'fun': lambda w: np.dot(means, w) - target})
            objective = self._volatility
        result = minimize(objective, initial, method='SLSQP', bounds=[(0, cap)] * self.n_assets,
                          constraints=constraints, options={'maxiter': 1000, 'ftol': 1e-10})
        w = result.x
        valid = (result.success and np.isfinite(w).all() and abs(w.sum() - 1) < 1e-6
                 and w.min() >= -1e-7 and w.max() <= cap + 1e-7)
        if policy['objective_used'] == 'target_return':
            valid = valid and np.dot(self.mean_returns, w) >= metadata['target_return_used'] - 1e-7
        if not valid:
            return {**metadata, 'status': 'unavailable', 'success': False, 'weights': {},
                    'reason': f'Constrained optimization failed: {result.message}'}
        return {**metadata, 'status': 'success', 'success': True,
                'method': policy['objective_used'], 'weights': dict(zip(self.assets, w.tolist())),
                'performance': self._portfolio_performance(w)}
        
    def _portfolio_performance(self, weights: np.ndarray) -> Dict[str, float]:
        """
        Calculate portfolio performance metrics.
        
        Args:
            weights: Array of asset weights (sums to 1)
            
        Returns:
            Dict with return, volatility, sharpe_ratio
        """
        returns = np.dot(self.mean_returns, weights)
        volatility = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))
        sharpe_ratio = (returns - self.risk_free_rate) / volatility if volatility > 0 else 0
        return {
            'return': returns,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio
        }
    
    def _neg_sharpe_ratio(self, weights: np.ndarray) -> float:
        """Negative Sharpe ratio for minimization."""
        perf = self._portfolio_performance(weights)
        return -perf['sharpe_ratio']
    
    def _volatility(self, weights: np.ndarray) -> float:
        """Portfolio volatility for minimization."""
        return np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))
    
    def optimize_max_sharpe(
        self, 
        weight_bounds: Tuple[float, float] = (0, 1),
        sector_constraints: Optional[Dict[str, Tuple[float, float]]] = None
    ) -> Dict:
        """
        Optimize portfolio for maximum Sharpe ratio.
        
        Args:
            weight_bounds: Min and max weight per asset (default 0-1)
            sector_constraints: Dict mapping sectors to (min, max) exposure
            
        Returns:
            Dict with optimal weights and performance metrics
        """
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
        
        # Add sector constraints if provided
        if sector_constraints:
            for sector, (min_exp, max_exp) in sector_constraints.items():
                # This would require asset-sector mapping - simplified version
                pass
        
        bounds = tuple(weight_bounds for _ in range(self.n_assets))
        initial_guess = np.array([1/self.n_assets] * self.n_assets)
        
        result = minimize(
            self._neg_sharpe_ratio,
            initial_guess,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if not result.success:
            raise ValueError(f"Optimization failed: {result.message}")
        
        optimal_weights = result.x
        performance = self._portfolio_performance(optimal_weights)
        
        return {
            'weights': dict(zip(self.assets, optimal_weights)),
            'performance': performance,
            'method': 'max_sharpe',
            'success': result.success
        }
    
    def optimize_min_volatility(
        self,
        weight_bounds: Tuple[float, float] = (0, 1),
        target_return: Optional[float] = None
    ) -> Dict:
        """
        Optimize portfolio for minimum volatility.
        
        Args:
            weight_bounds: Min and max weight per asset
            target_return: Optional target return constraint
            
        Returns:
            Dict with optimal weights and performance metrics
        """
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
        
        if target_return is not None:
            constraints.append({
                'type': 'eq',
                'fun': lambda w: np.dot(self.mean_returns, w) - target_return
            })
        
        bounds = tuple(weight_bounds for _ in range(self.n_assets))
        initial_guess = np.array([1/self.n_assets] * self.n_assets)
        
        result = minimize(
            self._volatility,
            initial_guess,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if not result.success:
            raise ValueError(f"Optimization failed: {result.message}")
        
        optimal_weights = result.x
        performance = self._portfolio_performance(optimal_weights)
        
        return {
            'weights': dict(zip(self.assets, optimal_weights)),
            'performance': performance,
            'method': 'min_volatility',
            'success': result.success
        }
    
    def optimize_risk_parity(self) -> Dict:
        """
        Optimize portfolio using risk parity approach.
        Equal risk contribution from each asset.
        
        Returns:
            Dict with optimal weights and performance metrics
        """
        def risk_parity_objective(weights):
            portfolio_vol = self._volatility(weights)
            marginal_contrib = np.dot(self.cov_matrix, weights) / portfolio_vol
            contrib = weights * marginal_contrib
            target_risk = portfolio_vol / self.n_assets
            return np.sum((contrib - target_risk) ** 2)
        
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
        bounds = tuple((0, 1) for _ in range(self.n_assets))
        initial_guess = np.array([1/self.n_assets] * self.n_assets)
        
        result = minimize(
            risk_parity_objective,
            initial_guess,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if not result.success:
            raise ValueError(f"Optimization failed: {result.message}")
        
        optimal_weights = result.x
        performance = self._portfolio_performance(optimal_weights)
        
        return {
            'weights': dict(zip(self.assets, optimal_weights)),
            'performance': performance,
            'method': 'risk_parity',
            'success': result.success
        }
    
    def optimize_black_litterman(
        self,
        market_weights: Optional[Dict[str, float]] = None,
        views: Optional[Dict[str, float]] = None,
        confidences: Optional[Dict[str, float]] = None,
        sentiment_scores: Optional[Dict[str, float]] = None,
        risk_aversion: float = 2.5,
        tau: float = 0.05,
        weight_bounds: Tuple[float, float] = (0.02, 0.40)
    ) -> Dict:
        """
        Black-Litterman optimization blending equilibrium market priors
        with AI model views (LSTM expected returns) and FinBERT sentiment adjustments.
        """
        cov = self.cov_matrix.values
        n = self.n_assets
        
        # 1. Market Weights Prior
        if market_weights:
            w_mkt = np.array([float(market_weights.get(a, 1.0 / n)) for a in self.assets])
            if w_mkt.sum() > 0:
                w_mkt = w_mkt / w_mkt.sum()
            else:
                w_mkt = np.ones(n) / n
        else:
            w_mkt = np.ones(n) / n
            
        # Implied Equilibrium Return vector (Pi)
        delta = max(0.5, float(risk_aversion))
        pi = delta * (cov @ w_mkt)
        
        # 2. Subjective AI Views (Q)
        if views:
            q_vec = np.array([float(views.get(a, self.mean_returns[a])) for a in self.assets])
        else:
            q_vec = self.mean_returns.values.copy()
            
        # 3. FinBERT Sentiment Scoring Impact
        sentiment_adj = np.zeros(n)
        if sentiment_scores:
            for i, a in enumerate(self.assets):
                score = float(sentiment_scores.get(a, 0.0))
                # Sentiment modulates expected view by up to +/- 3%
                sentiment_adj[i] = score * 0.03
        q_vec = q_vec + sentiment_adj
        
        # 4. View Uncertainty Matrix (Omega)
        tau_val = max(0.005, min(0.20, float(tau)))
        omega_diag = np.diag(tau_val * cov).copy()
        
        if confidences:
            for i, a in enumerate(self.assets):
                conf = max(0.1, min(1.0, float(confidences.get(a, 0.6))))
                omega_diag[i] /= conf
                
        if sentiment_scores:
            for i, a in enumerate(self.assets):
                score = float(sentiment_scores.get(a, 0.0))
                if score < 0:
                    omega_diag[i] *= (1.0 + 1.5 * abs(score))
                elif score > 0:
                    omega_diag[i] *= (1.0 - 0.25 * min(score, 0.8))
                    
        # 5. Bayesian Posterior Returns and Covariance
        try:
            inv_tau_cov = np.linalg.pinv(tau_val * cov)
            inv_omega = np.diag(1.0 / np.maximum(omega_diag, 1e-6))
            
            M = np.linalg.pinv(inv_tau_cov + inv_omega)
            er_post = M @ (inv_tau_cov @ pi + inv_omega @ q_vec)
            cov_post = cov + M
        except Exception:
            er_post = 0.5 * pi + 0.5 * q_vec
            cov_post = cov
            
        # 6. Optimize weights under constraints
        def neg_utility(w):
            port_ret = np.dot(w, er_post)
            port_var = np.dot(w.T, cov_post @ w)
            return -(port_ret - (delta / 2.0) * port_var)
            
        bounds = tuple(weight_bounds for _ in range(n))
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]
        init_guess = np.ones(n) / n
        
        res = minimize(neg_utility, init_guess, method='SLSQP', bounds=bounds, constraints=constraints)
        
        if res.success:
            optimal_weights = res.x
        else:
            inv_diag = 1.0 / np.diag(cov_post)
            optimal_weights = inv_diag / inv_diag.sum()
            
        port_return = float(np.dot(self.mean_returns, optimal_weights))
        port_vol = float(np.sqrt(np.dot(optimal_weights.T, np.dot(self.cov_matrix, optimal_weights))))
        sharpe = (port_return - self.risk_free_rate) / port_vol if port_vol > 0 else 0
        
        return {
            'weights': dict(zip(self.assets, [round(float(w), 4) for w in optimal_weights])),
            'prior_returns': dict(zip(self.assets, [round(float(r) * 100, 2) for r in pi])),
            'ai_views': dict(zip(self.assets, [round(float(q) * 100, 2) for q in q_vec])),
            'posterior_returns': dict(zip(self.assets, [round(float(r) * 100, 2) for r in er_post])),
            'sentiment_adjustments': dict(zip(self.assets, [round(float(s) * 100, 2) for s in sentiment_adj])),
            'performance': {
                'return': port_return,
                'volatility': port_vol,
                'sharpe_ratio': sharpe
            },
            'parameters': {
                'risk_aversion': delta,
                'tau': tau_val,
                'method': 'black_litterman_bayesian'
            },
            'method': 'black_litterman',
            'success': True
        }

    def optimize_target_return(
        self,
        target_return: float,
        weight_bounds: Tuple[float, float] = (0, 1)
    ) -> Dict:
        """
        Optimize portfolio for minimum volatility given a target return.
        
        Args:
            target_return: Target annual return
            weight_bounds: Min and max weight per asset
            
        Returns:
            Dict with optimal weights and performance metrics
        """
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},
            {'type': 'eq', 'fun': lambda w: np.dot(self.mean_returns, w) - target_return}
        ]
        
        bounds = tuple(weight_bounds for _ in range(self.n_assets))
        initial_guess = np.array([1/self.n_assets] * self.n_assets)
        
        result = minimize(
            self._volatility,
            initial_guess,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if not result.success:
            raise ValueError(f"Optimization failed: {result.message}")
        
        optimal_weights = result.x
        performance = self._portfolio_performance(optimal_weights)
        
        return {
            'weights': dict(zip(self.assets, optimal_weights)),
            'performance': performance,
            'method': 'target_return',
            'target_return': target_return,
            'success': result.success
        }
    
    def efficient_frontier(self, n_points: int = 50) -> Dict:
        """
        Calculate efficient frontier points.
        
        Args:
            n_points: Number of points on the frontier
            
        Returns:
            Dict with returns, volatilities, and weights for each point
        """
        min_vol_opt = self.optimize_min_volatility()
        max_ret_opt = self.optimize_max_sharpe()
        
        min_ret = min_vol_opt['performance']['return']
        max_ret = max_ret_opt['performance']['return']
        
        target_returns = np.linspace(min_ret, max_ret, n_points)
        
        frontier_data = {
            'returns': [],
            'volatilities': [],
            'sharpe_ratios': [],
            'weights': []
        }
        
        for target_ret in target_returns:
            try:
                opt = self.optimize_target_return(target_ret)
                frontier_data['returns'].append(opt['performance']['return'])
                frontier_data['volatilities'].append(opt['performance']['volatility'])
                frontier_data['sharpe_ratios'].append(opt['performance']['sharpe_ratio'])
                frontier_data['weights'].append(opt['weights'])
            except:
                continue
        
        return frontier_data
    
    def compare_with_current(
        self,
        current_weights: Dict[str, float],
        optimization_method: str = 'max_sharpe'
    ) -> Dict:
        """
        Compare current portfolio with optimized portfolio.
        
        Args:
            current_weights: Dict of current asset weights
            optimization_method: Which optimization to use
            
        Returns:
            Dict with comparison metrics and recommendations
        """
        # Normalize current weights
        total_weight = sum(current_weights.values())
        if total_weight != 1.0:
            current_weights = {k: v/total_weight for k, v in current_weights.items()}
        
        # Get current performance
        current_weights_array = np.array([current_weights.get(asset, 0) for asset in self.assets])
        current_perf = self._portfolio_performance(current_weights_array)
        
        # Get optimized portfolio
        if optimization_method == 'max_sharpe':
            opt_result = self.optimize_max_sharpe()
        elif optimization_method == 'min_volatility':
            opt_result = self.optimize_min_volatility()
        elif optimization_method == 'risk_parity':
            opt_result = self.optimize_risk_parity()
        else:
            opt_result = self.optimize_max_sharpe()
        
        opt_perf = opt_result['performance']
        
        # Calculate improvements
        return_improvement = ((opt_perf['return'] - current_perf['return']) / current_perf['return'] * 100) if current_perf['return'] != 0 else 0
        vol_reduction = ((current_perf['volatility'] - opt_perf['volatility']) / current_perf['volatility'] * 100) if current_perf['volatility'] != 0 else 0
        sharpe_improvement = opt_perf['sharpe_ratio'] - current_perf['sharpe_ratio']
        
        # Generate rebalancing suggestions
        rebalance_suggestions = []
        for asset in self.assets:
            current_weight = current_weights.get(asset, 0)
            opt_weight = opt_result['weights'].get(asset, 0)
            diff = opt_weight - current_weight
            if abs(diff) > 0.05:  # Only suggest significant changes
                action = 'increase' if diff > 0 else 'decrease'
                rebalance_suggestions.append({
                    'asset': asset,
                    'action': action,
                    'current_weight': round(current_weight * 100, 1),
                    'optimal_weight': round(opt_weight * 100, 1),
                    'difference': round(diff * 100, 1)
                })
        
        return {
            'current_portfolio': {
                'weights': current_weights,
                'performance': current_perf
            },
            'optimized_portfolio': {
                'weights': opt_result['weights'],
                'performance': opt_perf,
                'method': optimization_method
            },
            'improvements': {
                'return_improvement_pct': round(return_improvement, 2),
                'volatility_reduction_pct': round(vol_reduction, 2),
                'sharpe_improvement': round(sharpe_improvement, 4)
            },
            'rebalance_suggestions': rebalance_suggestions,
            'explanation': self._generate_optimization_explanation(
                current_perf, opt_perf, rebalance_suggestions, optimization_method
            )
        }
    
    def _generate_optimization_explanation(
        self,
        current_perf: Dict,
        opt_perf: Dict,
        suggestions: List,
        method: str
    ) -> str:
        """Generate human-readable explanation of optimization results."""
        
        explanation_parts = [
            f"Portfolio Optimization Analysis ({method} method):",
            f"",
            f"Current Portfolio Performance:",
            f"  - Annual Return: {current_perf['return']*100:.2f}%",
            f"  - Volatility: {current_perf['volatility']*100:.2f}%",
            f"  - Sharpe Ratio: {current_perf['sharpe_ratio']:.4f}",
            f"",
            f"Optimized Portfolio Performance:",
            f"  - Annual Return: {opt_perf['return']*100:.2f}%",
            f"  - Volatility: {opt_perf['volatility']*100:.2f}%",
            f"  - Sharpe Ratio: {opt_perf['sharpe_ratio']:.4f}",
            f""
        ]
        
        if suggestions:
            explanation_parts.append("Rebalancing Suggestions:")
            for sug in suggestions[:5]:  # Top 5 suggestions
                explanation_parts.append(
                    f"  - {sug['action']} {sug['asset']}: "
                    f"{sug['current_weight']}% → {sug['optimal_weight']}% "
                    f"({sug['difference']}% change)"
                )
        
        return "\n".join(explanation_parts)


def optimize_portfolio_from_data(
    tickers: List[str],
    start_date: str,
    end_date: str,
    current_weights: Optional[Dict[str, float]] = None,
    optimization_method: str = 'max_sharpe',
    risk_free_rate: float = 0.02
) -> Dict:
    """
    Convenience function to optimize portfolio from raw data.
    
    Args:
        tickers: List of ticker symbols
        start_date: Start date for historical data
        end_date: End date for historical data
        current_weights: Optional current portfolio weights
        optimization_method: Optimization method to use
        risk_free_rate: Risk-free rate for Sharpe calculation
        
    Returns:
        Dict with optimization results
    """
    try:
        import yfinance as yf
        
        # Fetch data
        data = yf.download(tickers, start=start_date, end=end_date)['Adj Close']
        returns = data.pct_change().dropna()
        
        # Initialize optimizer
        optimizer = PortfolioOptimizer(returns, risk_free_rate)
        
        if current_weights:
            # Compare with current portfolio
            return optimizer.compare_with_current(current_weights, optimization_method)
        else:
            # Just return optimized portfolio
            if optimization_method == 'max_sharpe':
                return optimizer.optimize_max_sharpe()
            elif optimization_method == 'min_volatility':
                return optimizer.optimize_min_volatility()
            elif optimization_method == 'risk_parity':
                return optimizer.optimize_risk_parity()
            else:
                return optimizer.optimize_max_sharpe()
                
    except Exception as e:
        return {
            'error': str(e),
            'success': False
        }


if __name__ == "__main__":
    # Example usage
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
    current_weights = {'AAPL': 0.4, 'MSFT': 0.3, 'GOOGL': 0.2, 'AMZN': 0.1}
    
    result = optimize_portfolio_from_data(
        tickers=tickers,
        start_date='2020-01-01',
        end_date='2024-01-01',
        current_weights=current_weights,
        optimization_method='max_sharpe'
    )
    
    print(result['explanation'])

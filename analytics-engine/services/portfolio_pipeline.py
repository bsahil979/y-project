"""
Unified Portfolio Pipeline — canonical analysis pipeline that chains all
existing ML engines into one coherent output.

Pipeline:
  User Portfolio
  -> Market Data (data_fetcher)
  -> Data Validation
  -> Canonical Portfolio Return Construction (financial_metrics)
  -> Portfolio Analytics & Risk (risk_metrics)
  -> ML Models (regime_detector, forecaster, sentiment_analyzer, meta_model)
  -> Risk Engine (risk_metrics + risk_budget)
  -> Stress Engine (stress_tester)
  -> Benchmark Engine (benchmark)
  -> Attribution Engine (attribution)
  -> Optimization (portfolio_optimizer)
  -> Recommendation Engine (recommendation_engine)
  -> Explainability & Advisor Context

Each stage consumes outputs from the previous stage. No calculation is
duplicated across stages.
"""
import os
import uuid
import numpy as np
import pandas as pd
from datetime import datetime, timezone

from services.data_fetcher import get_portfolio_data, normalize_currency_prices
from services.financial_metrics import (
    canonical_portfolio_returns,
    WEIGHT_SUM_TOLERANCE,
    DEFAULT_RISK_FREE_RATE,
)
from services.risk_metrics import get_risk_summary
from services.regime_detector import detect_market_regime_hmm
from services.stress_tester import get_stress_summary
from services.sentiment_analyzer import get_sentiment_analysis
from services.portfolio_score import (
    compute_portfolio_score,
    compute_asset_allocation,
    get_currency_symbol,
)
from services.benchmark import compute_benchmark_comparison
from services.attribution import compute_attribution
from services.risk_budget import compute_risk_budget, compute_correlation_matrix
from services.recommendation_engine import generate_recommendations
from trading_engine.meta_model import MarketMindMetaModel
from services.portfolio_optimizer import PortfolioOptimizer, build_ai_black_litterman_views
from services.regime_allocation import fit_allocations


def _price_series(prices: pd.DataFrame, ticker: str) -> pd.Series:
    """Extract a single ticker's closing-price series from a price DataFrame."""
    sym = ticker.upper().strip()
    if isinstance(prices, pd.Series):
        return prices.dropna()
    cols = {str(c).upper(): c for c in prices.columns}
    if sym in cols:
        return prices[cols[sym]].dropna()
    if len(prices.columns) == 1:
        return prices.iloc[:, 0].dropna()
    raise ValueError(f"No price column for {sym}")


def run_portfolio_pipeline(
    tickers: list[str],
    weights: list[float] | None = None,
    portfolio_value: float = 100000,
    start: str = "2020-01-01",
    end: str | None = None,
    horizon: int = 30,
    benchmark: str = "SPY",
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
    include_optional_ml: bool = True,
    portfolio_id: str | None = None,
    portfolio_revision: str | None = None,
    snapshot_as_of: str | None = None,
    currency: str | None = None,
    risk_preference: str = 'moderate',
    investment_horizon_years: float | None = None,
    horizon_source: str | None = None,
    base_currency: str | None = None,
    position_values: list[float] | None = None,
) -> dict:
    """
    Execute the full portfolio analysis pipeline.

    Returns a structured dict with every stage's output.
    """
    tickers = [t.strip().upper() for t in tickers]
    weights_array = np.asarray(weights, dtype=float)
    if not tickers or len(set(tickers)) != len(tickers) or any(not t for t in tickers):
        raise ValueError("Provide unique, non-empty tickers")
    if position_values is not None:
        native = np.asarray(position_values, dtype=float)
        if native.shape != (len(tickers),) or not np.isfinite(native).all() or (native < 0).any() or native.sum() <= 0:
            raise ValueError('Provide a non-negative native market value per ticker and a positive total')
    if position_values is None and weights is None:
        raise ValueError('Provide weights or native position_values')
    if weights is not None and (len(weights_array) != len(tickers) or not np.isfinite(weights_array).all()
            or (weights_array < 0).any() or abs(weights_array.sum() - 1.0) > WEIGHT_SUM_TOLERANCE):
        raise ValueError(f"Provide one non-negative weight per ticker, summing to 1 within tolerance {WEIGHT_SUM_TOLERANCE}")
    if not np.isfinite(portfolio_value) or portfolio_value <= 0:
        raise ValueError("Portfolio value must be positive and finite")

    # Safe normalization of tiny floating point drift
    if weights is not None:
        weights_array = weights_array / weights_array.sum()

    today = datetime.now().strftime("%Y-%m-%d")
    end = end or today
    if pd.Timestamp(start) >= pd.Timestamp(end):
        raise ValueError("Start date must precede end date")

    # ── 1. Market Data ────────────────────────────────────────────────
    data = get_portfolio_data(tickers, start, end)
    prices = data["prices"].loc[:, tickers]
    currency_map = data['currencies']
    currencies = {currency_map[t] for t in tickers}
    if currency and base_currency and currency.upper() != base_currency:
        raise ValueError('currency and base_currency must agree')
    if currency and not base_currency and len(currencies) == 1 and currency.upper() not in currencies:
        raise ValueError('Supplied currency does not match ticker quote currency; use base_currency for conversion')
    resolved_currency = base_currency or (currency.upper() if currency else None) or (
        'INR' if len(currencies) > 1 else next(iter(currencies)))
    prices, factors, fx = normalize_currency_prices(prices, currency_map, resolved_currency, start, end)
    returns = prices.pct_change(fill_method=None).dropna()
    if position_values is not None:
        converted_values = native * np.array([factors[t] for t in tickers])
        portfolio_value = float(converted_values.sum())
        if not np.isfinite(portfolio_value) or portfolio_value <= 0:
            raise ValueError('Converted position values must have a positive finite total')
        weights_array = converted_values / portfolio_value
    else:
        # Weights are dimensionless allocations and portfolio_value is already in base currency.
        converted_values = portfolio_value * weights_array
    weights = weights_array.tolist()
    fx['weight_source'] = 'converted_native_values' if position_values is not None else 'supplied_base_currency_weights'
    fx['position_values_base'] = dict(zip(tickers, converted_values.tolist()))
    currency_symbol = get_currency_symbol(dict.fromkeys(tickers, resolved_currency))

    stages = {
        "market_data": {"status": "SUCCESS", "reason": None},
        "risk": {"status": "SUCCESS", "reason": None},
        "risk_budget": {"status": "SUCCESS", "reason": None},
        "benchmark": {"status": "SUCCESS", "reason": None},
        "attribution": {"status": "SUCCESS", "reason": None},
        "regime": {"status": "SUCCESS", "reason": None},
        "stress_test": {"status": "SUCCESS", "reason": None},
        "optimization": {"status": "SUCCESS", "reason": None},
        "recommendations": {"status": "SUCCESS", "reason": None},
        "optional_ml": {
            "status": "SUCCESS" if include_optional_ml else "NOT_REQUESTED",
            "reason": None if include_optional_ml else "include_optional_ml is False",
        },
    }

    # ── 1b. Canonical Daily Portfolio Returns Series ───────────────────
    try:
        canonical_port_returns = canonical_portfolio_returns(returns, weights_array, tickers)
    except Exception as exc:
        canonical_port_returns = pd.Series(dtype=float)

    # ── 2. Risk Engine ────────────────────────────────────────────────
    try:
        risk = get_risk_summary(
            prices=prices,
            returns=returns,
            weights=weights_array,
            tickers=tickers,
            risk_free_rate=risk_free_rate,
        )
        risk_summary = risk["summary"].round(4).to_dict()
        portfolio_risk = risk.get("portfolio_risk")
        drawdown_series = risk["drawdown_series"]
    except Exception as exc:
        risk_summary = {}
        portfolio_risk = None
        drawdown_series = None
        stages["risk"] = {"status": "FAILED", "reason": str(exc)}

    # ── 3. Market Regime (HMM) ────────────────────────────────────────
    # SPY + portfolio-level regime
    try:
        spy_col = {str(c).upper(): c for c in prices.columns}.get("SPY")
        if spy_col:
            spy_prices = prices[spy_col].dropna()
            spy_returns = spy_prices.pct_change().dropna()
            market_regime = detect_market_regime_hmm(spy_returns)
        else:
            market_regime = detect_market_regime_hmm(returns.mean(axis=1))
        portfolio_regime = detect_market_regime_hmm(canonical_port_returns if not canonical_port_returns.empty else returns @ weights_array)
        if not market_regime or "current_regime" not in market_regime:
            stages["regime"] = {"status": "UNAVAILABLE", "reason": "HMM regime estimation returned incomplete data"}
    except Exception as exc:
        market_regime = {"current_regime": "Unknown", "confidence": 0.0}
        portfolio_regime = {"current_regime": "Unknown", "confidence": 0.0}
        stages["regime"] = {"status": "FAILED", "reason": str(exc)}

    # ── 4. Stress Testing ─────────────────────────────────────────────
    try:
        stress = get_stress_summary(tickers, weights, portfolio_value, prices=prices,
            benchmark_returns=returns.get(benchmark.upper()),
            benchmark_name=benchmark if benchmark.upper() in returns else 'current-weight portfolio')
    except Exception as exc:
        stress = {"stress_table": pd.DataFrame(), "worst_scenario": "N/A", "worst_loss": None, "worst_loss_pct": None, "error": str(exc)}
        stages["stress_test"] = {"status": "FAILED", "reason": str(exc)}

    # ── 5. Benchmark Comparison ───────────────────────────────────────
    try:
        benchmark_result = compute_benchmark_comparison(
            prices=prices,
            weights=weights_array,
            portfolio_value=portfolio_value,
            benchmark_ticker=benchmark,
            risk_free_rate=risk_free_rate,
            tickers=tickers,
            portfolio_returns=canonical_port_returns,
            base_currency=resolved_currency,
        )
        if isinstance(benchmark_result, dict) and "error" in benchmark_result:
            stages["benchmark"] = {"status": "UNAVAILABLE", "reason": benchmark_result["error"]}
    except Exception as exc:
        benchmark_result = {"error": str(exc)}
        stages["benchmark"] = {"status": "FAILED", "reason": str(exc)}

    # ── 6. Attribution ────────────────────────────────────────────────
    try:
        attribution = compute_attribution(
            tickers, weights, prices, portfolio_value, currency_symbol
        )
        if isinstance(attribution, dict) and "error" in attribution:
            stages["attribution"] = {"status": "UNAVAILABLE", "reason": attribution["error"]}
    except Exception as exc:
        attribution = {"error": str(exc)}
        stages["attribution"] = {"status": "FAILED", "reason": str(exc)}

    # ── 7. Risk Budgeting ─────────────────────────────────────────────
    try:
        risk_budget = compute_risk_budget(
            tickers, weights, returns, portfolio_value, confidence_level=0.95
        )
        if isinstance(risk_budget, dict) and "error" in risk_budget:
            stages["risk_budget"] = {"status": "UNAVAILABLE", "reason": risk_budget["error"]}
        else:
            risk_budget["currency"] = currency_symbol
    except Exception as exc:
        risk_budget = {"error": str(exc)}
        stages["risk_budget"] = {"status": "FAILED", "reason": str(exc)}

    try:
        correlation = compute_correlation_matrix(tickers, returns)
    except Exception:
        correlation = {}

    # ── 8. ML Models: Sentiment + MarketMind ─────────────────────────
    ticker_details = {}
    if not include_optional_ml:
        stages["optional_ml"] = {"status": "NOT_REQUESTED", "reason": "include_optional_ml is False"}
        for ticker in tickers:
            ticker_details[ticker] = {"status": "not_requested"}
    else:
        has_any_ml_success = False
        for ticker in tickers:
            sym = ticker.upper().strip()
            detail = {}
            try:
                detail["sentiment"] = get_sentiment_analysis(sym)
                has_any_ml_success = True
            except Exception as exc:
                detail["sentiment_error"] = str(exc)

            try:
                model = MarketMindMetaModel(
                    model_dir=os.path.join(os.path.dirname(__file__), "..", "models", "meta_model")
                )
                if model.is_ready():
                    if model.model is None:
                        model.load()
                    if model.model is not None:
                        detail["marketmind"] = model.predict_for_ticker(sym)
                        has_any_ml_success = True
                    else:
                        detail["marketmind"] = {"status": "not_trained"}
                else:
                    detail["marketmind"] = {"status": "not_trained"}
            except Exception as exc:
                detail["marketmind_error"] = str(exc)

            ticker_details[ticker] = detail
        stages["optional_ml"] = {
            "status": "SUCCESS" if has_any_ml_success else "UNAVAILABLE",
            "reason": None if has_any_ml_success else "No active ML model outputs available for tickers",
        }

    # ── 9. PPO is experimental and deliberately excluded from production ─
    rl_alloc = {
        "ready": False,
        "status": "experimental_disabled",
        "error": "PPO allocation is disabled for production decisions.",
    }

    # A transparent conventional baseline; the regime does not drive these weights.
    try:
        optimizer = PortfolioOptimizer(returns, risk_free_rate)
        allocation = optimizer.optimize_min_volatility()
        perf = optimizer._portfolio_performance(weights_array)
        perf["metric_type"] = "optimization_expected"
        perf["note"] = "Expected optimization performance using historical sample covariance and arithmetic mean returns; differs from realized historical CAGR."
        allocation["current_performance"] = perf
        allocation["metric_type"] = "optimization_expected"
        allocation["regime_aware"] = False
        allocation["evaluation"] = "in_sample"
        allocation["explanation"] = (
            "Minimizes historical covariance-based volatility with non-negative weights "
            "summing to 100%. Uses the displayed historical period, not an out-of-sample "
            "backtest. Market regime is shown separately and does not determine these weights."
        )
    except Exception as exc:
        allocation = {"status": "unavailable", "reason": str(exc)}

    try:
        regime_allocation = fit_allocations(returns, forecast_steps=2)
        if isinstance(regime_allocation, dict) and regime_allocation.get("status") == "unavailable":
            stages["optimization"] = {"status": "UNAVAILABLE", "reason": regime_allocation.get("reason", "Regime allocation unavailable")}
        else:
            stages["optimization"] = {"status": "SUCCESS", "reason": None}
    except (ValueError, np.linalg.LinAlgError) as exc:
        regime_allocation = {"status": "unavailable", "reason": str(exc)}
        stages["optimization"] = {"status": "UNAVAILABLE", "reason": str(exc)}

    # ── 10. Portfolio Score ───────────────────────────────────────────
    ai_optimizer = PortfolioOptimizer(returns, risk_free_rate)
    pi = 2.5 * ai_optimizer.cov_matrix.to_numpy() @ np.full(len(tickers), 1 / len(tickers))
    ai_views = build_ai_black_litterman_views(
        dict(zip(ai_optimizer.assets, pi)),
        dict(zip(ai_optimizer.assets, np.sqrt(np.diag(ai_optimizer.cov_matrix)))),
        {t: d.get('marketmind', {}).get('directional_probabilities',
            d.get('marketmind', {}).get('class_probabilities')) for t, d in ticker_details.items()},
        {t: d.get('sentiment', {}).get('finbert_score') for t, d in ticker_details.items()})
    ai_black_litterman_allocation = ai_optimizer.black_litterman(
        ai_views, risk_preference, investment_horizon_years, horizon_source)
    stages['ai_black_litterman_allocation'] = {
        'status': 'SUCCESS' if ai_black_litterman_allocation['success'] else 'UNAVAILABLE',
        'signal_status': ai_black_litterman_allocation['signal_status'],
        'reason': ai_black_litterman_allocation.get('reason')}
    if ai_black_litterman_allocation['effective_profile'] == 'aggressive':
        personalized_allocation = ai_black_litterman_allocation
    else:
        personalized_allocation = ai_optimizer.optimize_personalized(
            risk_preference, investment_horizon_years, horizon_source)
    stages['personalized_allocation'] = {
        'status': 'SUCCESS' if personalized_allocation['success'] else 'UNAVAILABLE',
        'reason': personalized_allocation.get('reason'),
    }
    asset_allocation = compute_asset_allocation(tickers, weights)
    portfolio_score = compute_portfolio_score(
        tickers=tickers,
        weights=weights,
        risk_summary=risk["summary"] if "summary" in risk else pd.DataFrame(),
        returns=returns,
        portfolio_value=portfolio_value,
        portfolio_metrics=portfolio_risk,
        risk_free_rate=risk_free_rate,
    )

    # ── 11. Recommendations ───────────────────────────────────────────
    try:
        recommendations = generate_recommendations(
            tickers=tickers,
            weights=weights,
            portfolio_value=portfolio_value,
            risk_summary=risk["summary"] if "summary" in risk else pd.DataFrame(),
            portfolio_returns=returns,
            regime=market_regime,
            stress=stress,
            portfolio_score=portfolio_score,
            attribution=attribution,
            risk_budget=risk_budget,
            forecast_details=ticker_details,
            marketmind_details={t: ticker_details.get(t, {}).get("marketmind", {}) for t in tickers},
            benchmark_comparison=benchmark_result,
            risk_preference=risk_preference,
            personalized_allocation=personalized_allocation,
            ai_black_litterman_allocation=ai_black_litterman_allocation,
        )
        stages["recommendations"] = {"status": "SUCCESS", "reason": None}
    except Exception as exc:
        recommendations = []
        stages["recommendations"] = {"status": "FAILED", "reason": str(exc)}

    # ── Identity & Metadata ──────────────────────────────────────────
    analysis_id = str(uuid.uuid4())
    analysis_as_of = datetime.now(timezone.utc).isoformat()
    analyzed_weights = [round(float(w), 6) for w in weights_array]

    methodology = {
        "return_type": "simple_daily",
        "trading_days_per_year": 252,
        "volatility_ddof": 1,
        "risk_free_rate_annual": risk_free_rate,
        "sharpe_method": "daily_excess_annualized",
        "sortino_mar": "risk_free_rate",
        "beta_method": "sample_covariance_over_sample_variance",
        "alpha_method": "jensens_alpha_annualized",
        "max_drawdown_model": "wealth_index_baseline_1",
        "portfolio_history_model": "constant_current_weights",
        "performance_label": "Historical simulation using current portfolio weights",
    }

    metadata = {
        'hmm': {k: market_regime.get(k) for k in ('hmm_converged', 'iterations_used',
            'covariance_type_used', 'state_probabilities')},
        "analysis_id": analysis_id,
        "portfolio_id": portfolio_id,
        "portfolio_revision": portfolio_revision,
        "snapshot_as_of": snapshot_as_of,
        "analysis_as_of": analysis_as_of,
        **fx,
        "currency": resolved_currency,
        "currency_symbol": currency_symbol,
        "benchmark": benchmark,
        "pipeline_version": "v2",
        "cached": False,
        "analyzed_tickers": tickers,
        "analyzed_weights": analyzed_weights,
        "methodology": methodology,
        "applied_profile": personalized_allocation['applied_profile'],
        "max_weight_cap": personalized_allocation['max_weight_cap'],
        "objective_used": personalized_allocation['objective_used'],
        "investment_horizon_years": investment_horizon_years,
        "horizon_source": personalized_allocation['horizon_source'],
        "horizon_modifier": personalized_allocation['horizon_modifier'],
        "personalized_constraints": {k: v for k, v in personalized_allocation.items()
                                     if k not in ('weights', 'performance')},
    }

    # ── Assemble ──────────────────────────────────────────────────────
    return {
        "analysis_id": analysis_id,
        "portfolio_id": portfolio_id,
        "portfolio_revision": portfolio_revision,
        "snapshot_as_of": snapshot_as_of,
        "analysis_as_of": analysis_as_of,
        **fx,
        "currency": resolved_currency,
        "currency_symbol": currency_symbol,
        "benchmark_ticker": benchmark,
        "pipeline_id": analysis_as_of,
        "pipeline_version": "v2",
        "cached": False,
        "metadata": metadata,
        "methodology": methodology,
        "stages": stages,
        "analyzed_tickers": tickers,
        "analyzed_weights": analyzed_weights,
        "tickers": tickers,
        "weights": analyzed_weights,
        "portfolio_value": portfolio_value,
        "period": {"start": start, "end": end},
        "market_data": {**data.get("price_metadata", {}), "first_observation": str(prices.index[0].date()),
                        "last_observation": str(prices.index[-1].date()), "price_observations": len(prices),
                        "return_observations": len(returns)},
        "risk_engine": risk_summary,
        "portfolio_risk": {k: v for k, v in portfolio_risk.items() if k not in ("drawdown_series", "portfolio_returns")} if portfolio_risk else None,
        "market_regime": market_regime,
        "portfolio_regime": portfolio_regime,
        "stress_test": {
            "error": stress.get("error"),
            "scenarios": stress.get("scenarios", {}),
            "stress_table": _clean_df(stress["stress_table"]) if "stress_table" in stress else {},
            "worst_scenario": stress.get("worst_scenario", "N/A"),
            "worst_loss": stress.get("worst_loss", 0),
            "worst_loss_pct": stress.get("worst_loss_pct", 0),
        },
        "benchmark": benchmark_result,
        "attribution": attribution,
        "risk_budget": risk_budget,
        "correlation": correlation,
        "ml_models": {
            "ticker_details": ticker_details,
            "rl_allocation": rl_alloc,
            "rl_ready": False,
        },
        "portfolio_score": portfolio_score,
        "asset_allocation": asset_allocation,
        "recommendations": recommendations,
        "allocation": allocation,
        "regime_allocation": regime_allocation,
        "personalized_allocation": personalized_allocation,
        "ai_black_litterman_allocation": ai_black_litterman_allocation,
    }


def _clean_df(df: pd.DataFrame) -> dict:
    """Convert a DataFrame to a JSON-serializable dict."""
    try:
        return df.to_dict()
    except Exception:
        return {"raw": str(df)}

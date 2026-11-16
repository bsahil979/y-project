# AI Black-Litterman allocation

The pipeline provides an AI comparison for every profile and uses it as the primary allocation for effective aggressive profiles. Short-horizon aggressive profiles retain maximum Sharpe. Standalone personalized optimization without AI views retains Phase 1 target-return behavior.

The equilibrium prior uses an equal-weight asset basket, not capitalization weights. Absolute annual return views follow the requested 65/35 MarketMind/FinBERT formula. Missing views are excluded from the posterior update. FinBERT-only aggregation excludes VADER fallback articles; missing news and VADER-only news produce null FinBERT scores.

Confidence is heuristic, not calibrated accuracy: 0.75 for two non-opposing sources, 0.35 for one source, 0.15 for opposing signs, zero for neither. Omega diagonal = max(tau * annual variance, 1e-12) * (1-confidence) / max(confidence, 1e-12), with tau=0.05. Prior and posterior utility solves use the same historical covariance and profile/horizon caps. Failed or infeasible solves return no weights.

The frontend requests optional inference and displays current/prior/AI weights and source coverage. A ticker without its own view can still change weight through covariance and constraints. These live signals and in-sample estimates are not out-of-sample performance evidence. Historical price selection does not make live news point-in-time historical news.

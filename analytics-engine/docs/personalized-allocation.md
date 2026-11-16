# Personalized allocation

`POST /portfolio/analyze` and `POST /portfolio/optimize` accept `risk_preference`
(`conservative`, `moderate`, `aggressive`; default `moderate`) and optional positive
finite `investment_horizon_years` and `horizon_source` (`explicit`, `nearest_goal`,
or `default`). Omitted source is inferred from the presence of a horizon; `default`
requires an absent horizon. `/recommendations` accepts the same fields.
Analysis cache keys include all three values. The optimize endpoint follows the profile
objective; the older `optimization_method` field is retained for payload compatibility
and does not override profile constraints.

| Profile | Objective | Position cap |
| --- | --- | --- |
| Conservative | Minimum volatility plus high-beta penalty | 20%; below five assets, min(100%, max(25%, 1.2 / asset count)) |
| Moderate | Maximum Sharpe | 30% |
| Aggressive | Minimum volatility at a historical return target | 40% |

Conservative beta is measured against the equally weighted input asset basket, not
an external market index. The objective adds 0.05 times weighted beta above one to
annualized volatility. Aggressive targets the 75th percentile of annualized asset
mean returns, lowered to the feasible maximum only if required by the position cap;
both requested and used targets and the adjustment flag are returned.

All allocations are long-only and fully invested. Infeasible small universes return
`status: infeasible`, no weights and a reason. Failed solves do not fall back to
unconstrained weights. Estimates are in-sample and exclude execution costs.
Horizon adjustments are deterministic:

- At most 2 years: cap is max(baseline cap minus 0.05, 1 / asset count).
  Conservative beta and volatility objective coefficients increase by 1.25x.
  Aggressive objective changes to maximum Sharpe, with effective profile moderate.
- Above 2 and below 7 years, including fractional years: baseline constraints,
  `horizon_modifier: baseline_medium_term`.
- At least 7 years: full baseline caps and objectives,
  `horizon_modifier: long_term_growth`.
- No horizon: original profile constraints, `horizon_modifier: default_profile`.

Short-term behavior reports `short_term_protection`, baseline cap, actual cap,
feasibility floor and whether the floor was applied. For small universes, the floor
can exceed even the baseline cap; this explicit exception allows full investment.
Requested and effective profiles are both retained. Beta uses the basket proxy.
Multiplying both conservative objective terms by the same factor does not change
their relative importance; weight changes come from the adjusted constraints.
These rules do not model liquidity or reserve cash, and tighter diversification caps
do not universally lower volatility. The deterministic aggressive-profile test shows
lower volatility on its fixture; it is not a guarantee for every portfolio.

The analysis response includes `personalized_allocation` beside the original
`allocation` and `regime_allocation`. Metadata records profile, cap, objective,
horizon, its source and modifier, and personalized constraints. Recommendation
explanations include these values and use the adjusted position caps. They retain
sector review thresholds (30/40/50%) and rebalance differences (2/4/5 percentage
points). Sector thresholds trigger reviews; they are not optimizer constraints.

Onboarding and Settings save a user-scoped local investor profile through
PortfolioDataService, notify the application context and update analysis payloads.
Legacy moderately conservative maps to conservative, moderately aggressive to
moderate, and very aggressive to aggressive. Preferences retain the existing local
storage behavior; this change does not introduce cloud profile synchronization.
An explicit horizon takes precedence; otherwise the frontend uses the nearest
future unfinished goal in the analyzed currency (and selected portfolio if scoped).
It never combines INR and USD goal horizons. Settings can clear the explicit horizon.

Tests: `python -m pytest tests/test_personalized_allocation.py -q` in analytics-engine;
`node --test tests/investorProfile.test.js tests/portfolioAnalyticsContract.test.js`
in frontend.

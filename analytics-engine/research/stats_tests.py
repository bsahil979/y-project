"""
stats_tests.py — Statistical significance tests for the paper.

Tests implemented:
  1. Bootstrap confidence intervals for Sharpe ratio
  2. Wilcoxon signed-rank test (non-parametric, monthly returns)
  3. Diebold-Mariano style test (compare strategy vs. baseline returns)
  4. Maximum Drawdown confidence interval (bootstrap)

These are required to prove that PPO+Regime improvements are statistically
significant, not due to chance — critical for acceptance at IEEE Access / Elsevier.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
from scipy import stats


TRADING_DAYS = 252


# ---------------------------------------------------------------------------
# 1. Bootstrap Sharpe Confidence Interval
# ---------------------------------------------------------------------------

def bootstrap_sharpe_ci(
    equity: pd.Series,
    rf_annual: float = 0.06,
    n_bootstrap: int = 10_000,
    confidence: float = 0.95,
    seed: int = 42,
) -> Dict:
    """
    Bootstrap 95% confidence interval for the Sharpe ratio.

    Method: Block bootstrap (block size = 21 trading days) to preserve
    autocorrelation structure of financial returns.

    Returns:
        {
          'sharpe_point'  : point estimate,
          'ci_lower'      : lower CI bound,
          'ci_upper'      : upper CI bound,
          'std_error'     : bootstrap std error,
          'n_bootstrap'   : number of bootstrap samples,
        }
    """
    rng = np.random.default_rng(seed)
    daily_returns = equity.pct_change().dropna().values
    rf_daily = (1.0 + rf_annual) ** (1.0 / TRADING_DAYS) - 1.0
    n = len(daily_returns)
    block_size = 21  # ~1 month

    def _sharpe(r):
        excess = r - rf_daily
        return (excess.mean() / (excess.std() + 1e-12)) * np.sqrt(TRADING_DAYS)

    point_estimate = _sharpe(daily_returns)

    # Block bootstrap
    sharpe_samples = []
    n_blocks = int(np.ceil(n / block_size))
    for _ in range(n_bootstrap):
        starts = rng.integers(0, max(n - block_size, 1), size=n_blocks)
        blocks = [daily_returns[s : s + block_size] for s in starts]
        sample = np.concatenate(blocks)[:n]
        sharpe_samples.append(_sharpe(sample))

    sharpe_samples = np.array(sharpe_samples)
    alpha = 1.0 - confidence
    ci_lower = float(np.percentile(sharpe_samples, 100 * alpha / 2))
    ci_upper = float(np.percentile(sharpe_samples, 100 * (1 - alpha / 2)))

    return {
        "sharpe_point": round(point_estimate, 4),
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "std_error": round(float(sharpe_samples.std()), 4),
        "n_bootstrap": n_bootstrap,
        "confidence": confidence,
    }


# ---------------------------------------------------------------------------
# 2. Wilcoxon Signed-Rank Test (Monthly Returns)
# ---------------------------------------------------------------------------

def wilcoxon_test(
    proposed_equity: pd.Series,
    baseline_equity: pd.Series,
    alternative: str = "greater",
) -> Dict:
    """
    Wilcoxon signed-rank test on monthly returns.
    Tests H0: proposed monthly returns == baseline monthly returns.
    Tests H1: proposed monthly returns > baseline monthly returns (one-sided).

    Returns:
        {
          'statistic'  : test statistic,
          'p_value'    : p-value,
          'significant': True if p < 0.05,
          'n_months'   : number of paired monthly observations,
          'alternative': alternative hypothesis,
        }
    """
    # Resample to monthly returns
    m1 = proposed_equity.resample("ME").last().pct_change().dropna()
    m2 = baseline_equity.resample("ME").last().pct_change().dropna()

    # Align on common dates
    common = m1.index.intersection(m2.index)
    m1 = m1.loc[common].values
    m2 = m2.loc[common].values

    if len(m1) < 10:
        return {
            "statistic": float("nan"),
            "p_value": float("nan"),
            "significant": False,
            "n_months": len(m1),
            "alternative": alternative,
            "note": "Insufficient data (<10 months)",
        }

    stat, p_val = stats.wilcoxon(m1 - m2, alternative=alternative)
    return {
        "statistic": round(float(stat), 4),
        "p_value": round(float(p_val), 4),
        "significant": float(p_val) < 0.05,
        "n_months": len(m1),
        "alternative": alternative,
    }


# ---------------------------------------------------------------------------
# 3. Paired t-test on Annual Returns (parametric alternative)
# ---------------------------------------------------------------------------

def paired_t_test(
    proposed_equity: pd.Series,
    baseline_equity: pd.Series,
    alternative: str = "greater",
) -> Dict:
    """
    Paired t-test on daily excess returns (proposed vs. baseline).
    Parametric complement to the Wilcoxon test.

    H0: mean(proposed - baseline) = 0
    H1: mean(proposed - baseline) > 0

    Returns:
        {'t_stat', 'p_value', 'significant', 'n_days', 'mean_excess_daily'}
    """
    r1 = proposed_equity.pct_change().dropna()
    r2 = baseline_equity.pct_change().dropna()
    common = r1.index.intersection(r2.index)
    diff = (r1.loc[common] - r2.loc[common]).values

    if len(diff) < 30:
        return {"t_stat": float("nan"), "p_value": float("nan"), "significant": False}

    t_stat, p_two = stats.ttest_1samp(diff, popmean=0.0)
    p_one = p_two / 2 if t_stat > 0 else 1.0 - p_two / 2  # one-sided

    return {
        "t_stat": round(float(t_stat), 4),
        "p_value": round(float(p_one), 4),
        "significant": float(p_one) < 0.05,
        "n_days": len(diff),
        "mean_excess_daily": round(float(diff.mean()), 6),
        "mean_excess_annualized": round(float(diff.mean() * TRADING_DAYS), 4),
    }


# ---------------------------------------------------------------------------
# 4. Bootstrap Max Drawdown CI
# ---------------------------------------------------------------------------

def bootstrap_max_dd_ci(
    equity: pd.Series,
    n_bootstrap: int = 5_000,
    confidence: float = 0.95,
    seed: int = 42,
) -> Dict:
    """
    Bootstrap confidence interval for Maximum Drawdown.
    Uses block bootstrap (block=21 days) to preserve serial correlation.
    """
    rng = np.random.default_rng(seed)
    daily_returns = equity.pct_change().dropna().values
    n = len(daily_returns)
    block_size = 21

    def _max_dd(r):
        eq = np.cumprod(1.0 + r)
        peak = np.maximum.accumulate(eq)
        dd = (eq - peak) / (peak + 1e-12)
        return float(dd.min())

    point_estimate = _max_dd(daily_returns)
    n_blocks = int(np.ceil(n / block_size))
    dd_samples = []
    for _ in range(n_bootstrap):
        starts = rng.integers(0, max(n - block_size, 1), size=n_blocks)
        blocks = [daily_returns[s : s + block_size] for s in starts]
        sample = np.concatenate(blocks)[:n]
        dd_samples.append(_max_dd(sample))

    dd_samples = np.array(dd_samples)
    alpha = 1.0 - confidence
    ci_lower = float(np.percentile(dd_samples, 100 * alpha / 2))
    ci_upper = float(np.percentile(dd_samples, 100 * (1 - alpha / 2)))

    return {
        "max_dd_point": round(point_estimate, 4),
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "confidence": confidence,
    }


# ---------------------------------------------------------------------------
# 5. Full statistical comparison report
# ---------------------------------------------------------------------------

def full_significance_report(
    proposed_equity: pd.Series,
    baselines: Dict[str, pd.Series],
    rf_annual: float = 0.06,
    proposed_name: str = "PPO-Regime (Ours)",
) -> pd.DataFrame:
    """
    Run all significance tests comparing the proposed strategy against each baseline.

    Returns a DataFrame with one row per baseline comparison.
    Suitable for inclusion as a paper table (Table 4 or Appendix).
    """
    rows = []
    for baseline_name, baseline_equity in baselines.items():
        wilcox = wilcoxon_test(proposed_equity, baseline_equity)
        ttest = paired_t_test(proposed_equity, baseline_equity)
        sharpe_ci = bootstrap_sharpe_ci(proposed_equity, rf_annual=rf_annual, n_bootstrap=5_000)

        rows.append({
            "Baseline": baseline_name,
            "Wilcoxon p": wilcox["p_value"],
            "Wilcoxon sig.": "✓" if wilcox["significant"] else "✗",
            "t-test p": ttest["p_value"],
            "t-test sig.": "✓" if ttest["significant"] else "✗",
            "Sharpe (proposed)": sharpe_ci["sharpe_point"],
            f"Sharpe {int(sharpe_ci['confidence']*100)}% CI": f"[{sharpe_ci['ci_lower']}, {sharpe_ci['ci_upper']}]",
            "N months": wilcox.get("n_months", "—"),
        })

    df = pd.DataFrame(rows).set_index("Baseline")
    return df

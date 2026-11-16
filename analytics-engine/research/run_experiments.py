"""
run_experiments.py — Main experiment runner for the research paper.

Usage:
    # From the analytics-engine directory:
    python -m research.run_experiments

    # Or with custom config:
    python -m research.run_experiments --tickers RELIANCE.NS TCS.NS INFY.NS SPY QQQ GLD TLT
                                       --start 2018-01-01 --end 2024-12-31
                                       --ppo-steps 200000 --folds 3

Output:
    research/results/
        equity_curves.csv       — daily equity for all strategies
        metrics_table.csv       — performance metrics (paper Table 3)
        table_results.tex       — LaTeX version of metrics table
        significance_table.csv  — statistical tests (paper Table 4)
        figures/
            fig1_equity_curves.pdf/png
            fig2_rolling_sharpe.pdf/png
            fig3_drawdowns.pdf/png
            fig4_regime_overlay.pdf/png
            fig5_ablation.pdf/png
            fig6_heatmap.pdf/png
"""

import sys
import os
import argparse
import logging
import json

# Ensure stdout and stderr handle unicode characters cleanly on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import numpy as np
import pandas as pd

# Ensure analytics-engine root is on path
_engine_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _engine_root not in sys.path:
    sys.path.insert(0, _engine_root)

from research.backtest_engine import (
    BacktestConfig,
    WalkForwardBacktester,
    PPORegimeAware,
    load_universe_data,
)
from research.baselines import (
    EqualWeight,
    BuyAndHold,
    MarkowitzMVO,
    MarkowitzMaxSharpe,
    PPONoRegime,
)
from research.metrics import metrics_table
from research.stats_tests import full_significance_report
from research.plot_results import PaperFigures

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
os.makedirs("research/results", exist_ok=True)
os.makedirs("research/results/figures", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("research/results/experiment.log", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger("run_experiments")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_regime_series(returns: pd.DataFrame) -> pd.Series:
    """
    Fit HMM on full portfolio returns and return per-day regime label.
    Used for Fig 4 regime overlay.
    """
    from hmmlearn.hmm import GaussianHMM

    port_ret = returns.mean(axis=1).fillna(0).values.reshape(-1, 1)
    try:
        hmm = GaussianHMM(n_components=3, covariance_type="diag", n_iter=100, random_state=42)
        hmm.fit(port_ret)
        states = hmm.predict(port_ret)
        # Sort: 0=Bear (lowest mean), 1=Sideways, 2=Bull (highest mean)
        means = hmm.means_.flatten()
        order = np.argsort(means)  # ascending
        remap = {old: new for new, old in enumerate(order)}
        states = np.array([remap[s] for s in states])
    except Exception:
        states = np.zeros(len(returns), dtype=int)

    return pd.Series(states, index=returns.index, name="regime")


def print_results_table(results: dict):
    """Pretty-print the metrics table to stdout."""
    metrics_list = [r["metrics"] for r in results.values()]
    df = metrics_table(metrics_list)
    print("\n" + "=" * 80)
    print("RESULTS TABLE (out-of-sample, walk-forward)")
    print("=" * 80)
    col_rename = {
        "total_return": "Total Ret %",
        "cagr": "CAGR %",
        "ann_vol": "Ann Vol %",
        "sharpe": "Sharpe",
        "sortino": "Sortino",
        "calmar": "Calmar",
        "max_drawdown": "Max DD %",
        "win_rate": "Win Rate %",
        "var_95": "VaR 95% %",
        "cvar_95": "CVaR 95% %",
        "turnover": "Turnover",
    }
    display_df = df.rename(columns=col_rename)
    print(display_df.to_string())
    print("=" * 80 + "\n")


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def run(config: BacktestConfig):
    os.makedirs(config.results_dir, exist_ok=True)
    os.makedirs(os.path.join(config.results_dir, "figures"), exist_ok=True)

    logger.info("=" * 70)
    logger.info("EXPERIMENT: Regime-Aware RL Portfolio Allocation")
    logger.info("=" * 70)
    logger.info(f"Universe ({len(config.tickers)} assets): {config.tickers}")
    logger.info(f"Period: {config.start_date} → {config.end_date}")
    logger.info(f"Walk-forward: {config.n_folds} folds | train={config.train_years}yr | test={config.test_years}yr")
    logger.info(f"PPO timesteps per fold: {config.ppo_timesteps:,}")

    # Step 1: Download data
    logger.info("\n[1/5] Downloading market data...")
    prices, returns = load_universe_data(config)

    # Save dataset info
    dataset_info = {
        "tickers": list(prices.columns),
        "start": str(prices.index[0].date()),
        "end": str(prices.index[-1].date()),
        "n_trading_days": len(prices),
    }
    with open(os.path.join(config.results_dir, "dataset_info.json"), "w", encoding="utf-8") as f:
        json.dump(dataset_info, f, indent=2)
    logger.info(f"   Data: {list(prices.columns)} | {len(prices)} days")

    # Step 2: Define strategies
    strategies = [
        PPORegimeAware(),           # Proposed method
        PPONoRegime(),              # Ablation
        MarkowitzMaxSharpe(),       # Classical ML baseline
        MarkowitzMVO(),             # Classical baseline
        EqualWeight(),              # Naive baseline
        BuyAndHold(),               # Passive baseline
    ]

    # Step 3: Run walk-forward backtest
    logger.info(f"\n[2/5] Running walk-forward backtest ({len(strategies)} strategies × {config.n_folds} folds)...")
    engine = WalkForwardBacktester(prices, returns, config)
    results = engine.run(strategies)

    # Step 4: Print results table
    logger.info("\n[3/5] Computing metrics and significance tests...")
    print_results_table(results)

    # Step 5: Statistical significance tests
    proposed_name = "PPO-Regime (Ours)"
    if proposed_name in results:
        proposed_eq = results[proposed_name]["equity"]
        baseline_equities = {
            name: r["equity"]
            for name, r in results.items()
            if name != proposed_name
        }
        sig_df = full_significance_report(
            proposed_eq, baseline_equities, rf_annual=config.rf_annual
        )
        sig_path = os.path.join(config.results_dir, "significance_table.csv")
        sig_df.to_csv(sig_path)
        logger.info(f"Significance table saved → {sig_path}")

        sig_latex = sig_df.to_latex(
            caption="Statistical significance tests: proposed PPO+Regime vs. baselines.",
            label="tab:significance",
            escape=True,
        )
        with open(os.path.join(config.results_dir, "table_significance.tex"), "w", encoding="utf-8") as f:
            f.write(sig_latex)

        print("\nSTATISTICAL SIGNIFICANCE (Wilcoxon & t-test, H1: proposed > baseline)")
        try:
            print(sig_df.to_string())
        except UnicodeEncodeError:
            print(sig_df.to_string().encode("ascii", "replace").decode("ascii"))

    # Step 6: Generate figures
    logger.info("\n[4/5] Generating paper figures...")
    regime_series = build_regime_series(returns)
    figs = PaperFigures(
        results=results,
        regime_series=regime_series,
        output_dir=os.path.join(config.results_dir, "figures"),
        rf_annual=config.rf_annual,
    )
    figs.plot_all()

    # Step 7: Final summary
    logger.info("\n[5/5] Experiment complete.")
    logger.info(f"All outputs saved in: {config.results_dir}/")
    logger.info("\nFiles for your paper:")
    logger.info(f"  Table 3 (LaTeX): {config.results_dir}/table_results.tex")
    logger.info(f"  Table 4 (LaTeX): {config.results_dir}/table_significance.tex")
    logger.info(f"  Fig 1–6 (PDF):   {config.results_dir}/figures/fig*.pdf")

    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Run walk-forward backtest for the RL Portfolio paper."
    )
    parser.add_argument(
        "--tickers", nargs="+",
        default=None,
        help="Asset tickers (e.g. RELIANCE.NS TCS.NS SPY QQQ GLD TLT)",
    )
    parser.add_argument("--start", default="2018-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2024-12-31", help="End date (YYYY-MM-DD)")
    parser.add_argument("--folds", type=int, default=3, help="Number of walk-forward folds")
    parser.add_argument("--train-years", type=float, default=3.0, help="Training window in years")
    parser.add_argument("--test-years", type=float, default=1.0, help="Test window in years")
    parser.add_argument("--ppo-steps", type=int, default=200_000, help="PPO timesteps per fold")
    parser.add_argument("--rf", type=float, default=0.06, help="Risk-free rate (annual)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--results-dir", default="research/results", help="Output directory")
    parser.add_argument("--price-file", default=None, help="Optional CSV file of pre-aligned daily prices")
    args = parser.parse_args()

    # Default mixed universe: 5 Indian + 5 US
    default_tickers = [
        "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
        "SPY", "QQQ", "GLD", "TLT", "EEM",
    ]

    config = BacktestConfig(
        tickers=args.tickers or default_tickers,
        start_date=args.start,
        end_date=args.end,
        n_folds=args.folds,
        train_years=args.train_years,
        test_years=args.test_years,
        ppo_timesteps=args.ppo_steps,
        rf_annual=args.rf,
        seed=args.seed,
        results_dir=args.results_dir,
        price_file=args.price_file,
    )

    run(config)


if __name__ == "__main__":
    main()

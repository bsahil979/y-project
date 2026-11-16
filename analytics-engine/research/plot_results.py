"""
plot_results.py — Paper-quality figures for the research paper.

Figures generated:
  Fig 1: Equity curves (log scale) — all strategies
  Fig 2: Rolling Sharpe ratio (63-day window)
  Fig 3: Drawdown comparison
  Fig 4: HMM Regime timeline overlaid on portfolio returns
  Fig 5: Ablation bar chart — PPO+Regime vs PPO-NoRegime
  Fig 6: Metrics comparison heatmap

Usage:
    from research.plot_results import PaperFigures
    figs = PaperFigures(results, regime_series, output_dir="research/results/figures")
    figs.plot_all()
"""

import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, Optional

# Matplotlib backend — use Agg for headless/server environments
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
import matplotlib.ticker as mtick
import matplotlib.patches as mpatches

_engine_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _engine_root not in sys.path:
    sys.path.insert(0, _engine_root)

from research.metrics import rolling_sharpe, drawdown_series

# ---------------------------------------------------------------------------
# Style constants
# ---------------------------------------------------------------------------

STRATEGY_COLORS = {
    "PPO-Regime (Ours)":    "#2563EB",   # Blue — proposed method (bold)
    "PPO-NoRegime":         "#93C5FD",   # Light blue — ablation
    "Markowitz-MaxSharpe":  "#16A34A",   # Green
    "Markowitz-MinVol":     "#86EFAC",   # Light green
    "Buy-and-Hold":         "#DC2626",   # Red
    "Equal-Weight":         "#9CA3AF",   # Gray
}

STRATEGY_LINESTYLES = {
    "PPO-Regime (Ours)":    "-",
    "PPO-NoRegime":         "--",
    "Markowitz-MaxSharpe":  "-",
    "Markowitz-MinVol":     "--",
    "Buy-and-Hold":         "-.",
    "Equal-Weight":         ":",
}

REGIME_COLORS = {0: "#FCA5A5", 1: "#86EFAC", 2: "#FDE68A"}  # Bear/Bull/Sideways
REGIME_LABELS = {0: "Bear", 1: "Bull", 2: "Sideways"}

FIGURE_DPI = 300
FONT_FAMILY = "DejaVu Sans"
plt.rcParams.update({
    "font.family": FONT_FAMILY,
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "legend.fontsize": 9,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


# ---------------------------------------------------------------------------
# PaperFigures class
# ---------------------------------------------------------------------------

class PaperFigures:
    """
    Generate all paper figures from backtest results.

    Args:
        results       : Dict from WalkForwardBacktester.run()
                        {name: {'equity': pd.Series, 'metrics': dict, ...}}
        regime_series : pd.Series of integer regime codes (0/1/2) aligned with equity dates
        output_dir    : Directory to save figures
        rf_annual     : Risk-free rate for rolling Sharpe
    """

    def __init__(
        self,
        results: Dict[str, Dict],
        regime_series: Optional[pd.Series] = None,
        output_dir: str = "research/results/figures",
        rf_annual: float = 0.06,
    ):
        self.results = results
        self.regime_series = regime_series
        self.output_dir = output_dir
        self.rf_annual = rf_annual
        os.makedirs(output_dir, exist_ok=True)

    def plot_all(self):
        """Generate all figures and save to output_dir."""
        saved = []
        saved.append(self.fig1_equity_curves())
        saved.append(self.fig2_rolling_sharpe())
        saved.append(self.fig3_drawdowns())
        if self.regime_series is not None:
            saved.append(self.fig4_regime_overlay())
        saved.append(self.fig5_ablation_bars())
        saved.append(self.fig6_metrics_heatmap())
        print(f"\n[OK] All figures saved to: {self.output_dir}")
        for p in saved:
            if p:
                print(f"   {p}")
        return saved

    # -----------------------------------------------------------------------
    # Figure 1: Equity Curves (log scale)
    # -----------------------------------------------------------------------
    def fig1_equity_curves(self) -> str:
        fig, ax = plt.subplots(figsize=(10, 5))
        for name, result in self.results.items():
            eq = result["equity"].dropna()
            color = STRATEGY_COLORS.get(name, "#666666")
            ls = STRATEGY_LINESTYLES.get(name, "-")
            lw = 2.5 if "Ours" in name else 1.5
            ax.plot(eq.index, eq.values, label=name, color=color, linestyle=ls, linewidth=lw)

        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:.1f}×"))
        ax.set_xlabel("Date")
        ax.set_ylabel("Portfolio Value (log scale, start = 1.0)")
        ax.set_title("Figure 1: Out-of-Sample Portfolio Equity Curves (Walk-Forward Backtest)")
        ax.legend(loc="upper left", framealpha=0.8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        fig.tight_layout()

        path = os.path.join(self.output_dir, "fig1_equity_curves.pdf")
        fig.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight")
        fig.savefig(path.replace(".pdf", ".png"), dpi=FIGURE_DPI, bbox_inches="tight")
        plt.close(fig)
        return path

    # -----------------------------------------------------------------------
    # Figure 2: Rolling Sharpe Ratio
    # -----------------------------------------------------------------------
    def fig2_rolling_sharpe(self) -> str:
        fig, ax = plt.subplots(figsize=(10, 4))
        for name, result in self.results.items():
            eq = result["equity"].dropna()
            roll_sharpe = rolling_sharpe(eq, window=63, rf_annual=self.rf_annual)
            color = STRATEGY_COLORS.get(name, "#666666")
            ls = STRATEGY_LINESTYLES.get(name, "-")
            lw = 2.0 if "Ours" in name else 1.2
            ax.plot(roll_sharpe.index, roll_sharpe.values, label=name, color=color, linestyle=ls, linewidth=lw)

        ax.axhline(0, color="black", linestyle="--", linewidth=0.8, alpha=0.5)
        ax.set_xlabel("Date")
        ax.set_ylabel("Rolling Sharpe Ratio (63-day)")
        ax.set_title("Figure 2: Rolling Sharpe Ratio Comparison")
        ax.legend(loc="upper left", framealpha=0.8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        fig.tight_layout()

        path = os.path.join(self.output_dir, "fig2_rolling_sharpe.pdf")
        fig.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight")
        fig.savefig(path.replace(".pdf", ".png"), dpi=FIGURE_DPI, bbox_inches="tight")
        plt.close(fig)
        return path

    # -----------------------------------------------------------------------
    # Figure 3: Drawdown Comparison
    # -----------------------------------------------------------------------
    def fig3_drawdowns(self) -> str:
        fig, ax = plt.subplots(figsize=(10, 4))
        for name, result in self.results.items():
            eq = result["equity"].dropna()
            dd = drawdown_series(eq)
            color = STRATEGY_COLORS.get(name, "#666666")
            ls = STRATEGY_LINESTYLES.get(name, "-")
            lw = 2.0 if "Ours" in name else 1.2
            ax.plot(dd.index, dd.values * 100, label=name, color=color, linestyle=ls, linewidth=lw)

        ax.set_xlabel("Date")
        ax.set_ylabel("Drawdown (%)")
        ax.set_title("Figure 3: Drawdown Comparison (Lower is Better)")
        ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
        ax.legend(loc="lower left", framealpha=0.8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        fig.tight_layout()

        path = os.path.join(self.output_dir, "fig3_drawdowns.pdf")
        fig.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight")
        fig.savefig(path.replace(".pdf", ".png"), dpi=FIGURE_DPI, bbox_inches="tight")
        plt.close(fig)
        return path

    # -----------------------------------------------------------------------
    # Figure 4: Regime Overlay on Returns
    # -----------------------------------------------------------------------
    def fig4_regime_overlay(self) -> str:
        if self.regime_series is None:
            return ""

        # Use proposed method equity for background
        proposed_key = next((k for k in self.results if "Ours" in k), list(self.results.keys())[0])
        eq = self.results[proposed_key]["equity"].dropna()

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 6), sharex=True, gridspec_kw={"height_ratios": [2, 1]})

        # Top: equity curve with regime background shading
        ax1.plot(eq.index, eq.values, color=STRATEGY_COLORS.get(proposed_key, "#2563EB"), linewidth=2, label=proposed_key)
        _shade_regimes(ax1, self.regime_series, eq.index)
        ax1.set_yscale("log")
        ax1.set_ylabel("Portfolio Value (log)")
        ax1.set_title("Figure 4: Portfolio Equity with HMM Market Regime Overlay")
        ax1.legend(loc="upper left")

        # Bottom: regime timeline
        regime_aligned = self.regime_series.reindex(eq.index, method="ffill").fillna(0)
        for regime_id, color in REGIME_COLORS.items():
            mask = regime_aligned == regime_id
            ax2.fill_between(
                regime_aligned.index,
                0, 1,
                where=mask.values,
                color=color, alpha=0.8,
                label=REGIME_LABELS[regime_id],
                transform=ax2.get_xaxis_transform(),
            )
        ax2.set_ylabel("Regime")
        ax2.set_yticks([])
        ax2.legend(loc="upper left")
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

        fig.tight_layout()
        path = os.path.join(self.output_dir, "fig4_regime_overlay.pdf")
        fig.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight")
        fig.savefig(path.replace(".pdf", ".png"), dpi=FIGURE_DPI, bbox_inches="tight")
        plt.close(fig)
        return path

    # -----------------------------------------------------------------------
    # Figure 5: Ablation Bar Chart
    # -----------------------------------------------------------------------
    def fig5_ablation_bars(self) -> str:
        metrics_of_interest = ["sharpe", "sortino", "calmar", "max_drawdown"]
        labels = ["Sharpe Ratio", "Sortino Ratio", "Calmar Ratio", "Max Drawdown (%)"]
        multipliers = [1, 1, 1, 100]  # convert max_dd to %

        strategies_to_compare = [
            k for k in self.results
            if "PPO" in k or "Markowitz" in k or "Equal" in k
        ]

        x = np.arange(len(metrics_of_interest))
        width = 0.8 / max(len(strategies_to_compare), 1)

        fig, ax = plt.subplots(figsize=(11, 5))
        for i, name in enumerate(strategies_to_compare):
            vals = []
            for m, mult in zip(metrics_of_interest, multipliers):
                v = self.results[name]["metrics"].get(m, 0.0)
                # max_drawdown is negative, show abs
                if m == "max_drawdown":
                    v = abs(v) * mult
                else:
                    v = v * mult
                vals.append(v)
            offset = (i - len(strategies_to_compare) / 2 + 0.5) * width
            color = STRATEGY_COLORS.get(name, "#999999")
            bars = ax.bar(x + offset, vals, width=width * 0.9, label=name, color=color, alpha=0.85)
            # Highlight proposed
            if "Ours" in name:
                for bar in bars:
                    bar.set_edgecolor("black")
                    bar.set_linewidth(1.5)

        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_title("Figure 5: Ablation Study — Strategy Performance Comparison")
        ax.set_ylabel("Metric Value")
        ax.legend(loc="upper right", framealpha=0.85)
        fig.tight_layout()

        path = os.path.join(self.output_dir, "fig5_ablation.pdf")
        fig.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight")
        fig.savefig(path.replace(".pdf", ".png"), dpi=FIGURE_DPI, bbox_inches="tight")
        plt.close(fig)
        return path

    # -----------------------------------------------------------------------
    # Figure 6: Metrics Heatmap
    # -----------------------------------------------------------------------
    def fig6_metrics_heatmap(self) -> str:
        metrics_to_show = ["cagr", "ann_vol", "sharpe", "sortino", "calmar", "max_drawdown", "win_rate"]
        col_labels = ["CAGR (%)", "Vol (%)", "Sharpe", "Sortino", "Calmar", "Max DD (%)", "Win Rate (%)"]
        pct_cols = {"cagr", "ann_vol", "max_drawdown", "win_rate"}

        strategy_names = list(self.results.keys())
        data = []
        for name in strategy_names:
            m = self.results[name]["metrics"]
            row = []
            for metric in metrics_to_show:
                v = m.get(metric, 0.0)
                if metric in pct_cols:
                    v = abs(v) * 100 if metric == "max_drawdown" else v * 100
                row.append(round(float(v), 2))
            data.append(row)

        data = np.array(data)
        # Normalize each column to [0, 1] for coloring
        norm_data = np.zeros_like(data)
        for j in range(data.shape[1]):
            col = data[:, j]
            col_min, col_max = col.min(), col.max()
            if col_max > col_min:
                norm_data[:, j] = (col - col_min) / (col_max - col_min)
            # For max_drawdown (lower is better), invert
            if metrics_to_show[j] == "max_drawdown":
                norm_data[:, j] = 1.0 - norm_data[:, j]

        fig, ax = plt.subplots(figsize=(12, max(4, len(strategy_names) * 0.8 + 1.5)))
        im = ax.imshow(norm_data, cmap="RdYlGn", aspect="auto", vmin=0, vmax=1)

        ax.set_xticks(range(len(col_labels)))
        ax.set_xticklabels(col_labels, rotation=30, ha="right")
        ax.set_yticks(range(len(strategy_names)))
        ax.set_yticklabels(strategy_names)

        # Annotate cells
        for i in range(len(strategy_names)):
            for j in range(len(metrics_to_show)):
                text = ax.text(
                    j, i, f"{data[i, j]:.2f}",
                    ha="center", va="center",
                    color="black", fontsize=9,
                    fontweight="bold" if "Ours" in strategy_names[i] else "normal",
                )

        ax.set_title("Figure 6: Performance Metrics Heatmap (Green = Better)")
        fig.tight_layout()

        path = os.path.join(self.output_dir, "fig6_heatmap.pdf")
        fig.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight")
        fig.savefig(path.replace(".pdf", ".png"), dpi=FIGURE_DPI, bbox_inches="tight")
        plt.close(fig)
        return path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _shade_regimes(ax, regime_series: pd.Series, date_index: pd.DatetimeIndex):
    """Shade background of ax according to HMM regime."""
    aligned = regime_series.reindex(date_index, method="ffill").fillna(0)
    current_regime = int(aligned.iloc[0])
    segment_start = date_index[0]

    for i in range(1, len(date_index)):
        r = int(aligned.iloc[i])
        if r != current_regime or i == len(date_index) - 1:
            ax.axvspan(
                segment_start, date_index[i],
                alpha=0.12,
                color=REGIME_COLORS.get(current_regime, "#FFFFFF"),
                label=f"_nolegend_",
            )
            current_regime = r
            segment_start = date_index[i]

    # Legend patches
    patches = [
        mpatches.Patch(color=REGIME_COLORS[r], alpha=0.4, label=REGIME_LABELS[r])
        for r in REGIME_COLORS
    ]
    ax.legend(handles=patches + [ax.lines[0]], loc="upper left")

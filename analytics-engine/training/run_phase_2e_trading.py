"""Phase 2E.4 / 2E.5: evaluation-only cost-aware trading analysis of frozen predictions."""

import hashlib
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PHASE_2E_DIRECTORY = os.path.join(ROOT, "models", "phase_2e")
PREDICTION_PATH = os.path.join(PHASE_2E_DIRECTORY, "holdout_predictions.csv")
PREDICTION_MANIFEST_PATH = os.path.join(PHASE_2E_DIRECTORY, "phase_2e_prediction_manifest.json")
REPORT_PATH = os.path.join(PHASE_2E_DIRECTORY, "phase_2e_trading_report.json")

STARTING_CAPITAL = 100000.0
DEFAULT_COST_BPS = 10  # 10 bps = 0.10% per trade
ANNUALIZATION_FACTOR = 252


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def simulate_trading(df, model_prefix, cost_bps=10, strategy="long_only", rebalance_freq=1):
    """Simulate portfolio performance for a given model prediction series."""
    cost_rate = cost_bps / 10000.0
    pred_col = f"{model_prefix}_prediction"
    
    dates = sorted(df["Date"].unique())
    n_dates = len(dates)
    
    # Pre-extract data structures for fast lookup
    grouped_data = {}
    for d, g in df.groupby("Date"):
        tickers = g["ticker"].to_numpy()
        preds = g[pred_col].to_numpy()
        f_rets = g["future_return"].to_numpy()
        
        if rebalance_freq == 1:
            r1_rets = np.where(f_rets > -1.0, (1.0 + f_rets) ** 0.2 - 1.0, -1.0)
            ret_map = dict(zip(tickers, r1_rets))
        else:
            ret_map = dict(zip(tickers, f_rets))
            
        grouped_data[d] = {
            "buy_tickers": tickers[preds == 1].tolist(),
            "sell_tickers": tickers[preds == -1].tolist() if strategy == "long_short" else [],
            "ret_map": ret_map,
        }
    
    portfolio_value = STARTING_CAPITAL
    equity_curve = []
    daily_returns = []
    turnover_series = []
    cost_series = []
    
    prev_weights = {}
    
    for idx, date in enumerate(dates):
        g_info = grouped_data[date]
        
        if strategy == "long_only":
            buy_tickers = g_info["buy_tickers"]
            n_buy = len(buy_tickers)
            if n_buy > 0:
                target_weights = {t: 1.0 / n_buy for t in buy_tickers}
            else:
                target_weights = {}
        elif strategy == "long_short":
            buy_tickers = g_info["buy_tickers"]
            sell_tickers = g_info["sell_tickers"]
            n_buy, n_sell = len(buy_tickers), len(sell_tickers)
            target_weights = {}
            if n_buy > 0:
                for t in buy_tickers:
                    target_weights[t] = 0.5 / n_buy
            if n_sell > 0:
                for t in sell_tickers:
                    target_weights[t] = -0.5 / n_sell
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
            
        if idx % rebalance_freq != 0 and idx > 0:
            target_weights = prev_weights.copy()
            
        all_tickers = set(prev_weights.keys()).union(set(target_weights.keys()))
        turnover = sum(abs(target_weights.get(t, 0.0) - prev_weights.get(t, 0.0)) for t in all_tickers)
        if idx == 0:
            turnover = sum(abs(target_weights.get(t, 0.0)) for t in target_weights)
            
        transaction_cost = turnover * cost_rate * portfolio_value
        
        ticker_returns = g_info["ret_map"]
        gross_return = sum(target_weights.get(t, 0.0) * ticker_returns.get(t, 0.0) for t in target_weights)
        net_return = (1.0 - (turnover * cost_rate)) * (1.0 + gross_return) - 1.0
        portfolio_value *= (1.0 + net_return)
        
        next_weights = {}
        if portfolio_value > 0 and (1.0 + gross_return) > 0:
            for t, w in target_weights.items():
                r_t = ticker_returns.get(t, 0.0)
                next_weights[t] = w * (1.0 + r_t) / (1.0 + gross_return)
        prev_weights = next_weights
        
        equity_curve.append({"Date": date, "portfolio_value": float(portfolio_value), "net_return": float(net_return)})
        daily_returns.append(net_return)
        turnover_series.append(turnover)
        cost_series.append(transaction_cost)
        
    daily_rets = np.array(daily_returns)
    total_net_return = (portfolio_value - STARTING_CAPITAL) / STARTING_CAPITAL
    annualized_return = ((portfolio_value / STARTING_CAPITAL) ** (ANNUALIZATION_FACTOR / n_dates)) - 1.0 if n_dates > 0 else 0.0
    annualized_volatility = float(np.std(daily_rets) * np.sqrt(ANNUALIZATION_FACTOR))
    
    mean_ret = float(np.mean(daily_rets))
    std_ret = float(np.std(daily_rets))
    sharpe_ratio = float((mean_ret / std_ret) * np.sqrt(ANNUALIZATION_FACTOR)) if std_ret > 1e-12 else 0.0
    
    values = np.array([e["portfolio_value"] for e in equity_curve])
    running_max = np.maximum.accumulate(values)
    drawdowns = (running_max - values) / running_max
    max_drawdown = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0
    
    total_turnover = float(np.sum(turnover_series))
    avg_daily_turnover = float(np.mean(turnover_series))
    total_transaction_costs = float(np.sum(cost_series))
    
    return {
        "starting_capital": STARTING_CAPITAL,
        "ending_capital": float(portfolio_value),
        "net_return": float(total_net_return),
        "annualized_return": float(annualized_return),
        "annualized_volatility": float(annualized_volatility),
        "sharpe_ratio": float(sharpe_ratio),
        "maximum_drawdown": float(max_drawdown),
        "total_turnover": float(total_turnover),
        "avg_daily_turnover": float(avg_daily_turnover),
        "total_transaction_costs": float(total_transaction_costs),
        "cost_bps": cost_bps,
        "strategy": strategy,
        "rebalance_freq_days": rebalance_freq,
        "trading_days": n_dates,
        "equity_curve_head": equity_curve[:5],
        "equity_curve_tail": equity_curve[-5:],
    }


def compute_deltas(a_res, b_res):
    return {
        "net_return": b_res["net_return"] - a_res["net_return"],
        "annualized_return": b_res["annualized_return"] - a_res["annualized_return"],
        "annualized_volatility": b_res["annualized_volatility"] - a_res["annualized_volatility"],
        "sharpe_ratio": b_res["sharpe_ratio"] - a_res["sharpe_ratio"],
        "maximum_drawdown": b_res["maximum_drawdown"] - a_res["maximum_drawdown"],
        "total_turnover": b_res["total_turnover"] - a_res["total_turnover"],
        "avg_daily_turnover": b_res["avg_daily_turnover"] - a_res["avg_daily_turnover"],
        "total_transaction_costs": b_res["total_transaction_costs"] - a_res["total_transaction_costs"],
    }


def main():
    if not os.path.exists(PREDICTION_PATH) or not os.path.exists(PREDICTION_MANIFEST_PATH):
        raise FileNotFoundError("Frozen Phase 2E.1 prediction CSV and manifest are required.")
    if os.path.exists(REPORT_PATH):
        raise FileExistsError("Phase 2E.4/2E.5 trading report already exists and is frozen; refusing to overwrite it.")
        
    with open(PREDICTION_MANIFEST_PATH, encoding="utf-8") as file:
        manifest = json.load(file)
    prediction_hash = sha256(PREDICTION_PATH)
    if prediction_hash != manifest["prediction_file"]["sha256"]:
        raise ValueError("Frozen Phase 2E.1 prediction CSV hash differs from its manifest.")
        
    frame = pd.read_csv(PREDICTION_PATH)
    if len(frame) != manifest["prediction_file"]["rows"] or list(frame.columns) != manifest["prediction_column_schema"]:
        raise ValueError("Frozen Phase 2E.1 prediction CSV differs from its manifest.")
        
    a_primary = simulate_trading(frame, "A", cost_bps=10, strategy="long_only", rebalance_freq=1)
    b_primary = simulate_trading(frame, "B", cost_bps=10, strategy="long_only", rebalance_freq=1)
    deltas_primary = compute_deltas(a_primary, b_primary)
    
    cost_sensitivities = {}
    for bps in [0, 5, 10, 20]:
        a_sens = simulate_trading(frame, "A", cost_bps=bps, strategy="long_only", rebalance_freq=1)
        b_sens = simulate_trading(frame, "B", cost_bps=bps, strategy="long_only", rebalance_freq=1)
        cost_sensitivities[f"{bps}_bps"] = {
            "A": a_sens,
            "B": b_sens,
            "B_minus_A": compute_deltas(a_sens, b_sens),
        }
        
    a_ls = simulate_trading(frame, "A", cost_bps=10, strategy="long_short", rebalance_freq=1)
    b_ls = simulate_trading(frame, "B", cost_bps=10, strategy="long_short", rebalance_freq=1)
    
    a_h5 = simulate_trading(frame, "A", cost_bps=10, strategy="long_only", rebalance_freq=5)
    b_h5 = simulate_trading(frame, "B", cost_bps=10, strategy="long_only", rebalance_freq=5)
    
    report = {
        "phase": "2E.4_2E.5",
        "status": "completed",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_mode": "prediction_artifact_only",
        "input": {
            "prediction_csv_path": PREDICTION_PATH,
            "prediction_csv_sha256": prediction_hash,
            "prediction_manifest_path": PREDICTION_MANIFEST_PATH,
            "prediction_manifest_sha256": sha256(PREDICTION_MANIFEST_PATH),
        },
        "constraints": {
            "models_loaded": False,
            "models_retrained": False,
            "dataset_loaded": False,
            "thresholds_changed": False,
            "resampling_performed": False,
            "future_return_used_as_input": False,
            "identical_execution_rules": True,
        },
        "simulation_parameters": {
            "starting_capital": STARTING_CAPITAL,
            "default_transaction_cost_bps": DEFAULT_COST_BPS,
            "annualization_factor": ANNUALIZATION_FACTOR,
            "holding_period_days": 1,
        },
        "primary_evaluation": {
            "A": a_primary,
            "B": b_primary,
            "B_minus_A": deltas_primary,
        },
        "sensitivities": {
            "cost_sensitivity": cost_sensitivities,
            "long_short_strategy": {
                "A": a_ls,
                "B": b_ls,
                "B_minus_A": compute_deltas(a_ls, b_ls),
            },
            "five_day_rebalance_period": {
                "A": a_h5,
                "B": b_h5,
                "B_minus_A": compute_deltas(a_h5, b_h5),
            },
        },
    }
    
    with open(REPORT_PATH, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, allow_nan=False)
        
    print(json.dumps({
        "report": REPORT_PATH,
        "input_sha256": prediction_hash,
        "primary_evaluation": {
            "A_sharpe": a_primary["sharpe_ratio"],
            "B_sharpe": b_primary["sharpe_ratio"],
            "A_net_return": a_primary["net_return"],
            "B_net_return": b_primary["net_return"],
            "A_max_drawdown": a_primary["maximum_drawdown"],
            "B_max_drawdown": b_primary["maximum_drawdown"],
            "B_minus_A_sharpe": deltas_primary["sharpe_ratio"],
            "B_minus_A_net_return": deltas_primary["net_return"],
        }
    }, indent=2))


if __name__ == "__main__":
    main()
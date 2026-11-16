"""Phase 2E.6: evaluation-only robustness and attribution analysis of frozen predictions."""
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
REPORT_PATH = os.path.join(PHASE_2E_DIRECTORY, "phase_2e_attribution_report.json")

STARTING_CAPITAL = 100000.0
ANNUALIZATION_FACTOR = 252

def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def simulate_subsegment(df, model_prefix, cost_bps=10):
    cost_rate = cost_bps / 10000.0
    pred_col = f"{model_prefix}_prediction"
    dates = sorted(df["Date"].unique())
    n_dates = len(dates)
    if n_dates == 0:
        return None
    grouped_data = {}
    for d, g in df.groupby("Date"):
        tickers = g["ticker"].to_numpy()
        preds = g[pred_col].to_numpy()
        f_rets = g["future_return"].to_numpy()
        r1_rets = np.where(f_rets > -1.0, (1.0 + f_rets) ** 0.2 - 1.0, -1.0)
        ret_map = dict(zip(tickers, r1_rets))
        grouped_data[d] = {
            "buy_tickers": tickers[preds == 1].tolist(),
            "ret_map": ret_map,
        }
    portfolio_value = STARTING_CAPITAL
    daily_returns = []
    turnover_series = []
    cost_series = []
    gross_returns = []
    prev_weights = {}
    for idx, date in enumerate(dates):
        g_info = grouped_data[date]
        buy_tickers = g_info["buy_tickers"]
        n_buy = len(buy_tickers)
        target_weights = {t: 1.0 / n_buy for t in buy_tickers} if n_buy > 0 else {}
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
        daily_returns.append(net_return)
        gross_returns.append(gross_return)
        turnover_series.append(turnover)
        cost_series.append(transaction_cost)
    daily_rets = np.array(daily_returns)
    total_net_return = (portfolio_value - STARTING_CAPITAL) / STARTING_CAPITAL
    annualized_return = ((portfolio_value / STARTING_CAPITAL) ** (ANNUALIZATION_FACTOR / n_dates)) - 1.0 if n_dates > 0 else 0.0
    annualized_volatility = float(np.std(daily_rets) * np.sqrt(ANNUALIZATION_FACTOR))
    std_ret = float(np.std(daily_rets))
    sharpe_ratio = float((np.mean(daily_rets) / std_ret) * np.sqrt(ANNUALIZATION_FACTOR)) if std_ret > 1e-12 else 0.0
    total_gross_return = float(np.prod(1.0 + np.array(gross_returns)) - 1.0)
    return {
        "net_return": float(total_net_return),
        "gross_return": float(total_gross_return),
        "annualized_return": float(annualized_return),
        "annualized_volatility": float(annualized_volatility),
        "sharpe_ratio": float(sharpe_ratio),
        "total_turnover": float(np.sum(turnover_series)),
        "avg_daily_turnover": float(np.mean(turnover_series)),
        "total_transaction_costs": float(np.sum(cost_series)),
        "trading_days": n_dates,
    }

def find_breakeven_cost(df):
    low, high = 0.0, 50.0
    best_bps = None
    for _ in range(30):
        mid = (low + high) / 2.0
        a_res = simulate_subsegment(df, "A", cost_bps=mid)
        b_res = simulate_subsegment(df, "B", cost_bps=mid)
        diff = b_res["net_return"] - a_res["net_return"]
        if abs(diff) < 1e-6:
            best_bps = mid
            break
        if diff > 0:
            high = mid
        else:
            low = mid
    if best_bps is None:
        best_bps = (low + high) / 2.0
    return float(best_bps)

def compute_monthly_returns(df, model_prefix, cost_bps=10):
    df_copy = df.copy()
    df_copy["month"] = df_copy["Date"].str.slice(0, 7)
    months = sorted(df_copy["month"].unique())
    monthly_results = []
    for m in months:
        sub_df = df_copy[df_copy["month"] == m]
        res = simulate_subsegment(sub_df, model_prefix, cost_bps=cost_bps)
        if res:
            monthly_results.append({
                "month": m,
                "net_return": res["net_return"],
                "gross_return": res["gross_return"],
                "turnover": res["total_turnover"],
                "transaction_costs": res["total_transaction_costs"],
            })
    return monthly_results

def compute_segmentation_breakdowns(df, segment_col, cost_bps=10):
    results = {}
    for seg_val in sorted(df[segment_col].unique()):
        sub_df = df[df[segment_col] == seg_val]
        a_res = simulate_subsegment(sub_df, "A", cost_bps=cost_bps)
        b_res = simulate_subsegment(sub_df, "B", cost_bps=cost_bps)
        if a_res and b_res:
            results[str(seg_val)] = {
                "rows": len(sub_df),
                "A": a_res,
                "B": b_res,
                "B_minus_A": {
                    "net_return": b_res["net_return"] - a_res["net_return"],
                    "sharpe_ratio": b_res["sharpe_ratio"] - a_res["sharpe_ratio"],
                    "turnover": b_res["total_turnover"] - a_res["total_turnover"],
                    "transaction_costs": b_res["total_transaction_costs"] - a_res["total_transaction_costs"],
                }
            }
    return results

def compute_ticker_attributions(df, cost_bps=10):
    ticker_res = {}
    for ticker in sorted(df["ticker"].unique()):
        sub_df = df[df["ticker"] == ticker]
        a_res = simulate_subsegment(sub_df, "A", cost_bps=cost_bps)
        b_res = simulate_subsegment(sub_df, "B", cost_bps=cost_bps)
        if a_res and b_res:
            ticker_res[ticker] = {
                "A_net_return": a_res["net_return"],
                "B_net_return": b_res["net_return"],
                "B_minus_A_net_return": b_res["net_return"] - a_res["net_return"],
                "A_turnover": a_res["total_turnover"],
                "B_turnover": b_res["total_turnover"],
            }
    sorted_tickers = sorted(ticker_res.items(), key=lambda x: x[1]["B_minus_A_net_return"], reverse=True)
    top_5 = dict(sorted_tickers[:5])
    bottom_5 = dict(sorted_tickers[-5:])
    return {
        "top_5_b_advantages": top_5,
        "bottom_5_b_disadvantages": bottom_5,
        "total_tickers_evaluated": len(ticker_res),
        "b_outperformed_tickers_count": sum(1 for v in ticker_res.values() if v["B_minus_A_net_return"] > 0),
    }

def main():
    if not os.path.exists(PREDICTION_PATH) or not os.path.exists(PREDICTION_MANIFEST_PATH):
        raise FileNotFoundError("Frozen Phase 2E.1 prediction CSV and manifest are required.")
    if os.path.exists(REPORT_PATH):
        raise FileExistsError("Phase 2E.6 attribution report already exists and is frozen; refusing to overwrite it.")
    with open(PREDICTION_MANIFEST_PATH, encoding="utf-8") as file:
        manifest = json.load(file)
    prediction_hash = sha256(PREDICTION_PATH)
    if prediction_hash != manifest["prediction_file"]["sha256"]:
        raise ValueError("Frozen Phase 2E.1 prediction CSV hash differs from its manifest.")
    frame = pd.read_csv(PREDICTION_PATH)
    if len(frame) != manifest["prediction_file"]["rows"] or list(frame.columns) != manifest["prediction_column_schema"]:
        raise ValueError("Frozen Phase 2E.1 prediction CSV differs from its manifest.")
    breakeven_cost_bps = find_breakeven_cost(frame)
    monthly_a = compute_monthly_returns(frame, "A", cost_bps=10)
    monthly_b = compute_monthly_returns(frame, "B", cost_bps=10)
    monthly_comparison = []
    for ma, mb in zip(monthly_a, monthly_b):
        monthly_comparison.append({
            "month": ma["month"],
            "A_net_return": ma["net_return"],
            "B_net_return": mb["net_return"],
            "B_minus_A_net_return": mb["net_return"] - ma["net_return"],
            "A_turnover": ma["turnover"],
            "B_turnover": mb["turnover"],
        })
    market_segmentation = compute_segmentation_breakdowns(frame, "market", cost_bps=10)
    sector_segmentation = compute_segmentation_breakdowns(frame, "sector", cost_bps=10)
    regime_segmentation = compute_segmentation_breakdowns(frame, "regime_code", cost_bps=10)
    ticker_attribution = compute_ticker_attributions(frame, cost_bps=10)
    report = {
        "phase": "2E.6",
        "status": "completed",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_mode": "prediction_artifact_only",
        "input": {
            "prediction_csv_path": PREDICTION_PATH,
            "prediction_csv_sha256": prediction_hash,
            "prediction_manifest_path": PREDICTION_MANIFEST_PATH,
        },
        "constraints": {
            "models_loaded": False,
            "models_retrained": False,
            "dataset_loaded": False,
            "thresholds_changed": False,
            "resampling_performed": False,
            "future_return_used_as_input": False,
        },
        "breakeven_analysis": {
            "crossover_cost_bps": breakeven_cost_bps,
            "interpretation": f"Below {breakeven_cost_bps:.2f} bps transaction cost Model A wins on raw signal return; above {breakeven_cost_bps:.2f} bps Model B wins due to lower turnover friction.",
        },
        "monthly_breakdown": monthly_comparison,
        "segmentation": {
            "by_market": market_segmentation,
            "by_sector": sector_segmentation,
            "by_regime": regime_segmentation,
        },
        "ticker_attribution": ticker_attribution,
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, allow_nan=False)
    print(json.dumps({
        "report": REPORT_PATH,
        "input_sha256": prediction_hash,
        "breakeven_cost_bps": breakeven_cost_bps,
        "b_outperformed_tickers_count": ticker_attribution["b_outperformed_tickers_count"],
        "total_tickers": ticker_attribution["total_tickers_evaluated"],
    }, indent=2))

if __name__ == "__main__":
    main()
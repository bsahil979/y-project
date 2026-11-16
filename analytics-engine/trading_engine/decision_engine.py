import numpy as np
import pandas as pd
import json
import os
import datetime
from .models_layer import TradingModels
from .exceptions import ModelNotFoundError
from .universal_models import apply_hybrid_to_trading_models
from .rl_agent import TradingEnv
from .meta_model import MarketMindMetaModel
from stable_baselines3 import PPO


class BrainMemory:
    """The 'Memory' layer: stores past decisions and outcomes."""
    def __init__(self, filepath="trading_memory.json"):
        self.filepath = filepath
        self.history = self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def record(self, entry):
        self.history.append(entry)
        if len(self.history) > 50:
            self.history = self.history[-50:]
        with open(self.filepath, "w") as f:
            json.dump(self.history, f, indent=4)

    def get_performance(self):
        if not self.history:
            return {"win_rate": 0.5, "total_trades": 0, "avg_profit": 0}
        wins = sum(1 for h in self.history if h.get("outcome") == "win")
        total = len(self.history)
        return {
            "win_rate": round(wins / total if total > 0 else 0.5, 2),
            "total_trades": total,
            "avg_profit": 0.02,
        }


class DecisionEngine:
    def __init__(self, data, ticker="generic", models_dir="../models", train_on_missing: bool = True):
        self.data = data
        self.ticker = ticker
        self.models_dir = models_dir
        self.tm = TradingModels(data)
        self.memory = BrainMemory()
        self.rl_model = None
        self.train_on_missing = train_on_missing
        self.universal = None
        self.analysis_mode = "none"
        self.model_sources = {}
        self.has_rl = False
        self.fallback_reason = "No PPO model available"
        self.meta_model = MarketMindMetaModel(model_dir=os.path.join(models_dir, 'meta_model'))

    def initialize(self, rl_timesteps=200):
        """Load per-ticker models, fall back to universal hybrid pool, then optional RL."""
        print("Brain thinking: Hybrid model load (per-ticker -> universal)...")
        hybrid = apply_hybrid_to_trading_models(self.tm, self.ticker, self.models_dir)
        self.analysis_mode = hybrid["analysis_mode"]
        self.model_sources = hybrid["components"]
        self.universal = hybrid["universal"]

        missing = [k for k in ("lstm", "rf", "hmm") if k not in self.model_sources]

        if missing:
            if not self.train_on_missing:
                print(f"No ML models for {self.ticker}. Using Live Technical Analysis fallback.")
                self.analysis_mode = "live_analysis"
                self.model_sources = {"lstm": "live_rules", "rf": "live_rules", "hmm": "live_rules"}
            else:
                print(f"Training missing components on live data (dev mode): {missing}")
                if "lstm" in missing:
                    self.tm.train_lstm(epochs=1)
                    self.model_sources["lstm"] = "live_trained"
                if "rf" in missing:
                    self.tm.train_rf()
                    self.model_sources["rf"] = "live_trained"
                if "hmm" in missing:
                    self.tm.train_hmm()
                    self.model_sources["hmm"] = "live_trained"
                self.analysis_mode = "live_trained"
        else:
            print(f"ML ready: mode={self.analysis_mode} sources={self.model_sources}")

        print("Brain learning: RL Agent...")
        env = TradingEnv(self.data)
        ppo_path = os.path.join(self.models_dir, f"{self.ticker}", "ppo_policy.zip")
        if os.path.exists(ppo_path):
            try:
                self.rl_model = PPO.load(ppo_path, env=env)
                self.has_rl = True
                self.fallback_reason = None
                print("PPO policy loaded (per-ticker).")
            except Exception as e:
                print("PPO load failed:", e)
                self.has_rl = False
                self.fallback_reason = "PPO load failed; using RF + regime fallback."
        else:
            self.has_rl = False
            if self.train_on_missing:
                self.rl_model = PPO("MlpPolicy", env, verbose=0)
                self.rl_model.learn(total_timesteps=rl_timesteps)
                self.has_rl = True
                self.fallback_reason = None
            else:
                self.fallback_reason = "No PPO for this ticker — using RF+regime rule fallback."
                print(self.fallback_reason)

    def _predict_rf(self):
        if self.model_sources.get("rf") == "universal":
            return self.universal.predict_rf(self.data)
        if self.model_sources.get("rf") == "live_rules":
            last_row = self.data.iloc[-1]
            rsi = float(last_row.get("rsi", 50))
            macd_diff = float(last_row.get("macd_diff", 0))
            if rsi < 40 and macd_diff > 0:
                return 1, 0.75
            elif rsi > 60 and macd_diff < 0:
                return -1, 0.75
            else:
                return 0, 0.5

        try:
            return self.tm.predict_rf()
        except Exception:
            last_row = self.data.iloc[-1]
            rsi = float(last_row.get("rsi", 50))
            macd_diff = float(last_row.get("macd_diff", 0))
            if rsi < 40 and macd_diff > 0:
                return 1, 0.7
            if rsi > 60 and macd_diff < 0:
                return -1, 0.7
            return 0, 0.5

    def _detect_regime(self):
        if self.model_sources.get("hmm") == "universal":
            return self.universal.detect_regime(self.data)
        if self.model_sources.get("hmm") == "live_rules":
            last_row = self.data.iloc[-1]
            macd_diff = float(last_row.get("macd_diff", 0))
            return "Bullish" if macd_diff >= 0 else "Bearish"

        try:
            return self.tm.detect_regime()
        except Exception:
            last_row = self.data.iloc[-1]
            macd_diff = float(last_row.get("macd_diff", 0))
            return "Bullish" if macd_diff >= 0 else "Bearish"

    def _predict_lstm(self, horizon=5):
        if self.model_sources.get("lstm") == "universal":
            return self.universal.predict_lstm_prices(self.data, horizon=horizon)
        if self.model_sources.get("lstm") == "live_rules":
            last_row = self.data.iloc[-1]
            close = float(last_row["Close"])
            macd_diff = float(last_row.get("macd_diff", 0))
            return np.array([close * (1 + (macd_diff / (close + 1e-5)) * (i + 1) * 0.05) for i in range(horizon)])

        try:
            return self.tm.predict_lstm(horizon)
        except Exception:
            last_row = self.data.iloc[-1]
            close = float(last_row["Close"])
            macd_diff = float(last_row.get("macd_diff", 0))
            return np.array([close * (1 + (macd_diff / (close + 1e-5)) * (i + 1) * 0.05) for i in range(horizon)])

    def _rule_action(self, rf_sig, regime):
        if regime == "Bullish" and rf_sig >= 0:
            return "BUY"
        if regime == "Bearish" and rf_sig <= 0:
            return "SELL"
        if rf_sig == 1:
            return "BUY"
        if rf_sig == -1:
            return "SELL"
        return "HOLD"

    def _predict_meta_model(self):
        try:
            if not self.meta_model.is_ready():
                self.meta_model.load()
            if self.meta_model.model is None:
                return None
            row = self.data.tail(1).copy()
            row['ema_50'] = row['Close'].ewm(span=50, adjust=False).mean()
            row['ema_200'] = row['Close'].ewm(span=200, adjust=False).mean()
            row['trend_strength'] = (row['Close'] - row['ema_50']) / row['ema_50'].replace(0, np.nan)
            row['momentum_5d'] = row['Close'].pct_change(5)
            row['momentum_10d'] = row['Close'].pct_change(10)
            row['lstm_signal'] = float(self.data['returns'].tail(10).mean())
            row['rf_signal'] = float((row['rsi'].iloc[-1] - 50) / 50.0 if 'rsi' in row.columns else 0.0)
            row['regime_code'] = int(1 if self._detect_regime() == 'Bullish' else (-1 if self._detect_regime() == 'Bearish' else 0))
            row['sentiment_score'] = 0.0
            result = self.meta_model.predict_single(row)
            return result
        except Exception:
            return None

    def get_decision(self):
        rf_sig, rf_prob = self._predict_rf()
        regime = self._detect_regime()
        lstm_forecast = self._predict_lstm(5)
        meta_result = self._predict_meta_model()

        last_row = self.data.iloc[-1]
        is_weekend = bool(last_row["is_weekend"])

        if self.has_rl and self.rl_model is not None:
            obs = np.array([
                float(last_row["rsi"]),
                float(last_row["macd_diff"]),
                float(last_row["adx"]),
                float(last_row["volatility"]),
                float(last_row["day_of_week"]) / 6.0,
                float(last_row["hour"]) / 23.0,
                float(last_row["is_weekend"]),
                float((lstm_forecast[-1] / last_row["Close"]) - 1),
                float(rf_sig),
                1.0 if regime == "Bullish" else (-1.0 if regime == "Bearish" else 0.0),
                1.0, 1.0,
            ], dtype=np.float32)
            rl_action, _ = self.rl_model.predict(obs, deterministic=True)
            action_map = {0: "HOLD", 1: "BUY", 2: "SELL"}
            final_action = action_map[int(rl_action)]
            decision_source = "rl_ppo"
        else:
            final_action = self._rule_action(rf_sig, regime)
            decision_source = "rf_regime_fallback"

        confidence_boost = 0
        if is_weekend and final_action != "HOLD":
            confidence_boost -= 0.1

        perf = self.memory.get_performance()
        self.memory.record({
            "timestamp": datetime.datetime.now().isoformat(),
            "action": final_action,
            "price": float(last_row["Close"]),
            "regime": regime,
            "is_weekend": is_weekend,
            "outcome": "pending",
        })

        confidence = float(rf_prob * 0.4) if rf_prob is not None else 0.0
        if (final_action == "BUY" and rf_sig == 1) or (final_action == "SELL" and rf_sig == -1):
            confidence += 0.4
        if (final_action == "BUY" and regime == "Bullish") or (final_action == "SELL" and regime == "Bearish"):
            confidence += 0.2
        if not self.has_rl:
            confidence *= 0.85
        confidence = max(0, min(1.0, confidence + confidence_boost))

        mode_label = {
            "per_ticker": "per-ticker ML (live data + saved models)",
            "universal": "universal ML (live data + shared models)",
            "hybrid": "hybrid ML (mix of per-ticker and universal)",
            "live_analysis": "Live Technical Analysis (RSI, MACD momentum rules)",
        }.get(self.analysis_mode, self.analysis_mode)

        reasoning = [
            f"Perception: {'Weekend' if is_weekend else 'Weekday'} — liquidity {'lower' if is_weekend else 'normal'}.",
            f"Thinking ({mode_label}): {regime} regime; LSTM trend {'up' if lstm_forecast[-1] > last_row['Close'] else 'down'}.",
            f"Signals: RF={rf_sig} (sources: {self.model_sources}).",
            f"Decision: {final_action} via {decision_source}"
            + (" (full RL)." if self.has_rl else " (no per-ticker RL; rule fallback)."),
        ]

        output = {
            "action": final_action,
            "confidence": round(confidence, 2),
            "reasoning": reasoning,
            "regime": regime,
            "is_weekend": is_weekend,
            "forecast": lstm_forecast.tolist(),
            "performance": perf,
            "analysis_mode": self.analysis_mode,
            "model_sources": self.model_sources,
            "has_rl": self.has_rl,
            "fallback_reason": self.fallback_reason,
        }

        if meta_result is not None:
            output["marketmind_model"] = {
                "recommendation": meta_result["recommendation"],
                "confidence": meta_result["confidence"],
                "score": meta_result["score"],
                "class_probabilities": meta_result["class_probabilities"],
            }
            output["action"] = meta_result["recommendation"]
            output["confidence"] = round(max(float(output["confidence"]), float(meta_result["confidence"])), 2)

        return output

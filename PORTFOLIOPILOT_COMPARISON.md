# PortfolioPilot vs. Smart Portfolio Advisor (LY) — Systematic Comparison & Action Plan

> Generated after analyzing **portfoliopilot.com** against the current state of this repo
> (`smart-portfolio-advisor/`).

---

## 0. What PortfolioPilot actually is

PortfolioPilot (by Global Predictions Inc., a SEC-Registered Investment Advisor) markets itself as an
**"AI Financial Advisor for self-directed investors."** Its pillars:

| # | Pillar | What it does |
|---|--------|--------------|
| 1 | **Net Worth Dashboard** | Aggregates ALL assets (brokerage, 401k, IRA, crypto, cash, loans, real estate, private equity, metals) via 12,000+ bank/brokerage connections into one net-worth view. |
| 2 | **AI Investing Advice** | Personalized buy/sell/hold recommendations + a portfolio "strength score" driven by an economic Knowledge Graph + Forecasting engine. |
| 3 | **Continuous Tax Optimization** | Monthly tax-loss harvesting (claims ~1.94%/yr from JP Morgan research). |
| 4 | **Estate Planning Checklist** | Documents, beneficiaries, wills, trusts, power-of-attorney tracking. |
| 5 | **Retirement Planner** | Goal-based projection, withdrawal modeling, Monte Carlo success probability. |
| 6 | **Scenario Modeling** | "What-if" sliders to test decisions over time. |
| 7 | **Monitoring & Alerts** | Economy + portfolio risk notifications. |
| 8 | **Pricing** | Free tier + Gold ($20/mo) — positioned as ~98% cheaper than a 1% AUM advisor. |

Brand framing: **"Finally there's a financial advisor you can trust — you."** No commissions, no human bias.

---

## 1. What LY (this project) already has — and is actually *better* at

Reading `MISSING_CAPABILITIES_ANALYSIS.md`, `api.js`, the services folder, and the frontend components,
LY already has a strong quant/AI foundation that PortfolioPilot does *not* emphasize:

✅ **Already implemented & strong (keep / lead with these):**
- ML forecasting: **TimesFM 2.5** 30-day price trajectories (`services/forecaster.py`)
- **HMM market-regime detection** (`services/regime_detector.py`, `/market-regime` endpoint)
- **FinBERT sentiment** from news (`services/sentiment_analyzer.py`)
- **PPO reinforcement-learning portfolio allocator** across 100 tickers (experimental)
- **LLM + RAG AI Advisor chat** with tool-calling (`agents/ai_advisor.py`, `/chat/tools`)
- **Risk metrics, stress testing, correlation, diversification scoring**
- **Benchmark comparison, attribution, risk budgeting** services (recently added)
- **Goal analyzer / goal engine** (`goal_analyzer.py`, `goal_engine.py`)
- **Monitoring & alert rules** (`monitoring_alerts.py`, `/monitoring/*` endpoints)
- **Paper trading / execution simulator**
- **Model training UI** (LSTM/HMM/RF/PPO)
- Multi-region (US + India) with localized currency

So LY is **ML-deeper** than PortfolioPilot. PortfolioPilot is **holistic-net-worth & advice-deeper** than LY.

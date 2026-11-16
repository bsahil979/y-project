# 🚀 Smart Portfolio Advisor & Recommendation System

[![React](https://img.shields.io/badge/Frontend-React-61DAFB?style=for-the-badge&logo=react)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Supabase](https://img.shields.io/badge/Database-Supabase-3ECF8E?style=for-the-badge&logo=supabase)](https://supabase.com/)
[![TensorFlow](https://img.shields.io/badge/AI-TensorFlow-FF6F00?style=for-the-badge&logo=tensorflow)](https://www.tensorflow.org/)

A portfolio-analysis application and research prototype. The current focus is explaining portfolio risk and testing whether HMM market-state information improves allocation. See [what we are building](./PROJECT_DIRECTION.md) and the [implemented research study](./analytics-engine/research/REGIME_STUDY.md). Other model modules remain exploratory extensions.

See the [complete project roadmap](./PROJECT_ROADMAP.md) for the delivery phases, paper plan, research checks and optional extensions. The [literature matrix](./LITERATURE_MATRIX.md) maps key portfolio and regime-switching papers to the project design and its limitations.

---

## 🏗️ System Architecture

See [ARCHITECTURE_DIAGRAM.md](./ARCHITECTURE_DIAGRAM.md) for the full visual system diagram.

| Component | Technology Stack | Core Responsibility |
| :--- | :--- | :--- |
| **Frontend** | React 18, Tailwind CSS, Recharts | Dynamic Dashboard, Real-time Visualizations, AI Advisor Chat |
| **Analytics Engine** | Python 3.9+, FastAPI, PyTorch | Market Regime Detection, LSTM Forecasting, Signal Classification |
| **Persistence Layer**| Supabase (PostgreSQL) | Secure User Auth, Portfolio Tracking, Historical Data Cache |

### PPO fallback and backtesting

The portfolio decision engine uses PPO when a model artifact exists. If PPO is missing, stale, or fails to load, the engine automatically falls back to the RF + regime rule set and continues generating a recommendation instead of failing. The backtesting module also returns safe neutral metrics when no valid price or signal data is present, preventing crashes during degraded market or data conditions.

---

## ✨ Key Features

- **📊 Advanced Market Analytics**: Real-time momentum tracking and volatility analysis.
- **🤖 AI Strategy Advisor**: A specialized LLM-powered chat interface contextualized with your portfolio data.
- **📈 ML-Powered Forecasting**: LSTM-based price predictions for major tech stocks and indices.
- **🌐 Regime Detection**: Hidden Markov Models (HMM) to identify market phases (Bull, Bear, Volatile).
- **💼 Portfolio Builder**: Quantitative asset allocation tools with risk-reward profiling.
- **⚡ Trading Execution Simulator**: Test strategies in a sandbox environment before going live.

---

## 📂 Repository Structure

```text
smart-portfolio-advisor/
├── frontend/             # React SPA (Vite, Tailwind, Shadcn/UI inspired)
├── analytics-engine/     # Python Microservice (ML Models, Decision Engine)
│   ├── models/           # Pre-trained ML artifacts (LSTM, HMM, RF)
│   ├── services/         # Core logic (Data Fetchers, Forecasting)
│   └── trading_engine/   # RL Agent and Simulation logic
└── scripts/              # Utility scripts for training and verification
```

---

## 🚀 Getting Started

### Prerequisites
- Node.js (v16+)
- Python 3.9+
- Git

### 1. Analytics Engine Setup
```bash
cd analytics-engine
python -m venv venv
source venv/bin/activate  # venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn api:app --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

### 🏎️ Quick Run (Windows)
For convenience, use the included batch scripts to launch both services:
```bash
run_all.bat
```

---

## 🛠️ Roadmap
- [ ] Integration with live broker APIs (Interactive Brokers, Alpaca)
- [ ] Multi-asset support (Crypto, Commodities, Forex)
- [ ] Advanced Backtesting suite with slippage and commission models
- [ ] Real-time push notifications for signal alerts

---
*Disclaimer: This tool is for educational and research purposes only. Always perform your own due diligence before trading.*

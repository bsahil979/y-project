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
| **Frontend** | React 19, Tailwind CSS, Recharts | Dynamic Dashboard, Real-time Visualizations, AI Advisor Chat |
| **Analytics Engine** | Python 3.10, FastAPI, PyTorch | Market Regime Detection, LSTM Forecasting, Signal Classification |
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

Use 64-bit Python 3.10, Node.js 24 LTS with npm, and Git. The root `requirements.txt` installs the Python backend. The frontend uses `frontend/package-lock.json`.

### Windows setup

Run these commands in PowerShell from the cloned repository:

```powershell
py -3.10 -m venv analytics-engine/venv
.\analytics-engine\venv\Scripts\python.exe -m pip install --upgrade pip
.\analytics-engine\venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd --prefix frontend ci --legacy-peer-deps
.\run_all.bat
```

### macOS or Linux setup

Run these commands from the repository root:

```bash
python3.10 -m venv analytics-engine/venv
analytics-engine/venv/bin/python -m pip install --upgrade pip
analytics-engine/venv/bin/python -m pip install -r requirements.txt
npm --prefix frontend ci --legacy-peer-deps
(cd analytics-engine && venv/bin/python -m uvicorn api:app --host 127.0.0.1 --port 8000)
```

In a second terminal at the repository root, run `npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173 --strictPort`.

Open [SmartPortfolio](http://localhost:5173) and choose **Try Demo** for local access. Open the [API documentation](http://localhost:8000/docs) to check that the backend is responding.

### Connect optional services

- **Cloud login**. Copy `frontend/.env.example` to `frontend/.env` and enter the Supabase project URL and public anon key for the project that owns the account. For a new project, apply `supabase/portfolio_schema.sql`, enable email authentication, and allow the callback URL `http://localhost:5173/auth`. Restart Vite after editing its environment.
- **LLM chat**. Copy `analytics-engine/.env.example` to `analytics-engine/.env`, configure a provider using the example, and restart the API.
- **Market data and model weights**. Live quotes require internet access. TimesFM downloads its checkpoint on first use. To reproduce predictions from trained model artifacts stored outside Git, copy those trusted artifacts into the corresponding paths under `analytics-engine/models/`. For optional semantic retrieval, use the backend environment to cache the embedding model with `python -c "from huggingface_hub import snapshot_download; snapshot_download('sentence-transformers/all-MiniLM-L6-v2')"`. The advisor uses TF-IDF when embeddings are unavailable.

---

## 🛠️ Roadmap
- [ ] Integration with live broker APIs (Interactive Brokers, Alpaca)
- [ ] Multi-asset support (Crypto, Commodities, Forex)
- [ ] Advanced Backtesting suite with slippage and commission models
- [ ] Real-time push notifications for signal alerts

---
*Disclaimer: This tool is for educational and research purposes only. Always perform your own due diligence before trading.*

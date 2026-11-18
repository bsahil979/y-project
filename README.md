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
- **Cloud portfolio isolation**. After the base schema, apply `supabase/portfolio_relationship_isolation.sql` to require holdings and transactions to link to portfolios and brokerage accounts owned by the same user. See the [two-account staging check](supabase/CLOUD_LOGIN_CHECKPOINT.md#two-account-staging-check) before public rollout.
- **LLM chat**. Copy `analytics-engine/.env.example` to `analytics-engine/.env`, configure a provider using the example, and restart the API.
- **Market data and model weights**. Live quotes require internet access. TimesFM downloads its checkpoint on first use. To reproduce predictions from trained model artifacts stored outside Git, copy those trusted artifacts into the corresponding paths under `analytics-engine/models/`. For optional semantic retrieval, use the backend environment to cache the embedding model with `python -c "from huggingface_hub import snapshot_download; snapshot_download('sentence-transformers/all-MiniLM-L6-v2')"`. The advisor uses TF-IDF when embeddings are unavailable.

### Check a production build locally

Run the backend with `uvicorn api:app --host 127.0.0.1 --port 8011` from `analytics-engine` using its virtual environment. In PowerShell, build and serve the frontend from the repository root:

```powershell
$env:VITE_API_URL = 'http://127.0.0.1:8011'
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend run preview -- --host 127.0.0.1 --port 4173 --strictPort
```

Open [the production preview](http://127.0.0.1:4173). Use Try Demo to check local persistence, then use dedicated staging accounts to check cloud persistence and account isolation. Record a sample holding, reload, run Advisor, and check the forecast's model label. Ask the assistant about a figure that can be checked against the Advisor screen. The API liveness endpoint is `/health`.

On a private host, serve `frontend/dist` with an index fallback for React routes. Set `VITE_API_URL` at build time and set backend `CORS_ALLOWED_ORIGINS` to the exact frontend origins. Register hosted Supabase and broker callbacks. Use one backend process while broker connections are stored in memory. Keep the app and API behind staging access controls. CORS controls browser origins only. Public exposure requires authentication and request quotas for expensive API paths, plus separate account isolation checks against the deployed database.

### Track forecasts against future actuals

From `analytics-engine`, run the following with its virtual environment. Keep a new output file for each forecast and record it before the next trading session closes.

```text
python -m evaluations.forecast_tracking record --api http://127.0.0.1:8011 --ticker MSFT --horizon 30 --output msft-forecast-001.json
python -m evaluations.forecast_tracking score --record msft-forecast-001.json --actuals msft-closes.csv
```

Supply `session_date,close_at,close` in the actuals CSV. Include the origin day and every subsequent exchange session through the forecast horizon, using timezone-aware close timestamps and the same provider and adjustment convention captured in the forecast. The score compares price error and terminal direction with a flat last-close baseline. Report model families and fallbacks separately across multiple stocks and forecast dates.

---

## 🛠️ Roadmap
- [ ] Integration with live broker APIs (Interactive Brokers, Alpaca)
- [ ] Multi-asset support (Crypto, Commodities, Forex)
- [ ] Advanced Backtesting suite with slippage and commission models
- [ ] Real-time push notifications for signal alerts

---
*Disclaimer: This tool is for educational and research purposes only. Always perform your own due diligence before trading.*

## Additional asset tracking

Manage holdings supports dated valuations for Indian mutual funds, real estate, private equity, cash, other assets, and liabilities. Apply supabase/multi_asset_schema.sql after the base schema to enable cloud persistence of valuation fields. Local valuations remain available if that migration is missing; the sync status reports failure.

Indian mutual funds use an AMFI scheme code, units and NAV. Fetch latest NAV reads AMFI's published NAV file, with manual dated entry available when the provider is unavailable. Recorded assets contribute to tracked net worth per currency on the holdings page. Liabilities reduce this total.

The mutual fund advisor computes historical NAV returns, volatility, drawdown, correlation and rule-based profile recommendations. AMFI scheme identity and MFapi history were verified with live data during development. These metrics replay current units and are not personal XIRR or forecasts. Stock optimization remains separate; fund target-weight optimization, underlying-stock overlap and transaction-based fund performance are not implemented. Real estate and private equity values are user estimates.

Broker imports support a live Upstox connection and labeled CSV accounts for other brokers. Imported accounts can share a portfolio or use separate portfolios. See [broker setup and coverage](analytics-engine/docs/upstox-import.md). Broker tokens are currently held in server memory and require reconnection after restart; this is not production-ready persistent connection storage.

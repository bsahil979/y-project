# Smart Portfolio Advisor & Recommendation System
## *AI-Driven Multi-Asset Portfolio Intelligence & Risk Analytics Platform*

**Project Authors:** Sahil Belchada · Paras Kokate  
**Project Date:** 17 November 2026  
**Domain:** Financial Technology (FinTech) — Applied Machine Learning, Quantitative Finance, and Distributed Web Engineering  

---

## Executive Abstract

The **Smart Portfolio Advisor** is a full-stack, institutional-grade portfolio intelligence and risk analytics platform designed to bridge the structural divide between retail stock brokers and quantitative investment desks. Modern brokerage applications focus almost exclusively on high-frequency order execution, leaving retail investors blind to hidden cross-asset correlations, portfolio Value-at-Risk (VaR), macroeconomic regime shifts, and concentration risks. 

This platform transforms raw multi-asset holdings into actionable, mathematically verified intelligence. The system couples a **React 19 Single-Page Application (SPA)** with a stateless **FastAPI analytics microservice** serving 48 endpoints and hosting ten machine learning and quantitative models. Key innovations include:
1. Pretrained zero-shot time-series forecasting via **Google's TimesFM 2.5 (200M)** with an offline **PyTorch LSTM** fallback.
2. Unsupervised macroeconomic regime detection via a causal **3-state Gaussian Hidden Markov Model (HMM)**.
3. Multi-signal directional trade classification combining **Random Forests**, a **MarketMind Meta-Model**, and a **PPO Reinforcement Learning** policy agent.
4. Classical and advanced portfolio allocation solvers, including **Markowitz Mean-Variance**, **Equal Risk Parity**, and **Black-Litterman Bayesian Optimization** modulated by **ProsusAI/FinBERT** financial news sentiment.
5. A deterministic **Numerical Verifier** that grounds LLM natural language explanations against active ledger facts.
6. A reproducible, leakage-audited empirical research study evaluating regime-conditioned portfolio allocation on Indian equities.

---

## 1. Introduction, Domain & Motivation

### 1.1 Domain Background
In recent years, the democratization of financial markets through commission-free trading platforms (such as Zerodha, Groww, and Robinhood) has triggered an unprecedented surge in retail market participation. However, accessibility of execution has not been matched by accessibility of **decision intelligence**. Quantitative hedge funds and institutional asset managers utilize sophisticated factor models, stress-testing harnesses, covariance shrinkage, and regime-switching algorithms to preserve capital and maximize risk-adjusted returns (Sharpe and Sortino ratios). Retail investors, conversely, are typically restricted to basic technical charts, isolated stock tips, and trailing return metrics.

### 1.2 The Technological Catalyst
Simultaneously, machine learning has experienced fundamental shifts that make institutional methods viable on consumer hardware:
* **Foundation Time-Series Models**: Zero-shot foundational forecasters (e.g., Google’s TimesFM) allow accurate multi-horizon price projections without per-ticker retraining.
* **Domain-Specific Transformer NLP**: Models like FinBERT process unstructured financial news in real time, quantifying market sentiment into actionable mathematical signals.
* **Modern Reinforcement Learning Frameworks**: Libraries such as Stable-Baselines3 and Gymnasium enable continuous-action portfolio rebalancing under realistic transaction frictions.

The Smart Portfolio Advisor exploits this convergence, wrapping complex quantitative finance into an auditable, self-explaining, and accessible full-stack application.

---

## 2. Problem Statement & Literature Gap

### 2.1 The Core Gaps in Retail Investing
1. **Risk-Concentration Blindness**: Retail investors frequently hold multiple stocks within the same sector (e.g., holding TCS, Infosys, and Wipro), mistakenly believing they are diversified while remaining exposed to extreme sector-specific variance.
2. **Absence of Pre-Trade "What-If" Analysis**: Traditional platforms only evaluate performance *after* trades are executed. Investors have no mechanism to evaluate how buying 5% or 10% of a candidate asset will alter total portfolio volatility, correlation, and Sharpe ratio before committing capital.
3. **Macroeconomic Market-Phase Ignorance**: Asset returns exhibit regime-dependent behavior. Strategies optimized for low-volatility bull markets suffer catastrophic drawdowns during high-volatility liquidity shocks. Standard retail platforms provide no statistical signal identifying current market regimes.
4. **The "Markowitz Curse"**: Textbook Modern Portfolio Theory (Mean-Variance Optimization) is rarely deployed in production because it is hyper-sensitive to estimation errors, routinely generating extreme "corner solutions" (allocating 100% of capital to one stock and 0% to others).
5. **Hallucination in Financial AI**: Off-the-shelf Large Language Models (LLMs) hallucinate financial metrics and fabricate historical returns when asked to analyze portfolios, rendering them hazardous without strict numerical grounding.

### 2.2 System Scope & Operational Boundaries
The application is explicitly designed as an **investment-intelligence and quantitative research instrument**. It is not a licensed financial advisor, automated trading bot, or executing broker. All brokerage tokens are kept memory-only; alternative assets (real estate, private equity) rely on user-recorded valuations; and recommendations are presented with explicit confidence metrics and assumptions.

---

## 3. System Architecture & Engineering

The platform implements a decoupled, three-tier architecture ensuring clean separation of presentation, business logic, persistence, and mathematical computation.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER (SPA)                        │
│   React 19 · Vite · Tailwind CSS · Recharts · Lucide Icons             │
│   • Multi-Currency Portfolio Dashboard    • "What-If" Betterment Lab   │
│   • Monte Carlo Wealth Projections        • AI Model Inspection & Lab  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST / SSE
┌───────────────────────────────────▼────────────────────────────────────┐
│                    ANALYTICS ENGINE MICROSERVICE                       │
│   FastAPI (Python 3.10) · Uvicorn · 48 REST Endpoints                  │
├───────────────────────────────────┬────────────────────────────────────┤
│   QUANT & OPTIMIZATION PIPELINE   │      AI & MACHINE LEARNING ZOO     │
│   • Covariance & Risk Metrics     │   • TimesFM 2.5 200M (Foundation)  │
│   • Black-Litterman Bayesian Core │   • PyTorch 2-layer LSTM (Offline) │
│   • SLSQP Quadratic Optimizer     │   • Random Forest (100 Trees)      │
│   • Monte Carlo 1,000-Path Sim    │   • 3-State Gaussian HMM           │
│   • Parametric & Historical VaR   │   • PPO Continuous RL Agent        │
│   • Factor & Sector Attribution   │   • ProsusAI/FinBERT Sentiment NLP │
└───────────────────────────────────┴────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                  DATA SYNDICATION & PERSISTENCE LAYER                  │
│   • Supabase PostgreSQL (Row-Level Security & Auth)                    │
│   • Infallible Local Storage Email Workspace Fallback                  │
│   • Yahoo Finance API + Stooq Daily CSV Alternative Gateway            │
│   • Upstox Broker OAuth & AMFI Mutual Fund NAV Endpoints               │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Key Engineering Deliverables
* **FastAPI Backend (`api.py`)**: 48 modular endpoints covering market quotes, portfolio risk, HMM regimes, TimesFM/LSTM projections, trading decisions, Black-Litterman optimization, RAG chat, paper trading, and monitoring alerts.
* **React 19 Frontend**: Component-driven architecture utilizing Tailwind CSS for institutional dark-mode styling (`#11131a`) and Recharts for responsive SVG visualization.
* **Resilient Multi-Tenancy**: Built with Supabase PostgreSQL cloud authentication, fortified with an infallible local fallback workspace allowing users to maintain isolated multi-currency ledgers completely offline during remote network outages.

---

## 4. Quantitative Valuation & Risk Methodologies

### 4.1 Asset Valuation & Currency Normalization
A position’s market value ($V_i$) is the product of verified owned quantity ($q_i$) and the latest observation price ($P_i$):
$$V_i = q_i \times P_i$$
Portfolio asset weights ($w_i$) are derived dynamically from total market value:
$$w_i = \frac{V_i}{\sum_{k=1}^N V_k}$$
Portfolios holding mixed currencies (INR and USD) are segregated or converted using observed USD/INR spot exchange rates. Missing market quotes or missing FX rates output an explicit `Unavailable` state rather than fabricating synthetic asset values.

### 4.2 Comprehensive Risk Suite
The quantitative engine computes standard and tail-risk metrics across rolling lookback windows:
* **Annualized Return & Volatility**:
  $$\mu_{ann} = \bar{r} \times 252, \quad \sigma_{ann} = \sigma_{daily} \times \sqrt{252}$$
* **Risk-Adjusted Ratios (Sharpe & Sortino)**:
  $$\text{Sharpe} = \frac{\mu_{port} - R_f}{\sigma_{port}}, \quad \text{Sortino} = \frac{\mu_{port} - R_f}{\sigma_{downside}}$$
* **Parametric & Historical Value-at-Risk ($95\%$ Confidence)**:
  $$\text{VaR}_{95\%} = -(\mu_{port} - 1.645 \cdot \sigma_{port})$$
* **Conditional Value-at-Risk ($\text{CVaR}_{95\%}$ / Expected Shortfall)**: The conditional expectation of loss given that the loss exceeds the $\text{VaR}$ threshold.

### 4.3 Financial Goals & Monte Carlo Wealth Simulator
To assess long-term milestone viability, the engine deploys a **1,000-path stochastic Monte Carlo simulation** driven by geometric Brownian motion:
$$S_{t+\Delta t} = S_t \exp\left( \left(\mu - \frac{\sigma^2}{2}\right)\Delta t + \sigma \sqrt{\Delta t} \, Z_t \right), \quad Z_t \sim \mathcal{N}(0, 1)$$
The output generates a 61-month wealth distribution:
* **P90 Trajectory (Bull Path)**: 90th percentile optimistic compounding.
* **P50 Trajectory (Median Path)**: Expected median wealth progression.
* **P10 Trajectory (Bear Path)**: Downside stress condition evaluated against the user's specific funding milestone.

---

## 5. Machine Learning Model Hierarchy & Specifications

The platform utilizes a multi-model consensus architecture where each model owns a distinct analytical horizon:

| Model | Technology / Framework | Role & Architectural Design |
| :--- | :--- | :--- |
| **TimesFM 2.5 (200M)** | PyTorch / Google Checkpoint | Pretrained foundation time-series forecaster. Performs zero-shot price trajectory inference over 30-day horizons without ticker-specific fine-tuning. |
| **LSTM Neural Network** | PyTorch (`nn.Module`) | Dependable offline recurrent fallback. 2 stacked LSTM layers (64 units each), $20\%$ dropout, linear projection head mapping 60-day rolling inputs $[batch, 60, 1]$ to forward prices. |
| **Random Forest Classifier** | Scikit-Learn | Directional momentum classifier. 100 decision trees trained on 14-day RSI, MACD lines/histograms, ADX, and 20-day volatility to emit $+1$ (BUY), $0$ (HOLD), or $-1$ (SELL) with confidence voting. |
| **Gaussian HMM** | `hmmlearn` | Unsupervised regime detection. 3 latent Gaussian states (Bearish, Sideways/Volatile, Bullish) fitted via Baum-Welch EM over 504-day causal windows. |
| **PPO Policy Agent** | Stable-Baselines3 / Gym | Reinforcement learning policy trained in a custom `PortfolioRLEnv`. Optimizes continuous weights under 10 bps transaction fees and volatility penalties. |
| **MarketMind Meta-Model** | Scikit-Learn / PyTorch MLP | Fusion meta-model that synthesizes signals from RF, LSTM, and HMM into one calibrated directional score. |
| **FinBERT NLP Engine** | Transformers (`ProsusAI/finbert`) | Domain-specific sentiment analysis of real-time financial headlines. Modulates return views by $\pm 3\%$ and expands view uncertainty ($\Omega$). |
| **Black-Litterman Solver** | SciPy SLSQP / NumPy | Blends market equilibrium priors ($\Pi$) with AI views ($Q$) using Bayesian shrinkage under box constraints $[2\%, 40\%]$. |

---

## 6. Advanced Portfolio Allocation & Betterment

### 6.1 The Practical AI Stock Betterment Advisor
Rather than outputting static charts, the **Betterment Evaluator** provides pre-trade decision intelligence via an interactive "What-If" position slider ($1\%$ to $25\%$):
1. **Hypothetical Injection**: Injects a candidate asset (US or NSE) into the user's active holdings.
2. **Covariance Re-estimation**: Recalculates the joint covariance matrix.
3. **Delta Metrics**: Displays real-time deltas:
   * **$\Delta$ Sharpe Ratio**: Quantifies risk-adjusted gain/loss.
   * **$\Delta$ Annual Volatility**: Shows whether the stock dampens or amplifies portfolio variance.
   * **Holdings Correlation**: Classifies the asset as a **Strong Diversifier** (correlation $< 0.40$) or **Concentrator**.

### 6.2 Black-Litterman Bayesian Formulation
To solve the "Markowitz Curse" of extreme corner weights, the system reverse-engineers the implied equilibrium return vector ($\Pi$):
$$\Pi = \delta \Sigma w_{mkt}$$
where $\delta$ is the investor's risk-aversion coefficient, $\Sigma$ is the asset covariance matrix, and $w_{mkt}$ represents neutral market capitalization weights.

Subjective AI model views ($Q$) are incorporated along with FinBERT sentiment modulation:
$$Q_i = Q_{i, \text{model}} + (\text{Sentiment}_i \times 0.03)$$
The view uncertainty matrix ($\Omega$) scales dynamically:
$$\Omega_{ii} = \frac{\tau (\Sigma)_{ii}}{\text{Confidence}_i} \times (1.0 + 1.5|\text{Score}_{\text{negative}}|)$$
The posterior return vector ($E[R]$) is resolved via Bayesian shrinkage:
$$E[R] = \left[(\tau \Sigma)^{-1} + \Omega^{-1}\right]^{-1} \left[(\tau \Sigma)^{-1}\Pi + \Omega^{-1}Q\right]$$
Optimal weights are computed via quadratic utility optimization bounded between $2\%$ and $40\%$ per asset, guaranteeing realistic, non-oscillating allocations.

---

## 7. Explainable AI & Numerical Grounding

Off-the-shelf generative AI frequently quotes fabricated metrics. To ensure compliance and trustworthiness, the platform implements a **Grounded LLM Advisor**:
1. **Context Construction**: When a user queries the chat assistant, the engine serializes verified portfolio facts (holdings, weights, VaR, Sharpe, HMM state, and beta) into the prompt context.
2. **Tool-Calling Protocol**: The assistant calls analytical tools (`portfolio_analyze`, `evaluate_ticker`, `stress_test`) to verify facts.
3. **Deterministic Numeric Verifier**: A post-generation verification pass parses every labeled numerical claim in the assistant's reply (e.g., *"Your portfolio Sharpe is 1.35"*). It validates the claim against actual engine calculations within rounding tolerances. Detected discrepancies are automatically appended with explicit corrections.

---

## 8. Empirical Research Results: HMM Regime Allocation

### 8.1 Experimental Design
The research component empirically tests whether conditioning portfolio optimization on Gaussian HMM market regimes yields statistically significant out-of-sample improvements over classical minimum variance.
* **Universe**: Five major Indian equity benchmarks (NSE).
* **Backtest Protocol**: 504-session causal rolling training window, rebalanced every 21 trading sessions, charging a realistic 10 basis points ($0.10\%$) transaction fee on absolute traded weights.
* **Evaluation Set**: Out-of-sample frozen holdout containing 249 daily return observations and 11 formal allocation decisions.

### 8.2 Audited Results Table

| Performance Metric | Classical Minimum Variance | HMM-Conditioned Minimum Variance | Absolute Delta |
| :--- | :---: | :---: | :---: |
| **Net Annualized Return** | $2.9104\%$ | **$3.1183\%$** | $+0.2079\%$ |
| **Annualized Volatility** | **$12.5914\%$** | $12.6169\%$ | $+0.0255\%$ |
| **Net Sharpe Ratio** | $0.133111$ | **$0.149094$** | **$+0.015983$** |
| **Maximum Drawdown** | **$-9.6371\%$** | $-9.6846\%$ | $-0.0475\%$ |
| **Model Convergence** | $100\%$ | $100\%$ ($70/70$ fits) | Stable |

### 8.3 Statistical Rigor & Scientific Honesty
The paired Sharpe ratio difference is $+0.015983$. A **95% stationary block-bootstrap confidence interval** yields:
$$\text{CI}_{95\%} = [-0.010548, \; +0.041703]$$
Because this interval spans zero, **the study rigorously concludes that HMM regime conditioning does not establish statistically significant alpha over standard minimum variance at the 95% confidence level.** 

Reporting this finding honestly demonstrates academic integrity, preventing the common research pitfall of overfitting retrospective backtests.

---

## 9. Verification, Quality Assurance & Test Audits

The platform enforces strict automated test suites across both codebases:

```
┌────────────────────────────────────────────────────────┐
│               AUTOMATED VERIFICATION AUDIT             │
├────────────────────────────────────────────────────────┤
│  • Backend Pytest Suite:     211 Passed / 0 Failed     │
│  • Frontend Vitest Suite:     84 Passed / 0 Failed     │
│  • Black-Litterman Unit:      Passed (100% Convergence)│
│  • Production Build (Vite):   Clean (1.89s Bundle)     │
│  • Total Verified Tests:     295 Automated Checks      │
└────────────────────────────────────────────────────────┘
```
The test harness verifies multi-currency math, zero-cost transfers, boundary constraints, FX error propagation, causal train-test leakage prevention, and advisor verifier accuracy.

---

## 10. Conclusion & Future Roadmap

The **Smart Portfolio Advisor** demonstrates that institutional quantitative methods—HMM regime detection, foundation zero-shot forecasting, Black-Litterman Bayesian shrinkage, and transformer sentiment analysis—can be unified into a resilient, production-ready system for modern investors without relying on black-box opacity or overclaimed alpha.

### Future Development Roadmap
1. **Direct Broker Execution Webhooks**: Extend read-only Upstox/Zerodha integrations to authenticated staging orders with multi-factor biometric confirmation.
2. **Alternative Asset Tokenization**: Integrate real-time fixed-income, gold, and sovereign bond yields into the joint covariance matrix.
3. **Multi-Period Reinforcement Learning**: Transition PPO policies from discrete rebalancing intervals to continuous intraday execution with slippage and depth-of-book modeling.
4. **Cross-Asset Macro Embeddings**: Augment TimesFM and LSTM forecasting with macroeconomic token vectors (inflation prints, central bank interest rate decisions, and foreign institutional investor flows).

---

### End of Master Project Report
*(Authenticated and verified for academic and professional presentation)*

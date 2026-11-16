# What we are building

We are building an app that helps a person understand their stock portfolio and compare possible allocations.

Example: someone owns five stocks. The app shows where their investment and risk are concentrated, estimates the current market conditions, and calculates alternative percentages for those stocks. It explains how it obtained the numbers.

## Are we building an ML model from scratch?

We train an existing model family, a Gaussian Hidden Markov Model (HMM), on historical data. We use the `hmmlearn` implementation rather than implementing the learning algorithm from scratch or claiming we invented HMMs. Training estimates parameters such as state means, state variances, and transitions from the supplied data.

Our work is the complete system around it: validated data, portfolio calculations, the connection from model probabilities to allocations, explanations, an application interface, and reproducible evaluation.

The HMM is unsupervised: it is not trained using manually supplied buy/sell labels. It discovers three statistical return states. The labels lower/middle/higher refer to their relative fitted mean returns; they are not guaranteed future outcomes.

## What the research paper is about

Working title: **Evaluating Regime-Aware Portfolio Allocation Using Hidden Markov Models**.

Question: does including learned market-state information improve out-of-sample risk-adjusted performance compared with the same allocation method without that information?

The proposed implementation estimates a different covariance matrix for each learned state, blends those matrices using predicted state probabilities, and optimizes portfolio weights. The matched baseline uses an unconditional covariance estimate from the same data with the same investment constraints. Buy-and-hold and equal-weight portfolios supply additional comparisons.

This is an empirical investigation using established techniques. A new algorithm, unique novelty, superior returns, or publication acceptance has not been established. Related-work review is still required before making a novelty claim.

## Current application

1. Record holdings and transactions.
2. View historical risk, concentration, benchmark comparison, and stress scenarios.
3. Open Improvements to compare allocation with and without market-state information.
4. Open Research to see a recorded chronological experiment, actual metrics, equity curves, assumptions, and limitations.

The holdings dashboard uses the latest available quote times quantity to calculate market-value weights. Missing or currency-mismatched prices block analysis for that currency instead of substituting purchase costs. INR and USD holdings are valued and analyzed separately; no combined currency total is invented. The conventional full-history allocation card and the capped rolling-history research comparison use different settings; do not compare their metrics as if they were the same experiment.

Main navigation is Portfolio, My Holdings, Transactions, Research, and Settings. Watchlists, forecasts, sentiment, trading experiments, chat, fundamentals, training, and goals are retained under Experimental tools. Placeholder non-stock assets, simulated progress/score widgets, and the approximate 30-day portfolio-change display were removed from the main flow.

Existing LSTM, Random Forest, PPO, sentiment, and chat modules remain optional. They are not combined into the current research method. Focus on the HMM allocation question before expanding those modules.

## Current evidence

The first development experiment uses five Indian stocks and one random seed. Decisions are fitted to earlier observations and evaluated on later returns, with delayed execution and costs. The initial run did not show a Sharpe-ratio improvement from adding regimes. This is a finding to investigate, not a reason to change evaluation rules until the result becomes positive.

Research-ready evidence still requires a literature review, a frozen final protocol, multiple seeds/periods, sensitivity checks, and appropriate uncertainty analysis. Visual browser testing also remains outstanding.

See `analytics-engine/research/REGIME_STUDY.md` for the exact implemented method and reproduction commands.

See [PROJECT_ROADMAP.md](./PROJECT_ROADMAP.md) for the end to end delivery and research plan.

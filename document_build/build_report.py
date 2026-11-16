from pathlib import Path
import json
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
doc = Document()
s = doc.sections[0]
s.top_margin = s.bottom_margin = Inches(.7)
s.left_margin = s.right_margin = Inches(.8)
s.page_width = Inches(8.27)
s.page_height = Inches(11.69)
for name in ['Normal','Title','Subtitle','Heading 1','Heading 2']:
    st = doc.styles[name]
    st.font.name = 'Calibri'
    st.font.color.rgb = RGBColor(0,0,0)
doc.styles['Normal'].font.size = Pt(10.5)
doc.styles['Normal'].paragraph_format.space_after = Pt(6)
doc.styles['Normal'].paragraph_format.line_spacing = 1.08
doc.styles['Title'].font.size = Pt(25)
doc.styles['Heading 1'].font.size = Pt(16)
doc.styles['Heading 2'].font.size = Pt(12)
for name in ['Heading 1','Heading 2']:
    doc.styles[name].paragraph_format.space_before = Pt(12)
    doc.styles[name].paragraph_format.space_after = Pt(6)
footer = s.footer.paragraphs[0]
footer.alignment = 2
footer.add_run('Page ').font.size = Pt(9)
field = OxmlElement('w:fldSimple'); field.set(qn('w:instr'),'PAGE'); footer._p.append(field)

def p(t): doc.add_paragraph(t)
def h(t): doc.add_heading(t,2)
def page(title): doc.add_heading(title,1)
def bullets(items):
    for t in items: doc.add_paragraph(t,'List Bullet')
def table(headers, rows, widths):
    t=doc.add_table(rows=1, cols=len(headers)); t.autofit=False
    for c,w in zip(t.columns,widths): c.width=Inches(w)
    for i,v in enumerate(headers): t.rows[0].cells[i].text=v
    for row in rows:
        cells=t.add_row().cells
        for i,v in enumerate(row): cells[i].text=str(v)
    for ri,row in enumerate(t.rows):
        for ci,cell in enumerate(row.cells):
            cell.width=Inches(widths[ci]); cell.vertical_alignment=1
            pr=cell._tc.get_or_add_tcPr()
            borders=OxmlElement('w:tcBorders')
            for edge in ['top','left','bottom','right']:
                e=OxmlElement('w:'+edge);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');borders.append(e)
            pr.append(borders)
            sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'E8EDF2' if ri==0 else 'FFFFFF');pr.append(sh)
            margin=OxmlElement('w:tcMar')
            for edge in ['top','left','bottom','right']:
                e=OxmlElement('w:'+edge);e.set(qn('w:w'),'85');e.set(qn('w:type'),'dxa');margin.append(e)
            pr.append(margin)
            for pp in cell.paragraphs:
                pp.paragraph_format.space_after=Pt(3)
                if ri == 0: pp.paragraph_format.keep_with_next = True
                for run in pp.runs: run.font.size=Pt(9.5);run.bold=ri==0
        cant=OxmlElement('w:cantSplit');row._tr.get_or_add_trPr().append(cant)
    repeat=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(repeat)
    doc.add_paragraph().paragraph_format.space_after=Pt(0)

doc.add_paragraph('AI Portfolio Advisor', 'Title')
doc.add_paragraph('Technical implementation and model evaluation', 'Subtitle')
p('Final year project technical inventory | 16 November 2026')
p('The project is an AI-assisted portfolio analysis and advisory application. It manages holdings, calculates financial risk and performance, compares allocations, runs predictive and sentiment models, and uses an AI chat interface to explain the results.')
p('The eight integration phases are implemented: profile and horizon constraints, AI Black-Litterman views, causal regime features, forecast provenance, RF quarantine, FX normalization, asset-sensitive stress tests and verified advisor explanations. The research dashboard separates implemented behavior from measured evidence. The HMM comparison is evaluated on unseen dates with costs; personalized and AI allocation methods now have a separate causal walk-forward replay on the same 2025 window. This retrospective evidence does not establish general investment superiority.')
h('1 System architecture')
table(['Layer','Technology','Responsibility'],[
['Frontend','React 19, Vite 8, Tailwind 4, React Router 7, Recharts 3','Portfolio screens, charts, navigation and chat'],
['Analytics API','Python, FastAPI, Uvicorn','Market data, financial engines, models and recommendations'],
['Persistence','Supabase Auth and PostgreSQL; browser storage','Sessions, portfolios, holdings, transactions and goals'],
['Model libraries','PyTorch, scikit-learn, hmmlearn, Stable-Baselines3, Transformers','Forecasting, classification, regimes, RL and sentiment']],[1.05,2.4,3.22])
p('Request flow: React interface → FastAPI → market data and portfolio calculations → optional models → allocation and recommendation logic → structured advisor context → LLM explanation → interface.')
p('The standard launch scripts start the frontend on port 5173 and the analytics API on port 8000. The backend entry point is analytics-engine/api.py. Frontend package declarations supersede older documentation that mentions React 18.')
h('2 Main project areas')
bullets(['frontend/src: screens, authentication context, portfolio snapshot and API clients.', 'analytics-engine/services: financial calculations, data acquisition, optimization and recommendations.', 'analytics-engine/trading_engine and training: model definitions, inference, environments and training scripts.', 'analytics-engine/research, evaluations and models: experiments, reports, weights and metadata.', 'supabase/portfolio_schema.sql: database schema and user ownership policies.'])

page('Portfolio data and financial analytics')
h('3 User accounts and portfolio records')
p('The application implements authentication, protected dashboard routes, multiple portfolios, portfolio selection, accounts, holdings, transactions, watchlists and financial goals. Holdings store ticker, quantity, average cost and currency. Transaction types include buys, sells, dividends, fees and transfers.')
p('Supabase tables are portfolios, accounts, holdings, transactions, financial_goals and watchlists. The migration defines row-level security using the authenticated user ID. Workspace data is cached locally and synchronized with Supabase. The schema files do not by themselves prove that every migration is applied to the live database.')
h('4 Valuation and currency handling')
p('Position value equals quantity multiplied by the current quote. Current portfolio weights are derived from those market values. A shared portfolio snapshot helps the dashboard and advisor consume the same holdings and prices.')
p('The pipeline normalizes mixed INR and USD holdings into a chosen base_currency before valuation, return estimation, covariance and optimization. Mixed portfolios default to INR; single-currency portfolios retain their currency. USD prices are multiplied by aligned USDINR=X quotes for INR valuation; INR prices are divided for USD valuation. Native position values use the latest aligned FX date. Exact observed dates are intersected without synthetic or backfilled rates. Missing FX raises an explicit error. Output records base_currency, fx_conversion_applied, fx_pair_used, valuation date and original_currency per holding.')
p('Historical portfolio performance uses current weights applied to historical asset returns. It is a historical simulation of the current allocation, not a reconstruction of the user’s actual transaction history.')
h('5 Market data engine')
p('Yahoo Finance through yfinance supplies adjusted closing-price history and quote information. Stooq is a fallback, with its adjustment convention marked unverified. Requests are cached for roughly 60 seconds. The engine preserves ticker order, aligns common dates, drops incomplete rows and records provenance and coverage. It raises an error when usable data cannot be obtained rather than generating simulated market prices.')
h('6 Central orchestration')
p('run_portfolio_pipeline coordinates validation, market data, portfolio returns, risk, HMM regimes, stress scenarios, benchmark comparison, attribution, risk budgets, optional sentiment and MarketMind predictions, allocation comparisons, scoring and recommendations. Responses include an analysis ID, portfolio revision, timestamps, methodology and stage statuses.')
h('7 Financial calculation conventions')
p('The shared financial_metrics module uses simple daily returns, geometric compounding, 252 trading sessions per year, sample standard deviation and a default annual risk-free rate of 2 percent.')
bullets(['Daily asset return: current close divided by previous close, minus one.', 'Portfolio daily return: sum of each asset return multiplied by its portfolio weight.', 'Cumulative return: product of one plus each daily return, minus one.', 'Annualized volatility: sample daily standard deviation multiplied by the square root of 252.', 'Sharpe ratio: mean daily excess return divided by its standard deviation, annualized by the square root of 252.'])

page('Risk allocation and portfolio decisions')
h('8 Risk benchmark and attribution outputs')
table(['Output','Purpose'],[
['CAGR and cumulative return','Describe compounded historical growth'],['Volatility Sharpe and Sortino','Measure variability and risk-adjusted performance'],['Maximum drawdown','Measure the largest peak-to-trough decline'],['VaR and CVaR','Describe loss thresholds and average tail losses'],['Beta and Jensen alpha','Compare sensitivity and performance with a benchmark'],['Correlation and risk contributions','Identify dependence and sources of portfolio risk'],['Return attribution and concentration','Explain holding contributions and allocation concentration']],[2.35,4.32])
p('These outputs are statistical calculations. They are distinct from prediction accuracy and do not require training a neural network.')
h('9 Portfolio optimization')
p('PortfolioOptimizer uses SciPy SLSQP constrained optimization. Implemented methods include minimum volatility, maximum Sharpe, risk parity, target-return optimization, Black–Litterman and an efficient frontier. Black–Litterman combines equilibrium return assumptions with supplied views.')
p('The pipeline returns conventional minimum-volatility, HMM-conditioned, personalized and AI Black-Litterman allocation comparisons. Current estimates use the supplied historical window and are labeled in-sample. Constraints are enforced during optimization; infeasible portfolios return a reason without fabricated weights. PPO remains experimental_disabled.')
p('AI views use Q = pi + 0.50 * annual volatility * signal. With both sources, signal = 0.65 * (P_buy - P_sell) + 0.35 * FinBERT; one source uses its own signal. Missing news remains None and VADER fallback is excluded. No sources means no tilt. The prior uses equal-weight equilibrium returns, not market capitalizations. Diagonal uncertainty rises with missing coverage or disagreement. Per-ticker provenance records net probabilities, sentiment, composite signal, Q, policy confidence and prior fallback.')
h('10 Recommendations and what if analysis')
p('Recommendations reference profile-specific concentration and rebalancing thresholds, horizon metadata and personalized target weights. Explanations can cite aligned MarketMind and FinBERT signals driving AI Black-Litterman tilts. Rules interpret calculated evidence rather than calibrated future success probabilities.')
p('The /ticker/evaluate endpoint compares existing weights with a proposed allocation to a stock. It checks recent history, common dates and matching currency, then compares historical return, volatility, Sharpe and correlation. The verdict describes a historical scenario, not an established future benefit.')
p('A separate portfolio health score ranges from 0 to 1000. Its components are downside protection, risk-adjusted return, allocation quality and resilience. It is a designed scoring formula rather than a calibrated learned probability.')
h('11 Personalization status')
p('Onboarding and Settings preferences now reach analysis and optimization. Conservative profiles minimize volatility, cap weights at 20 percent and penalize high beta; for fewer than five assets the cap is min(1, max(0.25, 1.2/n)). Moderate profiles maximize Sharpe with a 30 percent cap. Aggressive profiles use AI Black-Litterman with a 40 percent cap in the pipeline; standalone optimization without views uses a historical 75th-percentile target return. Horizon <=2 years reduces caps by five percentage points subject to the 1/n feasibility floor, multiplies conservative beta and volatility penalties by 1.25, and steps aggressive objectives down to maximum Sharpe. Horizons >2 and <7 retain baseline constraints; >=7 permits full profile growth behavior. Horizon source is explicit, nearest_goal or default. Metadata records the applied and effective profiles, objective, cap and modifier.')

page('Market regime and stock signal models')
h('12 Gaussian Hidden Markov Model')
p('A shared hmmlearn Gaussian HMM engine fits StandardScaler only on the causal training window. It uses three states, up to 500 iterations, tol=1e-4 and min_covar=1e-3. Non-converged full covariance fits and high-dimensional windows fall back to diagonal covariance with deterministic seed 42. Convergence checks inspect likelihood change rather than treating the iteration cap as success. Canonical ordering sorts by realized volatility with mean-return tie breaking: 0 low-volatility/bullish, 1 transition, 2 stress. Metadata exposes convergence, iteration count, covariance type and posterior state probabilities. Labels describe fitted history and do not guarantee market direction.')
p('The frozen portfolio research method uses three states and up to 504 prior daily return observations. It estimates state-conditioned covariance matrices, shrinks them 50 percent toward unconditional covariance, propagates state probabilities two transitions and solves a minimum-variance allocation.')
p('The research settings require non-negative weights totaling 100 percent, a 40 percent per-stock cap and rebalancing every 21 sessions. Decisions use earlier data, execution is delayed, and the backtest charges turnover costs. Comparisons include buy and hold, equal weight, conventional minimum variance and HMM-conditioned minimum variance.')
h('13 Per ticker Random Forest')
p('The older trading classifier uses scikit-learn RandomForestClassifier with a default 100 trees. Inputs are RSI, MACD, MACD signal, ADX, returns and volatility. The default target is the next five-bar return: BUY above +0.5 percent, SELL below −0.5 percent, otherwise HOLD. Model and scaler artifacts are stored separately.')
h('14 MarketMind classifier A')
p('MarketMind is a separate pooled stock classifier. Its 14 features are returns, RSI, MACD, MACD signal, MACD difference, ADX, volatility, EMA 50, EMA 200, trend strength, five-day momentum, ten-day momentum, sentiment score and regime code.')
p('Its dataset builder defaults to a five-day target with BUY and SELL thresholds of +1 and −1 percent. Training compares a 250-tree Random Forest with balanced class weights against HistGradientBoostingClassifier. The currently saved meta_model_metrics.json identifies Random Forest as the selected model. Candidate selection uses macro F1 on its selection block; this block must not be confused with an untouched final test.')
p('MarketMind now uses the shared causal HMM feature helper: at least 126 observations, a 504-observation lookback, refits every 21 sessions and forward filtering between refits. Warmup is neutral with unavailable posterior probabilities. The existing 14-column model shape is preserved; legacy saved encodings are mapped compatibly. New canonical codes are 0, 1 and 2. Archived Phase 2E scores predate this integration and do not validate the changed feature semantics; the Phase 8 allocation replay now independently retrains this architecture on five stocks with matured labels. A fresh pooled-classifier accuracy audit remains a separate task.')
h('15 MarketMind classifier B')
p('The experimental PyTorch network processes numeric features through layers of 128 and 64 units. It adds learned ticker, market and sector embeddings of dimensions 16, 4 and 8. A fusion network with 128 and 64 units produces three class logits. Training uses cross-entropy loss; inference converts logits into probabilities.')
p('These classifiers and the HMM are distinct components. Their existence does not establish that the complete application uses one jointly trained ensemble.')

page('Forecasting sentiment and reinforcement learning')
h('16 LSTM forecasting variants')
table(['Variant','Architecture and purpose'],[
['Per ticker trading LSTM','PyTorch; two layers; 64 hidden units; dropout 0.2; 60-observation windows; saved weights and scaler'],['Service fallback LSTM','Two layers; 50 hidden units; 60-observation windows; used by the forecast service when needed'],['Validated direct return LSTM','One 32-unit layer; 60 inputs; direct 30-step output; chronological train validation test splits'],['Universal fallback models','RF HMM and return-based LSTM trained on pooled ticker data; shared inference when per-ticker artifacts are unavailable']],[2.0,4.67])
p('The validated forecast code removes labels crossing split boundaries and compares with a last-close baseline. The saved MSFT experiment selected the baseline because the LSTM did not improve validation error. This result does not validate other LSTM variants.')
h('17 TimesFM forecasting')
p('The main service first attempts Google TimesFM 2.5 using the pretrained google/timesfm-2.5-200m-pytorch checkpoint. It supplies up to 512 historical log returns, forecasts 1 to 60 sessions and reconstructs a price path from those predicted returns.')
p('get_price_forecast is the primary API; get_lstm_forecast is only a deprecated compatibility wrapper. Responses expose model_family, is_pretrained_foundation_model, fallback_triggered, fallback_reason and validation_status. The chain is TimesFM-2.5, saved validated direct-return LSTM or its selected baseline, service LSTM, then last-close baseline. Verified chronological saved evaluations can receive out_of_sample_verified; unverified paths receive unverified_fallback. TimesFM pretraining exclusion is unverified. The four former internal wrapper calls now use the primary interface; one dedicated test checks the deprecation warning.')
h('18 Financial news sentiment')
p('The service collects Yahoo Finance and Google News headlines, deduplicates them, attempts ProsusAI/finbert classification and falls back to VADER. It returns article-level sentiment, aggregate positive negative and neutral counts, source information and the model used.')
p('FinBERT is pretrained. The inspected implementation does not demonstrate project-specific FinBERT fine-tuning. Missing news is reported as unavailable; a zero score alone should not be interpreted as observed neutral news.')
h('19 PPO experiments')
p('Stable-Baselines3 PPO and Gymnasium environments implement experimental trading and allocation policies. The multi-asset environment produces weights over stocks and cash using softmax-normalized actions. Inputs include momentum, volatility, signals, current weights, drawdowns and portfolio-level state information.')
p('The PPO reward combines return, drawdown and volatility penalties, a Sharpe bonus and turnover costs. HMM features now use causal expanding-window estimation and forward filtering; no full-series fit or backward fill is used. Warmup states have zero one-hot vectors. Environment and training metadata record causal_preprocessing=true. This correction does not retroactively validate saved PPO policies. PPO remains experimental_disabled in the production allocation pipeline.')

page('AI explanations planning and application access')
h('20 AI chat advisor')
p('The advisor receives a question and portfolio context, gathers relevant analytics, retrieves supporting news and financial concepts, constructs an LLM prompt and returns or streams an explanation. The LLM is an explanation and orchestration component, not a portfolio model trained by this project.')
p('Retrieval combines local MiniLM dense semantic cosine similarity (60 percent) with TF-IDF cosine similarity (40 percent). TF-IDF retains unigrams, bigrams and up to 5000 features. Locally cached sentence-transformers or mean-pooled transformer weights are supported without model downloads. Missing weights or embedding errors fall back to TF-IDF. Request-local metadata identifies hybrid_semantic_tfidf or tfidf_fallback.')
p('The canonical_facts contract comes directly from the latest portfolio pipeline: risk metrics, health score, base currency, current and target weights and HMM regime. A protected <verified_portfolio_facts> JSON prompt block prohibits invented figures and mental arithmetic. Deterministic verification compares labeled numbers using tolerances of 0.02 for ratios, 0.5 percentage points for percentage claims and 1 point for health score. grounding_check records checked claims and mismatches; deterministic corrections accompany mismatched values. API and final streaming metadata include advisor_provenance, with a UI verification badge. Streaming is buffered until verification. Unlabeled prose and all reasoning are not proven correct by this checker.')
h('21 Goal and stress engines')
p('Goal analysis uses historical return and covariance estimates with correlated random sampling. Its default 1000 Monte Carlo paths include monthly contributions and produce target-success estimates, shortfall measures and percentile trajectories. These are assumption-dependent simulation outputs.')
p("Stress testing replays each holding's exact endpoint return when both crisis dates are observed, including COVID (2020-02-19 to 2020-03-23) and the 2022 drawdown (2022-01-03 to 2022-06-16). Otherwise, shock = clamp(beta * benchmark shock - 0.5 * annualized residual volatility, -0.95, 0.20). Beta and residual volatility use empirical benchmark or portfolio returns. Per-holding metadata identifies realized_historical_replay or beta_idiosyncratic_factor, beta_used and benchmark_shock. Outputs retain chart keys and add contribution, portfolio loss and required recovery gain, not a promised recovery date.")
h('22 Additional services')
bullets(['Paper trading: virtual accounts, orders, balances, performance tracking and journal structures.', 'Monitoring: alert rules, monitoring cycles, active alerts and acknowledgement endpoints.', 'Model operations: universe listing, metadata, status, prediction and training-job endpoints.', 'Advanced analysis: efficient frontier, Black–Litterman and additional portfolio tools.'])
p('The presence of these modules and endpoints does not establish that every service runs continuously or is fully exposed in the main interface.')
h('23 Current interface and API access')
p('Current routes include dashboard, holdings, transactions, goals, portfolio management, fundamentals, forecasts, sentiment, trading, settings and advisor chat. The sidebar now exposes Model Audit and Scientific Benchmarks at /dashboard/research; /research redirects there. The read-only /research/evaluation-summary API serves saved evidence, artifact hashes, source freshness and implementation caveats. Model Training remains redirected; this page does not trigger training.')
p('Key endpoint groups include /quotes, /portfolio/analyze, /portfolio/history, /portfolio/optimize, /portfolio/benchmark, /portfolio/attribution, /portfolio/risk-budget, /portfolio/goal, /forecast/{ticker}, /sentiment/{ticker}, /marketmind/{ticker}, /ticker/evaluate and /chat. Tool and experimental endpoints support the additional services.')

page('Evaluation evidence and validation limits')
h('24 Saved model evaluation results')
table(['Experiment','Saved result','Interpretation'],[
['MarketMind Phase 2E','42568 holdout predictions; A accuracy 38.07%; B 38.47%','Both are below the 39.27% majority-class accuracy baseline'],['MarketMind macro F1','A 0.307; B 0.291','Class-level performance remains limited'],['MSFT direct return LSTM','Test MAE 5.728 versus baseline 5.573','LSTM loses; error units are cumulative log-return percentage points'],['TimesFM historical replay','24 origins; normalized error 5.280% versus baseline 5.146%','No overall advantage in this small two-symbol replay'],['HMM allocation study','Sharpe difference +0.0160; 95% interval -0.0105 to +0.0417','Interval includes zero; improvement is uncertain']],[1.5,2.55,2.62])
p('The regenerated HMM holdout contains 249 daily returns in 2025 for five selected Indian stocks. HMM net Sharpe is 0.1490939567 versus 0.1331110405 for minimum variance. The difference is 0.0159829162, with paired 21-session moving-block bootstrap 95 percent interval [-0.0105479573, 0.0417026550] from 10000 replicates. All 70 primary fits converged. Annual traded notional is 78.3410 percent versus 55.5373 percent; cumulative cost fractions are 0.077408 percent versus 0.054876 percent at 10 bps per absolute traded weight. The interval includes zero. These results evaluate HMM minimum variance, not personalized or AI Black-Litterman allocations.')
p('The TimesFM replay uses MSFT and RELIANCE.NS with a 30-session horizon. Its pretraining cutoff is unverified, so the replay is not established as an untouched model holdout. Its windows overlap and its universe is small.')
h('Personalized and AI allocation holdout replay')
study = json.loads((ROOT/'analytics-engine/research/personalized_phase8_2026-11-16/summary.json').read_text(encoding='utf-8'))
p(study['scope'])
p('The protocol was recorded before outcomes were inspected. All six strategies share 249 return dates in 2025, 504-session estimation windows, a 21-session rebalance schedule and 10 basis points per absolute traded weight. Decisions occur at close t, execution at t+1 and the first earned return at t+2. Pre-holdout positions are simulated to preserve boundary drift; no final liquidation is charged. The annual risk-free rate is 2 percent. The fixed investment horizon is ten years.')
p(study['model'])
p('Each training label matures no later than the decision date. Close-derived features are recomputed using trailing calculations and the shared causal HMM helper. ADX comes from the hashed historical trailing-feature snapshot. Stored future returns, targets, regime codes and sentiments are not used as inputs. Production saved models are not overwritten. Inputs are retrospectively adjusted and not vintage-certified; this limits strict point-in-time data claims.')
p('Historical sentiment coverage is unavailable_in_historical_replay. The classifier uses its missing-sentiment feature convention of zero; the Black-Litterman FinBERT score is None, not observed neutral. Only causal MarketMind probabilities tilt the views. The combined MarketMind plus FinBERT variant is not evaluated here.')
labels = {'Aggressive AI Black-Litterman': 'Aggressive AI BL', 'Aggressive target return': 'Aggressive target return'}
def label(name): return labels.get(name, name)
def pct(value): return f'{(0 if abs(value) < 1e-12 else 100*value):.6f}%'
table(['Strategy','Net annual return','Annual volatility','Net Sharpe','Max drawdown'], [[label(r['strategy']), pct(r['annualized_return']), pct(r['annualized_volatility']), f"{r['sharpe']:.6f}", pct(r['max_drawdown'])] for r in study['metrics']], [1.65,1.3,1.3,1.0,1.42])
p('Aggressive AI BL is the aggressive production-personalized path. Aggressive target return is the standalone historical-return ablation without AI views, not the live aggressive objective when views are supplied.')
table(['Strategy','Mean rebalance turnover','Annual traded notional','Cumulative cost fraction'], [[label(r['strategy']),pct(r['average_turnover']),pct(r['annualized_traded_notional']),pct(r['cumulative_cost_fraction'])] for r in study['metrics']], [1.85,1.6,1.6,1.62])
p(study['turnover_definition'])
h('Paired uncertainty and realized risk comparisons')
p('The tables report paired non-circular 21-session moving-block bootstrap 95 percent intervals using 10000 replicates and seed 20260927. These exploratory intervals are not adjusted for multiple comparisons. Values are rounded to six decimals; the JSON artifacts retain full precision.')
table(['Strategy','Baseline','Net Sharpe difference','95 percent interval'], [[label(r['strategy']),r['baseline'],f"{r['point_estimate']:.6f}", f"[{r['lower']:.6f}, {r['upper']:.6f}]"] for r in study['sharpe_intervals']], [1.65,1.35,1.3,2.37])
p('Conservative caps force five weights of exactly 20 percent, so its realized path equals the equal-weight baseline. A lower volatility or shallower drawdown versus equal weight cannot be demonstrated in this universe. A cap is a concentration constraint, not a guarantee of lower realized risk.')
for r in study['risk_comparisons']:
    direction = 'supports lower risk' if r['interval_supports_reduction'] else 'does not establish lower risk'
    p(f"{r['comparison']}, {r['metric']}: difference {pct(r['difference'])}; 95 percent interval [{pct(r['lower'])}, {pct(r['upper'])}]. The interval {direction} in this replay.")
p(study['risk_interpretation'])
p('Risk differences and their intervals above are percentage-point differences, not relative percentage changes. Tiny floating-point differences from the equal-weight path are economically zero.')
h('25 Evaluation artifacts and limitations')
p('Saved reports cover classification, calibration, trading, attribution, stress, forecasting and the HMM study. The classifier report includes balanced accuracy, class-level precision recall and F1, and confusion matrices. Separate training-selection scores must not be mixed with Phase 2E holdout scores.')
p('Exactly 100 legacy per-ticker RF evaluation records are quarantined with evaluation_status=invalidated_in_sample_overlap. Original scores are retained under quarantined_metrics for audit. Inference suppresses invalid accuracy-based confidence; downstream decisions handle unavailable confidence. This prevents leaked 100 percent training-overlap scores from appearing as live calibrated confidence. Other rule-based confidence coefficients are also not calibrated success probabilities.')
h('26 Technical completion status')
p('Implemented foundations include portfolio records, shared valuation, financial calculations, constrained allocation, model inference, structured recommendations, advisor chat and reproducible research artifacts. Models, deterministic financial calculations, rule-based decisions and LLM explanations have different roles and require different evaluation methods.')
p('All eight code phases are integrated. Preferences become explicit constraints; allocations and forecasts expose provenance and fallback behavior; FX and stress calculations use observed data; explanations receive deterministic numerical checks; and saved evaluation evidence is visible in the interface. The regenerated HMM method and the separate personalized/AI replay have chronological cost-aware evidence. The latter retrains the MarketMind RF architecture with causal HMM features at each decision, on five stocks only. It does not replace the archived pooled-classifier accuracy audit or validate every live model and horizon. No overall predictive or investment advantage is established.')

page('Source files and reproducibility')
p('Paths below are relative to the smart-portfolio-advisor project directory. They identify the main implementation and evidence supporting this inventory.')
table(['Area','Principal files'],[
['Application','frontend/src/App.jsx; frontend/src/pages/DashboardLayout.jsx; frontend/package.json'],['Persistence','frontend/src/services/portfolioData.js; supabase/portfolio_schema.sql'],['API and orchestration','analytics-engine/api.py; services/portfolio_pipeline.py'],['Data and calculations','services/data_fetcher.py; services/financial_metrics.py; services/risk_metrics.py; services/risk_budget.py'],['Allocation','services/portfolio_optimizer.py; services/regime_allocation.py'],['Forecasts','services/forecaster.py; services/saved_forecast.py; services/validated_forecast.py'],['Stock models','trading_engine/models_layer.py; trading_engine/meta_model.py; trading_engine/universal_models.py; training/marketmind_pytorch.py'],['Sentiment and advisor','services/sentiment_analyzer.py; services/historical_sentiment.py; agents/ai_advisor.py'],['Recommendations and planning','services/recommendation_engine.py; services/portfolio_score.py; services/goal_analyzer.py; services/stress_tester.py'],['RL and additional services','trading_engine/portfolio_rl_env.py; training/train_portfolio_rl.py; services/paper_trading.py; services/monitoring_alerts.py']],[1.65,5.02])
p('In the table, paths beginning with services, trading_engine, training or agents are inside analytics-engine.')
h('Primary evaluation records')
bullets(['MODEL_EVALUATION_AUDIT_2026-11-04.md', 'analytics-engine/research/PROTOCOL_V1.md and REGIME_STUDY.md', 'analytics-engine/models/phase_2e/phase_2e_classification_report.json', 'analytics-engine/models/phase_2e/phase_2e_prediction_manifest.json', 'analytics-engine/models/forecast_v2/MSFT/report.json', 'analytics-engine/evaluations/timesfm_replay_2026-11-04.json', 'analytics-engine/models/meta_model/meta_model_metrics.json', 'analytics-engine/research/regime_phase4_2026-11-15/manifest.json and report.md', 'analytics-engine/services/evaluation_summary.py', 'analytics-engine/research/PHASE8_PROTOCOL.md', 'analytics-engine/research/personalized_phase8_2026-11-16/summary.json and manifest.json'])
p('Pytest configuration at the project root and analytics-engine collects the complete maintained tests directory. The three obsolete live-data scripts are documented in analytics-engine/DIAGNOSTICS.md and isolated from collection; no maintained tests are excluded.')
p('Final validation passed 172 backend tests from repository-root discovery and 67 frontend tests, with no errors or failures. The production build passed with the existing bundle-size advisory. Regression coverage includes profile/horizon constraints, AI views, HMM causality, forecast provenance, RF quarantine, FX failures, stress sensitivity, advisor verification and artifact delivery.')
out=ROOT/'AI_Portfolio_Advisor_Technical_Report.docx'
doc.core_properties.title='AI Portfolio Advisor Technical Implementation and Model Evaluation'
doc.core_properties.subject='Final year project implementation inventory'
for element in [doc.styles.element, doc._element]:
    for border in list(element.iter(qn('w:pBdr'))):
        border.getparent().remove(border)
doc.save(out)
print(out)

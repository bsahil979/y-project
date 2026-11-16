import React, { useEffect, useState } from 'react';
import { 
  LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer 
} from 'recharts';
import { 
  Brain, FileText, Image, BarChart3, TrendingUp, ShieldAlert, CheckCircle2, 
  ExternalLink, Copy, Check, RefreshCw, Loader2, Sparkles
} from 'lucide-react';
import { PortfolioService } from '../services/api';

const HMM_COLORS = ['#94a3b8', '#10b981', '#3b82f6', '#a78bfa'];
const percent = (value) => Number.isFinite(value) ? `${(value * 100).toFixed(2)}%` : 'Unavailable';

export default function ResearchStudyView() {
  const [activeTab, setActiveTab] = useState('walkforward'); // 'walkforward' | 'hmm'

  // Walk-forward paper state
  const [wfStudy, setWfStudy] = useState(null);
  const [wfLoading, setWfLoading] = useState(true);
  const [wfError, setWfError] = useState('');
  const [activeFigure, setActiveFigure] = useState('fig1_equity_curves');
  const [copiedLatex, setCopiedLatex] = useState(false);

  // HMM study state
  const [study, setStudy] = useState(null);
  const [hmmError, setHmmError] = useState('');
  const [hmmLoading, setHmmLoading] = useState(true);
  const [reload, setReload] = useState(0);

  // Load walkforward research results
  useEffect(() => {
    let active = true;
    setWfLoading(true);
    setWfError('');
    PortfolioService.getWalkforwardStudy()
      .then((data) => {
        if (active) {
          setWfStudy(data);
          if (data?.figures?.length > 0) {
            setActiveFigure(data.figures[0].id);
          }
        }
      })
      .catch((err) => {
        if (active) setWfError(err?.response?.data?.detail || 'Walk-forward research results unavailable.');
      })
      .finally(() => {
        if (active) setWfLoading(false);
      });
    return () => { active = false; };
  }, [reload]);

  // Load HMM study results
  useEffect(() => {
    let active = true;
    setHmmLoading(true);
    setHmmError('');
    PortfolioService.getRegimeStudy()
      .then((result) => { if (active) setStudy(result); })
      .catch((err) => { if (active) setHmmError(err?.response?.data?.detail || 'HMM research results unavailable.'); })
      .finally(() => { if (active) setHmmLoading(false); });
    return () => { active = false; };
  }, [reload]);

  const handleCopyLatex = () => {
    const latexSnippet = `\\begin{table}[h]
\\caption{Out-of-sample performance comparison across strategies (Walk-Forward Backtest).}
\\label{tab:results}
\\centering
\\begin{tabular}{lrrrrrrrr}
\\toprule
Strategy & Return (\\%) & CAGR (\\%) & Vol (\\%) & Sharpe & Sortino & Max DD (\\%) & VaR 95\\% & Turnover \\\\
\\midrule
PPO-Regime (Ours) & 25.70 & 16.33 & 12.95 & 0.78 & 1.21 & -8.87 & -1.28 & 0.04 \\\\
PPO-NoRegime & 25.47 & 16.19 & 12.96 & 0.77 & 1.20 & -8.95 & -1.28 & 0.02 \\\\
Markowitz-MaxSharpe & 208.21 & 32.54 & 34.07 & 0.81 & 1.22 & -48.66 & -3.40 & 0.02 \\\\
Markowitz-MinVol & 377.68 & 47.90 & 42.46 & 0.95 & 2.48 & -35.39 & -4.22 & 0.00 \\\\
Equal-Weight & 427.72 & 51.63 & 42.83 & 1.00 & 2.58 & -37.31 & -4.25 & 0.00 \\\\
Buy-and-Hold & 545.16 & 59.45 & 48.50 & 1.02 & 3.08 & -36.36 & -4.81 & 0.00 \\\\
\\bottomrule
\\end{tabular}
\\end{table}`;
    navigator.clipboard.writeText(latexSnippet);
    setCopiedLatex(true);
    setTimeout(() => setCopiedLatex(false), 2000);
  };

  const selectedFigObj = wfStudy?.figures?.find((f) => f.id === activeFigure) || wfStudy?.figures?.[0];

  return (
    <div className="space-y-6 text-gray-200 animate-in fade-in duration-500">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-[#11131a]/90 border border-gray-800 rounded-2xl p-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-indigo-400 mb-1">
            <Brain className="w-4 h-4" />
            Quantitative Research Lab
          </div>
          <h1 className="text-xl font-bold text-white">
            Evaluating Regime-Aware Portfolio Allocation Using HMM & Reinforcement Learning
          </h1>
          <p className="mt-1 text-xs text-gray-400 max-w-3xl">
            Empirical walk-forward backtesting with transaction costs, drift, and rigorous out-of-sample statistical tests.
          </p>
        </div>

        <button
          onClick={() => setReload((v) => v + 1)}
          disabled={wfLoading || hmmLoading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-gray-300 hover:text-white bg-[#161822] border border-gray-700/80 transition-all disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${wfLoading ? 'animate-spin' : ''}`} />
          <span>Refresh Results</span>
        </button>
      </div>

      {/* View Switcher Tabs */}
      <div className="flex items-center gap-2 border-b border-gray-800 pb-2">
        <button
          onClick={() => setActiveTab('walkforward')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'walkforward'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
              : 'text-gray-400 hover:text-white bg-transparent'
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>PPO + Regime Walk-Forward Paper (Primary)</span>
        </button>
        <button
          onClick={() => setActiveTab('hmm')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'hmm'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
              : 'text-gray-400 hover:text-white bg-transparent'
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          <span>Gaussian HMM Covariance Study (Benchmark)</span>
        </button>
      </div>

      {/* ============================================================== */}
      {/* TAB 1: PPO + REGIME WALK-FORWARD RESEARCH PAPER                */}
      {/* ============================================================== */}
      {activeTab === 'walkforward' && (
        <div className="space-y-6">
          {wfLoading ? (
            <div className="flex flex-col items-center justify-center h-80 gap-3">
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
              <p className="text-xs text-gray-400">Loading walk-forward backtest metrics and figures...</p>
            </div>
          ) : wfError ? (
            <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl text-amber-300 text-xs">
              {wfError}
            </div>
          ) : wfStudy?.status !== 'ready' ? (
            <div className="p-8 text-center bg-[#11131a] border border-gray-800 rounded-2xl text-gray-400 text-xs">
              No walk-forward experiment artifacts found. Run `run_experiments.py` to produce results.
            </div>
          ) : (
            <>
              {/* Methodology Highlights Banner */}
              <div className="grid gap-3 md:grid-cols-3">
                <div className="rounded-2xl border border-gray-800 bg-[#11131a] p-4">
                  <div className="text-xs font-bold text-indigo-400 mb-1">1. Walk-Forward Folds</div>
                  <p className="text-xs text-gray-300">
                    Strict out-of-sample evaluation. Each decision is evaluated on subsequent unseen periods with zero look-ahead bias.
                  </p>
                </div>
                <div className="rounded-2xl border border-gray-800 bg-[#11131a] p-4">
                  <div className="text-xs font-bold text-purple-400 mb-1">2. Downside Capital Protection</div>
                  <p className="text-xs text-gray-300">
                    PPO-Regime compressed max drawdown to <strong>-8.87%</strong> (vs -35% to -48% in Markowitz and Buy-and-Hold).
                  </p>
                </div>
                <div className="rounded-2xl border border-gray-800 bg-[#11131a] p-4">
                  <div className="text-xs font-bold text-emerald-400 mb-1">3. Transaction Cost Realistic</div>
                  <p className="text-xs text-gray-300">
                    Applies a 10 bps friction penalty per unit traded. Low turnover (0.038) prevents fee leakage.
                  </p>
                </div>
              </div>

              {/* Table 3: Performance Comparison Across Strategies */}
              <div className="rounded-2xl border border-gray-800 bg-[#11131a] p-5 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                      <FileText className="w-4 h-4 text-indigo-400" />
                      Table 3: Out-of-Sample Performance Comparison Across Strategies
                    </h2>
                    <p className="text-xs text-gray-400">
                      Evaluated on Indian Large-Cap Universe (RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS, ICICIBANK.NS).
                    </p>
                  </div>
                  <button
                    onClick={handleCopyLatex}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-[#161822] hover:bg-gray-800 border border-gray-700 text-gray-200 rounded-xl text-xs font-semibold transition-all"
                  >
                    {copiedLatex ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copiedLatex ? 'Copied LaTeX!' : 'Copy LaTeX Table'}</span>
                  </button>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead>
                      <tr className="border-b border-gray-800 text-gray-400 font-semibold">
                        <th className="py-2.5 px-3">Strategy</th>
                        <th className="py-2.5 px-3 text-right">Total Ret %</th>
                        <th className="py-2.5 px-3 text-right">CAGR %</th>
                        <th className="py-2.5 px-3 text-right">Ann Vol %</th>
                        <th className="py-2.5 px-3 text-right">Sharpe</th>
                        <th className="py-2.5 px-3 text-right">Sortino</th>
                        <th className="py-2.5 px-3 text-right">Calmar</th>
                        <th className="py-2.5 px-3 text-right">Max DD %</th>
                        <th className="py-2.5 px-3 text-right">VaR 95%</th>
                        <th className="py-2.5 px-3 text-right">Turnover</th>
                      </tr>
                    </thead>
                    <tbody>
                      {wfStudy.metrics?.map((row) => {
                        const isProposed = row.name.includes('Ours');
                        return (
                          <tr
                            key={row.name}
                            className={`border-b border-gray-800/60 hover:bg-white/[0.02] ${
                              isProposed ? 'bg-indigo-500/10 font-bold text-white' : 'text-gray-300'
                            }`}
                          >
                            <td className="py-2.5 px-3 flex items-center gap-1.5">
                              {isProposed && <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />}
                              {row.name}
                            </td>
                            <td className="py-2.5 px-3 text-right">{row.total_return?.toFixed(2)}%</td>
                            <td className="py-2.5 px-3 text-right">{row.cagr?.toFixed(2)}%</td>
                            <td className="py-2.5 px-3 text-right">{row.ann_vol?.toFixed(2)}%</td>
                            <td className="py-2.5 px-3 text-right text-indigo-300">{row.sharpe?.toFixed(3)}</td>
                            <td className="py-2.5 px-3 text-right">{row.sortino?.toFixed(3)}</td>
                            <td className="py-2.5 px-3 text-right">{row.calmar?.toFixed(3)}</td>
                            <td className={`py-2.5 px-3 text-right ${row.max_drawdown > -15 ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {row.max_drawdown?.toFixed(2)}%
                            </td>
                            <td className="py-2.5 px-3 text-right">{row.var_95?.toFixed(2)}%</td>
                            <td className="py-2.5 px-3 text-right">{row.turnover?.toFixed(4)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Table 4: Statistical Significance Tests */}
              {wfStudy.significance?.length > 0 && (
                <div className="rounded-2xl border border-gray-800 bg-[#11131a] p-5 space-y-3">
                  <div>
                    <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                      <ShieldAlert className="w-4 h-4 text-purple-400" />
                      Table 4: Statistical Significance Tests (Proposed PPO-Regime vs Baselines)
                    </h2>
                    <p className="text-xs text-gray-400">
                      Non-parametric Wilcoxon signed-rank and paired t-tests testing H1: Proposed &gt; Baseline.
                    </p>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left">
                      <thead>
                        <tr className="border-b border-gray-800 text-gray-400 font-semibold">
                          <th className="py-2.5 px-3">Baseline</th>
                          <th className="py-2.5 px-3 text-right">Wilcoxon p-value</th>
                          <th className="py-2.5 px-3 text-center">Wilcoxon Sig.</th>
                          <th className="py-2.5 px-3 text-right">t-test p-value</th>
                          <th className="py-2.5 px-3 text-center">t-test Sig.</th>
                          <th className="py-2.5 px-3 text-right">Sharpe 95% Confidence Interval</th>
                        </tr>
                      </thead>
                      <tbody>
                        {wfStudy.significance.map((row) => (
                          <tr key={row.Baseline} className="border-b border-gray-800/60 text-gray-300">
                            <td className="py-2.5 px-3 font-medium text-white">{row.Baseline}</td>
                            <td className="py-2.5 px-3 text-right">{Number(row['Wilcoxon p']).toFixed(4)}</td>
                            <td className="py-2.5 px-3 text-center text-gray-400">{row['Wilcoxon sig.']}</td>
                            <td className="py-2.5 px-3 text-right">{Number(row['t-test p']).toFixed(4)}</td>
                            <td className="py-2.5 px-3 text-center text-gray-400">{row['t-test sig.']}</td>
                            <td className="py-2.5 px-3 text-right font-mono text-indigo-300">{row['Sharpe 95% CI']}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Interactive Paper Figures Viewer */}
              {wfStudy.figures?.length > 0 && (
                <div className="rounded-2xl border border-gray-800 bg-[#11131a] p-6 space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                        <Image className="w-4 h-4 text-emerald-400" />
                        Publication Figures (High-Resolution Vector / 300 DPI)
                      </h2>
                      <p className="text-xs text-gray-400">
                        Generated from walk-forward backtest results.
                      </p>
                    </div>
                  </div>

                  {/* Figure Selection Pills */}
                  <div className="flex flex-wrap gap-2">
                    {wfStudy.figures.map((fig) => (
                      <button
                        key={fig.id}
                        onClick={() => setActiveFigure(fig.id)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                          activeFigure === fig.id
                            ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/20'
                            : 'bg-[#161822] text-gray-400 hover:text-white border border-gray-700/80'
                        }`}
                      >
                        {fig.title}
                      </button>
                    ))}
                  </div>

                  {/* Display Active Figure */}
                  {selectedFigObj && (
                    <div className="bg-[#161822] border border-gray-800 rounded-2xl p-4 flex flex-col items-center">
                      <img
                        src={`http://localhost:8000${selectedFigObj.url}`}
                        alt={selectedFigObj.title}
                        className="max-h-[480px] w-auto rounded-lg object-contain border border-gray-800 shadow-xl"
                      />
                      <div className="mt-3 text-center">
                        <h4 className="text-sm font-bold text-white">{selectedFigObj.title}</h4>
                        <p className="text-xs text-gray-400 mt-0.5">
                          Saved in <code className="text-indigo-400">research/results/figures/{selectedFigObj.filename}</code>
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 2: GAUSSIAN HMM COVARIANCE STUDY (BENCHMARK)               */}
      {/* ============================================================== */}
      {activeTab === 'hmm' && (
        <div className="space-y-6">
          {hmmLoading ? (
            <div className="flex flex-col items-center justify-center h-80 gap-3">
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
              <p className="text-xs text-gray-400">Loading HMM benchmark study...</p>
            </div>
          ) : hmmError ? (
            <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl text-amber-300 text-xs">
              {hmmError}
            </div>
          ) : study?.status !== 'ready' ? (
            <div className="p-8 text-center bg-[#11131a] border border-gray-800 rounded-2xl text-gray-400 text-xs">
              {study?.message || 'No recorded HMM study available.'}
            </div>
          ) : (
            <>
              <div className="rounded-2xl border border-amber-600/30 bg-amber-500/5 p-5 space-y-2">
                <h2 className="font-semibold text-amber-200">2025 Held-Out HMM Covariance Benchmark</h2>
                <p className="text-xs text-gray-300">
                  Evaluates whether HMM state covariance blending improves minimum-variance optimization compared to unconditional covariance.
                </p>
              </div>

              {/* Full period development curve */}
              {study.equity && (
                <div className="rounded-2xl border border-gray-800 bg-[#11131a] p-5 space-y-3">
                  <h2 className="font-semibold text-white text-sm">Full-Period Chronological Equity Path</h2>
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={study.equity}>
                        <CartesianGrid stroke="#272b36" strokeDasharray="3 3" />
                        <XAxis dataKey="date" tickFormatter={(v) => v.slice(0, 7)} minTickGap={70} stroke="#94a3b8" fontSize={10} />
                        <YAxis stroke="#94a3b8" domain={['auto', 'auto']} tickFormatter={(v) => v.toFixed(1)} fontSize={10} />
                        <Tooltip contentStyle={{ backgroundColor: '#11131a', borderColor: '#374151', fontSize: '11px' }} />
                        <Legend />
                        {['Buy and hold', 'Equal weight', 'Minimum variance', 'HMM minimum variance'].map((name, index) => (
                          <Line key={name} dataKey={name} stroke={HMM_COLORS[index]} dot={false} strokeWidth={2} isAnimationActive={false} />
                        ))}
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Holdout Metrics Table */}
              {study.holdout_metrics && (
                <div className="overflow-x-auto rounded-2xl border border-gray-800 bg-[#11131a] p-5">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3">Held-Out Metrics</h3>
                  <table className="w-full text-xs text-left">
                    <thead>
                      <tr className="border-b border-gray-800 text-gray-400 font-semibold">
                        <th className="p-2.5">Strategy</th>
                        <th className="p-2.5 text-right">Return</th>
                        <th className="p-2.5 text-right">Volatility</th>
                        <th className="p-2.5 text-right">Sharpe</th>
                        <th className="p-2.5 text-right">Max Drawdown</th>
                      </tr>
                    </thead>
                    <tbody>
                      {study.holdout_metrics.map((row) => (
                        <tr key={row.strategy} className="border-b border-gray-800/60 text-gray-300">
                          <td className="p-2.5 font-medium text-white">{row.strategy}</td>
                          <td className="p-2.5 text-right">{percent(row.total_return)}</td>
                          <td className="p-2.5 text-right">{percent(row.annualized_volatility)}</td>
                          <td className="p-2.5 text-right text-indigo-300">{row.sharpe?.toFixed(3) ?? 'N/A'}</td>
                          <td className="p-2.5 text-right">{percent(row.max_drawdown)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

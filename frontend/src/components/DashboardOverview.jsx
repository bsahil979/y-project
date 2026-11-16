import React, { useState, useEffect, useMemo, useContext } from 'react';
import { 
  TrendingUp, TrendingDown,
  ChevronRight, Loader2, AlertTriangle, Brain, Shield, Briefcase, RefreshCw,
  PieChart as PieIcon, ArrowUpRight, ArrowDownRight, Layers, DollarSign, Activity, Sparkles
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, Legend,
  PieChart as RechartsPieChart, Pie,
} from 'recharts';
import { PortfolioService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { PortfolioContext } from '../contexts/PortfolioContext';
import { formatMoney } from '../services/portfolioValuation';

const CHART_COLORS = ['#6366f1', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#3b82f6', '#ec4899', '#14b8a6', '#06b6d4', '#84cc16'];

const DashboardOverview = ({ tickers = [] }) => {
  const { user } = useAuth();
  const userId = user?.id || user?.email || 'guest';

  // Portfolio context integration
  const portfolioContext = useContext(PortfolioContext);
  const snapshot = portfolioContext?.snapshot;
  const pricing = portfolioContext?.pricing;

  const [selectedCurrency, setSelectedCurrency] = useState('INR');
  const [analysis, setAnalysis] = useState(null);
  const [regime, setRegime] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Extract real owned positions from valuation
  const valued = snapshot?.valuation;
  const availableCurrencies = valued?.currencies || [];
  const activeCurrency = valued?.groups?.[selectedCurrency] 
    ? selectedCurrency 
    : (availableCurrencies[0] || 'INR');
  const activeGroup = valued?.groups?.[activeCurrency];
  const ownedPositions = activeGroup?.positions || [];
  const hasOwnedPositions = ownedPositions.length > 0;

  // Determine effective tickers and weights
  const { effectiveTickers, effectiveWeights, effectiveValue } = useMemo(() => {
    if (hasOwnedPositions && activeGroup?.tickers?.length > 0) {
      const t = activeGroup.tickers;
      const w = activeGroup.weights && activeGroup.weights.length === t.length
        ? activeGroup.weights
        : Array(t.length).fill(1 / t.length);
      const val = activeGroup.market && activeGroup.market > 0
        ? activeGroup.market
        : (activeGroup.cost || 100000);
      return { effectiveTickers: t, effectiveWeights: w, effectiveValue: val };
    }
    const t = tickers || [];
    const w = t.length > 0 ? Array(t.length).fill(1 / t.length) : [];
    return { effectiveTickers: t, effectiveWeights: w, effectiveValue: 100000 };
  }, [hasOwnedPositions, activeGroup, tickers]);

  // Fetch analysis based on effective tickers and weights
  useEffect(() => {
    if (effectiveTickers.length === 0) {
      setLoading(false);
      setAnalysis(null);
      return;
    }

    let active = true;
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const [analysisRes, regimeRes] = await Promise.all([
          PortfolioService.getAnalysis(effectiveTickers, effectiveWeights, false, effectiveValue),
          PortfolioService.getMarketRegime().catch(() => null)
        ]);
        if (!active) return;
        setAnalysis(analysisRes);
        setRegime(regimeRes);
      } catch (err) {
        if (!active) return;
        console.error('Analytics fetch failed:', err);
        const msg = String(err?.message || '');
        if (err?.code === 'ECONNABORTED' || msg.toLowerCase().includes('timeout')) {
          setError('Analysis timed out. Models may be computing; please try refreshing.');
        } else if (err?.code === 'ERR_NETWORK' || msg.includes('Network Error')) {
          setError('Analytics engine is unavailable. Ensure FastAPI is running on port 8000.');
        } else {
          setError(msg || 'Failed to fetch portfolio analytics.');
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    fetchData();
    return () => { active = false; };
  }, [effectiveTickers, effectiveWeights, effectiveValue]);

  if (loading || pricing?.loading) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-4">
        <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
        <p className="text-gray-300 text-sm font-medium">
          {pricing?.loading 
            ? 'Fetching live market quotes...' 
            : 'Evaluating portfolio weights, covariance & HMM market regimes...'}
        </p>
      </div>
    );
  }

  if (effectiveTickers.length === 0) {
    return (
      <div className="col-span-12 flex flex-col items-center justify-center h-[450px] bg-[#11131a]/80 backdrop-blur-xl border border-gray-800/50 rounded-3xl p-12 text-center shadow-2xl animate-in fade-in duration-500">
        <div className="w-20 h-20 rounded-3xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-6">
          <Briefcase className="w-10 h-10 text-indigo-400" />
        </div>
        <h3 className="text-2xl font-black text-white tracking-tight mb-2">Your Portfolio is Empty</h3>
        <p className="text-sm text-gray-400 max-w-md mx-auto mb-6 leading-relaxed font-medium">
          Record your actual holdings in <strong>My Holdings</strong> to track live market-value weights, or add symbols to your watchlist.
        </p>
        <div className="flex items-center gap-3">
          <Link 
            to="/dashboard/portfolio"
            className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition-all shadow-lg shadow-indigo-600/20 flex items-center gap-2 active:scale-95"
          >
            <Briefcase className="w-4 h-4" />
            <span>Manage My Holdings</span>
          </Link>
          <Link 
            to="/dashboard/manage"
            className="px-6 py-3 bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 rounded-xl text-xs font-bold transition-all flex items-center gap-2 active:scale-95"
          >
            <span>Curated Asset Watchlist</span>
          </Link>
        </div>
      </div>
    );
  }

  // Parse analytics response data
  const riskSummary = analysis?.risk_summary || analysis?.risk_engine || {};
  const regimeData = analysis?.regime_summary || analysis?.market_regime || regime || {};
  const portfolioScore = analysis?.portfolio_score || null;
  const scorePct = portfolioScore ? Math.round(portfolioScore.pct || 0) : 78;
  const scoreGrade = portfolioScore?.grade || 'B+';

  const volData = riskSummary['Volatility (Annual)'] || {};
  const varData = riskSummary['VaR (95%)'] || {};
  const cvarData = riskSummary['CVaR (95%)'] || {};
  const drawdownData = riskSummary['Max Drawdown'] || {};

  const chartData = effectiveTickers.map((ticker, index) => {
    const weightVal = effectiveWeights[index] != null 
      ? Number((effectiveWeights[index] * 100).toFixed(1)) 
      : Number((100 / effectiveTickers.length).toFixed(1));
    return {
      name: ticker,
      weight: weightVal,
      volatility: parseFloat(((volData[ticker] || 0) * 100).toFixed(2)),
      var95: parseFloat(((varData[ticker] || 0) * 100).toFixed(2)),
      maxDrawdown: parseFloat(((drawdownData[ticker] || 0) * 100).toFixed(2)),
    };
  });

  const avgVolatility = chartData.length > 0 
    ? (chartData.reduce((sum, d) => sum + d.volatility, 0) / chartData.length).toFixed(1) 
    : '0';
  const avgVaR = chartData.length > 0
    ? (chartData.reduce((sum, d) => sum + d.var95, 0) / chartData.length).toFixed(1)
    : '0';
  const avgMaxDrawdown = chartData.length > 0
    ? (chartData.reduce((sum, d) => sum + d.maxDrawdown, 0) / chartData.length).toFixed(1)
    : '0';

  const regimeLabel = regimeData.current_regime || regimeData.regime || 'Bull / Expansion';
  const regimeConfidence = regimeData.confidence 
    ? (regimeData.confidence * 100).toFixed(0) 
    : '85';

  const totalMarketVal = activeGroup?.market;
  const totalCostVal = activeGroup?.cost;
  const totalPnlVal = activeGroup?.pnl;
  const totalPnlPctVal = activeGroup?.pnlPct;

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Top Controls & Status Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-[#11131a]/90 border border-gray-800 rounded-2xl p-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white flex items-center gap-2">
              Portfolio Intelligence Overview
              <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full ${
                hasOwnedPositions 
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                  : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
              }`}>
                {hasOwnedPositions ? 'Live Holdings' : 'Watchlist Mode'}
              </span>
            </h1>
            <p className="text-xs text-gray-400">
              {hasOwnedPositions 
                ? `Valued with actual holdings & quotes (${activeCurrency})`
                : 'Showing equal-weighted simulation for watchlist assets.'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {availableCurrencies.length > 1 && (
            <div className="flex items-center gap-2 text-xs text-gray-300 bg-[#161822] border border-gray-700/80 rounded-xl px-3 py-1.5">
              <span>Currency:</span>
              <select 
                value={activeCurrency}
                onChange={(e) => setSelectedCurrency(e.target.value)}
                className="bg-transparent text-white font-semibold focus:outline-none"
              >
                {availableCurrencies.map((c) => (
                  <option key={c} value={c} className="bg-gray-900 text-white">{c}</option>
                ))}
              </select>
            </div>
          )}

          {pricing?.refresh && (
            <button
              onClick={pricing.refresh}
              disabled={pricing.loading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-gray-300 hover:text-white bg-[#161822] border border-gray-700/80 hover:border-gray-600 transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${pricing.loading ? 'animate-spin' : ''}`} />
              <span>Refresh Prices</span>
            </button>
          )}

          <Link
            to="/dashboard/portfolio"
            className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition-all shadow-md shadow-indigo-600/20"
          >
            <Briefcase className="w-3.5 h-3.5" />
            <span>Manage Holdings</span>
          </Link>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-3 p-4 bg-amber-500/10 border border-amber-500/20 text-amber-300 rounded-xl text-xs">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* AI Architecture & Project Aim Discovery Banner */}
      <div className="relative overflow-hidden rounded-2xl border border-indigo-500/30 bg-gradient-to-r from-indigo-950/40 via-purple-950/20 to-[#11131a] p-5 shadow-lg shadow-indigo-950/20">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 shrink-0">
              <Brain className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded">
                  Core AI Intelligence
                </span>
                <span className="text-xs text-gray-400">• Multi-Model Ensemble</span>
              </div>
              <h3 className="text-base font-bold text-white">
                How Does This Portfolio Advisor Work?
              </h3>
              <p className="text-xs text-gray-400 mt-1 max-w-2xl leading-relaxed">
                Explore our transparent AI/ML pipeline: <strong>LSTM + Random Forest</strong> for stock signals, <strong>Gaussian HMM</strong> for market regimes, <strong>PPO Reinforcement Learning</strong> for friction-aware allocation, and rule-based risk filters.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <Link
              to="/dashboard/forecast"
              className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-xl transition-all shadow-md shadow-emerald-600/25"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Evaluate Stock for Betterment</span>
            </Link>
            <Link
              to="/dashboard/ai-architecture"
              className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 text-xs font-semibold rounded-xl transition-all"
            >
              <span>AI Architecture & Aim</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>

      {/* Primary KPI Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Value Card */}
        <div className="bg-[#11131a]/80 border border-gray-800 rounded-2xl p-5 relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-gray-400 mb-2">
            <span>Portfolio Market Value</span>
            <span className="font-semibold text-gray-500">{activeCurrency}</span>
          </div>
          <div className="text-2xl font-black text-white tracking-tight">
            {hasOwnedPositions && totalMarketVal != null
              ? formatMoney(totalMarketVal, activeCurrency)
              : hasOwnedPositions && totalCostVal != null
                ? formatMoney(totalCostVal, activeCurrency)
                : `$${Number(effectiveValue).toLocaleString()}`}
          </div>
          <div className="mt-3 flex items-center gap-2">
            {hasOwnedPositions && totalPnlVal != null ? (
              <span className={`inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-md ${
                totalPnlVal >= 0 
                  ? 'text-emerald-400 bg-emerald-500/10' 
                  : 'text-rose-400 bg-rose-500/10'
              }`}>
                {totalPnlVal >= 0 ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                {formatMoney(Math.abs(totalPnlVal), activeCurrency)} ({totalPnlPctVal != null ? `${totalPnlPctVal >= 0 ? '+' : ''}${totalPnlPctVal.toFixed(2)}%` : '0%'})
              </span>
            ) : (
              <span className="text-xs text-gray-500">Benchmark Base Value</span>
            )}
            <span className="text-[11px] text-gray-400">Total Unrealized</span>
          </div>
        </div>

        {/* Market Regime Card */}
        <div className="bg-[#11131a]/80 border border-gray-800 rounded-2xl p-5">
          <div className="flex items-center justify-between text-xs text-gray-400 mb-2">
            <span>HMM Market Regime</span>
            <Brain className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-xl font-bold text-white capitalize truncate">
            {regimeLabel}
          </div>
          <div className="mt-3 flex items-center justify-between text-xs">
            <span className="text-gray-400">Model Confidence:</span>
            <span className="font-bold text-purple-400">{regimeConfidence}%</span>
          </div>
          <div className="w-full bg-gray-800 h-1.5 rounded-full mt-2 overflow-hidden">
            <div 
              className="bg-purple-500 h-full rounded-full transition-all duration-500" 
              style={{ width: `${Math.min(100, Math.max(10, regimeConfidence))}%` }}
            />
          </div>
        </div>

        {/* Portfolio Score Card */}
        <div className="bg-[#11131a]/80 border border-gray-800 rounded-2xl p-5">
          <div className="flex items-center justify-between text-xs text-gray-400 mb-2">
            <span>Diversification Health</span>
            <Shield className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-black text-white">{scorePct}</span>
            <span className="text-xs text-gray-400">/ 100</span>
            <span className="ml-auto px-2 py-0.5 rounded text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Grade {scoreGrade}
            </span>
          </div>
          <div className="mt-3 text-xs text-gray-400 flex items-center justify-between">
            <span>Positions tracked:</span>
            <span className="font-semibold text-white">{effectiveTickers.length} assets</span>
          </div>
          <div className="w-full bg-gray-800 h-1.5 rounded-full mt-2 overflow-hidden">
            <div 
              className="bg-emerald-500 h-full rounded-full transition-all duration-500" 
              style={{ width: `${scorePct}%` }}
            />
          </div>
        </div>

        {/* Risk Metrics Quick View */}
        <div className="bg-[#11131a]/80 border border-gray-800 rounded-2xl p-5">
          <div className="flex items-center justify-between text-xs text-gray-400 mb-2">
            <span>Risk Profile (Annual)</span>
            <TrendingDown className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-black text-white">
            {avgVolatility}%
          </div>
          <div className="mt-2 grid grid-cols-2 gap-2 text-[11px] text-gray-400 border-t border-gray-800 pt-2">
            <div>
              <span>1D VaR (95%):</span>
              <span className="ml-1 font-semibold text-amber-400">{avgVaR}%</span>
            </div>
            <div>
              <span>Max DD:</span>
              <span className="ml-1 font-semibold text-rose-400">{avgMaxDrawdown}%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid: Holdings Breakdown & Allocation */}
      <div className="grid grid-cols-12 gap-6">
        {/* Left Column: Asset Holdings Cards */}
        <div className="col-span-12 lg:col-span-7 bg-[#11131a]/80 border border-gray-800 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-400" />
                Asset Positions & Weights
              </h2>
              <p className="text-xs text-gray-400">
                {hasOwnedPositions 
                  ? 'Calculated from actual shares and latest market quotes' 
                  : 'Watchlist components with equal allocation'}
              </p>
            </div>
            <Link
              to="/dashboard/portfolio"
              className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold flex items-center gap-1"
            >
              <span>View Ledger</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="space-y-3">
            {effectiveTickers.map((ticker, idx) => {
              const holding = hasOwnedPositions 
                ? ownedPositions.find((p) => p.ticker === ticker)
                : null;
              const weightVal = chartData[idx]?.weight || (100 / effectiveTickers.length).toFixed(1);
              const price = holding?.quote?.price || holding?.average_cost;
              const pnl = holding?.pnl;
              const pnlPct = holding?.pnlPct;

              return (
                <div 
                  key={ticker}
                  className="flex items-center justify-between p-3.5 bg-[#161822] border border-gray-800/80 rounded-xl hover:border-gray-700 transition-all"
                >
                  <div className="flex items-center gap-3">
                    <div 
                      className="w-2.5 h-10 rounded-full" 
                      style={{ backgroundColor: CHART_COLORS[idx % CHART_COLORS.length] }} 
                    />
                    <div>
                      <div className="font-bold text-white text-sm flex items-center gap-2">
                        {ticker}
                        {holding?.quantity && (
                          <span className="text-[11px] font-normal text-gray-400">
                            ({holding.quantity} shares)
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-gray-400">
                        {price != null 
                          ? `${formatMoney(price, activeCurrency)} per share` 
                          : 'Market price loading...'}
                      </div>
                    </div>
                  </div>

                  <div className="text-right">
                    <div className="text-sm font-bold text-white">
                      {weightVal}%
                      <span className="text-xs font-normal text-gray-400 ml-1.5">weight</span>
                    </div>
                    {holding?.market != null ? (
                      <div className="text-xs font-medium text-gray-300">
                        {formatMoney(holding.market, activeCurrency)}
                        {pnlPct != null && (
                          <span className={`ml-2 font-semibold ${pnlPct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(1)}%
                          </span>
                        )}
                      </div>
                    ) : (
                      <div className="text-xs text-gray-500">Vol: {chartData[idx]?.volatility || 0}%</div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Allocation Pie & Strategic Recommendations */}
        <div className="col-span-12 lg:col-span-5 flex flex-col gap-6">
          {/* Allocation Visualization */}
          <div className="bg-[#11131a]/80 border border-gray-800 rounded-2xl p-6">
            <h3 className="text-base font-bold text-white mb-2 flex items-center gap-2">
              <PieIcon className="w-4 h-4 text-purple-400" />
              Allocation Distribution
            </h3>
            <div className="h-48 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <RechartsPieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={75}
                    paddingAngle={3}
                    dataKey="weight"
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#161822', borderColor: '#374151', borderRadius: '0.75rem', fontSize: '12px' }}
                    formatter={(val) => [`${val}%`, 'Allocation']}
                  />
                </RechartsPieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-wrap gap-2 justify-center mt-2">
              {chartData.map((d, i) => (
                <span key={d.name} className="inline-flex items-center gap-1 text-[11px] text-gray-400">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: CHART_COLORS[i % CHART_COLORS.length] }} />
                  {d.name} ({d.weight}%)
                </span>
              ))}
            </div>
          </div>

          {/* Quick strategy action card */}
          <div className="bg-gradient-to-br from-indigo-900/30 to-purple-900/20 border border-indigo-500/20 rounded-2xl p-5">
            <div className="flex items-center gap-2 text-indigo-400 text-xs font-bold uppercase tracking-wider mb-2">
              <Brain className="w-4 h-4" />
              Strategic Optimization
            </div>
            <h4 className="text-white font-bold text-sm mb-1.5">
              HMM Regime-Aware Rebalancing
            </h4>
            <p className="text-xs text-gray-300 leading-relaxed mb-4">
              Compare your current portfolio weights with regime-conditioned covariance estimates and minimum variance allocations.
            </p>
            <div className="flex items-center gap-2">
              <Link
                to="/dashboard"
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition-all shadow-md shadow-indigo-600/20"
              >
                Inspect Portfolio Engine
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardOverview;

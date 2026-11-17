import { normalizeExchangeSuffix } from '../utils/tickerUtils';
import React, { useState, useEffect, useCallback, useContext, useMemo, useRef } from 'react';
import { 
  TrendingUp, TrendingDown, Target, Brain, ShieldCheck, AlertTriangle, 
  ArrowRight, Sparkles, Plus, Sliders, CheckCircle2, BarChart3, Activity, 
  RefreshCw, Zap, ShieldAlert, Check, ChevronRight, Info
} from 'lucide-react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, 
  Tooltip, ResponsiveContainer, AreaChart, Area, ReferenceLine
} from 'recharts';
import { Link } from 'react-router-dom';
import { PortfolioService } from '../services/api';
import { PortfolioContext } from '../contexts/PortfolioContext';

const POPULAR_TICKERS = [
  { symbol: 'NVDA', name: 'Nvidia Corp', region: 'US' },
  { symbol: 'AAPL', name: 'Apple Inc', region: 'US' },
  { symbol: 'MSFT', name: 'Microsoft', region: 'US' },
  { symbol: 'AMZN', name: 'Amazon', region: 'US' },
  { symbol: 'SPY', name: 'S&P 500 ETF', region: 'US' },
  { symbol: 'QQQ', name: 'Nasdaq 100 ETF', region: 'US' },
  { symbol: 'RELIANCE.NS', name: 'Reliance Ind.', region: 'IN' },
  { symbol: 'TCS.NS', name: 'Tata Consultancy', region: 'IN' },
  { symbol: 'INFY.NS', name: 'Infosys Ltd', region: 'IN' },
  { symbol: 'HDFCBANK.NS', name: 'HDFC Bank', region: 'IN' },
  { symbol: 'ICICIBANK.NS', name: 'ICICI Bank', region: 'IN' },
];

const ForecastingView = ({ tickers = [], setTickers }) => {
  const portfolioContext = useContext(PortfolioContext);
  const snapshot = portfolioContext?.snapshot;
  const valued = snapshot?.valuation;

  const [selectedTicker, setSelectedTicker] = useState(() => normalizeExchangeSuffix(tickers[0] || 'NVDA'));
  const [inputTicker, setInputTicker] = useState(() => normalizeExchangeSuffix(tickers[0] || 'NVDA'));
  const [proposedWeight, setProposedWeight] = useState(0.05); // 5% default
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [addedSuccess, setAddedSuccess] = useState(false);
  const requestId = useRef(0);

  const fetchEvaluation = useCallback(async (sym, weight) => {
    if (!sym) return;
    const currentRequest = ++requestId.current;
    setLoading(true);
    setData(null);
    setError(null);
    setAddedSuccess(false);

    try {
      const currency = sym.endsWith('.NS') || sym.endsWith('.BO') ? 'INR' : 'USD';
      const group = valued?.groups?.[currency];
      if (!snapshot?.valid || !group?.complete || !group?.tickers?.length || !group?.weights?.length) {
        throw new Error(`Add a priced ${currency} holding before comparing this stock with your portfolio.`);
      }
      const payload = {
        ticker: sym.toUpperCase().trim(),
        proposed_weight: weight,
        current_tickers: group.tickers,
        current_weights: group.weights,
        portfolio_value: group.market,
        currency,
        horizon: 30,
      };

      let res;
      if (typeof PortfolioService?.evaluateTicker === 'function') {
        res = await PortfolioService.evaluateTicker(payload);
      } else {
        const resp = await fetch('http://localhost:8000/ticker/evaluate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!resp.ok) {
          const errData = await resp.json().catch(() => ({}));
          throw new Error(errData.detail || `Evaluation failed with status ${resp.status}`);
        }
        res = await resp.json();
      }
      if (currentRequest === requestId.current) setData(res);
    } catch (err) {
      console.error('Ticker evaluation failed:', err);
      const msg = err.response?.data?.detail || err.message || 'Failed to evaluate stock';
      if (currentRequest === requestId.current) setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      if (currentRequest === requestId.current) setLoading(false);
    }
  }, [valued, snapshot?.valid]);

  useEffect(() => {
    fetchEvaluation(selectedTicker, proposedWeight);
  }, [selectedTicker, proposedWeight, fetchEvaluation]);

  const handleSearchSubmit = (e) => {
    e?.preventDefault();
    const input = normalizeExchangeSuffix(inputTicker);
    const clean = ['JPL', 'JIO PLATFORMS', 'JIO PLATFORMS LIMITED'].includes(input) ? 'JPL.NS' : input;
    if (!clean) return;
    setInputTicker(clean);
    if (clean === selectedTicker) fetchEvaluation(clean, proposedWeight);
    else setSelectedTicker(clean);
  };

  const handleQuickSelect = (sym) => {
    const clean = normalizeExchangeSuffix(sym);
    setInputTicker(clean);
    setSelectedTicker(clean);
  };

  const handleAddToWatchlist = () => {
    if (!setTickers) return;
    setTickers(prev => {
      const clean = selectedTicker.toUpperCase();
      if (prev.includes(clean)) return prev;
      return [...prev, clean];
    });
    setAddedSuccess(true);
    setTimeout(() => setAddedSuccess(false), 3000);
  };

  // Format forecast chart data
  const chartData = useMemo(() => {
    if (!data || !data.forecast) return [];
    const spot = data.spot_price;
    const points = [
      { step: 0, label: 'Today', price: spot, actual: true },
      ...data.forecast.map(item => ({
        step: item.step,
        label: `Day ${item.step}`,
        price: item.predicted_price,
        actual: false,
      }))
    ];
    return points;
  }, [data]);

  const currencySymbol = data?.currency === 'INR' ? '₹' : '$';

  return (
    <div className="space-y-6 animate-in fade-in duration-500 text-slate-100">
      
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-3xl border border-slate-200 bg-white p-6 shadow-xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                <Brain className="w-3.5 h-3.5" />
                Practical AI Advisor
              </span>
              <span className="text-xs text-gray-400">• Experimental forecast and historical scenario</span>
            </div>
            <h1 className="text-2xl font-black text-white tracking-tight">
              Stock Estimate & Portfolio Comparison
            </h1>
            <p className="text-xs text-gray-400 leading-relaxed">
              Select a stock to see an experimental 30-session price estimate and compare a position size with your same-currency holdings. The comparison uses historical returns to estimate changes in <strong>Sharpe ratio</strong>, <strong>volatility</strong>, and <strong>correlation</strong>.
            </p>
          </div>

          {/* Search bar & Quick Selector */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <form onSubmit={handleSearchSubmit} className="relative flex items-center">
              <input
                type="text"
                value={inputTicker}
                onChange={(e) => setInputTicker(e.target.value)}
                placeholder="Search ticker (e.g. NVDA, RELIANCE.NS)"
                className="w-full sm:w-64 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-xs text-slate-900 placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
              <button
                type="submit"
                className="ml-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-[#ffffff] text-xs font-bold transition shadow-md shadow-indigo-600/30 shrink-0"
              >
                Analyze
              </button>
            </form>
          </div>
        </div>

        {/* Quick Ticker Universe Pills */}
        <div className="mt-5 pt-4 border-t border-gray-800/80 flex flex-wrap items-center gap-2 text-xs">
          <span className="text-[11px] font-semibold text-gray-400 mr-1 flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-indigo-400" />
            Quick Test:
          </span>
          {[...tickers.map(symbol => ({symbol, name: symbol})), ...POPULAR_TICKERS.filter(t => !tickers.includes(t.symbol))].map((t) => (
            <button
              key={t.symbol}
              onClick={() => handleQuickSelect(t.symbol)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                selectedTicker === t.symbol
                  ? 'bg-indigo-600 text-[#ffffff] font-bold shadow-md shadow-indigo-600/30'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              {t.symbol}
              <span className="ml-1 text-[10px] opacity-60">({t.region})</span>
            </button>
          ))}
        </div>
      </div>

      {/* Allocation Slider Control */}
      <div className="rounded-2xl border border-gray-800 bg-[#11131a]/90 p-5 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-600/10 border border-indigo-500/20 text-indigo-400">
              <Sliders className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                Simulated Allocation Weight:
                <span className="text-indigo-400 text-base font-black">
                  {Math.round(proposedWeight * 100)}% of Portfolio
                </span>
              </h3>
              <p className="text-xs text-gray-400 mt-0.5">
                Drag the slider to compare historical risk and return at different position sizes.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4 w-full md:w-72">
            <span className="text-xs text-gray-500 font-semibold">1%</span>
            <input
              type="range"
              min="0.01"
              max="0.25"
              step="0.01"
              value={proposedWeight}
              onChange={(e) => setProposedWeight(parseFloat(e.target.value))}
              className="w-full h-2 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
            />
            <span className="text-xs text-gray-500 font-semibold">25%</span>
          </div>
        </div>
      </div>

      {/* Error or Loading State */}
      {loading && !data && (
        <div className="flex flex-col items-center justify-center h-80 rounded-3xl border border-gray-800 bg-[#11131a]/80 p-8">
          <RefreshCw className="w-8 h-8 text-indigo-500 animate-spin mb-3" />
          <p className="text-sm font-medium text-gray-300">
            Loading model estimate and historical comparison for {selectedTicker}…
          </p>
          <span className="text-xs text-gray-500 mt-1">Evaluating covariance matrix and risk-adjusted Sharpe delta</span>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <div>
            <div className="font-bold">Evaluation Notice:</div>
            <div>{error}</div>
          </div>
        </div>
      )}

      {/* Main Results View */}
      {data?.status === 'limited_history' && (
        <section role="status" className="rounded-xl border border-blue-200 bg-blue-50 p-5 text-slate-900">
          <h3 className="font-semibold">{data.ticker} · Limited price history</h3>
          <p className="mt-2">Last available close: {currencySymbol}{data.spot_price.toLocaleString()} on {data.price_as_of}.</p>
          <p className="mt-2 text-sm">Your comparison has {data.price_observations} shared trading dates from {data.first_price_date} to {data.price_as_of}. The forecast and portfolio comparison require {data.required_observations}.</p>
        </section>
      )}
      {data && data.status !== 'limited_history' && (
        <>
          {/* 1. Prominent AI Betterment Verdict Banner */}
          <div className={`relative overflow-hidden rounded-3xl border bg-white p-6 shadow-xl ${
            data.verdict_type === 'positive'
              ? 'border-emerald-300'
              : data.verdict_type === 'warning'
                ? 'border-amber-300'
                : data.verdict_type === 'moderate'
                  ? 'border-indigo-300'
                  : 'border-rose-300'
          }`}>
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className={`px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider ${
                    data.verdict_type === 'positive'
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : data.verdict_type === 'warning'
                        ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                        : data.verdict_type === 'moderate'
                          ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30'
                          : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                  }`}>
                    {data.badge}
                  </span>
                  <span className="text-xs text-gray-400 font-semibold">• Historical Scenario Summary</span>
                </div>
                <h2 className="text-xl md:text-2xl font-black text-white tracking-tight">
                  {data.verdict}
                </h2>
                <p className="text-sm text-gray-300 max-w-3xl leading-relaxed">
                  {data.headline}
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-3 shrink-0">
                <button
                  onClick={handleAddToWatchlist}
                  className="flex items-center gap-1.5 px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-900 rounded-xl text-xs font-semibold transition border border-slate-300"
                >
                  {addedSuccess ? <Check className="w-4 h-4 text-emerald-400" /> : <Plus className="w-4 h-4 text-indigo-400" />}
                  <span>{addedSuccess ? 'Added to Watchlist!' : `Watch ${data.ticker}`}</span>
                </button>
                <Link
                  to="/dashboard/portfolio"
                  className="flex items-center gap-1.5 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-[#ffffff] rounded-xl text-xs font-semibold transition shadow-md shadow-indigo-600/30"
                >
                  <span>Record Holding</span>
                  <ChevronRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          </div>

          {/* 2. Before vs. After Impact Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Sharpe Ratio Impact */}
            <div className="rounded-2xl border border-gray-800 bg-[#11131a]/80 p-5 relative overflow-hidden">
              <div className="flex items-center justify-between text-xs text-gray-400 mb-2">
                <span>Portfolio Sharpe Ratio</span>
                <Target className="w-4 h-4 text-indigo-400" />
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-gray-500">Current: {data.portfolio_impact.base_sharpe.toFixed(2)}</span>
                <span className="text-gray-500 font-bold">&rarr;</span>
                <span className="text-2xl font-black text-white">
                  {data.portfolio_impact.sim_sharpe.toFixed(2)}
                </span>
              </div>
              <div className="mt-3">
                <span className={`inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-md ${
                  data.portfolio_impact.sharpe_delta >= 0
                    ? 'text-emerald-400 bg-emerald-500/10'
                    : 'text-rose-400 bg-rose-500/10'
                }`}>
                  {data.portfolio_impact.sharpe_delta >= 0 ? '+' : ''}
                  {data.portfolio_impact.sharpe_delta.toFixed(2)} Sharpe Delta
                </span>
              </div>
            </div>

            {/* Annual Volatility Impact */}
            <div className="rounded-2xl border border-gray-800 bg-[#11131a]/80 p-5 relative overflow-hidden">
              <div className="flex items-center justify-between text-xs text-gray-400 mb-2">
                <span>Annual Volatility (Risk)</span>
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-gray-500">Current: {data.portfolio_impact.base_volatility.toFixed(1)}%</span>
                <span className="text-gray-500 font-bold">&rarr;</span>
                <span className="text-2xl font-black text-white">
                  {data.portfolio_impact.sim_volatility.toFixed(1)}%
                </span>
              </div>
              <div className="mt-3">
                <span className={`inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-md ${
                  data.portfolio_impact.volatility_delta <= 0
                    ? 'text-emerald-400 bg-emerald-500/10'
                    : 'text-amber-400 bg-amber-500/10'
                }`}>
                  {data.portfolio_impact.volatility_delta <= 0 ? '' : '+'}
                  {data.portfolio_impact.volatility_delta.toFixed(1)}% Volatility Delta
                </span>
              </div>
            </div>

            {/* Expected Annual Return Impact */}
            <div className="rounded-2xl border border-gray-800 bg-[#11131a]/80 p-5 relative overflow-hidden">
              <div className="flex items-center justify-between text-xs text-gray-400 mb-2">
                <span>Historical Annualized Return</span>
                <TrendingUp className="w-4 h-4 text-indigo-400" />
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-gray-500">Current: {data.portfolio_impact.base_return.toFixed(1)}%</span>
                <span className="text-gray-500 font-bold">&rarr;</span>
                <span className="text-2xl font-black text-white">
                  {data.portfolio_impact.sim_return.toFixed(1)}%
                </span>
              </div>
              <div className="mt-3">
                <span className={`inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-md ${
                  data.portfolio_impact.return_delta >= 0
                    ? 'text-emerald-400 bg-emerald-500/10'
                    : 'text-rose-400 bg-rose-500/10'
                }`}>
                  {data.portfolio_impact.return_delta >= 0 ? '+' : ''}
                  {data.portfolio_impact.return_delta.toFixed(1)}% Return Delta
                </span>
              </div>
            </div>

            {/* Correlation to Portfolio Basket */}
            <div className="rounded-2xl border border-gray-800 bg-[#11131a]/80 p-5 relative overflow-hidden">
              <div className="flex items-center justify-between text-xs text-gray-400 mb-2">
                <span>Correlation to Holdings</span>
                <Activity className="w-4 h-4 text-purple-400" />
              </div>
              <div className="text-2xl font-black text-white">
                {data.portfolio_impact.correlation.toFixed(2)}
              </div>
              <div className="mt-3">
                <span className={`inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-md ${
                  data.portfolio_impact.correlation < 0.5
                    ? 'text-emerald-400 bg-emerald-500/10'
                    : 'text-gray-400 bg-gray-500/10'
                }`}>
                  {data.portfolio_impact.correlation < 0.5 ? 'Low Historical Correlation' : 'Higher Historical Correlation'}
                </span>
              </div>
            </div>
          </div>

          {/* 3. Ticker Price Prediction Chart & Signals */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Forecast Chart (2 Cols) */}
            <div className="lg:col-span-2 rounded-3xl border border-gray-800 bg-[#11131a]/80 p-6 shadow-sm">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-white">{data.ticker}</span>
                    <span className="text-xs text-gray-400">({data.currency})</span>
                    <span className="text-xs px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono">
                      {data.model}
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-gray-200 mt-1">
                    30-Session AI Price Projection Trajectory
                  </h3>
                </div>

                <div className="flex items-center gap-4 text-right">
                  <div>
                    <div className="text-[10px] uppercase font-bold text-gray-500">Latest Daily Close</div>
                    <div className="text-base font-black text-white">
                      {currencySymbol}{data.spot_price.toLocaleString()}
                    </div>
                    {data.price_as_of && <div className="text-[10px] text-gray-500">As of {data.price_as_of}</div>}
                  </div>
                  <div>
                    <div className="text-[10px] uppercase font-bold text-gray-500">Projected Move</div>
                    <div className={`text-base font-black flex items-center gap-1 ${
                      data.forecast_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}>
                      {data.forecast_pct >= 0 ? '+' : ''}{data.forecast_pct.toFixed(1)}%
                    </div>
                  </div>
                </div>
              </div>

              {/* Chart */}
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="forecastGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" vertical={false} />
                    <XAxis dataKey="label" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis 
                      stroke="#64748b" 
                      fontSize={11} 
                      tickLine={false} 
                      axisLine={false} 
                      domain={['auto', 'auto']}
                      tickFormatter={(v) => `${currencySymbol}${v}`} 
                    />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0d1117', color: '#f1f5f9', border: '1px solid #1e293b', borderRadius: '12px', fontSize: '12px' }}
                      formatter={(val, _name, item) => [
                        `${currencySymbol}${Number(val).toFixed(2)}`,
                        item.payload.actual ? 'Latest Daily Close' : 'Experimental Model Estimate'
                      ]}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="price" 
                      stroke="#6366f1" 
                      strokeWidth={3} 
                      fillOpacity={1} 
                      fill="url(#forecastGrad)" 
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              <div className="mt-4 flex items-center justify-between text-xs text-gray-500 pt-3 border-t border-gray-800">
                <span>Projection Model: {data.model} · Experimental estimate; accuracy is not established</span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></span>
                  Forward Horizon: 30 Trading Days
                </span>
              </div>
            </div>

            {/* Technical & Regime Health (1 Col) */}
            <div className="rounded-3xl border border-gray-800 bg-[#11131a]/80 p-6 flex flex-col justify-between">
              <div>
                <h4 className="text-sm font-bold text-white flex items-center gap-2 mb-4">
                  <BarChart3 className="w-4 h-4 text-indigo-400" />
                  Technical & Regime Diagnostics
                </h4>

                <div className="space-y-4">
                  {/* RSI */}
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                    <div className="flex items-center justify-between text-xs mb-1.5">
                      <span className="text-gray-400">14-Day RSI</span>
                      <span className="font-bold text-white">{data.rsi}</span>
                    </div>
                    <div className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full ${
                          data.rsi > 70 ? 'bg-amber-500' : data.rsi < 35 ? 'bg-emerald-500' : 'bg-indigo-500'
                        }`}
                        style={{ width: `${Math.min(data.rsi, 100)}%` }}
                      ></div>
                    </div>
                    <div className="flex justify-between text-[10px] text-gray-500 mt-1">
                      <span>Oversold (30)</span>
                      <span>Neutral</span>
                      <span>Overbought (70)</span>
                    </div>
                  </div>

                  {/* 20-Day Volatility */}
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-400">20-Day Annual Volatility</span>
                      <span className="font-bold text-white">{data.volatility_20d}%</span>
                    </div>
                    <div className="text-[11px] text-gray-500 mt-1">
                      {data.volatility_20d > 30 ? 'High volatility asset — requires disciplined sizing.' : 'Controlled volatility profile.'}
                    </div>
                  </div>

                  {/* Market Regime */}
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-400">HMM Market Regime</span>
                      <span className="font-bold text-indigo-400 uppercase tracking-wider">{data.regime}</span>
                    </div>
                    <div className="text-[11px] text-gray-500 mt-1">
                      {data.regime === 'Unavailable'
                        ? 'Market-state estimate is currently unavailable.'
                        : "A market state does not predict this stock's return."}
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-gray-800 text-center">
                <Link
                  to="/dashboard/ai-architecture"
                  className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold inline-flex items-center gap-1"
                >
                  <span>Read how the AI models generate these signals</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          </div>

          {/* 4. Strategic AI Betterment Insights (4 Cards) */}
          <div className="space-y-3">
            <h3 className="text-sm font-bold text-gray-300 uppercase tracking-wider flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              What Drives This Comparison
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {data.insights.map((insight, idx) => (
                <div 
                  key={idx}
                  className="rounded-2xl border border-gray-800 bg-[#11131a]/80 p-5 hover:border-indigo-500/30 transition-all space-y-2"
                >
                  <div className="flex items-center gap-2">
                    <div className={`p-1.5 rounded-lg ${
                      insight.positive 
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                        : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    }`}>
                      {insight.positive ? <Check className="w-3.5 h-3.5" /> : <Info className="w-3.5 h-3.5" />}
                    </div>
                    <h4 className="text-xs font-bold text-white">{insight.title}</h4>
                  </div>
                  <p className="text-xs text-gray-400 leading-relaxed pl-7">
                    {insight.text}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

    </div>
  );
};

export default ForecastingView;

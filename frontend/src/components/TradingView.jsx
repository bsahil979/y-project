import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config/api';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, PieChart, Pie, Cell 
} from 'recharts';
import { 
  TrendingUp, TrendingDown, AlertCircle, Zap, Cpu, Activity, Info, RefreshCcw, DollarSign, BarChart, History, Brain, Target, Compass, Radio
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useTrainedUniverse } from '../contexts/TrainedUniverseContext';

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444'];

const TradingView = ({ tickers = [] }) => {
  const { isReady, canRunMl } = useTrainedUniverse();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [isThinking, setIsThinking] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState(tickers[0] || '');

  const fetchTradingDecision = useCallback(async (targetTicker) => {
    const sym = targetTicker || selectedAsset;
    if (!sym) return;
    setLoading(true);
    setIsThinking(false);
    setError(null);
    try {
      const response = await axios.get(`${API_BASE_URL}/trading/decision?ticker=${sym}`);
      if (response.data.status === 'thinking') {
        setIsThinking(true);
        setData(null);
      } else {
        setData(response.data);
      }
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || err.message || 'Brain Sync Error');
    } finally {
      setLoading(false);
    }
  }, [selectedAsset]);

  useEffect(() => {
    if (tickers.length > 0 && !tickers.includes(selectedAsset)) {
      setSelectedAsset(tickers[0]);
    }
  }, [tickers, selectedAsset]);

  useEffect(() => {
    if (!selectedAsset) return;
    fetchTradingDecision(selectedAsset);
  }, [selectedAsset, fetchTradingDecision]);

  if (tickers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[450px] bg-white backdrop-blur-xl border border-slate-200 rounded-3xl p-12 text-center shadow-2xl animate-in fade-in duration-500">
        <div className="w-20 h-20 rounded-3xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-6">
          <Brain className="w-10 h-10 text-indigo-700" />
        </div>
        <h3 className="text-2xl font-black tracking-tight mb-2">No Assets Selected for AI Brain</h3>
        <p className="text-sm text-slate-600 max-w-md mx-auto leading-relaxed font-medium">
          Add ticker symbols using the top navigation header or Asset Studio gallery to activate live market analysis and MarketMind signals.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-700 pb-12">
      {/* Brain Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-indigo-700 text-[#ffffff] rounded-2xl flex items-center justify-center shadow-lg shadow-indigo-600/20">
            <Brain className="w-7 h-7 text-[#ffffff]" />
          </div>
          <div>
            <h1 className="text-3xl font-black tracking-tighter uppercase">AI Portfolio Signal</h1>
            <p className="text-slate-600 font-medium">
              {selectedAsset} · Clear investment signal and next-step guidance
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchTradingDecision(selectedAsset)}
            disabled={loading}
            className="flex items-center gap-2 px-6 py-3 bg-indigo-700 text-[#ffffff] hover:bg-indigo-800 rounded-2xl font-bold transition-all disabled:opacity-50 shadow-xl shadow-indigo-600/20 active:scale-95"
          >
            {loading ? <RefreshCcw className="w-5 h-5 animate-spin" /> : <Zap className="w-5 h-5" />}
            {loading ? 'Thinking...' : 'Refresh signal'}
          </button>
        </div>
      </div>

      {/* Asset Selector */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        {tickers.map(ticker => (
          <button
            key={ticker}
            onClick={() => setSelectedAsset(ticker)}
            className={`px-4 py-2 rounded-xl font-bold text-sm transition-all whitespace-nowrap border flex items-center gap-2 ${selectedAsset === ticker ? 'bg-indigo-700 text-[#ffffff]  border-indigo-500 shadow-lg shadow-indigo-600/20' : 'bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-100'}`}
          >
            {ticker}
            {isReady(ticker) ? (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700 font-bold">MARKETMIND</span>
            ) : canRunMl(ticker) ? (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-700 font-bold">ML</span>
            ) : (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-sky-100 text-sky-700 font-bold">LIVE</span>
            )}
          </button>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-[24px] border border-indigo-500/20 bg-indigo-500/10 p-4">
          <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-700">Position</div>
          <div className="mt-3 text-2xl font-black text-slate-900">Trend</div>
          <div className="mt-1 text-sm text-slate-900">Momentum, regime, and sentiment combined</div>
        </div>
        <div className="rounded-[24px] border border-emerald-500/20 bg-emerald-500/10 p-4">
          <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-700">Status</div>
          <div className="mt-3 text-2xl font-black text-slate-900">Ready</div>
          <div className="mt-1 text-sm text-slate-900">AI signal is refreshed and ready for review</div>
        </div>
        <div className="rounded-[24px] border border-violet-500/20 bg-violet-500/10 p-4">
          <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-violet-700">Advisor</div>
          <div className="mt-3 text-2xl font-black text-slate-900">Guidance</div>
          <div className="mt-1 text-sm text-slate-900">Actionable insight, not automated trading</div>
        </div>
      </div>

      {loading && !data ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <div key={i} className="h-48 bg-slate-100 border border-slate-200 animate-pulse rounded-3xl" />
          ))}
        </div>
      ) : data ? (
        <>
          <div className="flex items-start gap-3 rounded-2xl bg-amber-500/5 border border-amber-500/20 p-4 text-sm">
            <Info className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
            <p className="text-slate-600"><span className="font-bold text-amber-700">PPO allocation disabled.</span> This screen shows experimental signals only; no model-derived portfolio weights or trades are generated.</p>
          </div>
          {/* Main Decision & Thinking Layer */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* 1. Recommendation */}
            <div className="p-8 rounded-[2rem] bg-indigo-600/10 border border-indigo-600/20 backdrop-blur-3xl relative overflow-hidden group">
               <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity">
                  <Brain className="w-64 h-64 -mr-20 -mt-20" />
               </div>
                
               <div className="flex items-center gap-3 mb-6">
                 <Target className="w-5 h-5 text-indigo-700" />
                 <span className="text-xs font-bold uppercase tracking-widest text-indigo-700">Signal</span>
               </div>
                
               <div className="space-y-4 relative z-10">
                 <div className={`text-7xl font-black tracking-tighter ${data.decision.action === 'BUY' ? 'text-emerald-700' : (data.decision.action === 'SELL' ? 'text-rose-700' : 'text-amber-700')}`}>
                   {data.decision.action}
                 </div>
                 <div>
                    <div className="text-sm text-slate-600 font-medium tracking-wide">Investor view</div>
                    <div className="text-lg font-bold flex items-center gap-2">
                      Confidence: {(data.decision.confidence * 100).toFixed(0)}%
                      {data.is_dry_run && <span className="text-[10px] px-2 py-0.5 bg-slate-100 text-slate-600 rounded-lg">ADVISORY</span>}
                    </div>
                  </div>
                 <p className="text-slate-600 text-sm leading-relaxed">
                   This signal combines trend, regime, and sentiment into a simple action recommendation for review.
                 </p>
               </div>
            </div>
 
            {/* 2. Why this matters */}
            <div className="lg:col-span-2 p-8 rounded-[2rem] bg-slate-100 border border-slate-200 space-y-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Cpu className="w-5 h-5 text-indigo-700" />
                  <span className="text-xs font-bold uppercase tracking-widest text-slate-600">Why this matters</span>
                </div>
                <div className={`px-4 py-1 rounded-full text-xs font-bold border ${data.decision.is_weekend ? 'bg-amber-500/10 text-amber-700 border-amber-500/20' : 'bg-emerald-500/10 text-emerald-700 border-emerald-500/20'}`}>
                  {data.decision.is_weekend ? 'Lower liquidity' : 'Normal market conditions'}
                </div>
              </div>
 
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {data.decision.reasoning.map((reason, i) => (
                  <div key={i} className="p-4 rounded-2xl bg-slate-100 border border-slate-200 hover:border-indigo-500/30 transition-all">
                    <p className="text-xs text-slate-900 leading-relaxed font-medium">
                      {reason}
                    </p>
                  </div>
                ))}
              </div>

              <div className="h-[180px] mt-4">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data.chart_data}>
                    <XAxis dataKey="Date" hide />
                    <Tooltip contentStyle={{backgroundColor: '#ffffff', color: '#0f172a', border: '1px solid #e2e8f0', borderRadius: '10px'}} />
                    <Area type="monotone" dataKey="Close" stroke="#6366f1" fill="#6366f1" fillOpacity={0.1} strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Signal context */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
             
            <div className="p-8 rounded-[2rem] bg-slate-100 border border-slate-200">
              <div className="flex items-center gap-3 mb-6">
                <Activity className="w-5 h-5 text-emerald-700" />
                <span className="text-xs font-bold uppercase tracking-widest text-slate-600">Signal metrics</span>
              </div>
              <div className="space-y-6">
                <div className="flex justify-between items-end">
                  <span className="text-slate-600 text-sm">Momentum</span>
                  <span className="text-xl font-bold">{data.chart_data[data.chart_data.length-1].rsi.toFixed(1)}</span>
                </div>
                <div className="flex justify-between items-end">
                  <span className="text-slate-600 text-sm">Trend</span>
                  <span className={`text-xl font-bold ${data.chart_data[data.chart_data.length-1].macd_diff > 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
                    {data.chart_data[data.chart_data.length-1].macd_diff.toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between items-end">
                  <span className="text-slate-600 text-sm">Coverage</span>
                  <span className="text-xl font-bold uppercase tracking-tighter">{selectedAsset}</span>
                </div>
                 
                <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-xl mt-4">
                  <div className="text-[10px] font-bold text-indigo-700 uppercase mb-2">Signal confidence</div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-slate-600">Position strength</span>
                    <span className="text-sm font-bold text-emerald-700">{(data.decision.confidence * 100).toFixed(0)}%</span>
                  </div>
                </div>
              </div>
            </div>
 
            <div className="p-8 rounded-[2rem] bg-slate-100 border border-slate-200">
              <div className="flex items-center gap-3 mb-6">
                <History className="w-5 h-5 text-amber-700" />
                <span className="text-xs font-bold uppercase tracking-widest text-slate-600">Context</span>
              </div>
              <div className="space-y-4">
                <div className="rounded-2xl bg-slate-100 p-4">
                  <div className="text-[10px] font-bold uppercase tracking-widest text-slate-600">Market regime</div>
                  <div className="mt-2 text-lg font-black text-slate-900">{data.decision.is_weekend ? 'Lower liquidity' : 'Healthy trend'} </div>
                </div>
                <div className="rounded-2xl bg-slate-100 p-4">
                  <div className="text-[10px] font-bold uppercase tracking-widest text-slate-600">Trade feel</div>
                  <div className="mt-2 text-lg font-black text-slate-900">{data.decision.action === 'BUY' ? 'Momentum-led' : data.decision.action === 'SELL' ? 'Defensive' : 'Selective'}</div>
                </div>
              </div>
            </div>
 
            <div className="p-8 rounded-[2rem] bg-slate-100 border border-slate-200">
              <div className="flex items-center gap-3 mb-6">
                <Compass className="w-5 h-5 text-rose-700" />
                <span className="text-xs font-bold uppercase tracking-widest text-slate-600">Next step</span>
              </div>
              <div className="space-y-4">
                <div className="p-4 rounded-2xl bg-slate-100 text-center">
                  <div className="text-2xl font-black">{data.decision.action}</div>
                  <div className="text-[10px] text-slate-600 font-bold uppercase mt-1">Recommended action</div>
                </div>
                <div className="p-4 rounded-2xl bg-slate-100 text-center">
                  <div className="text-2xl font-black">{(data.decision.confidence * 100).toFixed(0)}%</div>
                  <div className="text-[10px] text-slate-600 font-bold uppercase mt-1">Confidence</div>
                </div>
              </div>
            </div>
          </div>
        </>
      ) : isThinking ? (
        <div className="bg-slate-100 border border-indigo-500/30 rounded-[3rem] p-20 flex flex-col items-center justify-center text-center backdrop-blur-xl">
          <div className="relative mb-8">
           <div className="absolute inset-0 bg-indigo-500/20 rounded-full blur-3xl animate-pulse"></div>
           <Brain className="w-24 h-24 text-indigo-700 animate-bounce relative z-10" />
          </div>
          <h2 className="text-4xl font-black text-slate-900 mb-4 tracking-tighter uppercase">Refreshing signal...</h2>
          <p className="text-slate-600 max-w-md mx-auto text-lg font-medium leading-relaxed">
           We are updating the latest market context and re-running the signal review for this asset.
          </p>
          <button 
           onClick={fetchTradingDecision}
           disabled={loading}
           className="mt-10 px-10 py-4 bg-indigo-700 text-[#ffffff] hover:bg-indigo-800  rounded-2xl font-bold transition-all flex items-center gap-3 shadow-xl shadow-indigo-600/20"
          >
           <RefreshCcw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
           {loading ? 'Refreshing signal...' : 'Check status'}
          </button>
        </div>
      ) : (
        <div className="p-20 text-center bg-slate-100 border border-slate-200 rounded-[3rem] backdrop-blur-xl">
           <AlertCircle className="w-16 h-16 text-rose-500 mx-auto mb-6 opacity-20" />
          <h2 className="text-2xl font-bold mb-2">Signal unavailable</h2>
          <p className="text-slate-600 max-w-sm mx-auto">{error || 'We could not refresh the latest signal for this asset right now.'}</p>
          <button onClick={() => fetchTradingDecision(selectedAsset)} className="mt-8 px-8 py-3 bg-slate-100 hover:bg-slate-100 rounded-2xl font-bold transition-all">
            Retry signal
          </button>
        </div>
      )}
    </div>
  );
};

export default TradingView;

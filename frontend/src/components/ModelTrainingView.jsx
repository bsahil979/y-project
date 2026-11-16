import React, { useState, useEffect, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { RefreshCw, Cpu, Globe, List, Play, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { PortfolioService } from '../services/api';
import { useTrainedUniverse } from '../contexts/TrainedUniverseContext';

const PRESETS = [
  { id: 'quick', label: 'Quick', hint: '~2–5 min per symbol · 15 LSTM epochs' },
  { id: 'standard', label: 'Standard', hint: '~10–20 min per symbol · 50 LSTM epochs' },
];

const ModelTrainingView = ({ tickers = [] }) => {
  const location = useLocation();
  const { refresh, summary, readySymbols, universalReady } = useTrainedUniverse();
  const [preset, setPreset] = useState('quick');
  const [singleTicker, setSingleTicker] = useState(
    location.state?.ticker || tickers[0] || 'AAPL'
  );
  const [job, setJob] = useState(null);
  const [pollError, setPollError] = useState(null);

  const pollStatus = useCallback(async () => {
    try {
      const data = await PortfolioService.getTrainingStatus();
      setJob(data);
      setPollError(null);
      if (data.status === 'completed') {
        refresh();
      }
    } catch (err) {
      setPollError(err.message || 'Could not reach training API');
    }
  }, [refresh]);

  useEffect(() => {
    const initialPoll = setTimeout(pollStatus, 0);
    const id = setInterval(pollStatus, 3000);
    return () => {
      clearTimeout(initialPoll);
      clearInterval(id);
    };
  }, [pollStatus]);

  useEffect(() => {
    if (tickers.length > 0 && !tickers.includes(singleTicker)) {
      const nextTicker = setTimeout(() => setSingleTicker(tickers[0]), 0);
      return () => clearTimeout(nextTicker);
    }
    return undefined;
  }, [tickers, singleTicker]);

  const startJob = async (jobType, extra = {}) => {
    setPollError(null);
    try {
      await PortfolioService.startTraining({ job_type: jobType, preset, ...extra });
      await pollStatus();
    } catch (err) {
      setPollError(err.response?.data?.detail || err.message);
    }
  };

  const running = job?.status === 'running';
  const progress = job?.progress || {};
  const pct = progress.total > 0 ? Math.round((progress.current / progress.total) * 100) : 0;

  return (
    <div className="space-y-6 pb-12 animate-in fade-in duration-500">
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 bg-violet-700 text-[#ffffff] rounded-2xl flex items-center justify-center shadow-lg shadow-violet-600/20">
          <RefreshCw className={`w-7 h-7 text-[#ffffff] ${running ? 'animate-spin' : ''}`} />
        </div>
        <div>
          <h1 className="text-3xl font-black tracking-tighter">Model Training</h1>
          <p className="text-slate-600 font-medium text-sm">
            Retrain the supported ML models on fresh historical data. MarketMind produces production BUY/HOLD/SELL signals; portfolio PPO allocation is disabled.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
        <div className="p-4 rounded-2xl bg-emerald-500/5 border border-emerald-500/20">
          <p className="text-emerald-700 font-bold text-xs uppercase mb-1">Per-ticker ready</p>
          <p className="text-2xl font-black">{readySymbols.length}</p>
        </div>
        <div className="p-4 rounded-2xl bg-violet-500/5 border border-violet-500/20">
          <p className="text-violet-700 font-bold text-xs uppercase mb-1">Universal hybrid</p>
          <p className="text-2xl font-black">{universalReady ? 'Ready' : 'Missing'}</p>
        </div>
        {summary && (
          <div className="p-4 rounded-2xl bg-indigo-500/5 border border-indigo-500/20">
            <p className="text-indigo-700 font-bold text-xs uppercase mb-1">Universe</p>
            <p className="text-sm text-slate-900">
              US {summary.us_ready}/{summary.us_total} · India {summary.india_ready}/{summary.india_total}
            </p>
          </div>
        )}
      </div>

      <div className="p-5 rounded-2xl bg-white border border-slate-200">
        <p className="text-xs font-bold text-slate-600 uppercase tracking-wider mb-3">Training preset</p>
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((p) => (
            <button
              key={p.id}
              type="button"
              disabled={running}
              onClick={() => setPreset(p.id)}
              className={`px-4 py-2 rounded-xl text-sm font-bold border transition-all ${
                preset === p.id
                  ? 'bg-indigo-700 text-[#ffffff] border-indigo-500 '
                  : 'bg-slate-100 border-slate-200 text-slate-600 hover:border-slate-200'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
        <p className="text-xs text-slate-600 mt-2">{PRESETS.find((p) => p.id === preset)?.hint}</p>
      </div>

      {pollError && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-700 text-sm">{pollError}</div>
      )}

      {job && job.status !== 'idle' && (
        <div className="p-5 rounded-2xl bg-slate-100 border border-slate-200">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
              Job: {job.job_type} · {job.preset} · {job.status}
            </span>
            {running && <Loader2 className="w-4 h-4 animate-spin text-indigo-700" />}
          </div>
          {progress.total > 0 && (
            <div className="mb-2">
              <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                <div className="h-full bg-indigo-500 transition-all" style={{ width: `${pct}%` }} />
              </div>
              <p className="text-xs text-slate-600 mt-1">
                {progress.current} / {progress.total}
                {progress.current_ticker ? ` · ${progress.current_ticker}` : ''}
              </p>
            </div>
          )}
          <p className="text-sm text-slate-600">{progress.message}</p>
          {job.error && <p className="text-sm text-rose-700 mt-2">{job.error}</p>}
          {job.results && Object.keys(job.results).length > 0 && (
            <div className="mt-4 max-h-40 overflow-y-auto custom-scrollbar space-y-1">
              {Object.entries(job.results).map(([sym, status]) => (
                <div key={sym} className="flex items-center gap-2 text-xs font-mono">
                  {status === 'OK' ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700 shrink-0" />
                  ) : (
                    <XCircle className="w-3.5 h-3.5 text-rose-700 shrink-0" />
                  )}
                  <span className="text-slate-900">{sym}</span>
                  <span className="text-slate-600 truncate">{status}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="p-5 rounded-2xl bg-white border border-slate-200 space-y-3">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-indigo-700" />
            <h3 className="font-bold text-sm">Retrain one symbol</h3>
          </div>
          <p className="text-xs text-slate-600">Train the supported per-ticker ML pipeline: LSTM + RF + HMM. MarketMind signals are served from the pooled production artifact.</p>
          <input
            type="text"
            value={singleTicker}
            onChange={(e) => setSingleTicker(e.target.value.toUpperCase())}
            disabled={running}
            className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm uppercase font-mono"
            placeholder="AAPL"
          />
          <button
            type="button"
            disabled={running || !singleTicker.trim()}
            onClick={() => startJob('ticker', { ticker: singleTicker.trim() })}
            className="w-full py-2.5 bg-indigo-700 text-[#ffffff] hover:bg-indigo-800 disabled:opacity-40 rounded-xl text-sm font-bold flex items-center justify-center gap-2"
          >
            <Play className="w-4 h-4" /> Retrain {singleTicker || 'symbol'}
          </button>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-200 space-y-3">
          <div className="flex items-center gap-2">
            <List className="w-4 h-4 text-sky-700" />
            <h3 className="font-bold text-sm">Retrain watchlist</h3>
          </div>
          <p className="text-xs text-slate-600">
            {tickers.length > 0
              ? `Symbols: ${tickers.join(', ')}`
              : 'Add symbols to your watchlist first.'}
          </p>
          <button
            type="button"
            disabled={running || tickers.length === 0}
            onClick={() => startJob('portfolio', { tickers })}
            className="w-full py-2.5 bg-sky-700 text-[#ffffff] hover:bg-sky-800 disabled:opacity-40 rounded-xl text-sm font-bold flex items-center justify-center gap-2"
          >
            <Play className="w-4 h-4" /> Retrain watchlist ({tickers.length})
          </button>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-200 space-y-3">
          <div className="flex items-center gap-2">
            <Globe className="w-4 h-4 text-violet-700" />
            <h3 className="font-bold text-sm">Retrain universal hybrid</h3>
          </div>
          <p className="text-xs text-slate-600">Shared models for any ticker without per-ticker files (~5–10 min).</p>
          <button
            type="button"
            disabled={running}
            onClick={() => startJob('universal')}
            className="w-full py-2.5 bg-violet-700 text-[#ffffff] hover:bg-violet-800 disabled:opacity-40 rounded-xl text-sm font-bold flex items-center justify-center gap-2"
          >
            <Play className="w-4 h-4" /> Retrain universal
          </button>
        </div>

        <div className="p-5 rounded-2xl bg-amber-500/5 border border-amber-500/20 space-y-3 lg:col-span-2">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-amber-700" />
            <h3 className="font-bold text-sm text-amber-700">Portfolio allocation PPO disabled</h3>
          </div>
          <p className="text-xs text-slate-600">
            PPO is experimental and is not used for production recommendations, weights, or trade execution. Use MarketMind signals and the rule-based decision options instead.
          </p>
          <div className="text-[11px] text-amber-700 font-semibold uppercase tracking-wider">Status: experimental · disabled</div>
        </div>

        <div className="p-5 rounded-2xl bg-amber-500/5 border border-amber-500/20 space-y-3">
          <h3 className="font-bold text-sm text-amber-700">Retrain full universe (100)</h3>
          <p className="text-xs text-slate-600">
            All US + India tickers, then universal. Quick preset ~2–4 hours; run when the machine is idle.
          </p>
          <button
            type="button"
            disabled={running}
            onClick={() => {
              if (window.confirm('This will retrain ~100 symbols and may take hours. Continue?')) {
                startJob('universe');
              }
            }}
            className="w-full py-2.5 bg-amber-700 text-[#ffffff] hover:bg-amber-800 disabled:opacity-40 rounded-xl text-sm font-bold flex items-center justify-center gap-2"
          >
            <Play className="w-4 h-4" /> Retrain all 100 + universal
          </button>
        </div>
      </div>
    </div>
  );
};

export default ModelTrainingView;

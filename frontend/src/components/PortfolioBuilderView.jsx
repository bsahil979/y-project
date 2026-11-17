import React, { useState, useMemo } from 'react';
import {
  Search, Plus, Check, X, Zap, ArrowRight, Loader2, AlertCircle, Brain, Radio
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useTrainedUniverse } from '../contexts/TrainedUniverseContext';
import { normalizeTickerSymbol } from '../utils/tickerUtils';

const PortfolioBuilderView = ({ tickers, setTickers }) => {
  const [activeRegion, setActiveRegion] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [liveTickerInput, setLiveTickerInput] = useState('');
  const navigate = useNavigate();
  const { universeAll, loading, error, summary, refresh, isReady, canRunMl, universalReady, readySymbols } = useTrainedUniverse();

  const toggleAsset = (symbol) => {
    const sym = symbol.toUpperCase().trim();
    if (tickers.includes(sym)) {
      setTickers(tickers.filter((t) => t !== sym));
    } else {
      setTickers([...tickers, sym]);
    }
  };

  const addLiveTicker = () => {
    const raw = liveTickerInput.toUpperCase().trim();
    if (!raw) return;
    const sym = normalizeTickerSymbol(raw, {
      readySymbols,
      universeSymbols: universeAll.map((a) => a.symbol),
    });
    if (tickers.includes(sym)) {
      setLiveTickerInput('');
      return;
    }
    setTickers([...tickers, sym]);
    setLiveTickerInput('');
  };

  /** Full curated universe — not only symbols with on-disk models (fresh installs had an empty list before). */
  const filteredUniverse = useMemo(() => {
    return universeAll.filter((asset) => {
      const matchesRegion = activeRegion === 'All' || asset.region === activeRegion;
      const q = searchQuery.toLowerCase();
      const matchesSearch = !q ||
        asset.symbol.toLowerCase().includes(q) ||
        asset.name.toLowerCase().includes(q);
      return matchesRegion && matchesSearch;
    });
  }, [universeAll, activeRegion, searchQuery]);

  const portfolioMl = tickers.filter((t) => isReady(t));
  const portfolioHybrid = tickers.filter((t) => !isReady(t) && canRunMl(t));
  const portfolioLive = tickers.filter((t) => !canRunMl(t));

  const regionCounts = useMemo(() => ({
    All: universeAll.length,
    US: universeAll.filter((a) => a.region === 'US').length,
    India: universeAll.filter((a) => a.region === 'India').length,
  }), [universeAll]);

  return (
    <div className="grid grid-cols-12 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="col-span-12 rounded-[30px] border border-indigo-500/20 bg-gradient-to-r from-indigo-500/10 via-white to-slate-50 p-8 shadow-2xl shadow-indigo-950/20 relative overflow-hidden">
        <div className="absolute -right-10 top-0 h-52 w-52 rounded-full bg-indigo-500/20 blur-[100px]" />
        <div className="absolute left-1/3 top-10 h-40 w-40 rounded-full bg-cyan-500/10 blur-[80px]" />
        <div className="relative z-10 max-w-3xl">
          <span className="mb-4 inline-flex items-center gap-1.5 rounded-full border border-indigo-400/30 bg-indigo-500/10 px-3 py-1 text-xs font-bold uppercase tracking-widest text-indigo-700">
            <Zap className="h-3 w-3" /> Watchlist analysis
          </span>
          <h2 className="mb-2 text-3xl font-black tracking-tight text-slate-900">Discover investments</h2>
          <p className="text-sm leading-relaxed text-slate-900 font-medium">
            <strong className="text-emerald-700">Saved model artifacts ({readySymbols.length})</strong> — availability does not establish forecast accuracy.
            <br />
            <strong className="text-violet-700">Hybrid</strong>
            {universalReady ? ' — universal model artifacts are available for additional symbols.' : ' — universal model artifacts are unavailable.'}
            <br />
            <strong className="text-sky-700">Other symbols</strong> — market data and model estimates depend on provider and model availability.
            {summary && (
              <span className="mt-2 block text-indigo-700">
                Saved models: {summary.us_ready}/{summary.us_total} US · {summary.india_ready}/{summary.india_total} India
              </span>
            )}
          </p>
        </div>
      </div>

      <div className="col-span-12 lg:col-span-8">
        <div className="mb-6 rounded-[26px] border border-sky-500/20 bg-sky-500/5 p-5">
          <div className="mb-2 flex items-center gap-2">
            <Radio className="h-4 w-4 text-sky-700" />
            <h3 className="text-sm font-bold uppercase tracking-wider text-sky-700">Add any symbol — live analysis</h3>
          </div>
          <p className="mb-4 text-xs text-slate-600">
            US tickers like <span className="font-mono text-slate-900">WMT</span> or India like <span className="font-mono text-slate-900">INFY.NS</span>.
            {universalReady
              ? ' Hybrid ML support is available with universal models.'
              : ' Sentiment and fundamentals depend on available provider data.'}
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              value={liveTickerInput}
              onChange={(e) => setLiveTickerInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addLiveTicker()}
              placeholder="Enter any ticker..."
              className="flex-1 rounded-xl border border-slate-200 bg-slate-100 px-4 py-2.5 text-sm uppercase text-slate-900 outline-none transition focus:border-sky-400/40"
            />
            <button
              type="button"
              onClick={addLiveTicker}
              className="flex items-center gap-2 rounded-xl bg-sky-700 text-[#ffffff] px-5 py-2.5 text-xs font-bold  transition hover:bg-sky-800"
            >
              <Plus className="h-4 w-4" /> Add live
            </button>
          </div>
        </div>

        <div className="mb-3 flex items-center gap-2">
          <Brain className="h-4 w-4 text-emerald-700" />
          <h3 className="text-sm font-bold uppercase tracking-wider text-emerald-700">
            Curated universe ({universeAll.length} symbols · {readySymbols.length} with saved models)
          </h3>
        </div>
        <p className="mb-4 text-xs text-slate-600">
          Pick any symbol below. A saved model label means local files exist; it does not imply evaluated predictive quality.
        </p>

        <div className="mb-4 flex flex-col items-center justify-between gap-4 rounded-[24px] border border-slate-200 bg-slate-100 p-4 shadow-xl md:flex-row">
          <div className="relative w-full md:w-72">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-600" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search symbols..."
              className="w-full rounded-xl border border-slate-200 bg-slate-100 pl-9 pr-4 py-2.5 text-xs text-slate-900 placeholder-slate-500 outline-none transition focus:border-indigo-500/50"
            />
          </div>
          <div className="flex flex-wrap gap-1">
            {['All', 'US', 'India'].map((region) => (
              <button
                key={region}
                type="button"
                onClick={() => setActiveRegion(region)}
                className={`rounded-xl px-3 py-1.5 text-xs font-bold transition-all ${
                  activeRegion === region
                    ? 'bg-indigo-700 text-[#ffffff] '
                    : 'text-slate-900 hover:bg-white/5'
                }`}
              >
                {region} ({regionCounts[region] ?? 0})
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="flex h-40 items-center justify-center gap-3 rounded-[24px] border border-slate-200 bg-slate-100 text-slate-900">
            <Loader2 className="h-6 w-6 animate-spin text-indigo-700" />
            <span className="text-sm">Loading trained symbols...</span>
          </div>
        ) : error ? (
          <div className="rounded-[24px] border border-rose-500/20 bg-rose-500/5 p-8 text-center">
            <AlertCircle className="mx-auto mb-3 h-10 w-10 text-rose-700" />
            <p className="mb-4 text-sm text-rose-700">{error}</p>
            <button type="button" onClick={refresh} className="rounded-xl bg-indigo-700 text-[#ffffff] px-4 py-2 text-xs font-bold ">
              Retry
            </button>
          </div>
        ) : filteredUniverse.length === 0 ? (
          <div className="rounded-[24px] border border-slate-200 bg-slate-100 p-8 text-center text-sm text-slate-600">
            {universeAll.length === 0
              ? 'No universe data. Is the analytics API running on port 8000?'
              : 'No symbols match your filters.'}
          </div>
        ) : (
          <div className="grid max-h-[420px] grid-cols-1 gap-3 overflow-y-auto pr-1 md:grid-cols-2 custom-scrollbar">
            {filteredUniverse.map((asset) => {
              const isSelected = tickers.includes(asset.symbol);
              const icon = asset.region === 'India' ? '🇮🇳' : '🇺🇸';
              return (
                <button
                  key={asset.symbol}
                  type="button"
                  onClick={() => toggleAsset(asset.symbol)}
                  className={`rounded-[22px] border p-4 text-left transition-all ${
                    isSelected
                      ? 'border-emerald-500/40 bg-emerald-500/10 shadow-lg shadow-emerald-950/20'
                      : 'border-slate-200 bg-slate-100 hover:border-indigo-500/30 hover:bg-slate-100'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xl">{icon}</span>
                      <div>
                        <p className="text-sm font-bold text-slate-900">{asset.symbol}</p>
                        <p className="max-w-[140px] truncate text-[10px] text-slate-600">{asset.name}</p>
                      </div>
                    </div>
                    {isSelected ? (
                      <Check className="h-4 w-4 text-emerald-700" />
                    ) : (
                      <Plus className="h-4 w-4 text-slate-600" />
                    )}
                  </div>
                  {asset.trained ? (
                    <span className="mt-2 inline-block rounded-full bg-emerald-500/10 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-emerald-700">
                      Saved model files
                    </span>
                  ) : (
                    <span className="mt-2 inline-block rounded-full bg-slate-100 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-slate-900">
                      Model files unavailable
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>

      <div className="col-span-12 lg:col-span-4">
        <div className="sticky top-8 rounded-[28px] border border-slate-200 bg-slate-100 p-6 shadow-xl shadow-slate-950/30 backdrop-blur-xl">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-900">Your watchlist</h3>
            <span className="rounded-full bg-indigo-500/10 px-2 py-0.5 text-[10px] font-bold text-indigo-700">
              {tickers.length}
            </span>
          </div>

          {portfolioMl.length > 0 && (
            <div className="mb-4">
              <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-emerald-700">Saved model files ({portfolioMl.length})</p>
              <div className="space-y-1.5">
                {portfolioMl.map((sym) => (
                  <div key={sym} className="flex items-center justify-between rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-2">
                    <span className="font-mono text-xs font-bold text-slate-900">{sym}</span>
                    <button type="button" onClick={() => toggleAsset(sym)} className="text-slate-600 hover:text-rose-700">
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {portfolioHybrid.length > 0 && (
            <div className="mb-4">
              <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-violet-700">Hybrid ML ({portfolioHybrid.length})</p>
              <div className="space-y-1.5">
                {portfolioHybrid.map((sym) => (
                  <div key={sym} className="flex items-center justify-between rounded-xl border border-violet-500/20 bg-violet-500/5 p-2">
                    <span className="font-mono text-xs font-bold text-slate-900">{sym}</span>
                    <button type="button" onClick={() => toggleAsset(sym)} className="text-slate-600 hover:text-rose-700">
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {portfolioLive.length > 0 && (
            <div className="mb-4">
              <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-sky-700">Live-only ({portfolioLive.length})</p>
              <div className="space-y-1.5">
                {portfolioLive.map((sym) => (
                  <div key={sym} className="flex items-center justify-between rounded-xl border border-sky-500/20 bg-sky-500/5 p-2">
                    <span className="font-mono text-xs font-bold text-slate-900">{sym}</span>
                    <button type="button" onClick={() => toggleAsset(sym)} className="text-slate-600 hover:text-rose-700">
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {tickers.length === 0 && (
            <p className="py-6 text-center text-xs text-slate-600">Add symbols to your watchlist for available analysis.</p>
          )}

          <button
            type="button"
            onClick={() => navigate('/dashboard/forecast')}
            disabled={tickers.length === 0}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-700 text-[#ffffff] py-3 text-xs font-bold  transition hover:bg-indigo-800 disabled:opacity-30"
          >
            Explore selected stocks <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default PortfolioBuilderView;

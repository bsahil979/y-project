import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { PortfolioService } from '../services/api';
import { API_BASE_URL } from '../config/api';

const TrainedUniverseContext = createContext({
  universeAll: [],
  assets: [],
  readySymbols: [],
  loading: true,
  error: null,
  summary: null,
  refresh: () => {},
  isReady: () => false,
  universalReady: false,
  canRunMl: () => false,
});

export function TrainedUniverseProvider({ children }) {
  const [universeAll, setUniverseAll] = useState([]);
  const [assets, setAssets] = useState([]);
  const [readySymbols, setReadySymbols] = useState([]);
  const [universalReady, setUniversalReady] = useState(false);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await PortfolioService.getTrainedUniverse();
      const all = data.all_assets || [...(data.us || []), ...(data.india || [])];
      setUniverseAll(all);
      setAssets(data.assets || all.filter((a) => a.trained));
      setReadySymbols(data.ready_symbols || []);
      setUniversalReady(Boolean(data.universal_ready));
      setSummary(data.summary || null);
    } catch (err) {
      console.error('Failed to load trained universe:', err);
      const detail = err.response?.data?.detail;
      const msg =
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
            ? detail.map((d) => d.msg || d).join('; ')
            : err.message || '';
      const hint =
        err.code === 'ECONNABORTED' || msg.toLowerCase().includes('timeout')
          ? 'Request timed out — is the analytics API responding? Try restarting uvicorn on port 8000.'
          : msg.includes('Network Error') || err.code === 'ERR_NETWORK'
          ? `Cannot reach ${API_BASE_URL} — start the analytics API.`
          : msg || 'Analytics API unavailable';
      setError(hint);
      setUniverseAll([]);
      setAssets([]);
      setReadySymbols([]);
      setUniversalReady(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 60000);
    return () => clearInterval(interval);
  }, [refresh]);

  const isReady = useCallback(
    (symbol) => {
      const sym = String(symbol || '').toUpperCase();
      return readySymbols.some((s) => s.toUpperCase() === sym);
    },
    [readySymbols]
  );

  const canRunMl = useCallback(
    (symbol) => isReady(symbol) || universalReady,
    [isReady, universalReady]
  );

  return (
    <TrainedUniverseContext.Provider
      value={{ universeAll, assets, readySymbols, universalReady, loading, error, summary, refresh, isReady, canRunMl }}
    >
      {children}
    </TrainedUniverseContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useTrainedUniverse() {
  return useContext(TrainedUniverseContext);
}

import axios from 'axios';
import { normalizeInvestorProfile } from './investorProfile.js';
import { API_BASE_URL, API_TIMEOUT, CHAT_TIMEOUT, ENDPOINTS } from '../config/api';

const analyticsApi = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: API_TIMEOUT,
});

let connectionStatus = 'unknown';
let listeners = new Set();

export const ConnectionService = {
  getStatus: () => connectionStatus,
  subscribe: (cb) => {
    listeners.add(cb);
    return () => listeners.delete(cb);
  },
  _setStatus: (status) => {
    if (status !== connectionStatus) {
      connectionStatus = status;
      listeners.forEach((cb) => cb(status));
    }
  },
};

const ANALYSIS_CACHE_TTL_MS = 15 * 60 * 1000;

const getCacheKey = (prefix, payload) => {
  try {
    return `spa_cache_${prefix}_${JSON.stringify(payload)}`;
  } catch {
    return null;
  }
};

const getFromSessionCache = (key) => {
  if (!key) return null;
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return null;
    const { data, timestamp } = JSON.parse(raw);
    if (Date.now() - timestamp < ANALYSIS_CACHE_TTL_MS) {
      return data;
    }
    sessionStorage.removeItem(key);
    return null;
  } catch {
    return null;
  }
};

const setToSessionCache = (key, data) => {
  if (!key || !data) return;
  try {
    sessionStorage.setItem(key, JSON.stringify({ data, timestamp: Date.now() }));
  } catch {
    // sessionStorage full or unavailable
  }
};

export const PortfolioService = {
  getQuotes: async (tickers) => {
    const symbols = [...new Set((tickers || []).map((ticker) => String(ticker).toUpperCase().trim()).filter(Boolean))];
    if (symbols.length === 0) return { quotes: {} };
    const res = await analyticsApi.post(ENDPOINTS.quotes, { tickers: symbols }, { timeout: 30000 });
    return res.data;
  },

  getAnalysis: async (tickers, weights, forceRefresh = false, portfolioValue = 100000) => {
    const payload = {
      tickers,
      weights: weights || tickers.map(() => 1 / tickers.length),
      portfolio_value: portfolioValue,
      start: '2020-01-01',
      end: new Date().toISOString().split('T')[0],
    };

    const cacheKey = getCacheKey('analyze', payload);
    if (!forceRefresh) {
      const cached = getFromSessionCache(cacheKey);
      if (cached) return cached;
    }

    try {
      const res = await analyticsApi.post(ENDPOINTS.analyze, payload, { timeout: 120000 });
      ConnectionService._setStatus('connected');
      if (res.data) setToSessionCache(cacheKey, res.data);
      return res.data;
    } catch (err) {
      if (err?.code === 'ECONNABORTED' || String(err?.message || '').toLowerCase().includes('timeout')) {
        const retryRes = await analyticsApi.post(ENDPOINTS.analyze, payload, { timeout: 180000 });
        ConnectionService._setStatus('connected');
        if (retryRes.data) setToSessionCache(cacheKey, retryRes.data);
        return retryRes.data;
      }
      ConnectionService._setStatus('disconnected');
      throw err;
    }
  },

  getForecast: async (ticker, horizon = 30, refresh = false) => {
    const sym = (ticker || '').toUpperCase().trim();
    const res = await analyticsApi.get(ENDPOINTS.forecast(sym), {
      params: { horizon, refresh: refresh ? 1 : 0 },
      timeout: 120000,
    });
    return res.data;
  },

  getMarketRegime: async () => {
    const res = await analyticsApi.get(ENDPOINTS.regime);
    return res.data;
  },

  getSentiment: async (ticker) => {
    const res = await analyticsApi.get(ENDPOINTS.sentiment(ticker));
    return res.data;
  },

  getFundamentals: async (ticker) => {
    const res = await analyticsApi.get(ENDPOINTS.fundamentals(ticker));
    return res.data;
  },

  getTradingDecision: async (ticker) => {
    const res = await analyticsApi.get(ENDPOINTS.tradingDecision, {
      params: { ticker },
    });
    return res.data;
  },

  getTrainedUniverse: async () => {
    const res = await analyticsApi.get(ENDPOINTS.modelsUniverse);
    return res.data;
  },

  getTrainingStatus: async () => {
    const res = await analyticsApi.get(ENDPOINTS.trainingStatus);
    return res.data;
  },

  startTraining: async ({ job_type, preset = 'quick', ticker, tickers }) => {
    const res = await analyticsApi.post(ENDPOINTS.trainingStart, {
      job_type,
      preset,
      ticker: ticker || null,
      tickers: tickers || null,
    });
    return res.data;
  },

  checkHealth: async () => {
    try {
      const res = await analyticsApi.get(ENDPOINTS.modelsStatus, { timeout: 10000 });
      ConnectionService._setStatus('connected');
      return { ok: true, data: res.data };
    } catch (err) {
      ConnectionService._setStatus('disconnected');
      return { ok: false, error: err.message };
    }
  },

  getPortfolioAnalysis: async (payload, forceRefresh = false) => {
    payload = { ...payload, ...normalizeInvestorProfile(payload) };
    const cacheKey = getCacheKey('portfolioAnalyze', payload);
    if (!forceRefresh) {
      const cached = getFromSessionCache(cacheKey);
      if (cached) return { ...cached, cached: true };
    }
    const requestPayload = forceRefresh ? { ...payload, force_refresh: true } : payload;
    const res = await analyticsApi.post(ENDPOINTS.portfolioAnalyze, requestPayload, { timeout: 180000 });
    if (res.data) setToSessionCache(cacheKey, res.data);
    return res.data;
  },

  getCachedPortfolioAnalysis: (payload) => {
    payload = { ...payload, ...normalizeInvestorProfile(payload) };
    const cacheKey = getCacheKey('portfolioAnalyze', payload);
    return getFromSessionCache(cacheKey);
  },

  getBenchmarkComparison: async (payload) => {
    const res = await analyticsApi.post(ENDPOINTS.portfolioBenchmark, payload, { timeout: 120000 });
    return res.data;
  },

  optimizePortfolio: async (payload) => {
    const res = await analyticsApi.post('/portfolio/optimize',
      { ...payload, ...normalizeInvestorProfile(payload) }, { timeout: 120000 });
    return res.data;
  },

  getBenchmarks: async () => {
    const res = await analyticsApi.get(ENDPOINTS.benchmarks);
    return res.data;
  },

  getPortfolioAttribution: async (payload) => {
    const res = await analyticsApi.post(ENDPOINTS.portfolioAttribution, payload, { timeout: 120000 });
    return res.data;
  },

  getPortfolioRiskBudget: async (payload) => {
    const res = await analyticsApi.post(ENDPOINTS.portfolioRiskBudget, payload, { timeout: 120000 });
    return res.data;
  },

  analyzeGoal: async (payload) => {
    const res = await analyticsApi.post(ENDPOINTS.portfolioGoal, payload, { timeout: 180000 });
    return res.data;
  },

  getRecommendations: async (payload) => {
    const res = await analyticsApi.post(ENDPOINTS.recommendations, payload, { timeout: 180000 });
    return res.data;
  },

  chatWithTools: async (payload) => {
    const res = await analyticsApi.post(ENDPOINTS.chatTools, payload, { timeout: 180000 });
    return res.data;
  },

  getPpoStatus: async () => {
    const res = await analyticsApi.get(ENDPOINTS.ppoStatus);
    return res.data;
  },
};

export const ChatService = {
  getAdvisorStatus: async () => {
    const res = await analyticsApi.get(ENDPOINTS.advisorStatus);
    return res.data;
  },

  sendMessage: async (payload) => {
    const res = await analyticsApi.post(ENDPOINTS.chat, payload, { timeout: CHAT_TIMEOUT });
    return res.data;
  },

  sendMessageStream: async (payload, onChunk) => {
    const res = await fetch(`${API_BASE_URL}${ENDPOINTS.chatStream}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`Advisor request failed (${res.status}).`);
    const reader = res.body?.getReader();
    if (!reader) throw new Error('Streaming not supported in this browser.');

    const decoder = new TextDecoder();
    let buffer = '';
    let completed = false;

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split('\n\n');
      buffer = parts.pop() || '';

      for (const part of parts) {
        const lines = part.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.content) onChunk(data.content);
              if (data.done || data.error) {
                if (!completed) onChunk(null, data);
                completed = true;
              }
            } catch (e) {
              console.error('SSE parse error:', e);
            }
          }
        }
      }
    }
    if (!completed) throw new Error('Advisor stream ended before completing the response.');
  },

  evaluateTicker: async (payload) => {
    const res = await analyticsApi.post(ENDPOINTS.evaluateTicker, payload, { timeout: 60000 });
    return res.data;
  },

  getAdvancedLab: async (payload) => {
    try {
      const res = await analyticsApi.post(ENDPOINTS.advancedLab, payload, { timeout: 60000 });
      return res.data;
    } catch (err) {
      const direct = await fetch('http://localhost:8000/portfolio/advanced-lab', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!direct.ok) throw err;
      return await direct.json();
    }
  },
};

export default analyticsApi;

export async function getEvaluationSummary() {
  const response = await analyticsApi.get("/research/evaluation-summary");
  return response.data;
}

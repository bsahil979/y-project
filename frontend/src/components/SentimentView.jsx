import React, { useState, useEffect, useCallback, useRef } from 'react';
import { 
  TrendingUp, TrendingDown, Minus, Loader2, AlertTriangle,
  Newspaper, BarChart3, ExternalLink, ArrowRight, Zap
} from 'lucide-react';
import { 
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid
} from 'recharts';
import { PortfolioService } from '../services/api';

const COLORS = { positive: '#10b981', negative: '#f43f5e', neutral: '#6b7280' };

const SentimentView = ({ tickers = [] }) => {
  const [sentimentData, setSentimentData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [ticker, setTicker] = useState(tickers[0] || 'AAPL');
  const [inputTicker, setInputTicker] = useState(tickers[0] || 'AAPL');

  const requestId = useRef(0);

  const fetchSentiment = useCallback(async (sym) => {
    if (!sym) return;
    const id = ++requestId.current;
    try {
      setLoading(true);
      setSentimentData(null);
      setError(null);
      const res = await PortfolioService.getSentiment(sym);
      if (id === requestId.current) setSentimentData(res);
    } catch (err) {
      console.error('Sentiment fetch failed:', err);
      if (id === requestId.current) setError(err.response?.data?.detail || err.message);
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!ticker) return;
    fetchSentiment(ticker);
  }, [ticker, fetchSentiment]);

  const handleAnalyze = () => {
    const symbol = inputTicker.trim().toUpperCase();
    if (!symbol) return;
    setInputTicker(symbol);
    if (symbol === ticker) fetchSentiment(symbol);
    else setTicker(symbol);
  };

  const getSentimentIcon = (sentiment) => {
    if (sentiment === 'Positive') return <TrendingUp className="w-4 h-4 text-emerald-700" />;
    if (sentiment === 'Negative') return <TrendingDown className="w-4 h-4 text-rose-700" />;
    return <Minus className="w-4 h-4 text-slate-600" />;
  };

  const getScoreColor = (score) => {
    if (score >= 0.05) return 'text-emerald-700';
    if (score <= -0.05) return 'text-rose-700';
    return 'text-slate-600';
  };

  const getOverallColor = (sentiment) => {
    if (sentiment?.includes('Bullish')) return 'from-emerald-100 to-teal-50';
    if (sentiment?.includes('Bearish')) return 'from-rose-100 to-pink-50';
    return 'from-slate-100 to-slate-50';
  };

  return (
    <div className="grid grid-cols-12 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      
      {/* Header */}
      <div className="col-span-12 flex items-center justify-between bg-white backdrop-blur-xl border border-slate-200 p-6 rounded-3xl">
        <div className="flex gap-8">
          <div className="flex flex-col">
            <span className="text-xs text-slate-600 uppercase font-bold tracking-widest mb-1">Engine</span>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
              <span className="text-sm font-bold text-slate-900">{sentimentData?.models_used?.join(' + ') || 'News sentiment (NLP)'}</span>
            </div>
          </div>
          <div className="flex flex-col border-l border-slate-200 pl-8">
            <span className="text-xs text-slate-600 uppercase font-bold tracking-widest mb-1">Data Sources</span>
            <span className="text-sm font-bold text-slate-900">Yahoo Finance + Google News</span>
          </div>
          <div className="flex flex-col border-l border-slate-200 pl-8">
            <span className="text-xs text-slate-600 uppercase font-bold tracking-widest mb-1">Ticker</span>
            <span className="text-sm font-bold text-indigo-700">{ticker}</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="text"
            value={inputTicker}
            onChange={(e) => setInputTicker(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
            className="bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs w-32 text-slate-900 uppercase focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
            placeholder="e.g. NVDA or TCS.NS"
          />
          <button 
            onClick={handleAnalyze}
            className="px-4 py-2 bg-indigo-700 text-[#ffffff] hover:bg-indigo-800  rounded-xl text-xs font-bold transition-all flex items-center gap-2"
          >
            <Zap className="w-3 h-3" /> Analyze
          </button>
        </div>
      </div>

      <p className="col-span-12 text-xs text-slate-600 -mt-2 px-1">
        Works for any symbol (US or India e.g. <span className="text-indigo-700 font-mono">RELIANCE.NS</span>) — no ML training required.
        {tickers.length > 0 && (
          <span className="ml-2">
            Portfolio:
            {tickers.map(sym => (
              <button
                key={sym}
                type="button"
                onClick={() => { setInputTicker(sym); setTicker(sym); }}
                className={`ml-1.5 px-2 py-0.5 rounded-lg font-mono text-[10px] font-bold ${ticker === sym ? 'bg-indigo-700 text-[#ffffff] ' : 'bg-slate-100 text-slate-600 hover:text-slate-900'}`}
              >
                {sym}
              </button>
            ))}
          </span>
        )}
      </p>

      {loading ? (
        <div className="col-span-12 flex flex-col items-center justify-center h-96 gap-4">
          <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
          <p className="text-slate-600 text-sm">Analyzing sentiment for {ticker}...</p>
        </div>
      ) : error ? (
        <div className="col-span-12 flex flex-col items-center justify-center h-96 gap-4">
          <AlertTriangle className="w-10 h-10 text-amber-700" />
          <p className="text-slate-600 text-sm">Sentiment error: {error}</p>
        </div>
      ) : sentimentData?.status === 'no_news' ? (
        <div className="col-span-12 bg-white border border-slate-200 rounded-3xl p-8">
          <h2 className="font-bold">No recent news for {sentimentData.ticker}</h2>
          <p className="text-slate-600 mt-2">{sentimentData.message}</p>
        </div>
      ) : sentimentData && (
        <>
          {/* Overall Sentiment Card */}
          <div className="col-span-4">
            <div className={`bg-gradient-to-br ${getOverallColor(sentimentData.overall_sentiment)} rounded-3xl p-8 shadow-xl relative overflow-hidden group h-full`}>
              <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-10 -mt-10 blur-3xl group-hover:scale-110 transition-transform duration-700"></div>
              <p className="text-slate-900 text-sm font-medium mb-1">Overall Sentiment</p>
              <h2 className="text-3xl font-bold text-slate-900 tracking-tight mb-2">{sentimentData.overall_sentiment}</h2>
              <div className="mt-2 flex items-center gap-2 text-slate-900 bg-white/10 w-fit px-3 py-1.5 rounded-full text-xs font-bold backdrop-blur-md uppercase tracking-wide">
                <BarChart3 className="w-3 h-3" />
                Score: {sentimentData.overall_score} | {(sentimentData.confidence * 100).toFixed(0)}% directional strength
              </div>
              <p className="mt-4 text-slate-900 text-xs">{sentimentData.articles_analyzed} articles from {sentimentData.sources_used?.join(' + ') || 'multiple sources'}</p>
            </div>
          </div>

          {/* Sentiment Breakdown Pie */}
          <div className="col-span-4 bg-white backdrop-blur-xl border border-slate-200 rounded-3xl p-6 shadow-xl">
            <h3 className="text-lg font-semibold mb-4">Sentiment Distribution</h3>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={[
                      { name: 'Positive', value: sentimentData.sentiment_breakdown.positive },
                      { name: 'Negative', value: sentimentData.sentiment_breakdown.negative },
                      { name: 'Neutral', value: sentimentData.sentiment_breakdown.neutral },
                    ]}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    <Cell fill={COLORS.positive} />
                    <Cell fill={COLORS.negative} />
                    <Cell fill={COLORS.neutral} />
                  </Pie>
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#ffffff', color: '#0f172a', border: '1px solid #e2e8f0', borderRadius: '12px' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex justify-center gap-6 mt-2">
              {[
                { label: 'Bullish', count: sentimentData.sentiment_breakdown.positive, color: 'bg-emerald-500' },
                { label: 'Bearish', count: sentimentData.sentiment_breakdown.negative, color: 'bg-rose-500' },
                { label: 'Neutral', count: sentimentData.sentiment_breakdown.neutral, color: 'bg-gray-500' },
              ].map(item => (
                <div key={item.label} className="flex items-center gap-2 text-xs">
                  <div className={`w-2.5 h-2.5 rounded-full ${item.color}`} />
                  <span className="text-slate-600">{item.label}: <span className="text-slate-900 font-bold">{item.count}</span></span>
                </div>
              ))}
            </div>
          </div>

          {/* Score Distribution Bar Chart */}
          <div className="col-span-4 bg-white backdrop-blur-xl border border-slate-200 rounded-3xl p-6 shadow-xl">
            <h3 className="text-lg font-semibold mb-4">Article Scores</h3>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={sentimentData.articles.map((a, i) => ({ name: `${i + 1}`, score: a.score }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                  <XAxis dataKey="name" stroke="#6b7280" fontSize={10} tickLine={false} axisLine={false} />
                  <YAxis stroke="#6b7280" fontSize={10} tickLine={false} axisLine={false} domain={[-1, 1]} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#ffffff', color: '#0f172a', border: '1px solid #e2e8f0', borderRadius: '12px' }}
                    formatter={(value) => [value.toFixed(3), 'Compound Score']}
                  />
                  <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                    {sentimentData.articles.map((a, i) => (
                      <Cell key={i} fill={a.score >= 0.05 ? COLORS.positive : a.score <= -0.05 ? COLORS.negative : COLORS.neutral} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* News Feed */}
          <div className="col-span-12 bg-white backdrop-blur-xl border border-slate-200 rounded-3xl p-6 shadow-xl">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Newspaper className="w-5 h-5 text-indigo-700" />
                News Sentiment Feed
              </h3>
              <span className="text-xs text-slate-600">{sentimentData.articles_analyzed} articles</span>
            </div>
            <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
              {sentimentData.articles.map((article, idx) => (
                <div 
                  key={idx} 
                  className="flex items-start gap-4 p-4 bg-slate-100 rounded-2xl border border-slate-200 hover:border-slate-200 transition-all group"
                >
                  <div className="mt-1 flex-shrink-0">
                    {getSentimentIcon(article.sentiment)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-900 font-medium leading-snug line-clamp-2 group-hover:text-slate-900 transition-colors">
                      {article.title}
                    </p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-slate-600">
                      <span>{article.publisher}</span>
                      <span>•</span>
                      <span>{article.published}</span>
                      {article.source && (
                        <>
                          <span>•</span>
                          <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider ${
                            article.source === 'Google News' ? 'bg-blue-500/10 text-blue-700' : 'bg-violet-500/10 text-violet-700'
                          }`}>{article.source}</span>
                        </>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-2 flex-shrink-0">
                    <span className={`text-xs font-bold px-2 py-1 rounded-lg ${
                      article.sentiment === 'Positive' ? 'text-emerald-700 bg-emerald-500/10 ring-1 ring-emerald-500/20' :
                      article.sentiment === 'Negative' ? 'text-rose-700 bg-rose-500/10 ring-1 ring-rose-500/20' :
                      'text-slate-600 bg-gray-500/10 ring-1 ring-gray-500/20'
                    }`}>
                      {article.sentiment}
                    </span>
                    <span className={`text-xs font-mono ${getScoreColor(article.score)}`}>
                      {article.score > 0 ? '+' : ''}{article.score}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default SentimentView;

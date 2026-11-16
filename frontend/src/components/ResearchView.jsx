import React from 'react';
import { Link } from 'react-router-dom';
import { 
  BarChart3, CheckCircle2, ArrowRight, Sparkles
} from 'lucide-react';

const ResearchView = ({ tickers = [] }) => {

  // Top row: feature summary cards matching actual project tech stack
  const topCards = [
    {
      title: 'VADER Sentiment Engine',
      path: '/dashboard/sentiment',
      color: 'indigo',
      description: 'Multi-source news sentiment aggregation powered by Yahoo Finance & GNews feeds. VADER NLP scoring quantifies bullish/bearish emotional intensity across each tracked instrument.',
      features: [
        'Yahoo Finance + GNews dual-source aggregation',
        'VADER NLP compound sentiment scoring',
        'Bullish vs Bearish polarity distribution',
      ],
    },
    {
      title: 'LSTM + HMM Forecaster',
      path: '/dashboard/forecast',
      color: 'emerald',
      description: 'Deep learning LSTM neural networks generate multi-day price trajectory forecasts. Hidden Markov Models detect current market regime probabilities across your portfolio.',
      features: [
        'PyTorch LSTM 2-layer price forecasting',
        'Gaussian HMM regime detection (Bull/Bear/Neutral)',
        'Monte Carlo VaR & CVaR risk quantification',
      ],
    },
    {
      title: 'RL Decision Brain',
      path: '/dashboard/trading',
      color: 'purple',
      description: 'PPO Reinforcement Learning agent trained via Stable-Baselines3 integrates RSI, MACD, ADX, volatility, and all ensemble model signals to output optimal BUY/SELL/HOLD policy actions.',
      features: [
        'PPO policy gradient agent (Stable-Baselines3)',
        'Multi-signal ensemble: LSTM + RF + HMM inputs',
        'Confidence-weighted action with memory archive',
      ],
    },
  ];

  // Bottom row: detailed named tool cards
  const bottomCards = [
    {
      emoji: '📰',
      title: 'News Sentiment Tracker',
      path: '/dashboard/sentiment',
      description: 'Real-time emotional pulse detection from financial news. Each headline is scored by VADER\'s compound algorithm and aggregated into per-ticker sentiment gauges with source attribution.',
      features: [
        'Per-article compound sentiment scores',
        'Source-attributed headline breakdowns',
        'Trending topic & keyword extraction',
      ],
    },
    {
      emoji: '📈',
      title: 'Quantitative Risk Analyzer',
      path: '/dashboard/forecast',
      description: 'Portfolio-level risk decomposition engine. Calculates annualized volatility, Value at Risk (VaR 95%), Conditional VaR, max drawdown, and outputs AI rebalancing strategy recommendations.',
      features: [
        'Annualized volatility & max drawdown per asset',
        'Monte Carlo VaR (95%) & CVaR stress testing',
        'AI-generated rebalancing strategy options',
      ],
    },
    {
      emoji: '🧠',
      title: 'Adaptive RL Policy Viewer',
      path: '/dashboard/trading',
      description: 'Inspect the Reinforcement Learning agent\'s live decision pipeline. View the multi-tier cognitive layers: Perception (RSI/MACD), Thinking (ensemble signals), Memory (trade archive), and Self-Awareness (win rate).',
      features: [
        'Live perception layer: RSI, MACD, ADX indicators',
        'Decision confidence with reasoning traces',
        'Historical memory archive & mental accuracy',
      ],
    },
  ];

  const getColorClasses = (color) => {
    const map = {
      indigo: {
        border: 'border-indigo-500/20 hover:border-indigo-500/40',
        accent: 'text-indigo-400',
        gradient: 'from-indigo-600/20 to-transparent',
        glow: 'shadow-indigo-500/5',
      },
      emerald: {
        border: 'border-emerald-500/20 hover:border-emerald-500/40',
        accent: 'text-emerald-400',
        gradient: 'from-emerald-600/20 to-transparent',
        glow: 'shadow-emerald-500/5',
      },
      purple: {
        border: 'border-purple-500/20 hover:border-purple-500/40',
        accent: 'text-purple-400',
        gradient: 'from-purple-600/20 to-transparent',
        glow: 'shadow-purple-500/5',
      },
    };
    return map[color] || map.indigo;
  };

  if (tickers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[450px] bg-[#11131a]/80 backdrop-blur-xl border border-gray-800/50 rounded-3xl p-12 text-center shadow-2xl animate-in fade-in duration-500">
        <div className="w-20 h-20 rounded-3xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-6">
          <BarChart3 className="w-10 h-10 text-indigo-400" />
        </div>
        <h3 className="text-2xl font-black tracking-tight mb-2">No Assets to Research</h3>
        <p className="text-sm text-gray-400 max-w-md mx-auto mb-6 leading-relaxed font-medium">
          Add ticker symbols to your watchlist first. Each research tool below will analyze your active portfolio instruments.
        </p>
        <Link 
          to="/dashboard/manage"
          className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition-all shadow-lg shadow-indigo-600/20 flex items-center gap-2 active:scale-95"
        >
          <span>Open Watchlist Manager</span>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="rounded-[28px] border border-white/10 bg-slate-900/60 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.45)] backdrop-blur-sm">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <span className="rounded-full border border-indigo-500/30 bg-indigo-500/10 px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.22em] text-indigo-300">
            Research Hub
          </span>
          <span className="text-xs text-slate-500">•</span>
          <span className="inline-flex items-center gap-2 text-xs font-bold text-emerald-400">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            {tickers.length} Active Instruments
          </span>
        </div>
        <p className="max-w-3xl text-sm leading-relaxed text-slate-300">
          Multi-model analysis suite integrating LSTM forecasting, HMM regime detection, VADER sentiment NLP, Random Forest classification, and PPO Reinforcement Learning agents.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        {topCards.map((card, idx) => {
          const c = getColorClasses(card.color);
          return (
            <Link
              key={idx}
              to={card.path}
              className={`group relative block overflow-hidden rounded-[26px] border bg-slate-900/60 p-6 shadow-xl shadow-slate-950/20 transition-all duration-300 hover:-translate-y-0.5 hover:border-white/20 ${c.border}`}
            >
              <div className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${c.gradient}`} />
              <div className="mb-5 flex items-start justify-between gap-3">
                <div className="inline-flex rounded-xl border border-white/10 bg-white/5 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.22em] text-slate-400">
                  Intelligence layer
                </div>
              </div>
              <p className="mb-5 min-h-[72px] text-xs leading-relaxed text-slate-400">
                {card.description}
              </p>

              <div className="space-y-2.5">
                {card.features.map((feature, fIdx) => (
                  <div key={fIdx} className="flex items-start gap-2.5">
                    <CheckCircle2 className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${c.accent}`} />
                    <span className="text-xs font-medium leading-relaxed text-slate-300">{feature}</span>
                  </div>
                ))}
              </div>
            </Link>
          );
        })}
      </div>

      <div className="flex items-center gap-4">
        <div className="h-px flex-1 bg-white/10" />
        <span className="h-2 w-2 rounded-full bg-indigo-500/60" />
        <div className="h-px flex-1 bg-white/10" />
      </div>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        {bottomCards.map((card, idx) => (
          <Link
            key={idx}
            to={card.path}
            className="group block rounded-[26px] border border-white/10 bg-slate-900/60 p-6 shadow-xl shadow-slate-950/20 transition-all duration-300 hover:-translate-y-0.5 hover:border-indigo-500/30"
          >
            <div className="mb-4 flex items-center gap-3">
              <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-xl shadow-inner shadow-slate-950/50">
                {card.emoji}
              </span>
              <h3 className="text-sm font-bold tracking-tight text-white transition-colors group-hover:text-indigo-300">
                {card.title}
              </h3>
            </div>

            <p className="mb-5 min-h-[60px] text-xs leading-relaxed text-slate-400">
              {card.description}
            </p>

            <div className="space-y-2.5">
              {card.features.map((feature, fIdx) => (
                <div key={fIdx} className="flex items-start gap-2.5">
                  <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-400" />
                  <span className="text-xs font-medium leading-relaxed text-slate-300">{feature}</span>
                </div>
              ))}
            </div>

            <div className="mt-5 flex items-center justify-between border-t border-white/10 pt-4">
              <span className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">Launch Tool</span>
              <ArrowRight className="h-4 w-4 text-slate-500 transition-all group-hover:translate-x-1 group-hover:text-indigo-300" />
            </div>
          </Link>
        ))}
      </div>

      <Link
        to="/dashboard/chat"
        className="group block rounded-[28px] border border-indigo-500/25 bg-gradient-to-r from-indigo-600/10 via-slate-900/80 to-purple-600/10 p-8 transition-all duration-300 hover:border-indigo-400/40 hover:shadow-[0_20px_50px_rgba(99,102,241,0.1)]"
      >
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-5">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-600 to-violet-500 shadow-lg shadow-indigo-600/20 transition-transform duration-300 group-hover:scale-105">
              <Sparkles className="h-7 w-7 text-white" />
            </div>
            <div>
              <h3 className="mb-1 text-base font-bold text-white transition-colors group-hover:text-indigo-300">
                AI Portfolio Advisor — Conversational Intelligence
              </h3>
              <p className="max-w-xl text-xs leading-relaxed text-slate-400">
                Ask anything about your portfolio in natural language. Get instant AI-powered insights combining outputs from the LSTM forecaster, HMM regime detector, VADER sentiment scores, and RL policy recommendations.
              </p>
            </div>
          </div>
          <ArrowRight className="h-5 w-5 shrink-0 text-slate-500 transition-all group-hover:translate-x-1 group-hover:text-indigo-300" />
        </div>
      </Link>
    </div>
  );
};

export default ResearchView;

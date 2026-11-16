import { profileForAnalysis } from '../services/investorProfile.js';
import { useLocation } from 'react-router-dom';
import React, { useState, useRef, useEffect } from 'react';
import {
  MessageSquare,
  Send,
  Bot,
  User as UserIcon,
  Sparkles,
  Info,
  Loader2,
  Zap,
  Globe,
  Brain,
  TrendingUp,
} from 'lucide-react';
import { PortfolioService, ChatService } from '../services/api';
import { advisorPortfolioContext } from '../services/portfolioSnapshot';
import { holdingAnswer } from '../services/advisorHolding';
import { conversationReply } from '../services/advisorConversation';
import ReactMarkdown from 'react-markdown';
import { chatHistoryKey, readChatHistory, writeChatHistory, readChatSessions, sessionHistoryKey, createChatSession } from '../services/advisorHistory';

const STOPWORDS = new Set([
  'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'WAS', 'ONE', 'OUR',
  'OUT', 'DAY', 'GET', 'HAS', 'HIM', 'HIS', 'HOW', 'ITS', 'MAY', 'NEW', 'NOW', 'OLD',
  'SEE', 'TWO', 'WHO', 'DID', 'LET', 'PUT', 'SAY', 'SHE', 'TOO', 'USE', 'ANY', 'RISK',
  'GIVE', 'WHAT', 'WHEN', 'WITH', 'FROM', 'THAT', 'THIS', 'YOUR', 'HAVE', 'EACH', 'MANY',
  'SOME', 'INTO', 'MORE', 'VERY', 'AFTER', 'OVER', 'ALSO', 'BACK', 'ONLY', 'COME', 'EVEN',
  'WANT', 'WELL', 'MUCH', 'PREDICT', 'FORECAST', 'PRICE', 'NEWS',
]);

/** Prefer symbols on the user's watchlist, then any plausible ticker token. */
function extractTicker(userMsg, watchlist) {
  const mentioned = new Set((userMsg.toUpperCase().match(/[A-Z][A-Z0-9.-]*/g) || []));
  const ownedMatch = (watchlist || []).find((ticker) => mentioned.has(ticker.toUpperCase()) || mentioned.has(ticker.toUpperCase().replace(/\.(NS|BO)$/, '')));
  if (ownedMatch) return ownedMatch;
  const tokens = userMsg.match(/\b[a-z]{1,5}\b/gi);
  if (!tokens) return watchlist[0] || null;
  const wl = new Set((watchlist || []).map((t) => t.toUpperCase()));
  const candidates = tokens
    .map((t) => t.toUpperCase())
    .filter((s) => s.length >= 2 && s.length <= 5 && /^[A-Z]+$/.test(s) && !STOPWORDS.has(s));

  for (const c of candidates) {
    if (wl.has(c)) return c;
  }
  return candidates[0] || watchlist[0] || null;
}

function classifyIntents(msgLower) {
  return {
    forecast:
      /forecast|predict|price target|where will|next week|next day|trajectory|lstm|timesfm/.test(
        msgLower
      ),
    sentiment:
      /sentiment|headline|news|bullish|bearish|vader|headlines|media/.test(msgLower),
    regime:
      /regime|market condition|macro|broad market|spy\b|overall market/.test(msgLower),
    portfolio:
      /portfolio|allocation|rebalance|risk level|\brisk\b|stress|var\b|drawdown|diversif|weight/.test(
        msgLower
      ),
    help: /help|^hi\b|^hello|what can you|how do you/.test(msgLower),
  };
}

function summarizeDecisionOptions(analysis) {
  if (analysis?.risk_budget || analysis?.allocation) {
    const lines = [];
    const volatility = analysis.risk_budget?.portfolio_volatility;
    if (Number.isFinite(volatility)) lines.push(`Historical annualized portfolio volatility: ${(volatility * 100).toFixed(2)}%.`);
    if (analysis.market_regime?.current_regime) lines.push(`Portfolio market-state estimate: ${analysis.market_regime.current_regime}. Statistical states do not guarantee future returns.`);
    if (analysis.allocation?.explanation) lines.push(analysis.allocation.explanation);
    const suggested = analysis.allocation?.weights;
    if (suggested && typeof suggested === 'object') lines.push(`Suggested allocation: ${Object.entries(suggested).map(([ticker, weight]) => `${ticker} ${(Number(weight) * 100).toFixed(1)}%`).join(', ')}.`);
    return lines.join('\n\n');
  }
  const opts = analysis?.decision_options;
  if (!Array.isArray(opts) || opts.length === 0) return '';

  const lines = [];
  const regimeLabel = analysis?.regime_summary?.current_regime;
  if (regimeLabel) {
    const conf = analysis.regime_summary?.confidence;
    const confStr =
      typeof conf === 'number' ? ` (${Math.round(conf * 100)}% confidence)` : '';
    lines.push(`Your portfolio analysis sees a ${regimeLabel} regime${confStr}.`);
  }

  const highlight =
    opts.find((o) => o.option === 'Balanced') || opts.find((o) => o.option === 'Conservative') || opts[0];
  if (highlight) {
    lines.push(
      `${highlight.option} approach: ${highlight.description}. Worst-case stress: ${highlight.downside_risk || 'n/a'}.`
    );
    const topReasons = (highlight.reasoning || []).slice(0, 3);
    if (topReasons.length) {
      lines.push(topReasons.map((r) => `• ${r}`).join('\n'));
    }
  }

  return lines.join('\n\n');
}

async function buildAdvisorReply(userMsg, tickers, ownedContext = null) {
  const msgLower = userMsg.toLowerCase();
  const intents = classifyIntents(msgLower);
  if (intents.help) {
    return ownedContext?.error || `Hello! I can help explain your ${ownedContext?.currency || ''} portfolio risk and allocation. Ask "What is my portfolio risk?" or "How can I improve my allocation?" You can also ask about a specific holding's forecast or news sentiment.`;
  }
  if (ownedContext?.error) return ownedContext.error;
  const symbol = extractTicker(userMsg, tickers);
  const weights = ownedContext?.weights || (tickers.length ? tickers.map(() => 1 / tickers.length) : []);

  if (!tickers.length && ownedContext?.error) return ownedContext.error;
  if (!tickers.length) {
    const onlyRegime = intents.regime && !intents.forecast && !intents.sentiment;
    if (onlyRegime) {
      try {
        const regime = await PortfolioService.getMarketRegime();
        return [
          'You do not have a watchlist yet — showing broad market regime only (SPY proxy).',
          `${regime.current_regime} (state ${regime.state_id}, confidence ${Math.round((regime.confidence || 0) * 100)}%).`,
          'Add tickers under Watchlist for portfolio risk and trade-offs tailored to you.',
        ].join('\n\n');
      } catch {
        return 'Add tickers to your watchlist first, so I can run portfolio analysis. You can still ask about market regime once the analytics server is reachable.';
      }
    }
    return [
      'I need at least one ticker on your Watchlist to pull risk metrics, forecasts, and sentiment.',
      'Add symbols from Watchlist, then ask things like:',
      '• What’s my portfolio risk?\n• Forecast for AAPL\n• Sentiment on MSFT',
    ].join('\n\n');
  }

  const fetchPortfolio = intents.portfolio || (ownedContext && intents.regime) || (!intents.forecast && !intents.sentiment && !intents.regime);
  const fetchForecast = intents.forecast;
  const fetchSentiment = intents.sentiment;
  const fetchRegime = !ownedContext && intents.regime;

  const parts = [];

  const tasks = [];
  let analysis = null;
  let regime = null;
  let forecast = null;
  let sentiment = null;

  if (fetchPortfolio && ownedContext?.error) parts.push(ownedContext.error);
  if (fetchPortfolio && !ownedContext?.error) {
    // Canonical path: consumes /portfolio/analyze with snapshot identity and market-value weights.
    // Legacy fallback: calls legacy /analyze only for standalone ticker-only callers.
    const analysisPromise = ownedContext?.request
      ? PortfolioService.getPortfolioAnalysis(ownedContext.request)
      : PortfolioService.getAnalysis(tickers, weights, false, ownedContext?.portfolio_value);
    tasks.push(
      analysisPromise
        .then((r) => {
          analysis = r;
        })
        .catch(() => {})
    );
  }
  if (fetchRegime) {
    tasks.push(
      PortfolioService.getMarketRegime()
        .then((r) => {
          regime = r;
        })
        .catch(() => {})
    );
  }
  if (fetchForecast && symbol) {
    tasks.push(
      PortfolioService.getForecast(symbol, Number(userMsg.match(/(\d+)\s*[- ]?\s*(?:day|session)/i)?.[1] || 10))
        .then((r) => {
          forecast = r;
        })
        .catch((err) => { forecast = { error: err.response?.data?.detail || err.message || 'Forecast request failed' }; })
    );
  }
  if (fetchSentiment && symbol) {
    tasks.push(
      PortfolioService.getSentiment(symbol)
        .then((r) => {
          sentiment = r;
        })
        .catch(() => {})
    );
  }

  await Promise.all(tasks);

  if (intents.help) {
    parts.push(
     `I answer using your SmartPortfolio engine: risk tables, HMM regime, optional TimesFM price path, and FinBERT news sentiment — not a generic web LLM. You can also toggle LLM mode for natural-language explanations that combine these signals with RAG-retrieved news and a financial knowledge base.`
    );
  }

  if (regime) {
    parts.push(
      `Market regime (SPY): ${regime.current_regime} — confidence ${Math.round((regime.confidence || 0) * 100)}%.`
    );
  }

  if (forecast?.forecast?.length) {
    const last = forecast.forecast[forecast.forecast.length - 1];
    const first = forecast.forecast[0];
    parts.push(
      `${forecast.ticker || symbol} experimental ${forecast.model || 'unspecified model'} forecast (${forecast.forecast.length} sessions, ${forecast.currency || 'currency unavailable'}): latest close ${Number(forecast.spot_price).toFixed(2)} → session 1 ${Number(first.predicted_price).toFixed(2)} → session ${forecast.forecast.length} ${Number(last.predicted_price).toFixed(2)}.${forecast.fallback_reason ? ` Fallback: ${forecast.fallback_reason}` : ''}`
    );
  } else if (fetchForecast && symbol) {
    parts.push(`Forecast unavailable for ${symbol}: ${forecast?.error || forecast?.warning || 'No forecast values were returned.'}`);
  } else if (fetchForecast && !symbol) {
    parts.push('Name a symbol (e.g. AAPL) or add it to your watchlist for a forecast.');
  }

  if (sentiment) {
    parts.push(
      `${sentiment.ticker} news sentiment: ${sentiment.overall_sentiment} (score ${sentiment.overall_score}, ${sentiment.articles_analyzed} headlines, FinBERT).`
    );
  } else if (fetchSentiment && !symbol) {
    parts.push('Name a ticker for sentiment, or add one to your watchlist.');
  }

  if (analysis) {
    const body = summarizeDecisionOptions(analysis);
    if (body) parts.push(`Portfolio snapshot\n\n${body}`);
    else parts.push('Portfolio analysis returned no decision options — check that the analytics API is running.');
  } else if (fetchPortfolio && !ownedContext?.error) {
    parts.push('Could not load portfolio analysis. Is the analytics server running at http://localhost:8000 ?');
  }

  if (parts.length === 0) {
    return 'Ask about risk, forecast, sentiment, or market regime, or type help.';
  }

  return parts.join('\n\n');
}

const ChatAdvisor = ({ portfolioSnapshot, userId = null, tickers: legacyTickers = [] }) => {
  const location = useLocation();
  const allocationEntry = useRef(null);
  const currencyPreferenceKey = userId && portfolioSnapshot?.portfolioId ? `spa_chat_currency:${JSON.stringify([userId, portfolioSnapshot.portfolioId])}` : null;
  const [selectedCurrency, setSelectedCurrency] = useState(() => {
    try { return currencyPreferenceKey ? localStorage.getItem(currencyPreferenceKey) || '' : ''; } catch { return ''; }
  });
  const currencies = portfolioSnapshot?.valuation.currencies || [];
  const activeCurrency = currencies.includes(selectedCurrency) ? selectedCurrency : currencies.includes(portfolioSnapshot?.baseCurrency) ? portfolioSnapshot.baseCurrency : currencies[0];
  // Compatibility for old standalone callers only. App always supplies the owned snapshot.
  const tickers = portfolioSnapshot ? [...new Set(portfolioSnapshot.holdings.filter((holding) => holding.currency === activeCurrency).map((holding) => holding.ticker))] : legacyTickers;
  const ownedContext = portfolioSnapshot ? advisorPortfolioContext(portfolioSnapshot, activeCurrency) : null;
  const scopeKey = chatHistoryKey(userId, portfolioSnapshot?.portfolioId, activeCurrency);
  const [sessionState, setSessionState] = useState(() => {
    let active = 'original';
    try { active = localStorage.getItem(`${scopeKey}:active`) || active; } catch { /* Optional preference. */ }
    const sessions = readChatSessions(scopeKey);
    return { scope: scopeKey, sessions, active: sessions.some((row) => row.id === active) ? active : 'original' };
  });
  const currentSessions = sessionState.scope === scopeKey ? sessionState.sessions : readChatSessions(scopeKey);
  const activeSession = sessionState.scope === scopeKey ? sessionState.active : 'original';
  const historyKey = sessionHistoryKey(scopeKey, activeSession);
  const [messages, updateMessages] = useState(() => readChatHistory(historyKey));
  const historyRef = useRef({ key: historyKey, messages });
  const setMessages = (next) => {
    // Persist before React updates, including a reply completing after navigation.
    const previous = historyRef.current.key === historyKey ? historyRef.current.messages : readChatHistory(historyKey);
    const updated = typeof next === 'function' ? next(previous) : next;
    writeChatHistory(historyKey, updated);
    if (historyRef.current.key === historyKey) {
      historyRef.current.messages = updated;
      updateMessages(updated);
    }
  };
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [chatStarted, setChatStarted] = useState(() => messages.length > 0);
  const [infoOpen, setInfoOpen] = useState(false);
  const [useLLM, setUseLLM] = useState(true);
  const [llmConfigured, setLlmConfigured] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const scrollRef = useRef(null);
  const requestSeq = useRef(0);
  const streamingTextRef = useRef('');

  const chooseSession = (id, sessions = currentSessions) => {
    setSessionState({ scope: scopeKey, sessions, active: id });
    setInput('');
    try { if (scopeKey) localStorage.setItem(`${scopeKey}:active`, id); } catch { /* Optional preference. */ }
  };
  const chatControls = <div className="flex flex-wrap items-center gap-2">
    <button type="button" disabled={loading || isStreaming} onClick={() => {
      const next = createChatSession(scopeKey);
      chooseSession(next.session.id, next.sessions);
    }} className="rounded-lg bg-indigo-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">New chat</button>
    {currentSessions.length > 1 && <select aria-label="Saved chats" disabled={loading || isStreaming} value={activeSession}
      onChange={(event) => chooseSession(event.target.value)} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700">
      {currentSessions.map((session) => <option key={session.id} value={session.id}>{session.title}</option>)}
    </select>}
  </div>;

  useEffect(() => {
    const restored = readChatHistory(historyKey);
    historyRef.current = { key: historyKey, messages: restored };
    updateMessages(restored);
    setChatStarted(restored.length > 0);
  }, [historyKey]);

  useEffect(() => {
    const entry = location.state;
    if (location.pathname !== '/dashboard/chat' || !entry?.allocationCurrency || entry.portfolioId !== portfolioSnapshot?.portfolioId ||
        allocationEntry.current === location.key || loading || isStreaming) return;
    allocationEntry.current = location.key;
    setSelectedCurrency(entry.allocationCurrency);
    setInput('Explain my suggested allocation. Which holding changes most, and how do my risk preference and investment horizon affect it?');
  }, [location, portfolioSnapshot?.portfolioId, loading, isStreaming]);

  const currencySelector = currencies.length > 1 && (
    <label className="flex items-center gap-2 text-sm text-slate-700">
      Analyze holdings in
      <select aria-label="Advisor currency" value={activeCurrency} disabled={loading || isStreaming}
        onChange={(event) => {
          setSelectedCurrency(event.target.value);
          try { if (currencyPreferenceKey) localStorage.setItem(currencyPreferenceKey, event.target.value); } catch { /* Optional preference. */ }
        }}
        className="rounded-lg border border-slate-300 bg-white px-3 py-2">
        {currencies.map((currency) => <option key={currency} value={currency}>{currency}</option>)}
      </select>
      <span className="text-xs">Currencies are analyzed separately.</span>
    </label>
  );

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading, streamingText, isStreaming]);

  useEffect(() => {
    ChatService.getAdvisorStatus()
      .then((status) => setLlmConfigured(status.llm_configured))
      .catch(() => setLlmConfigured(false));
  }, []);

  const handleSendMessage = async (e) => {
    if (e) e.preventDefault();
    if (!input.trim() || loading || isStreaming) return;

    const userMsg = input.trim();
    setInput('');

    if (!chatStarted) setChatStarted(true);

    setMessages((prev) => [...prev, { role: 'user', text: userMsg }]);

    const casualReply = conversationReply(userMsg);
    if (casualReply) {
      setMessages((prev) => [...prev, { role: 'assistant', text: casualReply }]);
      return;
    }

    if (useLLM && llmConfigured && ownedContext?.error) {
      setMessages((prev) => [...prev, { role: 'assistant', text: ownedContext.error }]);
      return;
    }
    if (useLLM && llmConfigured) {
      setLoading(true);
      setIsStreaming(true);
      setStreamingText('');
      streamingTextRef.current = '';

      const weights = tickers.length ? tickers.map(() => 1 / tickers.length) : [];
      const payload = {
        query: userMsg,
        start: ownedContext?.request?.start || '2023-01-01',
        tickers: ownedContext?.tickers || tickers,
        weights: ownedContext?.weights || weights,
        portfolio_value: ownedContext?.portfolio_value ?? 100000,
        portfolio_id: portfolioSnapshot?.portfolioId || null,
        portfolio_revision: portfolioSnapshot?.portfolioRevision || null,
        currency: ownedContext?.currency || 'USD',
        portfolio_context: portfolioSnapshot ? {
          portfolio_id: portfolioSnapshot.portfolioId,
          portfolio_revision: portfolioSnapshot.portfolioRevision,
          as_of: portfolioSnapshot.asOf,
          ...profileForAnalysis(portfolioSnapshot, activeCurrency),
          currency: activeCurrency,
          holdings: portfolioSnapshot.holdings.filter((holding) => holding.currency === activeCurrency).map((holding) => ({
            ticker: holding.ticker, currency: holding.currency, quantity: holding.quantity,
            average_cost: holding.average_cost, market_value: holding.market_value,
          })),
          transactions: portfolioSnapshot.transactions.filter((transaction) => transaction.currency === activeCurrency).map((transaction) => ({
            ticker: transaction.ticker, currency: transaction.currency, transaction_type: transaction.transaction_type,
            quantity: transaction.quantity, price: transaction.price, fees: transaction.fees, transaction_date: transaction.transaction_date,
          })),
        } : null,
        top_k: 5,
      };

      try {
        await ChatService.sendMessageStream(payload, (chunk, meta) => {
          if (chunk) {
            streamingTextRef.current += chunk;
            setStreamingText(streamingTextRef.current);
          }
          if (meta && (meta.done || meta.error)) {
            const finalText = streamingTextRef.current || '';
            if (meta.error && !finalText) {
              setIsStreaming(false);
              setLoading(false);
              setStreamingText('');
              setMessages((prev) => [...prev, {
                role: 'assistant',
                text: typeof meta.error === 'string' ? meta.error : 'The advisor could not complete this request. Please try again later.',
              }]);
            } else {
              setIsStreaming(false);
              setLoading(false);
              setStreamingText('');
              setMessages((prev) => [...prev, {
                role: 'assistant',
                text: finalText || '(no response)',
                grounding_check: meta.grounding_check, advisor_provenance: meta.advisor_provenance,
              }]);
            }
          }
        });
      } catch (error) {
        setIsStreaming(false);
        setLoading(false);
        setStreamingText('');
        setMessages((prev) => [...prev, {
          role: 'assistant',
          text: error.message || 'Unable to reach the advisor. Check your connection and try again.',
        }]);
      }
      return;
    }

    setLoading(true);

    const seq = ++requestSeq.current;

    try {
      const aiResponse = holdingAnswer(userMsg, portfolioSnapshot, activeCurrency) || await buildAdvisorReply(userMsg, tickers, ownedContext);
      if (seq !== requestSeq.current) return;
      setMessages((prev) => [...prev, { role: 'assistant', text: aiResponse }]);
    } catch {
      if (seq !== requestSeq.current) return;
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: 'Something went wrong. Confirm the analytics API is up and try again.',
        },
      ]);
    } finally {
      if (seq === requestSeq.current) setLoading(false);
    }
  };

  if (!chatStarted) {
    return (
      <div className="w-full min-h-[calc(100vh-200px)] bg-gradient-to-b from-white via-indigo-50 to-slate-50 relative overflow-hidden">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl animate-blob" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl animate-blob animation-delay-2000" />
        </div>

        <div className="relative z-10 max-w-4xl mx-auto px-6 py-12 flex flex-col items-center justify-center min-h-[calc(100vh-200px)]">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600/10 border border-indigo-600/30 rounded-full mb-8 animate-in fade-in duration-500">
            <Zap className="w-4 h-4 text-indigo-700" />
            <span className="text-sm font-semibold text-indigo-700">Analytics-backed Q&amp;A</span>
          </div>

          <h1 className="text-5xl md:text-6xl font-black text-center mb-6 leading-tight animate-in fade-in slide-in-from-bottom-4 duration-700">
            Ask your{' '}
            <span className="text-indigo-700">portfolio brain</span>
          </h1>

          <p className="text-center text-slate-600 text-lg max-w-2xl mb-12 leading-relaxed animate-in fade-in slide-in-from-bottom-4 duration-700 delay-100">
            Answers are built from the same backend as the rest of SmartPortfolio: <span className="text-slate-900 font-semibold">risk metrics</span>,{' '}
            <span className="text-slate-900 font-semibold">HMM regime</span>,{' '}
            <span className="text-slate-900 font-semibold">experimental price forecasts</span>, and{' '}
            <span className="text-slate-900 font-semibold">FinBERT news sentiment</span> — grounded in your
            watchlist when you ask. {llmConfigured && 'Toggle the LLM switch for natural-language explanations powered by an AI model on top of the analytics.'}
          </p>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-12 w-full max-w-3xl animate-in fade-in slide-in-from-bottom-4 duration-700 delay-200">
            <div className="text-center text-emerald-700 text-sm font-bold">
              <Globe className="w-4 h-4 inline mr-1" />
              Live data
            </div>
            <div className="text-center text-emerald-700 text-sm font-bold">
              <Brain className="w-4 h-4 inline mr-1" />
              Regime + risk
            </div>
            <div className="text-center text-emerald-700 text-sm font-bold">
              <TrendingUp className="w-4 h-4 inline mr-1" />
              Forecasts
            </div>
            <div className="text-center text-emerald-700 text-sm font-bold">
              <MessageSquare className="w-4 h-4 inline mr-1" />
              News sentiment
            </div>
          </div>

          <div className="mb-6 flex flex-wrap gap-4">{currencySelector}{chatControls}</div>
          <form
            onSubmit={handleSendMessage}
            className="w-full max-w-2xl animate-in fade-in slide-in-from-bottom-4 duration-700 delay-300"
          >
            <div className="relative group">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-600 to-purple-600 rounded-2xl blur opacity-0 group-hover:opacity-30 transition-all duration-500" />
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask anything..."
                className="relative w-full bg-white border border-slate-200 rounded-2xl py-5 pl-6 pr-16 text-base focus:outline-none focus:ring-2 focus:ring-indigo-600/50 focus:border-transparent transition-all shadow-xl text-slate-900 placeholder-gray-500"
              />
              <button
                type="submit"
                className="absolute right-2 top-1/2 -translate-y-1/2 px-4 py-2.5 bg-indigo-700 text-[#ffffff] hover:bg-indigo-800  rounded-lg flex items-center gap-2 transition-all shadow-lg active:scale-95 disabled:opacity-50 font-semibold text-sm"
            disabled={loading || isStreaming || !input.trim()}
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                Ask
              </button>
            </div>
          </form>

          <div className="flex flex-wrap gap-3 mt-8 justify-center max-w-2xl">
            <button
              type="button"
              onClick={() => setInput('Summarize my portfolio risk and regime')}
              className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-100 border border-slate-200 rounded-lg transition-all"
            >
              Risk &amp; regime
            </button>
            <button
              type="button"
              onClick={() => setInput('Give a short price forecast for my top holding')}
              className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-100 border border-slate-200 rounded-lg transition-all"
            >
              Forecast
            </button>
            <button
              type="button"
              onClick={() => setInput('What is the news sentiment on my first ticker?')}
              className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-100 border border-slate-200 rounded-lg transition-all"
            >
              Sentiment
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-[calc(100vh-200px)] flex flex-col bg-white backdrop-blur-3xl border border-slate-200 rounded-[2.5rem] shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-500">
      <div className="p-6 border-b border-slate-200 flex items-center justify-between bg-gradient-to-r from-transparent via-indigo-600/5 to-transparent">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-indigo-700 text-[#ffffff] rounded-2xl flex items-center justify-center shadow-lg shadow-indigo-600/20 ring-4 ring-indigo-600/10">
            <Bot className="w-7 h-7 text-slate-900" />
          </div>
          <div>
            <h3 className="font-bold text-slate-900 flex items-center gap-2">
              AI Wealth Advisor
              <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
            </h3>
            <p className="text-xs text-indigo-700 font-bold uppercase tracking-widest">
              Powered by SmartPortfolio analytics APIs
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {currencySelector}
          {chatControls}
          {llmConfigured ? (
            <>
              <span className="text-xs text-slate-600">Template</span>
              <button
                type="button"
                onClick={() => setUseLLM((v) => !v)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
                  useLLM ? 'bg-indigo-700 text-[#ffffff]' : 'bg-slate-100'
                }`}
                title={useLLM ? 'Switch to template mode' : 'Switch to LLM mode'}
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
                    useLLM ? 'translate-x-5' : 'translate-x-1'
                  }`}
                />
              </button>
              <span className="text-xs text-slate-600">LLM</span>
            </>
          ) : (
            <span
              className="text-xs text-gray-600"
              title="LLM not configured on the analytics server. Set LLM_API_KEY to enable."
            >
              LLM unavailable — holdings summaries only
            </span>
          )}
          <button
            type="button"
            onClick={() => setInfoOpen((o) => !o)}
            className="p-2.5 rounded-xl hover:bg-slate-100 text-slate-600 transition-all"
            title="How this works"
          >
            <Info className="w-5 h-5" />
          </button>
          <span className="p-2.5 rounded-xl text-gray-600">
            <Sparkles className="w-5 h-5 text-amber-700" />
          </span>
        </div>
      </div>

      {infoOpen && (
        <div className="px-6 py-3 bg-indigo-600/5 border-b border-slate-200 text-xs text-slate-600 leading-relaxed">
          Template mode stitches together <strong className="text-slate-900">/analyze</strong>,{' '}
          <strong className="text-slate-900">/market-regime</strong>,{' '}
          <strong className="text-slate-900">/forecast</strong>, and{' '}
          <strong className="text-slate-900">/sentiment</strong> via rule-based intent matching.
          LLM mode sends your question to <strong className="text-slate-900">/chat/stream</strong>,{' '}
          which gathers the same ML context plus RAG-retrieved news and knowledge-base{' '}
          <strong className="text-slate-900">documents</strong>, then calls a configured{' '}
          language model for a natural-language explanation. Not investment advice.
        </div>
      )}

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-8 space-y-8 scroll-smooth custom-scrollbar"
      >
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-4 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div
              className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-lg ${
                m.role === 'assistant' ? 'bg-indigo-700 text-[#ffffff] ' : 'bg-slate-100 text-slate-600'
              }`}
            >
              {m.role === 'assistant' ? <Bot className="w-6 h-6" /> : <UserIcon className="w-6 h-6" />}
            </div>

            <div
              className={`max-w-[75%] p-5 rounded-2xl text-sm leading-relaxed shadow-sm ${
                m.role === 'assistant'
                  ? 'bg-slate-100 text-slate-900 border-l-4 border-indigo-600 whitespace-pre-wrap'
                  : 'bg-indigo-700 text-[#ffffff]  font-medium ml-12 rounded-tr-none'
              }`}
            >
              {m.grounding_check?.status === 'verified' && <small className="block text-xs text-slate-600">Labeled figures verified against Quant Engine</small>}
              {m.grounding_check?.status === 'mismatch_detected' && <small className="block text-xs text-amber-700">Quant Engine corrections included</small>}
              {m.role === 'assistant' ? <div className="[&_p]:mb-3 [&_p:last-child]:mb-0 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_strong]:font-semibold"><ReactMarkdown skipHtml>{m.text}</ReactMarkdown></div> : m.text}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-4">
            <div className="w-10 h-10 rounded-xl bg-indigo-700 text-[#ffffff]  flex items-center justify-center shrink-0 shadow-lg animate-pulse">
              <Bot className="w-6 h-6" />
            </div>
            <div className="bg-slate-100 p-5 rounded-2xl flex items-center gap-3">
              <Loader2 className="w-4 h-4 text-indigo-500 animate-spin" />
              <span className="text-xs text-slate-600 font-medium italic">
                {useLLM && llmConfigured ? 'Gathering ML context + RAG...' : 'Querying analytics...'}
              </span>
            </div>
          </div>
        )}
        {isStreaming && streamingText && (
          <div className="flex gap-4">
            <div className="w-10 h-10 rounded-xl bg-indigo-700 text-[#ffffff]  flex items-center justify-center shrink-0 shadow-lg">
              <Bot className="w-6 h-6" />
            </div>
            <div className="bg-slate-100 p-5 rounded-2xl text-sm leading-relaxed shadow-sm border-l-4 border-indigo-600 whitespace-pre-wrap">
              <ReactMarkdown skipHtml>{streamingText}</ReactMarkdown>
              <span className="inline-block w-2 h-4 bg-indigo-400 animate-pulse ml-0.5" />
            </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSendMessage} className="p-6 bg-white border-t border-slate-200">
        <div className="relative group">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything about your portfolio or the market..."
            className="w-full bg-white border border-slate-200 rounded-2xl py-5 pl-7 pr-16 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-600/40 focus:border-indigo-600/50 transition-all shadow-inner text-slate-900"
          />
             <button
                type="submit"
                className="absolute right-3 top-1/2 -translate-y-1/2 w-11 h-11 bg-indigo-700 text-[#ffffff] hover:bg-indigo-800  rounded-xl flex items-center justify-center transition-all shadow-lg shadow-indigo-600/20 active:scale-95 disabled:opacity-50"
                disabled={loading || isStreaming || !input.trim()}
              >
            <Send className="w-5 h-5" />
          </button>
        </div>
        <div className="flex flex-wrap gap-4 mt-4">
          <button
            type="button"
            onClick={() => setInput('Summarize my portfolio risk and regime')}
            className="text-[10px] uppercase tracking-wider font-bold text-slate-600 hover:text-indigo-700 transition-colors"
          >
            Risk &amp; regime
          </button>
          <button
            type="button"
            onClick={() => setInput('Give a short price forecast for my top holding')}
            className="text-[10px] uppercase tracking-wider font-bold text-slate-600 hover:text-indigo-700 transition-colors"
          >
            Forecast
          </button>
          <button
            type="button"
            onClick={() => setInput('What is the news sentiment on my first ticker?')}
            className="text-[10px] uppercase tracking-wider font-bold text-slate-600 hover:text-indigo-700 transition-colors"
          >
            Sentiment
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatAdvisor;

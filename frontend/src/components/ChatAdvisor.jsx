import './ChatAdvisor.css';
import { profileForAnalysis } from '../services/investorProfile.js';
import { Link, useLocation } from 'react-router-dom';
import React, { useState, useRef, useEffect } from 'react';
import {
  MessageSquare,
  Send,
  Bot,
  Loader2,
  Zap,
  Globe,
  Brain,
  TrendingUp,
  X, Maximize2, Minimize2, ThumbsUp, ThumbsDown,
} from 'lucide-react';
import { PortfolioService, ChatService } from '../services/api';
import { advisorPortfolioContext } from '../services/portfolioSnapshot';
import { assetValue } from '../services/assetTracking';
import { holdingAnswer } from '../services/advisorHolding';
import { portfolioOverview, quickPortfolioAnswer, quickPortfolioIntent } from '../services/advisorQuickAnswer';
import { conversationReply, appHelpReply } from '../services/advisorConversation';
import AdvisorMarkdown from './AdvisorMarkdown';
import { chatHistoryKey, readChatHistory, writeChatHistory, readChatSessions, sessionHistoryKey, createChatSession } from '../services/advisorHistory';

import { resolveChatSymbol, formatNewsSentiment } from '../services/advisorMarket.js';

function classifyIntents(msgLower) {
  return {
    forecast:
      /forecast|predict|price target|where will|next week|next day|trajectory|lstm|timesfm/.test(
        msgLower
      ),
    sentiment:
      /sentiment|headline|news|bullish|bearish|vader|headlines|media/.test(msgLower),
    regime:
      /regime|market condition|macro|broad market|overall market/.test(msgLower),
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

    const suggested = analysis.personalized_allocation?.success && analysis.personalized_allocation.weights;
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

export async function buildAdvisorReply(userMsg, tickers, ownedContext = null) {
  const msgLower = userMsg.toLowerCase();
  const intents = classifyIntents(msgLower);
  if (intents.help && !intents.forecast && !intents.sentiment) {
    return ownedContext?.error || `Hello! I can help explain your ${ownedContext?.currency || ''} portfolio risk and allocation. Ask "What is my portfolio risk?" or "How can I improve my allocation?" You can also ask about a specific holding's forecast or news sentiment.`;
  }
  const marketOnly = (intents.forecast || intents.sentiment) && !intents.portfolio && !intents.regime;
  if (ownedContext?.error && !marketOnly) return ownedContext.error;
  const symbol = resolveChatSymbol(userMsg, tickers);
  if ((intents.forecast || intents.sentiment) && !symbol) return 'Which ticker should I check? Enter one exchange symbol, such as RELIANCE.NS or MSFT.';
  const weights = ownedContext?.weights || (tickers.length ? tickers.map(() => 1 / tickers.length) : []);

  if (!tickers.length && !marketOnly) {
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
      ? PortfolioService.getPortfolioAnalysis({ ...ownedContext.request, include_optional_ml: intents.sentiment })
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
    parts.push(formatNewsSentiment(sentiment, symbol));
  } else if (fetchSentiment) {
    parts.push(`The news service could not retrieve sentiment for ${symbol}. Please retry.`);
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

const ChatAdvisor = ({ portfolioSnapshot, userId = null, tickers: legacyTickers = [], docked = false, expanded = false, onExpand, onClose }) => {
  const location = useLocation();
  const allocationEntry = useRef(null);
  const currencyPreferenceKey = userId && portfolioSnapshot?.portfolioId ? `spa_chat_currency:${JSON.stringify([userId, portfolioSnapshot.portfolioId])}` : null;
  const [selectedCurrency, setSelectedCurrency] = useState(() => {
    try { return currencyPreferenceKey ? localStorage.getItem(currencyPreferenceKey) || '' : ''; } catch { return ''; }
  });
  const trackedAssets = portfolioSnapshot?.trackedAssets || [];
  const currencies = [...new Set([...(portfolioSnapshot?.valuation.currencies || []), ...trackedAssets.map(asset => asset.currency)])];
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
  useEffect(() => {
    if (!docked) return;
    const closeOnEscape = event => { if (event.key === 'Escape') onClose?.(); };
    document.addEventListener('keydown', closeOnEscape);
    return () => document.removeEventListener('keydown', closeOnEscape);
  }, [docked, onClose]);
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
  const composerRef = useRef(null);
  const [useLLM, setUseLLM] = useState(true);
  const [isStreaming, setIsStreaming] = useState(false);
  const streamController = useRef(null);
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
    }} className="rounded-lg bg-blue-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">New chat</button>
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

  const handleSendMessage = async (e) => {
    if (e) e.preventDefault();
    if (!input.trim() || loading || isStreaming) return;

    const userMsg = input.trim();
    setInput('');

    if (!chatStarted) setChatStarted(true);

    setMessages((prev) => [...prev, { role: 'user', text: userMsg }]);

    const casualReply = appHelpReply(userMsg) || conversationReply(userMsg);
    if (!useLLM && casualReply) {
      setMessages((prev) => [...prev, { role: 'assistant', text: casualReply }]);
      return;
    }

    const category = /\bmutual funds?\b/i.test(userMsg) ? 'mutual_fund' : /\bcash\b/i.test(userMsg) ? 'cash' : null;
    if (!useLLM && category && /\b(list|own|have|value|balance|worth)\b/i.test(userMsg)
        && !/\b(should|recommend|compare|risk|forecast|performance)\b/i.test(userMsg)) {
      const assets = trackedAssets.filter(asset => asset.currency === activeCurrency && asset.asset_type === category);
      const money = new Intl.NumberFormat('en-IN', { style: 'currency', currency: activeCurrency || 'INR' });
      const rows = assets.map(asset => {
        const value = assetValue(asset);
        return `- ${asset.name || asset.ticker}: ${value == null ? 'Value unavailable' : money.format(value)}${asset.valuation_date ? ' as of ' + asset.valuation_date : ''}`;
      });
      setMessages(prev => [...prev, {role: 'assistant', text: rows.length ? rows.join('\n') : 'No matching assets are recorded in the selected currency.'}]);
      return;
    }

    const quickIntent = !useLLM && ownedContext && quickPortfolioIntent(userMsg);
    if (quickIntent === 'overview') {
      setMessages(prev => [...prev, { role: 'assistant', text: portfolioOverview(portfolioSnapshot, activeCurrency) }]);
      return;
    }
    if (quickIntent) {
      if (ownedContext.error) {
        setMessages(prev => [...prev, { role: 'assistant', text: ownedContext.error }]);
        return;
      }
      setLoading(true);
      const request = { ...ownedContext.request, include_optional_ml: false };
      try {
        const result = await PortfolioService.getPortfolioAnalysis(request, false, 30000);
        if (result.portfolio_revision !== request.portfolio_revision) {
          throw new Error('The analysis returned a different portfolio revision.');
        }
        setMessages(prev => [...prev, { role: 'assistant', text: quickPortfolioAnswer(quickIntent, result) }]);
      } catch {
        setMessages(prev => [...prev, {
          role: 'assistant',
          text: 'Portfolio analysis did not finish in time or is unavailable. Open Advisor and refresh the analysis, then try again.',
        }]);
      } finally {
        setLoading(false);
      }
      return;
    }

    const intents = classifyIntents(userMsg.toLowerCase());
    const marketOnly = (intents.sentiment || intents.forecast) && !intents.portfolio && !intents.regime;
    if (!useLLM && !intents.sentiment && !intents.forecast && !/\b(?:forecast|predict|sentiment|news|suggested|target|recommend|allocation|rebalance|should|too high|too low)\b/i.test(userMsg)
        && /\b(?:own|ownership|shares|weight|invested|quantity|cost basis|purchase price|market value|profit\/loss)\b/i.test(userMsg)) {
      const reply = portfolioSnapshot?.valid && holdingAnswer(userMsg, portfolioSnapshot, activeCurrency);
      if (reply) {
        setMessages(prev => [...prev, { role: 'assistant', text: reply }]);
        return;
      }
    }

    if (useLLM) {
      setLoading(true);
      setIsStreaming(true);
      setStreamingText('');
      streamingTextRef.current = '';

      const weights = tickers.length ? tickers.map(() => 1 / tickers.length) : [];
      const cachedAnalysis = ownedContext?.request
        ? PortfolioService.getCachedPortfolioAnalysis(ownedContext.request)
          || PortfolioService.getCachedPortfolioAnalysis({ ...ownedContext.request, include_optional_ml: false })
        : null;
      let marketContext = null;
      if (marketOnly) {
        try {
          marketContext = await buildAdvisorReply(userMsg, tickers, ownedContext);
        } catch {
          marketContext = 'Market data could not be loaded for this question.';
        }
      }
      const payload = {
        query: userMsg,
        conversational: true,
        start: ownedContext?.request?.start || '2023-01-01',
        tickers: ownedContext?.tickers || tickers,
        weights: ownedContext?.weights || weights,
        portfolio_value: ownedContext?.portfolio_value ?? 100000,
        portfolio_id: portfolioSnapshot?.portfolioId || null,
        portfolio_revision: portfolioSnapshot?.portfolioRevision || null,
        currency: ownedContext?.currency || 'USD',
        portfolio_context: portfolioSnapshot ? {
          app_guidance: appHelpReply(userMsg),
          market_context: marketContext,
          portfolio_id: portfolioSnapshot.portfolioId,
          portfolio_revision: portfolioSnapshot.portfolioRevision,
          as_of: portfolioSnapshot.asOf,
          available_analysis: cachedAnalysis ? {
            portfolio_risk: cachedAnalysis.portfolio_risk,
            personalized_allocation: cachedAnalysis.personalized_allocation,
            analysis_id: cachedAnalysis.analysis_id,
          } : null,
          recent_turns: messages.slice(-6).map(({ role, text }) => ({ role, text: text.slice(0, 800) })),
          ...profileForAnalysis(portfolioSnapshot, activeCurrency),
          currency: activeCurrency,
          holdings: portfolioSnapshot.holdings.filter((holding) => holding.currency === activeCurrency).map((holding) => ({
            ticker: holding.ticker, currency: holding.currency, quantity: holding.quantity,
            average_cost: holding.average_cost, market_value: holding.market_value,
          })),
          tracked_assets: trackedAssets.filter(asset => asset.currency === activeCurrency).map(asset => ({
            name: asset.name || asset.ticker, currency: asset.currency, type: asset.asset_type,
            recorded_value: assetValue(asset), valuation_date: asset.valuation_date,
          })),
          transactions: portfolioSnapshot.transactions.filter((transaction) => transaction.currency === activeCurrency).map((transaction) => ({
            ticker: transaction.ticker, currency: transaction.currency, transaction_type: transaction.transaction_type,
            quantity: transaction.quantity, price: transaction.price, fees: transaction.fees, transaction_date: transaction.transaction_date,
          })),
        } : {
          recent_turns: messages.slice(-6).map(({role, text}) => ({role, text: text.slice(0, 800)})),
          app_guidance: appHelpReply(userMsg), market_context: marketContext,
        },
        top_k: 5,
      };

      try {
        streamController.current = new AbortController();
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
        }, streamController.current.signal);
      } catch (error) {
        setIsStreaming(false);
        setLoading(false);
        setStreamingText('');
        setMessages((prev) => [...prev, {
          role: 'assistant',
          text: error.name === 'AbortError' ? 'Reply stopped.' : error.name === 'TimeoutError'
            ? 'The AI explanation took too long. Try again or switch to Analytics summary.'
            : error.message || 'Unable to reach the advisor. Try again or switch to Analytics summary.',
        }]);
      }
      return;
    }

    setLoading(true);

    const seq = ++requestSeq.current;

    try {
      const aiResponse = await buildAdvisorReply(userMsg, tickers, ownedContext);
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

  const busy = loading || isStreaming;
  const symbol = tickers[0];
  const prompts = [
    [Brain, 'Portfolio risk', 'Which risks matter most in my portfolio?'],
    [TrendingUp, 'Allocation', 'Explain my suggested allocation and the biggest weight change.'],
    ...(symbol ? [[Globe, 'Market news', `What is the news sentiment for ${symbol}?`],
      [Zap, 'Forecast', `Show the experimental 10-session forecast for ${symbol}.`]] : []),
  ];
  function selectPrompt(question) {
    setInput(question);
    composerRef.current?.focus();
  }
  const hasFunds = portfolioSnapshot?.trackedAssets?.some(asset => asset.asset_type === 'mutual_fund');
  return <section aria-label="Portfolio assistant" className={`portfolio-chat ${docked ? 'is-docked' : ''} mx-auto flex w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white text-slate-900`}>
    <header className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 px-4 py-4 sm:px-7">
      <div className="flex items-center gap-3"><div className="rounded-xl bg-blue-50 p-3 text-blue-700"><MessageSquare size={22}/></div>
        <div><h2 className="text-xl font-semibold">AI Assistant</h2><p className="text-sm text-slate-600">
          {tickers.length ? `${tickers.length} stock${tickers.length === 1 ? '' : 's'}${activeCurrency ? ' · '+activeCurrency : ''}` : 'No stocks selected'}
        </p></div></div>
      <div className="flex flex-wrap items-center gap-3">{currencySelector}{chatControls}
        {docked && <><button type="button" aria-label={expanded ? 'Restore assistant' : 'Expand assistant'} onClick={onExpand}>{expanded ? <Minimize2 size={18}/> : <Maximize2 size={18}/>}</button><button type="button" aria-label="Close assistant" onClick={onClose}><X size={20}/></button></>}
      </div>
    </header>
    <div ref={scrollRef} className="assistant-messages max-h-[58dvh] min-h-48 overflow-y-auto px-4 py-6 sm:px-8">
      {!chatStarted ? <div className="mx-auto max-w-3xl">
        <h3 className="mb-5 text-2xl font-semibold tracking-tight">What would you like to understand?</h3>
        {ownedContext?.error ? <div className="rounded-lg border bg-slate-50 p-4"><p>{ownedContext.error}</p>
          <Link className="text-blue-700 underline" to={hasFunds ? '/dashboard/advisor' : '/dashboard/portfolio'}>{hasFunds ? 'Analyze my mutual funds' : 'Review my holdings'}</Link></div>
          : <div className="grid gap-3 sm:grid-cols-2">{prompts.map(([Icon,label,question])=><button type="button" key={label}
            onClick={()=>selectPrompt(question)} className="rounded-xl border border-slate-200 p-4 text-left hover:border-blue-400 focus-visible:outline-blue-600">
            <span className="flex items-center gap-2 text-sm font-semibold text-blue-700"><Icon size={17}/>{label}</span>
            <span className="mt-2 block text-slate-800">{question}</span></button>)}</div>}
      </div> : <div className="mx-auto max-w-3xl space-y-5" role="log" aria-label="Conversation">
        {messages.map((m,i)=><article key={i} className={m.role==='user'?'assistant-question ml-auto w-fit max-w-[90%] rounded-xl bg-blue-50 px-4 py-3':'assistant-answer min-w-0 text-sm leading-7'}>
          {m.role==='user'?m.text:<><p className="mb-1 flex items-center gap-2 text-sm font-semibold text-blue-700"><Bot size={16}/>SmartPortfolio</p>
            <AdvisorMarkdown>{m.text}</AdvisorMarkdown>
            <div className="assistant-feedback" aria-label="Rate this response">{[['helpful', ThumbsUp], ['unhelpful', ThumbsDown]].map(([rating, Icon]) => <button type="button" key={rating} aria-label={rating === 'helpful' ? 'Helpful response' : 'Unhelpful response'} aria-pressed={m.rating === rating} onClick={() => setMessages(rows => rows.map((row, index) => index === i ? {...row, rating: row.rating === rating ? null : rating} : row))}><Icon size={15}/></button>)}</div>
            {m.grounding_check?.status==='verified' && <small className="text-emerald-800">Labeled figures verified against Quant Engine</small>}
            {m.grounding_check?.status==='mismatch_detected' && <small className="text-amber-800">Quant Engine corrections included</small>}</>}
        </article>)}
        {busy && !streamingText && <p role="status" className="flex items-center gap-2 text-sm text-slate-600"><Loader2 size={16} className="animate-spin"/>{isStreaming ? 'Preparing the AI explanation…' : 'Loading portfolio analytics…'}</p>}
        {isStreaming && streamingText && <AdvisorMarkdown>{streamingText}</AdvisorMarkdown>}
      </div>}
    </div>
    <div className="assistant-suggestions">
      <span>Explore your portfolio</span>
      <div>{['Review my portfolio', 'How do I connect a broker?', 'How do I add real estate?'].map(question => <button key={question} type="button" disabled={busy} onClick={() => selectPrompt(question)}>{question}</button>)}</div>
    </div>
    <form onSubmit={handleSendMessage} className="border-t border-slate-200 bg-slate-50 p-4 sm:px-8">
      <div className="mx-auto max-w-3xl">
        <div className="flex items-end gap-2 rounded-xl border border-slate-300 bg-white p-2 focus-within:border-blue-600">
          <textarea ref={composerRef} aria-label="Question for the portfolio assistant" rows={1} value={input}
            onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter' && !e.shiftKey && !e.nativeEvent.isComposing){e.preventDefault();e.currentTarget.form.requestSubmit();}}}
            placeholder="Ask anything…" className="min-w-0 flex-1 resize-y bg-white p-2 text-base outline-none"/>
          {isStreaming && <button type="button" onClick={() => streamController.current?.abort()} className="text-sm text-blue-700">Stop</button>}
          <button type="submit" disabled={busy || !input.trim()} aria-label="Send question" className="rounded-lg bg-blue-700 p-3 text-white disabled:opacity-40"><Send size={18}/></button>
        </div>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm text-slate-600">
          <label>Answer mode <select disabled={busy} value={useLLM?'ai':'analytics'} onChange={e=>setUseLLM(e.target.value==='ai')}>
            <option value="ai">AI explanation</option><option value="analytics">Analytics summary</option></select></label>
          <Link to="/dashboard/advisor" className="text-blue-700">Open portfolio analysis →</Link>
        </div>
      </div>
    </form>
  </section>;
};

export default ChatAdvisor;

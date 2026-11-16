import { currencyForTicker } from './portfolioLedger.js';
import { profileForAnalysis } from './investorProfile.js';

export const formatMoney = (value, currency) => value == null || !Number.isFinite(value)
  ? 'Unavailable'
  : new Intl.NumberFormat('en-IN', { style: 'currency', currency, maximumFractionDigits: 2 }).format(value);

export function quoteIssue(quote) {
  if (quote?.error_code === 'invalid_symbol') return 'No market data found; check the ticker and exchange suffix.';
  if (quote?.error_code === 'provider_unavailable') return 'Price provider unavailable; try refreshing later.';
  if (quote?.error) return 'Price unavailable; check the ticker or refresh later.';
  return null;
}

export function formatQuoteFreshness(quote) {
  if (!quote || quoteIssue(quote)) return quoteIssue(quote) || 'Price unavailable';
  const fetched = quote.retrieved_at ? new Date(quote.retrieved_at) : null;
  const fetchedLabel = fetched && Number.isFinite(fetched.getTime())
    ? `received ${new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(fetched)}`
    : 'retrieval time unavailable';
  const sessionLabel = quote.last_daily_session ? `daily data through ${quote.last_daily_session}` : 'daily session date unavailable';
  const sourceLabel = quote.price_source === 'stooq_daily_close'
    ? 'Stooq daily close'
    : quote.price_source === 'yahoo_daily_close'
      ? 'Yahoo Finance daily close'
      : 'Yahoo Finance provider quote';
  return `${sourceLabel}; ${fetchedLabel}; ${sessionLabel}. This is the latest session available from the provider; markets may be closed on weekends or holidays, and prices may be delayed.`;
}

/** One valuation contract for holdings, sidebar and analytics; never substitute cost for price. */
export function valuePortfolio(holdings = [], quotes = {}) {
  const groups = {};
  const positions = holdings.filter((h) => Number(h.quantity) !== 0).map((holding) => {
    const ticker = String(holding.ticker || '').trim().toUpperCase();
    const currency = currencyForTicker(ticker, String(holding.currency || 'USD').toUpperCase());
    const quantity = Number(holding.quantity);
    const averageCost = Number(holding.average_cost);
    const quote = quotes[ticker];
    const price = Number(quote?.price);
    let issue = null;
    if (!ticker || !Number.isFinite(quantity) || quantity <= 0) issue = 'Invalid position';
    else if (!Number.isFinite(price) || price <= 0 || quote?.error) issue = quoteIssue(quote) || 'Price unavailable';
    else if (String(quote?.currency || '').toUpperCase() !== currency) issue = 'Quote currency does not match position';
    const cost = Number.isFinite(averageCost) && averageCost >= 0 && quantity > 0 ? quantity * averageCost : null;
    const market = issue ? null : quantity * price;
    const pnl = market == null || cost == null ? null : market - cost;
    const position = { ...holding, ticker, currency, quantity, cost, market, pnl,
      pnlPct: pnl == null || cost <= 0 ? null : pnl / cost * 100, issue, quote };
    const group = groups[currency] ||= { currency, positions: [], tickers: [], marketByTicker: {}, missing: [] };
    group.positions.push(position);
    if (!group.tickers.includes(ticker)) group.tickers.push(ticker);
    if (issue) group.missing.push({ ticker, reason: issue });
    else group.marketByTicker[ticker] = (group.marketByTicker[ticker] || 0) + market;
    return position;
  });
  for (const group of Object.values(groups)) {
    group.complete = group.missing.length === 0;
    group.market = group.complete ? group.positions.reduce((sum, p) => sum + p.market, 0) : null;
    group.cost = group.positions.every((p) => p.cost != null) ? group.positions.reduce((sum, p) => sum + p.cost, 0) : null;
    group.pnl = group.market == null || group.cost == null ? null : group.market - group.cost;
    group.pnlPct = group.pnl == null || group.cost <= 0 ? null : group.pnl / group.cost * 100;
    group.weights = group.complete && group.market > 0 ? group.tickers.map((t) => group.marketByTicker[t] / group.market) : [];
  }
  return { positions, groups, currencies: Object.keys(groups).sort() };
}

export function analysisRequest(group, snapshot = null) {
  if (!group?.complete || !group.weights.length || !['INR', 'USD'].includes(group.currency)) return null;
  return {
    portfolio_id: snapshot?.portfolioId || null,
    ...profileForAnalysis(snapshot, group.currency),
    portfolio_revision: snapshot?.portfolioRevision || null,
    snapshot_as_of: snapshot?.asOf || null,
    currency: group.currency,
    benchmark: group.currency === 'INR' ? '^NSEI' : 'SPY',
    portfolio_value: group.market,
    tickers: group.tickers,
    weights: group.weights,
    start: '2023-01-01',
    include_optional_ml: true,
  };
}

export function combinedAnalysisRequest(valuation, baseCurrency, snapshot) {
  const groups = valuation.currencies.map(code => valuation.groups[code]);
  if (groups.length !== 2 || !['INR', 'USD'].includes(baseCurrency) ||
      groups.some(group => !group.complete || !['INR', 'USD'].includes(group.currency))) return null;
  const entries = groups.flatMap(group => group.tickers.map(t => [t, group.marketByTicker[t]]));
  return {
    portfolio_id: snapshot.portfolioId, portfolio_revision: snapshot.portfolioRevision,
    snapshot_as_of: snapshot.asOf, ...profileForAnalysis(snapshot, baseCurrency),
    base_currency: baseCurrency, tickers: entries.map(([ticker]) => ticker),
    position_values: entries.map(([, value]) => value), start: '2023-01-01',
    benchmark: baseCurrency === 'INR' ? '^NSEI' : 'SPY', include_optional_ml: true,
  };
}

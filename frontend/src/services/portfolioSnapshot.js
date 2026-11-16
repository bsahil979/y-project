import { derivePortfolioFromTransactions } from './portfolioLedger.js';
import { valuePortfolio, analysisRequest } from './portfolioValuation.js';

const stableJson = (value) => JSON.stringify(value, (_key, item) =>
  item && typeof item === 'object' && !Array.isArray(item)
    ? Object.fromEntries(Object.entries(item).sort(([a], [b]) => a.localeCompare(b))) : item);

// Opaque content revision, not a database sequence. Quotes and other portfolios
// do not change it. Same persisted inputs produce the same revision after reload.
function revisionFor(value) {
  let hash = 14695981039346656037n;
  for (const char of stableJson(value)) hash = BigInt.asUintN(64, (hash ^ BigInt(char.codePointAt(0))) * 1099511628211n);
  return `v1-${hash.toString(16)}`;
}

/** Canonical selected owned portfolio. Raw workspace holdings are opening positions.
 * Snake-case holding fields remain compatible with persistence and valuePortfolio.
 * asOf is snapshot construction time; quote timestamps remain on each holding.
 */
export function getPortfolioSnapshot(workspace, selectedPortfolioId = workspace.selectedPortfolioId, { quotes = {}, asOf = new Date().toISOString() } = {}) {
  const portfolio = workspace.portfolios.find((row) => row.id === selectedPortfolioId);
  const belongs = (row) => Boolean(portfolio) && row.portfolio_id === portfolio.id;
  const openingHoldings = workspace.holdings.filter(belongs);
  const transactions = workspace.transactions.filter(belongs);
  const accountIds = new Set([...openingHoldings, ...transactions].map((row) => row.account_id).filter(Boolean));
  const accounts = workspace.accounts.filter((row) => accountIds.has(row.id));
  const ledger = derivePortfolioFromTransactions(transactions, openingHoldings);
  const valuation = valuePortfolio(ledger.holdings, quotes);
  // These are the same position objects used by valuation and the UI.
  for (const holding of valuation.positions) {
    holding.current_price = holding.market == null ? null : Number(holding.quote.price);
    holding.market_value = holding.market;
  }
  const errors = portfolio || !selectedPortfolioId ? ledger.errors
    : [{ message: 'Selected portfolio does not exist.' }];
  return {
    portfolioId: portfolio?.id || null,
    portfolioRevision: revisionFor({ portfolio: portfolio || null, accounts, openingHoldings, transactions }),
    asOf, baseCurrency: portfolio?.base_currency || null,
    investorProfile: workspace.investorProfile,
    goals: (workspace.goals || []).filter(goal => !goal.portfolio_id || goal.portfolio_id === selectedPortfolioId),
    accounts, holdings: valuation.positions, openingHoldings, transactions,
    valuation, summary: ledger.summary, errors, valid: errors.length === 0,
  };
}

/** Adapter for the existing chat API, which accepts only one currency/value. */
export function advisorPortfolioContext(snapshot, currency = null) {
  if (!snapshot.valid) return { error: 'Correct the selected portfolio history before asking for portfolio analysis.' };
  if (!snapshot.holdings.length) return { error: 'Add owned holdings to the selected portfolio first.' };
  if (!currency && snapshot.valuation.currencies.length !== 1) return { error: 'The selected portfolio contains multiple currencies. Select a currency to analyze its holdings separately.' };
  const group = snapshot.valuation.groups[currency || snapshot.valuation.currencies[0]];
  if (!group) return { error: 'No holdings are available for the selected currency.' };
  if (!['INR', 'USD'].includes(group.currency)) return { error: 'Portfolio analysis currently supports INR and USD holdings.' };
  if (!group.complete || !group.weights.length) return { error: 'Current prices are required for portfolio chat. Refresh prices and try again.' };
  return {
    tickers: group.tickers,
    weights: group.weights,
    portfolio_value: group.market,
    currency: group.currency,
    request: analysisRequest(group, snapshot),
  };
}

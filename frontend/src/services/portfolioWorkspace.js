import { currencyForTicker } from './portfolioLedger.js';

/**
 * Explicit financial workspace model.
 *
 * A watchlist is not an owned portfolio. Holdings are only created when the
 * user supplies quantity and cost-basis information. This prevents analytics
 * from silently treating searched symbols as positions.
 */
export const createEmptyWorkspace = () => ({
  selectedPortfolioId: null,
  watchlistTickers: [],
  watchlists: [],
  portfolios: [],
  accounts: [],
  holdings: [],
  transactions: [],
  goals: [],
});

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
export const isUuid = (value) => uuidPattern.test(String(value || ''));

export const createId = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') return crypto.randomUUID();
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (character) => {
    const random = Math.random() * 16 | 0;
    const value = character === 'x' ? random : (random & 0x3 | 0x8);
    return value.toString(16);
  });
};

const legacyIdToUuid = (value) => {
  let hashA = 2166136261;
  let hashB = 2166136261;
  [...String(value || '')].forEach((character, index) => {
    const code = character.charCodeAt(0);
    hashA = Math.imul(hashA ^ code, 16777619);
    hashB = Math.imul(hashB ^ (code + index), 16777619);
  });
  const hex = `${(hashA >>> 0).toString(16).padStart(8, '0')}${(hashB >>> 0).toString(16).padStart(8, '0')}${((hashA ^ hashB) >>> 0).toString(16).padStart(8, '0')}${((hashB ^ 0x9e3779b9) >>> 0).toString(16).padStart(8, '0')}`.slice(0, 32);
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-4${hex.slice(13, 16)}-${((parseInt(hex.slice(16, 18), 16) & 0x3f) | 0x80).toString(16)}${hex.slice(18, 20)}-${hex.slice(20)}`;
};

const ensureId = (value) => {
  if (uuidPattern.test(String(value || ''))) return value;
  return value ? legacyIdToUuid(value) : createId();
};

export const safeParse = (value, fallback) => {
  try {
    const parsed = JSON.parse(value);
    return parsed ?? fallback;
  } catch {
    return fallback;
  }
};

export const normalizeWorkspace = (workspace) => {
  const empty = createEmptyWorkspace();
  const source = workspace || {};
  const sourceHoldings = Array.isArray(source.holdings) ? source.holdings : [];
  const sourceTransactions = Array.isArray(source.transactions) ? source.transactions : [];
  const portfolios = (Array.isArray(source.portfolios) ? source.portfolios : []).map((row) => ({ ...row, id: ensureId(row.id) }));
  const accounts = (Array.isArray(source.accounts) ? source.accounts : []).map((row) => ({ ...row, id: ensureId(row.id) }));
  // Preserve explicit foreign identities, including legacy IDs. Never merge an
  // orphan reference into a different portfolio or the unassigned account.
  for (const row of [...sourceHoldings, ...sourceTransactions]) {
    if (row.portfolio_id && !portfolios.some((p) => p.id === ensureId(row.portfolio_id))) {
      portfolios.push({ id: ensureId(row.portfolio_id), name: 'Imported Portfolio', base_currency: row.currency || 'USD' });
    }
    if (row.account_id && !accounts.some((a) => a.id === ensureId(row.account_id))) {
      accounts.push({ id: ensureId(row.account_id), name: 'Imported Account', currency: row.currency || 'USD' });
    }
  }
  let legacyPortfolioId = portfolios.length === 1 ? portfolios[0].id : null;
  if ([...sourceHoldings, ...sourceTransactions].some((row) => !row.portfolio_id) && !legacyPortfolioId) {
    legacyPortfolioId = ensureId('legacy-unassigned-portfolio');
    if (!portfolios.some((p) => p.id === legacyPortfolioId)) {
      portfolios.push({ id: legacyPortfolioId, name: 'Imported Portfolio', base_currency: 'USD' });
    }
  }
  const requestedId = source.selectedPortfolioId ? ensureId(source.selectedPortfolioId) : null;
  // Default selection is made once at the workspace boundary, never by consumers.
  const selectedPortfolioId = portfolios.some((p) => p.id === requestedId) ? requestedId
    : [...portfolios].sort((a, b) => a.id.localeCompare(b.id))[0]?.id || null;
  return {
    ...empty,
    ...source,
    selectedPortfolioId,
    watchlistTickers: Array.isArray(source.watchlistTickers)
      ? [...new Set(source.watchlistTickers.map((ticker) => String(ticker).toUpperCase().trim()).filter(Boolean))]
      : [],
    watchlists: Array.isArray(source.watchlists) ? source.watchlists.map((row) => ({ ...row, id: ensureId(row.id) })) : [],
    portfolios,
    accounts,
    holdings: sourceHoldings.map((row) => ({
      ...row,
      id: ensureId(row.id),
      currency: currencyForTicker(row.ticker, row.currency || 'USD'),
      portfolio_id: row.portfolio_id ? ensureId(row.portfolio_id) : legacyPortfolioId,
      account_id: row.account_id ? ensureId(row.account_id) : null,
    })),
    transactions: sourceTransactions.map((row) => ({
      ...row,
      id: ensureId(row.id),
      ticker: String(row.ticker || '').toUpperCase().trim(),
      currency: currencyForTicker(row.ticker, row.currency || 'USD'),
      portfolio_id: row.portfolio_id ? ensureId(row.portfolio_id) : legacyPortfolioId,
      account_id: row.account_id ? ensureId(row.account_id) : null,
    })),
    // Goals belong to the user, not a portfolio (matches the cloud schema).
    // Strip the field also from pending snapshots made by older combine code.
    goals: (Array.isArray(source.goals) ? source.goals : []).map(({portfolio_id, ...row}) => ({ ...row, id: ensureId(row.id) })),
  };
};


export function selectPortfolio(workspace, portfolioId) {
  if (!workspace.portfolios.some((portfolio) => portfolio.id === portfolioId)) {
    throw new Error('Select an existing portfolio.');
  }
  return { ...workspace, selectedPortfolioId: portfolioId };
}

/** Only the first owned record may create a portfolio; selection is explicit thereafter. */
export function ensureSelectedPortfolio(workspace, currency) {
  if (workspace.selectedPortfolioId) {
    if (!workspace.portfolios.some((p) => p.id === workspace.selectedPortfolioId)) throw new Error('Select an existing portfolio.');
    return workspace;
  }
  if (workspace.portfolios.length) throw new Error('Select a portfolio before adding positions.');
  const portfolio = { id: createId(), name: 'My Portfolio', base_currency: currency };
  return { ...workspace, portfolios: [portfolio], selectedPortfolioId: portfolio.id };
}

/** Explicitly consolidate owned portfolios while preserving account and row IDs. */
export function combineOwnedPortfolios(workspace) {
  if (!workspace.portfolios.length) return workspace;
  const target = workspace.selectedPortfolioId || workspace.portfolios[0].id;
  const move = rows => rows.map(row => ({...row, portfolio_id: target}));
  return {...workspace, selectedPortfolioId:target,
    portfolios:[{...workspace.portfolios.find(p => p.id === target), name:'My Portfolio'}],
    holdings:move(workspace.holdings), transactions:move(workspace.transactions),
    goals:(workspace.goals || []).map(({portfolio_id, ...goal}) => goal)};
}

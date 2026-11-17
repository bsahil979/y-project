import { isTrackedAsset } from './assetTracking.js';
import { supabase } from './supabaseClient';
import { normalizeInvestorProfile } from './investorProfile.js';
export {
  currencyForTicker,
  derivePortfolioFromTransactions,
  validateTransactionLedger,
} from './portfolioLedger.js';
import { currencyForTicker } from './portfolioLedger.js';

import { createEmptyWorkspace, createId, isUuid, normalizeWorkspace, safeParse } from './portfolioWorkspace.js';
export { createEmptyWorkspace, createId, ensureSelectedPortfolio, selectPortfolio } from './portfolioWorkspace.js';
export { getPortfolioSnapshot } from './portfolioSnapshot.js';
const workspaceKey = (userId) => `smart_advisor_workspace_${userId}`;
const pendingKey = (userId) => `smart_advisor_pending_${userId}`;
const legacyWatchlistKey = (userId) => `smart_portfolio_${userId}`;

const readLocalWorkspace = (userId) => {
  if (!userId) return createEmptyWorkspace();

  const saved = localStorage.getItem(workspaceKey(userId));
  if (saved) return normalizeWorkspace(safeParse(saved, createEmptyWorkspace()));

  // Backward-compatible migration: old ticker-only data becomes a watchlist,
  // never an owned holding.
  const legacy = safeParse(localStorage.getItem(legacyWatchlistKey(userId)), []);
  return normalizeWorkspace({ watchlistTickers: Array.isArray(legacy) ? legacy : [] });
};

const writeLocalWorkspace = (userId, workspace) => {
  if (!userId) return;
  localStorage.setItem(workspaceKey(userId), JSON.stringify(normalizeWorkspace(workspace)));
};

const saveQueues = new Map();

export const PortfolioDataService = {
  getInvestorProfile(userId) {
    return normalizeInvestorProfile(safeParse(localStorage.getItem(`onboarding_data_${userId}`), {}));
  },
  saveInvestorProfile(userId, value) {
    const profile = normalizeInvestorProfile(value);
    const existing = safeParse(localStorage.getItem(`onboarding_data_${userId}`), {});
    localStorage.setItem(`onboarding_data_${userId}`, JSON.stringify({ ...existing, ...value, ...profile, risk: profile.risk_preference }));
    const workspace = readLocalWorkspace(userId);
    writeLocalWorkspace(userId, { ...workspace, investorProfile: profile });
    window.dispatchEvent(new CustomEvent('investor-profile-changed', { detail: { userId, profile } }));
    return profile;
  },
  async getWorkspaceResult(userId) {
    const localWorkspace = { ...readLocalWorkspace(userId), investorProfile: this.getInvestorProfile(userId) };
    if (!isUuid(userId)) return { workspace: localWorkspace, status: 'local-only' };

    // Failed writes remain authoritative until explicitly saved successfully.
    const pending = safeParse(localStorage.getItem(pendingKey(userId)), null);
    if (pending) return { workspace: normalizeWorkspace(pending), status: 'sync-failed',
      error: new Error('Unsynced local changes retained. Save again to retry cloud synchronization.') };

    try {
      const results = await Promise.all([
        supabase.from('portfolios').select('*').eq('user_id', userId),
        supabase.from('accounts').select('*').eq('user_id', userId),
        supabase.from('holdings').select(localWorkspace.holdings.some(isTrackedAsset) ? '*,manual_value,valuation_date,valuation_source' : '*').eq('user_id', userId),
        supabase.from('transactions').select('*').eq('user_id', userId),
        supabase.from('financial_goals').select('*').eq('user_id', userId),
        supabase.from('watchlists').select('*').eq('user_id', userId),
      ]);

      // Never combine partially loaded cloud tables with local parent/child rows.
      if (results.some(({error}) => error)) {
        return {workspace:localWorkspace, status:'sync-failed', error:results.find(({error}) => error).error};
      }
      const [portfolios, accounts, holdings, transactions, goals, watchlists] = results;
      const remoteWatchlists = watchlists.error ? localWorkspace.watchlists : watchlists.data;
      const remoteWatchlistTickers = remoteWatchlists?.[0]?.tickers;
      const remoteWorkspace = normalizeWorkspace({
        ...localWorkspace,
        portfolios: portfolios.error ? localWorkspace.portfolios : portfolios.data,
        accounts: accounts.error ? localWorkspace.accounts : accounts.data,
        holdings: holdings.error ? localWorkspace.holdings : holdings.data,
        transactions: transactions.error ? localWorkspace.transactions : transactions.data,
        goals: goals.error ? localWorkspace.goals : goals.data,
        watchlists: remoteWatchlists,
        watchlistTickers: Array.isArray(remoteWatchlistTickers) ? remoteWatchlistTickers : localWorkspace.watchlistTickers,
      });
      writeLocalWorkspace(userId, remoteWorkspace);
      const hasRemoteError = results.some(({ error }) => error);
      return {
        workspace: remoteWorkspace,
        status: hasRemoteError ? 'sync-failed' : 'synced',
        error: hasRemoteError ? results.find(({ error }) => error).error : null,
      };
    } catch (error) {
      console.warn('Portfolio workspace lookup warning; using local fallback:', error);
      return { workspace: localWorkspace, status: 'sync-failed', error };
    }
  },

  async getWorkspace(userId) {
    const result = await this.getWorkspaceResult(userId);
    return result.workspace;
  },

  async saveWorkspace(userId, workspace) {
    const previous = saveQueues.get(userId) || Promise.resolve();
    const next = previous.catch(() => {}).then(() => this.persistWorkspace(userId, workspace));
    saveQueues.set(userId, next);
    try { return await next; } finally { if (saveQueues.get(userId) === next) saveQueues.delete(userId); }
  },
  async persistWorkspace(userId, workspace) {
    if (!userId) return { status: 'local-only' };
    const before = readLocalWorkspace(userId);
    const normalized = normalizeWorkspace(workspace);
    writeLocalWorkspace(userId, normalized);
    // Demo and local-fallback accounts do not exist in auth.users and therefore
    // cannot satisfy the UUID/RLS foreign keys in Supabase.
    if (!isUuid(userId)) return { status: 'local-only' };

    const pendingJson = JSON.stringify(normalized);
    localStorage.setItem(pendingKey(userId), pendingJson);
    try {
      const upsertRows = async (table, rows) => {
        const records = rows.map((row) => ({ ...row, user_id: userId }));
        // PostgREST fills missing keys with null in heterogeneous batches.
        // Keep new rows separate from fetched rows carrying default timestamps.
        const groups = new Map();
        for (const record of records) {
          const shape = Object.keys(record).sort().join(',');
          if (!groups.has(shape)) groups.set(shape, []);
          groups.get(shape).push(record);
        }
        for (const batch of groups.values()) {
          const { error } = await supabase.from(table).upsert(batch, { onConflict: 'id', defaultToNull: false });
          if (error) throw error;
        }
      };
      const deleteStaleRows = async (table, rows, remoteRows) => {
        const records = rows.map((row) => ({ ...row, user_id: userId }));
        const localIds = new Set(records.map((row) => row.id));
        const field = table === 'financial_goals' ? 'goals' : table;
        const knownIds = new Set((before[field] || []).map(row => row.id));
        const staleIds = remoteRows.filter((row) => knownIds.has(row.id) && !localIds.has(row.id)).map((row) => row.id);
        if (staleIds.length) {
          const { error } = await supabase.from(table).delete().eq('user_id', userId).in('id', staleIds);
          if (error) throw error;
        }
      };
      const tables = [
        ['portfolios', normalized.portfolios], ['accounts', normalized.accounts],
        ['holdings', normalized.holdings], ['transactions', normalized.transactions],
        ['financial_goals', normalized.goals],
        ['watchlists', normalized.watchlists.length ? normalized.watchlists : (normalized.watchlistTickers.length ? [{ id: createId(), name: 'Main Watchlist', tickers: normalized.watchlistTickers }] : [])],
      ];
      const remote = await Promise.all(tables.map(([table]) => supabase.from(table).select('id').eq('user_id', userId)));
      if (remote.some(({ error }) => error)) throw remote.find(({ error }) => error).error;
      // Upsert parents first to satisfy foreign keys, then remove children before
      // parents so deleting a portfolio cannot be blocked by dependent rows.
      for (const index of [0, 1, 2, 3, 4, 5]) {
        await upsertRows(tables[index][0], tables[index][1]);
      }
      for (const index of [2, 3, 4, 5, 1, 0]) {
        await deleteStaleRows(tables[index][0], tables[index][1], remote[index].data || []);
      }
      if (localStorage.getItem(pendingKey(userId)) === pendingJson) {
        localStorage.removeItem(pendingKey(userId));
      }
      return { status: 'synced' };
    } catch (error) {
      console.warn('Portfolio workspace sync warning; local copy retained:', error?.code || '', error?.message || 'Unknown cloud error');
      return { status: 'sync-failed', error };
    }
  },

  normalizeWorkspace,
  createEmptyWorkspace,
};

export const createHolding = ({
  portfolioId,
  accountId = null,
  ticker,
  quantity,
  averageCost,
  currency = 'USD',
}) => ({
  id: createId(),
  portfolio_id: portfolioId,
  account_id: accountId,
  ticker: String(ticker).toUpperCase().trim(),
  quantity: Number(quantity),
  average_cost: Number(averageCost),
  currency: currencyForTicker(ticker, currency),
});

export const createTransaction = ({
  portfolioId,
  accountId = null,
  ticker,
  transactionType,
  quantity = 0,
  price = 0,
  fees = 0,
  transactionDate,
  currency = 'USD',
}) => ({
  id: createId(),
  portfolio_id: portfolioId,
  account_id: accountId,
  ticker: String(ticker || '').toUpperCase().trim(),
  transaction_type: transactionType,
  quantity: Number(quantity),
  price: Number(price),
  fees: Number(fees),
  transaction_date: transactionDate || new Date().toISOString().slice(0, 10),
  created_at: new Date().toISOString(),
  currency: currencyForTicker(ticker, currency),
});

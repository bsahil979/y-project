import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { getPortfolioSnapshot, advisorPortfolioContext } from '../src/services/portfolioSnapshot.js';
import { normalizeWorkspace, selectPortfolio, ensureSelectedPortfolio, createEmptyWorkspace } from '../src/services/portfolioWorkspace.js';
import { validateTransactionLedger } from '../src/services/portfolioLedger.js';
import { analysisRequest } from '../src/services/portfolioValuation.js';

const opening = (overrides = {}) => ({ id: 'h1', portfolio_id: 'p1', account_id: 'a1', ticker: 'AAPL', currency: 'USD', quantity: 10, average_cost: 100, ...overrides });
const trade = (overrides = {}) => ({ id: 't1', portfolio_id: 'p1', account_id: 'a1', ticker: 'AAPL', currency: 'USD', transaction_type: 'buy', quantity: 5, price: 160, fees: 0, transaction_date: '2026-01-01', ...overrides });
const workspace = (overrides = {}) => ({ ...createEmptyWorkspace(), selectedPortfolioId: 'p1',
  portfolios: [{ id: 'p1', name: 'One', base_currency: 'USD' }, { id: 'p2', name: 'Two', base_currency: 'USD' }],
  accounts: [{ id: 'a1', name: 'Account one' }, { id: 'a2', name: 'Account two' }], ...overrides });
const options = { asOf: '2026-09-29T12:00:00Z', quotes: { AAPL: { price: 200, currency: 'USD' } } };
const snapshot = (overrides = {}) => getPortfolioSnapshot(workspace(overrides), 'p1', options);

describe('canonical selected portfolio snapshot', () => {
  it('records additions and removals as trades without duplicating holdings or erasing history', () => {
    const buy = trade({ quantity: 12, price: 100, transaction_date: '2026-10-12' });
    const added = snapshot({ transactions: [buy] });
    assert.equal(added.holdings[0].quantity, 12);
    assert.equal(added.openingHoldings.length, 0);
    const sell = trade({ id: 'sale', transaction_type: 'sell', quantity: 12, price: 110, transaction_date: '2026-10-13' });
    const removed = snapshot({ transactions: [buy, sell] });
    assert.equal(removed.holdings.length, 0);
    assert.equal(removed.transactions.length, 2);
    assert.equal(removed.summary.realizedPnl, 120);
    assert.equal(removed.valid, true);
    const legacy = snapshot({ holdings: [opening()], transactions: [trade({ transaction_type: 'sell', quantity: 10, price: 110 })] });
    assert.equal(legacy.holdings.length, 0);
    assert.equal(legacy.openingHoldings.length, 1);
    assert.equal(legacy.transactions.length, 1);
  });
  it('represents manual holdings with identity, cost, valuation and provenance', () => {
    const result = snapshot({ holdings: [opening()] });
    assert.equal(result.portfolioId, 'p1');
    assert.equal(result.asOf, options.asOf);
    assert.equal(result.baseCurrency, 'USD');
    assert.deepEqual(result.accounts.map((a) => a.id), ['a1']);
    const h = result.holdings[0];
    assert.equal(h.portfolio_id, 'p1');
    assert.equal(h.account_id, 'a1');
    assert.equal(h.quantity, 10);
    assert.equal(h.average_cost, 100);
    assert.equal(h.current_price, 200);
    assert.equal(h.market_value, 2000);
    assert.deepEqual(h.source, { type: 'opening', holdingIds: ['h1'], transactionIds: [] });
  });
  it('supports transaction-created holdings', () => {
    const h = snapshot({ transactions: [trade()] }).holdings[0];
    assert.equal(h.quantity, 5);
    assert.equal(h.average_cost, 160);
    assert.equal(h.source.type, 'transactions');
  });
  it('adds buys and fees to opening quantity and cost', () => {
    const h = snapshot({ holdings: [opening()], transactions: [trade({ fees: 10 })] }).holdings[0];
    assert.equal(h.quantity, 15);
    assert.equal(h.cost_basis, 1810);
    assert.equal(h.average_cost, 1810 / 15);
    assert.equal(h.source.type, 'opening_and_transactions');
  });
  it('sells opening inventory using the existing average-cost accounting', () => {
    const result = snapshot({ holdings: [opening()], transactions: [trade({ transaction_type: 'sell', quantity: 4, price: 150, fees: 2 })] });
    assert.equal(result.holdings[0].quantity, 6);
    assert.equal(result.holdings[0].cost_basis, 600);
    assert.equal(result.summary.realizedPnl, 198);
    assert.equal(result.valid, true);
  });
  it('isolates the same ticker across portfolios and honors explicit selection', () => {
    const w = workspace({ holdings: [opening(), opening({ id: 'h2', portfolio_id: 'p2', quantity: 99 })],
      transactions: [trade({ portfolio_id: 'p2' })] });
    assert.equal(getPortfolioSnapshot(w).holdings[0].quantity, 10);
    const selected = selectPortfolio(w, 'p2');
    assert.equal(getPortfolioSnapshot(selected).holdings[0].quantity, 104);
    assert.equal(w.selectedPortfolioId, 'p1');
    assert.throws(() => selectPortfolio(w, 'unknown'));
    assert.equal(getPortfolioSnapshot(w, 'unknown').holdings.length, 0);
    assert.equal(getPortfolioSnapshot(w, 'unknown').valid, false);
  });
  it('keeps same-ticker account positions separate and only sells the named account', () => {
    const result = snapshot({ holdings: [opening(), opening({ id: 'h2', account_id: 'a2', quantity: 20 })],
      transactions: [trade({ transaction_type: 'sell', quantity: 3 })] });
    assert.deepEqual(result.holdings.map((h) => [h.account_id, h.quantity]), [['a1', 7], ['a2', 20]]);
    assert.equal(new Set(result.holdings.map((h) => h.id)).size, 2);
    assert.deepEqual(result.valuation.groups.USD.tickers, ['AAPL']);
    assert.equal(result.valuation.groups.USD.market, 5400);
  });
  it('distinguishes same-ticker currencies and unassigned accounts', () => {
    const result = snapshot({ holdings: [opening(), opening({ id: 'h2', currency: 'EUR' }), opening({ id: 'h3', account_id: null })] });
    assert.equal(result.holdings.length, 3);
    assert.equal(result.holdings[1].market_value, null);
  });
  it('adding a different transaction never removes opening positions', () => {
    const result = snapshot({ holdings: [opening(), opening({ id: 'h2', ticker: 'MSFT' })], transactions: [trade({ ticker: 'NVDA' })] });
    assert.deepEqual(result.holdings.map((h) => h.ticker), ['AAPL', 'MSFT', 'NVDA']);
  });
  it('cash dividends and fees preserve every opening position', () => {
    const result = snapshot({ holdings: [opening()], transactions: [trade({ ticker: '', transaction_type: 'dividend', quantity: 0, price: 12 }), trade({ id: 't2', ticker: '', transaction_type: 'fee', quantity: 0, price: 2 })] });
    assert.equal(result.holdings[0].quantity, 10);
    assert.equal(result.summary.byCurrency.USD.dividends, 12);
    assert.equal(result.summary.byCurrency.USD.fees, 2);
  });
  it('rejects oversells without borrowing inventory across accounts or portfolios', () => {
    const holdings = [opening(), opening({ portfolio_id: 'p2', quantity: 100 }), opening({ account_id: 'a2', quantity: 100 })];
    const sell = trade({ transaction_type: 'sell', quantity: 11 });
    assert.equal(validateTransactionLedger([sell], holdings).available, 10);
    assert.equal(validateTransactionLedger([trade({ transaction_type: 'sell', quantity: 10 })], holdings), null);
    const invalid = snapshot({ holdings, transactions: [sell] });
    assert.equal(invalid.valid, false);
    assert.equal(invalid.holdings[0].quantity, 10); // invalid sell is reported, never clamped
  });
  it('detects deletion of inventory needed by later sells', () => {
    const buy = trade();
    const sell = trade({ id: 't2', transaction_type: 'sell', quantity: 12, transaction_date: '2026-01-02' });
    assert.equal(validateTransactionLedger([buy, sell], [opening()]), null);
    assert.ok(validateTransactionLedger([sell], [opening()]));
    assert.ok(validateTransactionLedger([buy, sell], []));
  });
  it('replays equal-date activity deterministically using creation time and ID', () => {
    const buy = trade({ id: 'a' });
    const sell = trade({ id: 'b', transaction_type: 'sell', quantity: 2 });
    assert.equal(snapshot({ transactions: [sell, buy] }).holdings[0].quantity, 3);
  });
  it('shares the canonical holding objects with valuation and uses those weights for analytics/advisor', () => {
    const result = snapshot({ holdings: [opening()], transactions: [trade()] });
    assert.strictEqual(result.holdings, result.valuation.positions);
    assert.strictEqual(result.holdings[0], result.valuation.groups.USD.positions[0]);
    const analysis = analysisRequest(result.valuation.groups.USD);
    const advisor = advisorPortfolioContext(result);
    assert.deepEqual(advisor.tickers, analysis.tickers);
    assert.deepEqual(advisor.weights, analysis.weights);
    assert.equal(advisor.portfolio_value, 3000);
    assert.equal(advisor.portfolio_value, analysis.portfolio_value);
  });
  it('never substitutes watchlists, cost basis or combined currencies for owned value', () => {
    assert.match(advisorPortfolioContext(snapshot({ watchlistTickers: ['MSFT'] })).error, /owned holdings/);
    const unpriced = getPortfolioSnapshot(workspace({ holdings: [opening()] }));
    assert.equal(unpriced.holdings[0].current_price, null);
    assert.match(advisorPortfolioContext(unpriced).error, /prices/);
    assert.match(advisorPortfolioContext(snapshot({ holdings: [opening(), opening({ id: 'h2', currency: 'EUR' })] })).error, /multiple currencies/);
  });
  it('advisor selects one currency without mixing values or using missing prices', () => {
    const result = getPortfolioSnapshot(workspace({ holdings: [opening(), opening({ id: 'india', ticker: 'TCS.NS', currency: 'INR', quantity: 2 })] }), 'p1', { quotes: { AAPL: { price: 200, currency: 'USD' }, 'TCS.NS': { price: 3000, currency: 'INR' } } });
    const indian = advisorPortfolioContext(result, 'INR');
    assert.deepEqual(indian.tickers, ['TCS.NS']);
    assert.equal(indian.portfolio_value, 6000);
    assert.equal(indian.request.benchmark, '^NSEI');
    assert.equal(advisorPortfolioContext(result, 'USD').portfolio_value, 2000);
    assert.match(advisorPortfolioContext(result, 'EUR').error, /No holdings/);
  });
  it('revision survives reload/quote refresh and ignores other portfolios and watchlists', () => {
    const w = workspace({ holdings: [opening()] });
    const before = getPortfolioSnapshot(w);
    assert.equal(before.portfolioRevision, getPortfolioSnapshot(JSON.parse(JSON.stringify(w)), 'p1', options).portfolioRevision);
    assert.equal(before.portfolioRevision, getPortfolioSnapshot({ ...w, watchlistTickers: ['MSFT'], transactions: [trade({ portfolio_id: 'p2' })] }).portfolioRevision);
    assert.notEqual(before.portfolioRevision, getPortfolioSnapshot({ ...w, transactions: [trade()] }).portfolioRevision);
  });
});

describe('existing workspace migration and selection', () => {
  it('maps legacy parent IDs and child references together, without losing account boundaries', () => {
    const result = normalizeWorkspace(workspace({ holdings: [opening(), opening({ id: 'h2', portfolio_id: 'p2', account_id: 'a2' })] }));
    assert.equal(result.holdings[0].portfolio_id, result.portfolios.find((p) => p.name === 'One').id);
    assert.equal(result.holdings[1].account_id, result.accounts.find((a) => a.name === 'Account two').id);
    assert.equal(result.selectedPortfolioId, result.holdings[0].portfolio_id);
    assert.deepEqual(normalizeWorkspace(result), result);
    assert.match(result.selectedPortfolioId, /^[0-9a-f-]{36}$/);
  });
  it('preserves orphan identities rather than merging them into an unrelated portfolio/account', () => {
    const result = normalizeWorkspace(workspace({ holdings: [opening({ portfolio_id: 'orphan', account_id: 'orphan-account' })] }));
    assert.equal(result.portfolios.length, 3);
    assert.equal(result.accounts.length, 3);
    assert.equal(getPortfolioSnapshot(result).holdings.length, 0);
    assert.equal(getPortfolioSnapshot(result, result.holdings[0].portfolio_id).holdings[0].quantity, 10);
  });
  it('migrates unscoped legacy records once and retains explicit selection on reload', () => {
    const result = normalizeWorkspace({ ...createEmptyWorkspace(), holdings: [opening({ portfolio_id: null, account_id: null })] });
    assert.equal(result.portfolios.length, 1);
    assert.equal(result.selectedPortfolioId, result.holdings[0].portfolio_id);
    assert.deepEqual(normalizeWorkspace(JSON.parse(JSON.stringify(result))), result);
  });
  it('does not guess an owner for unscoped records when multiple portfolios exist', () => {
    const result = normalizeWorkspace(workspace({ holdings: [opening({ portfolio_id: null })] }));
    assert.equal(result.portfolios.length, 3);
    assert.equal(getPortfolioSnapshot(result).holdings.length, 0);
  });
  it('creates/selects a portfolio only for an empty workspace', () => {
    const result = ensureSelectedPortfolio(createEmptyWorkspace(), 'INR');
    assert.equal(result.portfolios.find((p) => p.id === result.selectedPortfolioId).base_currency, 'INR');
    assert.strictEqual(ensureSelectedPortfolio(result, 'USD'), result);
    assert.throws(() => ensureSelectedPortfolio(workspace({ selectedPortfolioId: null }), 'USD'));
  });
});

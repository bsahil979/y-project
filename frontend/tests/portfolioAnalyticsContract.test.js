import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { getPortfolioSnapshot, advisorPortfolioContext } from '../src/services/portfolioSnapshot.js';
import { analysisRequest } from '../src/services/portfolioValuation.js';
import { createEmptyWorkspace } from '../src/services/portfolioWorkspace.js';

const opening = (overrides = {}) => ({
  id: 'h1',
  portfolio_id: 'p1',
  account_id: 'a1',
  ticker: 'AAPL',
  currency: 'USD',
  quantity: 10,
  average_cost: 100,
  ...overrides,
});

const workspace = (overrides = {}) => ({
  ...createEmptyWorkspace(),
  selectedPortfolioId: 'p1',
  portfolios: [
    { id: 'p1', name: 'US Portfolio', base_currency: 'USD' },
    { id: 'p2', name: 'India Portfolio', base_currency: 'INR' },
  ],
  accounts: [{ id: 'a1', name: 'Primary Account' }],
  ...overrides,
});

describe('frontend canonical portfolio analytics contract', () => {
  it('builds canonical analysis request with snapshot identity, ISO currency, and market-value weights', () => {
    const ws = workspace({
      holdings: [
        opening({ ticker: 'AAPL', quantity: 10, average_cost: 100 }),
        opening({ id: 'h2', ticker: 'MSFT', quantity: 20, average_cost: 200 }),
      ],
    });
    const snapshot = getPortfolioSnapshot(ws, 'p1', {
      quotes: {
        AAPL: { price: 200, currency: 'USD' }, // 10 * 200 = 2000
        MSFT: { price: 300, currency: 'USD' }, // 20 * 300 = 6000 -> Total = 8000
      },
    });

    const group = snapshot.valuation.groups.USD;
    const req = analysisRequest(group, snapshot);

    assert.equal(req.portfolio_id, 'p1');
    assert.equal(req.portfolio_revision, snapshot.portfolioRevision);
    assert.equal(req.snapshot_as_of, snapshot.asOf);
    assert.equal(req.currency, 'USD');
    assert.equal(req.benchmark, 'SPY');
    assert.equal(req.portfolio_value, 8000);
    assert.deepEqual(req.tickers, ['AAPL', 'MSFT']);
    assert.deepEqual(req.weights, [2000 / 8000, 6000 / 8000]);
    assert.equal(req.include_optional_ml, true);
  });

  it('supports zero cost basis without invalidating market-value weights or portfolio value', () => {
    const ws = workspace({
      holdings: [
        opening({ ticker: 'AAPL', quantity: 5, average_cost: 0 }), // transferred holding with 0 cost basis
        opening({ id: 'h2', ticker: 'MSFT', quantity: 5, average_cost: 100 }),
      ],
    });
    const snapshot = getPortfolioSnapshot(ws, 'p1', {
      quotes: {
        AAPL: { price: 100, currency: 'USD' }, // 500
        MSFT: { price: 100, currency: 'USD' }, // 500
      },
    });

    const group = snapshot.valuation.groups.USD;
    const req = analysisRequest(group, snapshot);

    assert.equal(req.portfolio_value, 1000);
    assert.deepEqual(req.weights, [0.5, 0.5]);
  });

  it('generates independent canonical requests for INR with ^NSEI and USD with SPY', () => {
    const ws = workspace({
      holdings: [
        opening({ ticker: 'AAPL', currency: 'USD', quantity: 10 }),
        opening({ id: 'h2', ticker: 'TCS.NS', currency: 'INR', quantity: 5 }),
      ],
    });
    const snapshot = getPortfolioSnapshot(ws, 'p1', {
      quotes: {
        AAPL: { price: 150, currency: 'USD' },
        'TCS.NS': { price: 3000, currency: 'INR' },
      },
    });

    const usdReq = analysisRequest(snapshot.valuation.groups.USD, snapshot);
    const inrReq = analysisRequest(snapshot.valuation.groups.INR, snapshot);

    assert.equal(usdReq.currency, 'USD');
    assert.equal(usdReq.benchmark, 'SPY');
    assert.deepEqual(usdReq.tickers, ['AAPL']);

    assert.equal(inrReq.currency, 'INR');
    assert.equal(inrReq.benchmark, '^NSEI');
    assert.deepEqual(inrReq.tickers, ['TCS.NS']);
  });

  it('produces distinct cache keys and changes portfolio_revision when positions change', () => {
    const wsA = workspace({ holdings: [opening({ quantity: 10 })] });
    const snapA = getPortfolioSnapshot(wsA, 'p1', { quotes: { AAPL: { price: 100, currency: 'USD' } } });
    const reqA = analysisRequest(snapA.valuation.groups.USD, snapA);

    const wsB = workspace({ holdings: [opening({ quantity: 20 })] });
    const snapB = getPortfolioSnapshot(wsB, 'p1', { quotes: { AAPL: { price: 100, currency: 'USD' } } });
    const reqB = analysisRequest(snapB.valuation.groups.USD, snapB);

    assert.notEqual(snapA.portfolioRevision, snapB.portfolioRevision);
    assert.notEqual(JSON.stringify(reqA), JSON.stringify(reqB));
  });

  it('advisorPortfolioContext carries the canonical analysis request for owned portfolio', () => {
    const ws = workspace({
      holdings: [
        opening({ ticker: 'AAPL', quantity: 10, average_cost: 100 }),
      ],
    });
    const snapshot = getPortfolioSnapshot(ws, 'p1', {
      quotes: { AAPL: { price: 150, currency: 'USD' } },
    });

    const context = advisorPortfolioContext(snapshot);
    assert.equal(context.currency, 'USD');
    assert.equal(context.portfolio_value, 1500);
    assert.deepEqual(context.tickers, ['AAPL']);
    assert.deepEqual(context.weights, [1]);
    assert.ok(context.request);
    assert.equal(context.request.portfolio_id, 'p1');
    assert.equal(context.request.portfolio_revision, snapshot.portfolioRevision);
    assert.equal(context.request.benchmark, 'SPY');
    assert.equal(context.request.portfolio_value, 1500);
  });
});
